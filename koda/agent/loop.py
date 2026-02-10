"""
Agent Loop - Enhanced with Pi Mono parity
Supports: retry, parallel tools, max iterations, AbortSignal
"""
import asyncio
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum
import time

from koda.ai.types import (
    Context,
    AssistantMessage,
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
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        model: ModelInfo,
        tools: List[AgentTool],
        config: Optional[AgentLoopConfig] = None
    ):
        self.provider = provider
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.config = config or AgentLoopConfig()
        self.iteration_count = 0
        self.tool_call_count = 0
        self._abort_signal: Optional[Any] = None
    
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
                    signal=signal
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
                if on_event:
                    on_event(AgentEvent(
                        type=AgentEventType.AGENT_END,
                        data={"iterations": self.iteration_count},
                        timestamp=int(time.time() * 1000)
                    ))
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
                # No tool calls, we're done
                if on_event:
                    on_event(AgentEvent(
                        type=AgentEventType.AGENT_END,
                        data={"iterations": self.iteration_count},
                        timestamp=int(time.time() * 1000)
                    ))
                return response
            
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
    
    async def _execute_tool_with_retry(
        self,
        tool_call: ToolCall,
        signal: Optional[Any]
    ) -> ToolResultMessage:
        """Execute tool with retry logic"""
        tool_name = tool_call.name
        tool = self.tools.get(tool_name)
        
        if not tool:
            return ToolResultMessage(
                role="toolResult",
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=[TextContent(type="text", text=f"Error: Tool '{tool_name}' not found")],
                is_error=True,
                timestamp=int(time.time() * 1000)
            )
        
        for attempt in range(self.config.retry_attempts):
            # Check abort
            if signal and getattr(signal, 'aborted', False):
                return ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=[TextContent(type="text", text="Error: Operation aborted")],
                    is_error=True,
                    timestamp=int(time.time() * 1000)
                )
            
            try:
                # Execute tool with timeout
                result = await asyncio.wait_for(
                    self._execute_tool(tool, tool_call.arguments),
                    timeout=self.config.tool_timeout
                )
                
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
                    delay = self.config.retry_delay_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                
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
                    delay = self.config.retry_delay_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                
                return ToolResultMessage(
                    role="toolResult",
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=[TextContent(type="text", text=error_text)],
                    is_error=True,
                    timestamp=int(time.time() * 1000)
                )
        
        # Should not reach here
        return ToolResultMessage(
            role="toolResult",
            tool_call_id=tool_call.id,
            tool_name=tool_name,
            content=[TextContent(type="text", text="Error: Max retries exceeded")],
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
