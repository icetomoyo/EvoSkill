"""
Agent Loop - Enhanced with Pi Mono parity
Supports: retry, parallel tools, max iterations, AbortSignal, steering, follow-up, continue

P2 Enhancements:
- waitForIdle() method with pending tool call awareness
- Pending tool calls tracking
"""
import asyncio
from typing import Optional, Dict, List, Callable, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import time

from koda.ai.types import (
    Context,
    AssistantMessage,
    UserMessage,
    ToolCall,
    ToolResultMessage,
    TextContent,
    StopReason,
    ModelInfo,
    AgentEvent,
    AgentEventType,
)
from koda.ai.provider_base import BaseProvider
from koda.ai.event_stream import AssistantMessageEventStream
from koda.agent.queue import MessageQueue, DeliveryMode, QueuedMessage
from koda.agent.types import PendingToolCall


@dataclass
class AgentLoopConfig:
    """Agent Loop configuration"""
    max_iterations: int = 50
    max_tool_calls_per_turn: int = 32
    retry_attempts: int = 3
    retry_delay_base: float = 1.0  # Exponential backoff base
    tool_timeout: float = 600.0  # 10 minutes
    enable_parallel_tools: bool = True
    max_parallel_tools: int = 8
    enable_steering: bool = True  # Check for steering messages
    enable_follow_up: bool = True  # Check for follow-up messages after completion


class AgentTool:
    """Agent tool wrapper"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        execute: Callable[..., Any],
        label: Optional[str] = None
    ):
        self.name = name
        self.label = label or name
        self.description = description
        self.parameters = parameters
        self.execute = execute


class AgentLoop:
    """
    Enhanced Agent Loop

    Equivalent to Pi Mono's agent-loop.ts

    Features:
    - Max iteration protection
    - Tool error retry with exponential backoff
    - Parallel tool execution
    - Graceful error handling
    - AbortSignal support
    - Steering message handling (interrupt tool execution)
    - Follow-up message handling (continue after completion)
    - agentLoopContinue (resume from current context)

    P2 Enhancements:
    - waitForIdle() with pending tool call awareness
    - Pending tool calls tracking for status monitoring
    """

    def __init__(
        self,
        provider: BaseProvider,
        model: ModelInfo,
        tools: List[AgentTool],
        config: Optional[AgentLoopConfig] = None,
        message_queue: Optional[MessageQueue] = None
    ):
        self.provider = provider
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.config = config or AgentLoopConfig()
        self.queue = message_queue or MessageQueue()
        self.iteration_count = 0
        self.tool_call_count = 0
        self._abort_signal: Optional[Any] = None
        self._is_running: bool = False
        self._idle_event: asyncio.Event = asyncio.Event()
        self._idle_event.set()  # Start as idle

        # P2: Pending tool calls tracking
        self._pending_tool_calls: Dict[str, PendingToolCall] = {}
        self._tool_call_completed: asyncio.Event = asyncio.Event()
        self._tool_call_completed.set()  # Start as no pending calls

    @property
    def is_idle(self) -> bool:
        """Check if agent is idle (not running)"""
        return self._idle_event.is_set()

    @property
    def has_pending_tools(self) -> bool:
        """Check if there are pending tool calls"""
        return len(self._pending_tool_calls) > 0

    @property
    def pending_tool_count(self) -> int:
        """Get number of pending tool calls"""
        return len(self._pending_tool_calls)

    @property
    def running_tool_count(self) -> int:
        """Get number of currently running tool calls"""
        return sum(1 for tc in self._pending_tool_calls.values() if tc.is_running)

    def get_pending_tool_calls(self) -> List[PendingToolCall]:
        """Get list of all pending tool calls"""
        return list(self._pending_tool_calls.values())

    def get_running_tool_calls(self) -> List[PendingToolCall]:
        """Get list of currently running tool calls"""
        return [tc for tc in self._pending_tool_calls.values() if tc.is_running]

    def get_failed_tool_calls(self) -> List[PendingToolCall]:
        """Get list of failed tool calls"""
        return [tc for tc in self._pending_tool_calls.values() if tc.is_failed]

    async def wait_for_idle(self, timeout: float = 30.0) -> bool:
        """
        Wait for agent to become idle.

        P2 Enhancement: Also waits for all pending tool calls to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if agent became idle, False if timeout
        """
        try:
            # Wait for main idle event
            await asyncio.wait_for(self._idle_event.wait(), timeout=timeout)

            # Also wait for any pending tool calls
            if self.has_pending_tools:
                remaining_timeout = timeout
                start_time = time.time()

                while self.has_pending_tools and remaining_timeout > 0:
                    try:
                        await asyncio.wait_for(
                            self._tool_call_completed.wait(),
                            timeout=remaining_timeout
                        )
                        elapsed = time.time() - start_time
                        remaining_timeout = timeout - elapsed
                    except asyncio.TimeoutError:
                        return False

            return True
        except asyncio.TimeoutError:
            return False

    async def wait_for_tools_complete(self, timeout: float = 60.0) -> bool:
        """
        Wait specifically for all pending tool calls to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all tools completed, False if timeout
        """
        if not self.has_pending_tools:
            return True

        try:
            await asyncio.wait_for(self._tool_call_completed.wait(), timeout=timeout)
            return not self.has_pending_tools
        except asyncio.TimeoutError:
            return False

    def _track_tool_call_start(self, tool_call: ToolCall) -> PendingToolCall:
        """Track the start of a tool call"""
        pending = PendingToolCall(
            id=tool_call.id,
            name=tool_call.name,
            arguments=tool_call.arguments,
            status="running",
            created_at=time.time()
        )
        pending.mark_running()
        self._pending_tool_calls[tool_call.id] = pending
        self._tool_call_completed.clear()
        return pending

    def _track_tool_call_complete(
        self,
        tool_call_id: str,
        result: Any = None,
        error: Optional[str] = None
    ) -> Optional[PendingToolCall]:
        """Track the completion of a tool call"""
        pending = self._pending_tool_calls.get(tool_call_id)
        if pending:
            if error:
                pending.mark_failed(error)
            else:
                pending.mark_completed(result)

            # Remove completed calls after tracking
            del self._pending_tool_calls[tool_call_id]

            # Check if all tools are done
            if not self.has_pending_tools:
                self._tool_call_completed.set()

        return pending

    async def run(
        self,
        context: Context,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
        signal: Optional[Any] = None
    ) -> AssistantMessage:
        """
        Run Agent Loop until completion

        Args:
            context: Conversation context
            on_event: Event callback
            signal: AbortSignal for cancellation

        Returns:
            Final assistant message
        """
        self._abort_signal = signal
        self.iteration_count = 0
        self.tool_call_count = 0
        self._is_running = True
        self._idle_event.clear()

        try:
            current_context = Context(
                system_prompt=context.system_prompt,
                messages=list(context.messages),
                tools=context.tools
            )

            while self.iteration_count < self.config.max_iterations:
                # Check for abort
                if signal and getattr(signal, 'aborted', False):
                    return self._create_error_message("Operation aborted")

                self.iteration_count += 1

                if on_event:
                    on_event(AgentEvent(
                        type=AgentEventType.TURN_START,
                        data={"iteration": self.iteration_count},
                        timestamp=int(time.time() * 1000)
                    ))

                # Get assistant response
                try:
                    response = await self.provider.complete(
                        self.model,
                        current_context,
                    )
                except Exception as e:
                    error_msg = self._create_error_message(f"Provider error: {str(e)}")
                    if on_event:
                        on_event(AgentEvent(
                            type=AgentEventType.ERROR,
                            data={"error": str(e)},
                            timestamp=int(time.time() * 1000)
                        ))
                    return error_msg

                # Check for abort after response
                if signal and getattr(signal, 'aborted', False):
                    return self._create_error_message("Operation aborted")

                # Check if done
                if response.stop_reason == StopReason.STOP:
                    result = await self._handle_completion(
                        response, current_context, on_event
                    )
                    if result:
                        return result
                    return response

                if response.stop_reason == StopReason.LENGTH:
                    # Max tokens reached, return what we have
                    if on_event:
                        on_event(AgentEvent(
                            type=AgentEventType.AGENT_END,
                            data={"iterations": self.iteration_count, "reason": "max_tokens"},
                            timestamp=int(time.time() * 1000)
                        ))
                    return response

                # Handle tool calls
                tool_calls = [
                    content for content in response.content
                    if content.type == "toolCall"
                ]

                if not tool_calls:
                    # No tool calls, we're done - check for follow-up
                    result = await self._handle_completion(
                        response, current_context, on_event
                    )
                    if result:
                        return result
                    return response

                # Check for steering messages before executing tools
                if self.config.enable_steering:
                    steering_msg = self._check_steering()
                    if steering_msg:
                        # Add assistant response and steering message
                        current_context.messages.append(response)
                        current_context.messages.append(UserMessage(
                            role="user",
                            content=steering_msg.content,
                            timestamp=int(time.time() * 1000)
                        ))

                        if on_event:
                            on_event(AgentEvent(
                                type=AgentEventType.TURN_END,
                                data={"iteration": self.iteration_count, "steered": True},
                                timestamp=int(time.time() * 1000)
                            ))
                        continue  # Skip tool execution, continue to next iteration

                # Execute tool calls
                if len(tool_calls) == 1 or not self.config.enable_parallel_tools:
                    # Sequential execution
                    results = []
                    for tool_call in tool_calls:
                        result = await self._execute_tool_with_retry(
                            tool_call,
                            signal
                        )
                        results.append(result)

                        # Check steering after each tool
                        if self.config.enable_steering:
                            steering_msg = self._check_steering()
                            if steering_msg:
                                # Skip remaining tools
                                current_context.messages.append(response)
                                for r in results:
                                    current_context.messages.append(r)
                                current_context.messages.append(UserMessage(
                                    role="user",
                                    content=steering_msg.content,
                                    timestamp=int(time.time() * 1000)
                                ))
                                break

                        if on_event:
                            on_event(AgentEvent(
                                type=AgentEventType.TOOL_RESULT,
                                data={
                                    "tool": tool_call.name,
                                    "result": result.content[0].text if result.content else ""
                                },
                                timestamp=int(time.time() * 1000)
                            ))
                    else:
                        # No steering, continue normally
                        current_context.messages.append(response)
                        for result in results:
                            current_context.messages.append(result)
                else:
                    # Parallel execution
                    results = await self._execute_tools_parallel(
                        tool_calls,
                        signal
                    )

                    if on_event:
                        for result in results:
                            on_event(AgentEvent(
                                type=AgentEventType.TOOL_RESULT,
                                data={
                                    "tool": result.tool_name,
                                    "result": result.content[0].text if result.content else ""
                                },
                                timestamp=int(time.time() * 1000)
                            ))

                    # Add assistant message and tool results to context
                    current_context.messages.append(response)
                    for result in results:
                        current_context.messages.append(result)

                if on_event:
                    on_event(AgentEvent(
                        type=AgentEventType.TURN_END,
                        data={"iteration": self.iteration_count},
                        timestamp=int(time.time() * 1000)
                    ))

            # Max iterations reached
            return self._create_error_message(f"Max iterations ({self.config.max_iterations}) reached")

        finally:
            self._is_running = False
            self._idle_event.set()

    async def run_continue(
        self,
        context: Context,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
        signal: Optional[Any] = None
    ) -> AssistantMessage:
        """
        Continue from existing context without adding new messages.

        This is equivalent to Pi Mono's agentLoopContinue().
        It resumes the agent loop from the current context state.

        Args:
            context: Existing conversation context
            on_event: Event callback
            signal: AbortSignal for cancellation

        Returns:
            Final assistant message
        """
        # Don't reset iteration count - continue from where we were
        self._abort_signal = signal
        self._is_running = True
        self._idle_event.clear()

        try:
            current_context = Context(
                system_prompt=context.system_prompt,
                messages=list(context.messages),  # Use existing messages
                tools=context.tools
            )

            while self.iteration_count < self.config.max_iterations:
                # Check for abort
                if signal and getattr(signal, 'aborted', False):
                    return self._create_error_message("Operation aborted")

                self.iteration_count += 1

                if on_event:
                    on_event(AgentEvent(
                        type=AgentEventType.TURN_START,
                        data={"iteration": self.iteration_count, "continued": True},
                        timestamp=int(time.time() * 1000)
                    ))

                # Get assistant response
                try:
                    response = await self.provider.complete(
                        self.model,
                        current_context,
                    )
                except Exception as e:
                    return self._create_error_message(f"Provider error: {str(e)}")

                # Check for steering
                if self.config.enable_steering:
                    steering_msg = self._check_steering()
                    if steering_msg:
                        current_context.messages.append(UserMessage(
                            role="user",
                            content=steering_msg.content,
                            timestamp=int(time.time() * 1000)
                        ))
                        continue

                # Check completion
                if response.stop_reason in (StopReason.STOP, StopReason.LENGTH):
                    result = await self._handle_completion(
                        response, current_context, on_event
                    )
                    if result:
                        return result
                    return response

                # Handle tool calls
                tool_calls = [c for c in response.content if c.type == "toolCall"]
                if not tool_calls:
                    result = await self._handle_completion(
                        response, current_context, on_event
                    )
                    if result:
                        return result
                    return response

                # Execute tools and continue
                results = await self._execute_tools_parallel(tool_calls, signal)
                current_context.messages.append(response)
                for result in results:
                    current_context.messages.append(result)

            return self._create_error_message(f"Max iterations ({self.config.max_iterations}) reached")

        finally:
            self._is_running = False
            self._idle_event.set()

    def _check_steering(self) -> Optional[QueuedMessage]:
        """Check for steering messages in queue"""
        if self.queue.get_pending_steering() > 0:
            msg = self.queue.get_next()
            if msg and msg.mode == DeliveryMode.STEERING:
                return msg
        return None

    async def _handle_completion(
        self,
        response: AssistantMessage,
        context: Context,
        on_event: Optional[Callable[[AgentEvent], None]]
    ) -> Optional[AssistantMessage]:
        """
        Handle completion - check for follow-up messages.

        Returns:
            New response if follow-up was processed, None otherwise
        """
        if not self.config.enable_follow_up:
            if on_event:
                on_event(AgentEvent(
                    type=AgentEventType.AGENT_END,
                    data={"iterations": self.iteration_count},
                    timestamp=int(time.time() * 1000)
                ))
            return None

        # Check for follow-up messages
        follow_up = self.queue.get_next()
        if follow_up and follow_up.mode == DeliveryMode.FOLLOW_UP:
            # Add follow-up and continue
            context.messages.append(response)
            context.messages.append(UserMessage(
                role="user",
                content=follow_up.content,
                timestamp=int(time.time() * 1000)
            ))

            if on_event:
                on_event(AgentEvent(
                    type=AgentEventType.TURN_END,
                    data={"iteration": self.iteration_count, "follow_up": True},
                    timestamp=int(time.time() * 1000)
                ))
            return None  # Will continue in main loop

        if on_event:
            on_event(AgentEvent(
                type=AgentEventType.AGENT_END,
                data={"iterations": self.iteration_count},
                timestamp=int(time.time() * 1000)
            ))
        return None

    async def _execute_tool_with_retry(
        self,
        tool_call: ToolCall,
        signal: Optional[Any]
    ) -> ToolResultMessage:
        """Execute tool with retry logic and P2 tracking"""
        tool_name = tool_call.name
        tool = self.tools.get(tool_name)

        # P2: Track tool call start
        pending = self._track_tool_call_start(tool_call)

        if not tool:
            error_msg = f"Error: Tool '{tool_name}' not found"
            self._track_tool_call_complete(tool_call.id, error=error_msg)
            return ToolResultMessage(
                role="toolResult",
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=[TextContent(type="text", text=error_msg)],
                is_error=True,
                timestamp=int(time.time() * 1000)
            )

        for attempt in range(self.config.retry_attempts):
            # Check abort
            if signal and getattr(signal, 'aborted', False):
                error_msg = "Error: Operation aborted"
                self._track_tool_call_complete(tool_call.id, error=error_msg)
                return ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=[TextContent(type="text", text=error_msg)],
                    is_error=True,
                    timestamp=int(time.time() * 1000)
                )

            try:
                # Execute tool with timeout
                result = await asyncio.wait_for(
                    self._execute_tool(tool, tool_call.arguments),
                    timeout=self.config.tool_timeout
                )

                # P2: Track completion
                self._track_tool_call_complete(tool_call.id, result=result)

                return ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=[TextContent(type="text", text=str(result))],
                    is_error=False,
                    timestamp=int(time.time() * 1000)
                )

            except asyncio.TimeoutError:
                error_text = f"Error: Tool execution timed out after {self.config.tool_timeout}s"
                if attempt < self.config.retry_attempts - 1:
                    pending.increment_retry()
                    delay = self.config.retry_delay_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

                # P2: Track failure
                self._track_tool_call_complete(tool_call.id, error=error_text)

                return ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=[TextContent(type="text", text=error_text)],
                    is_error=True,
                    timestamp=int(time.time() * 1000)
                )

            except Exception as e:
                error_text = f"Error: {str(e)}"
                if attempt < self.config.retry_attempts - 1:
                    pending.increment_retry()
                    delay = self.config.retry_delay_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue

                # P2: Track failure
                self._track_tool_call_complete(tool_call.id, error=error_text)

                return ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=[TextContent(type="text", text=error_text)],
                    is_error=True,
                    timestamp=int(time.time() * 1000)
                )

        # Should not reach here
        error_msg = "Error: Max retries exceeded"
        self._track_tool_call_complete(tool_call.id, error=error_msg)
        return ToolResultMessage(
            role="toolResult",
            tool_call_id=tool_call.id,
            tool_name=tool_name,
            content=[TextContent(type="text", text=error_msg)],
            is_error=True,
            timestamp=int(time.time() * 1000)
        )

    async def _execute_tools_parallel(
        self,
        tool_calls: List[ToolCall],
        signal: Optional[Any]
    ) -> List[ToolResultMessage]:
        """Execute tools in parallel with concurrency limit"""
        # Limit parallel execution
        semaphore = asyncio.Semaphore(self.config.max_parallel_tools)

        async def execute_with_limit(tool_call: ToolCall) -> ToolResultMessage:
            async with semaphore:
                return await self._execute_tool_with_retry(tool_call, signal)

        tasks = [execute_with_limit(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_calls[i].id,
                    tool_name=tool_calls[i].name,
                    content=[TextContent(type="text", text=f"Error: {str(result)}")],
                    is_error=True,
                    timestamp=int(time.time() * 1000)
                ))
            else:
                final_results.append(result)

        return final_results

    async def _execute_tool(self, tool: AgentTool, arguments: Dict[str, Any]) -> Any:
        """Execute a single tool"""
        self.tool_call_count += 1

        # Check if execute is async
        if asyncio.iscoroutinefunction(tool.execute):
            return await tool.execute(**arguments)
        else:
            # Run sync function in thread
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: tool.execute(**arguments))

    def _create_error_message(self, error_text: str) -> AssistantMessage:
        """Create error assistant message"""
        return AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text=f"Error: {error_text}")],
            api=self.provider.api_type,
            provider=self.provider.provider_id,
            model=self.model.id,
            stop_reason=StopReason.ERROR,
            error_message=error_text,
            timestamp=int(time.time() * 1000)
        )


# Convenience function for agentLoopContinue
async def agent_loop_continue(
    loop: AgentLoop,
    context: Context,
    on_event: Optional[Callable[[AgentEvent], None]] = None,
    signal: Optional[Any] = None
) -> AssistantMessage:
    """
    Continue agent loop from existing context.

    This is a convenience function matching Pi Mono's agentLoopContinue().

    Args:
        loop: AgentLoop instance
        context: Existing context
        on_event: Event callback
        signal: AbortSignal

    Returns:
        Final assistant message
    """
    return await loop.run_continue(context, on_event, signal)
