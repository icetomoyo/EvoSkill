"""
AgentSession - Unified session abstraction for all agent modes
Equivalent to Pi Mono's AgentSession

Provides a consistent interface for:
- Interactive mode
- Non-interactive mode
- Headless mode
- RPC mode
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from enum import Enum
import uuid

from koda.ai.types import (
    Context,
    Message,
    AssistantMessage,
    UserMessage,
    ToolResultMessage,
    ModelInfo,
    Tool,
    StopReason,
)
from koda.ai.provider_base import BaseProvider
from koda.ai.event_stream import AssistantMessageEventStream
from koda.coding.session_manager import SessionManager, SessionEntry
from koding.coding.core.event_bus import EventBus
from koda.agent.tools import ToolRegistry, ToolContext
from koda.agent.queue import MessageQueue, DeliveryMode
from koda.agent.transform import convert_to_llm, transform_context, TransformConfig


class SessionState(Enum):
    """Agent session state"""
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    COMPACTING = "compacting"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class AgentSessionConfig:
    """AgentSession configuration"""
    # Model settings
    model: str = "claude-sonnet-4"
    provider: str = "anthropic"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Context settings
    max_context_tokens: int = 180000
    compaction_threshold: float = 0.8
    enable_compaction: bool = True

    # Tool settings
    enable_tools: bool = True
    tool_timeout: float = 600.0
    max_parallel_tools: int = 8

    # Steering/Follow-up settings
    enable_steering: bool = True
    enable_follow_up: bool = True
    steering_mode: str = "one-at-a-time"
    follow_up_mode: str = "one-at-a-time"

    # Session settings
    session_id: Optional[str] = None
    working_dir: Path = field(default_factory=Path.cwd)
    auto_save: bool = True
    save_interval: float = 30.0


@dataclass
class CompactionResult:
    """Result of context compaction"""
    success: bool
    original_tokens: int
    new_tokens: int
    tokens_saved: int
    entries_removed: int
    summary: Optional[str] = None


@dataclass
class SessionEvent:
    """Event emitted by AgentSession"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class AgentSession:
    """
    Unified Agent Session

    This is the core abstraction used by all agent modes. It provides:
    - Unified API for prompting and continuing
    - Context management with automatic compaction
    - Tool registry and execution
    - Event emission for UI updates
    - Session persistence
    - Branch/restore capabilities
    """

    def __init__(
        self,
        provider: BaseProvider,
        model: ModelInfo,
        config: Optional[AgentSessionConfig] = None
    ):
        """
        Initialize AgentSession.

        Args:
            provider: LLM provider instance
            model: Model information
            config: Session configuration
        """
        self.provider = provider
        self.model = model
        self.config = config or AgentSessionConfig()

        # Generate session ID if not provided
        self.session_id = self.config.session_id or str(uuid.uuid4())

        # Core components
        self.session_manager: Optional[SessionManager] = None
        self.event_bus = EventBus()
        self.tools = ToolRegistry()
        self.queue = MessageQueue(
            steering_mode=self.config.steering_mode,
            follow_up_mode=self.config.follow_up_mode
        )

        # State
        self.state = SessionState.IDLE
        self._context: Context = Context(messages=[])
        self._idle_event = asyncio.Event()
        self._idle_event.set()
        self._current_task: Optional[asyncio.Task] = None
        self._cancelled = False

        # Metrics
        self._total_tokens_input = 0
        self._total_tokens_output = 0
        self._total_cost = 0.0
        self._tool_calls_count = 0

    @property
    def is_idle(self) -> bool:
        """Check if session is idle"""
        return self.state == SessionState.IDLE

    @property
    def context(self) -> Context:
        """Get current context"""
        return self._context

    @property
    def messages(self) -> List[Message]:
        """Get messages from context"""
        return self._context.messages

    async def initialize(self) -> None:
        """Initialize session and load any existing state"""
        if self.session_manager:
            await self.session_manager.load_session(self.session_id)

    async def prompt(
        self,
        message: str,
        images: Optional[List[Any]] = None
    ) -> AsyncIterator[SessionEvent]:
        """
        Send a prompt and stream response events.

        Args:
            message: User message
            images: Optional list of images

        Yields:
            SessionEvent objects
        """
        self.state = SessionState.RUNNING
        self._idle_event.clear()
        self._cancelled = False

        try:
            # Build user message
            if images:
                content = [{"type": "text", "text": message}]
                for img in images:
                    content.append(img)
            else:
                content = message

            user_msg = UserMessage(
                role="user",
                content=content,
                timestamp=int(datetime.now().timestamp() * 1000)
            )

            # Add to context
            self._context.messages.append(user_msg)

            # Emit user message event
            yield SessionEvent("user_message", {"content": message})

            # Transform context if needed
            transformed = self._prepare_context()

            # Stream LLM response
            self.state = SessionState.THINKING
            yield SessionEvent("llm_start")

            try:
                stream = await self.provider.stream(self.model, transformed)

                assistant_msg = AssistantMessage(
                    role="assistant",
                    content=[],
                    api=self.provider.api_type,
                    provider=self.provider.provider_id,
                    model=self.model.id,
                    timestamp=int(datetime.now().timestamp() * 1000)
                )

                async for event in stream:
                    if self._cancelled:
                        break

                    if event.type == "text_delta":
                        yield SessionEvent("text_delta", {"text": event.delta})

                    elif event.type == "thinking_delta":
                        yield SessionEvent("thinking_delta", {"thinking": event.delta})

                    elif event.type == "toolcall_start":
                        yield SessionEvent("tool_call_start", {
                            "tool": event.tool_call.name if event.tool_call else None
                        })

                    elif event.type == "toolcall_end":
                        if event.tool_call:
                            # Execute tool
                            async for tool_event in self._execute_tool(event.tool_call):
                                yield tool_event

                    elif event.type == "done":
                        # Update assistant message
                        if event.partial:
                            assistant_msg = event.partial
                        assistant_msg.stop_reason = event.reason or StopReason.STOP

                        # Add to context
                        self._context.messages.append(assistant_msg)

                        # Update metrics
                        self._total_tokens_input += assistant_msg.usage.input
                        self._total_tokens_output += assistant_msg.usage.output
                        self._total_cost += assistant_msg.usage.cost.get("total", 0)

                        yield SessionEvent("llm_end", {
                            "stop_reason": assistant_msg.stop_reason.value,
                            "usage": {
                                "input": assistant_msg.usage.input,
                                "output": assistant_msg.usage.output,
                            }
                        })

                    elif event.type == "error":
                        yield SessionEvent("error", {"error": str(event.error)})
                        self.state = SessionState.ERROR
                        return

                # Check for follow-up messages
                if self.queue.get_pending_count() > 0:
                    follow_up = self.queue.get_next()
                    if follow_up:
                        # Recursively handle follow-up
                        async for event in self.prompt(follow_up.content):
                            yield event
                        return

                # Check for compaction
                if self._should_compact():
                    async for event in self._do_compaction():
                        yield event

            except Exception as e:
                yield SessionEvent("error", {"error": str(e)})
                self.state = SessionState.ERROR
                return

            # Complete
            self.state = SessionState.IDLE
            yield SessionEvent("complete")

        finally:
            self._idle_event.set()

            # Auto-save if enabled
            if self.config.auto_save and self.session_manager:
                await self._save_session()

    async def continue_(self) -> AsyncIterator[SessionEvent]:
        """
        Continue from current context without new user message.

        Yields:
            SessionEvent objects
        """
        if not self._context.messages:
            yield SessionEvent("error", {"error": "No context to continue from"})
            return

        # Get the last message to understand state
        last_msg = self._context.messages[-1]

        # If last message is from assistant with tool calls, execute them
        if isinstance(last_msg, AssistantMessage):
            tool_calls = [c for c in last_msg.content if c.type == "toolCall"]
            if tool_calls:
                for tool_call in tool_calls:
                    async for event in self._execute_tool(tool_call):
                        yield event

                # Continue LLM call for tool results
                async for event in self._continue_with_tool_results():
                    yield event

        # If last message is tool result, continue to LLM
        elif isinstance(last_msg, ToolResultMessage):
            async for event in self._continue_with_tool_results():
                yield event

        else:
            yield SessionEvent("error", {"error": "Cannot continue from current state"})

    async def _continue_with_tool_results(self) -> AsyncIterator[SessionEvent]:
        """Continue after tool results"""
        self.state = SessionState.THINKING
        yield SessionEvent("llm_start")

        transformed = self._prepare_context()
        stream = await self.provider.stream(self.model, transformed)

        # Similar to prompt() but without adding user message
        # ... (streaming logic similar to prompt())

        yield SessionEvent("llm_end")

    async def wait_for_idle(self, timeout: float = 30.0) -> bool:
        """
        Wait for session to become idle.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            True if became idle, False if timeout
        """
        try:
            await asyncio.wait_for(self._idle_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def compact(self) -> CompactionResult:
        """
        Trigger context compaction.

        Returns:
            CompactionResult with details
        """
        self.state = SessionState.COMPACTING

        original_tokens = self._estimate_tokens()
        entries_count = len(self._context.messages)

        try:
            # Use transform to compact
            config = TransformConfig(
                max_tokens=int(self.config.max_context_tokens * 0.7),
            )
            result = transform_context(self._context, config)

            self._context = result.context

            return CompactionResult(
                success=True,
                original_tokens=original_tokens,
                new_tokens=result.new_tokens,
                tokens_saved=result.tokens_saved,
                entries_removed=entries_count - len(self._context.messages),
            )

        except Exception as e:
            return CompactionResult(
                success=False,
                original_tokens=original_tokens,
                new_tokens=original_tokens,
                tokens_saved=0,
                entries_removed=0,
                summary=f"Compaction failed: {str(e)}"
            )

        finally:
            self.state = SessionState.IDLE

    def branch(self, entry_id: Optional[str] = None) -> "AgentSession":
        """
        Create a branch from current or specified entry.

        Args:
            entry_id: Entry to branch from (None = current state)

        Returns:
            New AgentSession with branched context
        """
        # Create new session
        new_config = AgentSessionConfig(
            model=self.config.model,
            provider=self.config.provider,
            session_id=str(uuid.uuid4()),
            working_dir=self.config.working_dir,
        )

        new_session = AgentSession(self.provider, self.model, new_config)

        # Copy context
        if entry_id:
            # Find entry and copy up to it
            new_session._context = self._context  # Simplified
        else:
            new_session._context = Context(
                system_prompt=self._context.system_prompt,
                messages=list(self._context.messages),
                tools=self._context.tools
            )

        return new_session

    def steer(self, content: str) -> None:
        """Queue steering message"""
        self.queue.queue_steering(content)

    def follow_up(self, content: str) -> None:
        """Queue follow-up message"""
        self.queue.queue_follow_up(content)

    def cancel(self) -> None:
        """Cancel current operation"""
        self._cancelled = True

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "messages_count": len(self._context.messages),
            "total_tokens_input": self._total_tokens_input,
            "total_tokens_output": self._total_tokens_output,
            "total_cost": self._total_cost,
            "tool_calls_count": self._tool_calls_count,
        }

    def _prepare_context(self) -> Context:
        """Prepare context for LLM call"""
        if not self.config.enable_tools:
            return self._context

        # Add tools to context
        tools = []
        for name in self.tools.list_tools():
            tool = self.tools.get(name)
            if tool:
                tools.append(Tool(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters
                ))

        context = Context(
            system_prompt=self._context.system_prompt,
            messages=list(self._context.messages),
            tools=tools if tools else None
        )

        # Transform if needed
        if self._estimate_tokens() > self.config.max_context_tokens * self.config.compaction_threshold:
            return convert_to_llm(
                context,
                self.config.provider,
                self.config.model,
                self.config.max_context_tokens
            )

        return context

    async def _execute_tool(self, tool_call) -> AsyncIterator[SessionEvent]:
        """Execute a tool call"""
        self.state = SessionState.EXECUTING_TOOL
        self._tool_calls_count += 1

        tool_name = tool_call.name
        yield SessionEvent("tool_execution_start", {"tool": tool_name})

        try:
            result = await self.tools.execute(
                tool_name,
                tool_call.arguments,
                ToolContext(
                    working_dir=str(self.config.working_dir),
                    env={},
                    timeout=self.config.tool_timeout
                )
            )

            # Add result to context
            tool_result = ToolResultMessage(
                role="toolResult",
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=[{"type": "text", "text": str(result)}],
                timestamp=int(datetime.now().timestamp() * 1000)
            )
            self._context.messages.append(tool_result)

            yield SessionEvent("tool_result", {
                "tool": tool_name,
                "result": str(result)[:1000]  # Truncate for event
            })

        except Exception as e:
            error_result = ToolResultMessage(
                role="toolResult",
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=[{"type": "text", "text": f"Error: {str(e)}"}],
                is_error=True,
                timestamp=int(datetime.now().timestamp() * 1000)
            )
            self._context.messages.append(error_result)

            yield SessionEvent("tool_error", {
                "tool": tool_name,
                "error": str(e)
            })

    def _should_compact(self) -> bool:
        """Check if compaction is needed"""
        if not self.config.enable_compaction:
            return False

        tokens = self._estimate_tokens()
        threshold = self.config.max_context_tokens * self.config.compaction_threshold
        return tokens > threshold

    async def _do_compaction(self) -> AsyncIterator[SessionEvent]:
        """Perform compaction"""
        yield SessionEvent("compaction_start")

        result = await self.compact()

        yield SessionEvent("compaction_end", {
            "tokens_saved": result.tokens_saved,
            "entries_removed": result.entries_removed,
        })

    def _estimate_tokens(self) -> int:
        """Estimate current token count"""
        total = 0

        if self._context.system_prompt:
            total += len(self._context.system_prompt) // 4

        for msg in self._context.messages:
            if isinstance(msg, UserMessage):
                content = msg.content
                if isinstance(content, str):
                    total += len(content) // 4
            elif isinstance(msg, AssistantMessage):
                for item in msg.content:
                    if hasattr(item, 'text'):
                        total += len(item.text) // 4
                    elif hasattr(item, 'thinking'):
                        total += len(item.thinking) // 4
            elif isinstance(msg, ToolResultMessage):
                for item in msg.content:
                    if hasattr(item, 'text'):
                        total += len(item.text) // 4

        return total

    async def _save_session(self) -> None:
        """Save session state"""
        if self.session_manager:
            # Save context and state
            pass  # Implementation depends on SessionManager
