"""
Enhanced Agent

Event-driven agent with full Pi-style features.
Supports: steering, follow-up, wait for idle, continue from context

P1 Enhancements:
- AgentMessage union type (str, dict, Message objects)
- Dynamic API Key resolution (getApiKey callback)
- Session ID management (session-based caching)
- Thinking budgets configuration
- Enhanced prompt() method (accepts AgentMessage[]/images)
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from koda.ai.provider import LLMProvider, Message, StreamEvent, ToolCall
from koda.ai.types import AssistantMessage, UserMessage, TextContent, ImageContent
from koda.agent.events import EventBus, Event, EventType
from koda.agent.tools import ToolRegistry, ToolContext
from koda.agent.queue import MessageQueue, DeliveryMode
from koda.agent.transform import convert_to_llm, transform_context, TransformConfig
from koda.agent.types import (
    AgentMessage,
    ThinkingBudget,
    ImageInput,
    PendingToolCall,
    ApiKeyResolver,
    SessionCache,
    normalize_agent_message,
    create_user_message,
)
from koda.mes.history import HistoryManager


class AgentState(Enum):
    """Agent state"""
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Agent configuration"""
    max_iterations: int = 10
    max_tokens: int = 128000
    temperature: float = 0.7
    enable_compaction: bool = True
    compaction_threshold: float = 0.75
    require_confirmation: bool = True
    working_dir: Path = field(default_factory=Path.cwd)

    # Tool settings
    default_tools: List[str] = field(default_factory=lambda: ["read", "write", "edit", "bash"])

    # Queue settings
    steering_mode: str = "one-at-a-time"
    follow_up_mode: str = "one-at-a-time"

    # Transform settings
    enable_transform: bool = True
    transform_on_context_full: bool = True

    # P1: Session and API Key settings
    session_id: Optional[str] = None
    api_key: Optional[str] = None

    # P1: Thinking budget configuration
    thinking_budget: Optional[ThinkingBudget] = None


@dataclass
class AgentMessage:
    """
    Wrapper for agent messages (supports steering/follow-up with full message objects)

    P1 Enhancement: Now serves as a factory for creating messages from various types.
    Supports str, dict, UserMessage, and AssistantMessage.
    """
    content: str
    role: str = "user"
    metadata: Dict[str, Any] = field(default_factory=dict)
    images: List[ImageInput] = field(default_factory=list)

    @classmethod
    def from_user_message(cls, msg: UserMessage) -> "AgentMessage":
        """Create from UserMessage"""
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        images = []
        if isinstance(msg.content, list):
            for part in msg.content:
                if hasattr(part, 'data') and hasattr(part, 'mime_type'):
                    images.append(ImageInput(data=part.data, mime_type=part.mime_type))
        return cls(content=content, role="user", images=images)

    @classmethod
    def from_assistant_message(cls, msg: AssistantMessage) -> "AgentMessage":
        """Create from AssistantMessage"""
        text_parts = [c.text for c in msg.content if hasattr(c, 'text')]
        return cls(content=" ".join(text_parts), role="assistant")

    @classmethod
    def from_string(cls, content: str, role: str = "user", **metadata) -> "AgentMessage":
        """Create from string content"""
        return cls(content=content, role=role, metadata=metadata)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create from dictionary"""
        return cls(
            content=data.get("content", ""),
            role=data.get("role", "user"),
            metadata=data.get("metadata", {}),
            images=[ImageInput(**img) if isinstance(img, dict) else img
                   for img in data.get("images", [])]
        )

    @classmethod
    def from_any(cls, message: AgentMessage) -> "AgentMessage":
        """
        Create AgentMessage from any supported type.

        Args:
            message: str, dict, UserMessage, AssistantMessage, or AgentMessage

        Returns:
            AgentMessage instance
        """
        if isinstance(message, cls):
            return message
        if isinstance(message, str):
            return cls.from_string(message)
        if isinstance(message, dict):
            return cls.from_dict(message)
        if isinstance(message, UserMessage):
            return cls.from_user_message(message)
        if isinstance(message, AssistantMessage):
            return cls.from_assistant_message(message)
        # Fallback
        return cls(content=str(message))

    def to_user_message(self) -> UserMessage:
        """Convert to UserMessage for LLM"""
        if self.images:
            content_parts = [TextContent(type="text", text=self.content)]
            for img in self.images:
                content_parts.append(ImageContent(
                    type="image",
                    data=img.data,
                    mime_type=img.mime_type
                ))
            return UserMessage(
                role="user",
                content=content_parts,
                timestamp=int(time.time() * 1000)
            )
        return UserMessage(
            role="user",
            content=self.content,
            timestamp=int(time.time() * 1000)
        )


class Agent:
    """
    Enhanced Agent with event system

    Features:
    - Event-driven architecture
    - Message queue (steering/follow-up)
    - Tool registry
    - History management with compaction
    - State management
    - waitForIdle for synchronization
    - continue_ for resuming from current context
    - Enhanced steer/follow_up with full message objects

    P1 Enhancements:
    - Dynamic API Key resolution (getApiKey callback)
    - Session ID management (session-based caching)
    - Thinking budgets configuration
    - Enhanced prompt() method (accepts AgentMessage[]/images)
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        config: Optional[AgentConfig] = None,
        get_api_key: Optional[ApiKeyResolver] = None
    ):
        """
        Args:
            llm_provider: LLM provider
            config: Agent configuration
            get_api_key: Optional callback for dynamic API key resolution
        """
        self.llm = llm_provider
        self.config = config or AgentConfig()

        # P1: Dynamic API Key resolution
        self._get_api_key = get_api_key

        # P1: Session management
        self._session_id = self.config.session_id or str(uuid.uuid4())
        self._session_cache: SessionCache = {}

        # Components
        self.events = EventBus()
        self.tools = ToolRegistry()
        self.queue = MessageQueue(
            steering_mode=self.config.steering_mode,
            follow_up_mode=self.config.follow_up_mode
        )
        self.history = HistoryManager(
            max_tokens=self.config.max_tokens,
            compaction_threshold=self.config.compaction_threshold
        )

        # State
        self.state = AgentState.IDLE
        self._current_task: Optional[asyncio.Task] = None
        self._cancelled = False
        self._idle_event: asyncio.Event = asyncio.Event()
        self._idle_event.set()  # Start as idle

        # Context for continue
        self._current_context: List[Message] = []

        # P1: Pending tool calls tracking
        self._pending_tool_calls: Dict[str, PendingToolCall] = {}

        # Register built-in tools
        self._register_builtin_tools()

    @property
    def session_id(self) -> str:
        """Get current session ID"""
        return self._session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        """Set session ID"""
        self._session_id = value

    @property
    def api_key(self) -> Optional[str]:
        """
        Get API key using dynamic resolution.

        Priority:
        1. Callback (get_api_key)
        2. Config API key
        3. Provider API key
        """
        if self._get_api_key:
            return self._get_api_key()
        if self.config.api_key:
            return self.config.api_key
        return getattr(self.llm, 'api_key', None)

    @property
    def thinking_budget(self) -> Optional[ThinkingBudget]:
        """Get thinking budget configuration"""
        return self.config.thinking_budget

    @thinking_budget.setter
    def thinking_budget(self, value: Optional[ThinkingBudget]) -> None:
        """Set thinking budget configuration"""
        self.config.thinking_budget = value

    def get_session_cache(self, key: str, default: Any = None) -> Any:
        """Get value from session cache"""
        return self._session_cache.get(key, default)

    def set_session_cache(self, key: str, value: Any) -> None:
        """Set value in session cache"""
        self._session_cache[key] = value

    def clear_session_cache(self) -> None:
        """Clear session cache"""
        self._session_cache.clear()

    async def prompt(
        self,
        messages: Union[AgentMessage, List[AgentMessage]],
        images: Optional[List[Union[str, ImageInput]]] = None,
        **kwargs
    ) -> AsyncIterator[Event]:
        """
        Enhanced prompt method accepting AgentMessage array and images.

        This is the P1 enhanced version that supports:
        - Multiple message formats (str, dict, UserMessage, AssistantMessage)
        - Image inputs
        - Thinking budgets

        Args:
            messages: Single message or list of messages
            images: Optional list of image URLs or ImageInput objects
            **kwargs: Additional options (temperature, max_tokens, etc.)

        Yields:
            Events during execution
        """
        # Normalize messages to list
        if not isinstance(messages, list):
            messages = [messages]

        # Convert to AgentMessage instances
        agent_messages = [AgentMessage.from_any(msg) for msg in messages]

        # Build content with images if provided
        if images and agent_messages:
            # Add images to the last message
            last_msg = agent_messages[-1]
            image_inputs = []
            for img in images:
                if isinstance(img, str):
                    if img.startswith(('http://', 'https://', 'data:')):
                        image_inputs.append(ImageInput.from_url(img))
                    else:
                        # Assume base64
                        image_inputs.append(ImageInput.from_base64(img))
                else:
                    image_inputs.append(img)
            last_msg.images = image_inputs

        # Process each message
        for msg in agent_messages:
            if msg.role == "user":
                user_msg = msg.to_user_message()
                self.history.add_message(Message.user(
                    msg.content,
                    images=[img.data for img in msg.images] if msg.images else None
                ))

        # Run with thinking budget if configured
        async for event in self.run("", **kwargs):
            yield event

    @property
    def is_idle(self) -> bool:
        """Check if agent is idle"""
        return self.state == AgentState.IDLE

    @property
    def is_running(self) -> bool:
        """Check if agent is running"""
        return self.state in (AgentState.RUNNING, AgentState.THINKING, AgentState.EXECUTING_TOOL)

    async def wait_for_idle(self, timeout: float = 30.0) -> bool:
        """
        Wait for agent to complete current work.

        This is useful for synchronization when you need to ensure
        the agent has finished processing before taking action.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if agent became idle, False if timeout
        """
        try:
            await asyncio.wait_for(self._idle_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def continue_(self) -> AsyncIterator[Event]:
        """
        Continue from current context without adding new messages.

        This resumes the agent from where it left off, useful for:
        - Continuing after external intervention
        - Processing queued follow-up messages
        - Resuming after steering

        Yields:
            Events during execution
        """
        if not self._current_context:
            yield Event.create(EventType.ERROR, {"message": "No context to continue from"})
            return

        # Convert current context to history format
        for msg in self._current_context:
            self.history.add_message(msg)

        # Run without adding new user message
        async for event in self.run(""):
            yield event

    async def run(self, user_input: str) -> AsyncIterator[Event]:
        """
        Run agent with user input

        Args:
            user_input: User message

        Yields:
            Events during execution
        """
        self.state = AgentState.RUNNING
        self._cancelled = False
        self._idle_event.clear()

        # Emit start event
        yield Event.create(EventType.AGENT_START, {"input": user_input})

        # Add to history
        if user_input:
            self.history.add_message(Message.user(user_input))

        try:
            # Agent loop
            for iteration in range(self.config.max_iterations):
                if self._cancelled:
                    yield Event.create(EventType.CANCELLED)
                    self.state = AgentState.CANCELLED
                    return

                # Check for steering messages
                steering_msg = self.queue.get_next()
                if steering_msg and steering_msg.mode == DeliveryMode.STEERING:
                    self.history.add_message(Message.user(steering_msg.content))
                    yield Event.create(EventType.STEERING, {"content": steering_msg.content})

                # Emit turn start
                yield Event.create(EventType.TURN_START, {"iteration": iteration})

                # Build messages
                messages = self._build_messages()

                # Apply transform if enabled
                if self.config.enable_transform:
                    messages = self._apply_transform(messages)

                # Store current context for continue
                self._current_context = list(messages)

                # Call LLM
                self.state = AgentState.THINKING
                yield Event.create(EventType.LLM_START)

                tool_calls = []
                response_text = ""

                async for event in self._call_llm(messages):
                    if event.type == "text":
                        response_text += event.data
                        yield Event.create(EventType.LLM_DELTA, {"text": event.data})
                    elif event.type == "tool_call":
                        tool_calls.append(event.data)
                    elif event.type == "stop":
                        break

                yield Event.create(EventType.LLM_END, {"text": response_text})

                # Handle tool calls
                if tool_calls:
                    self.state = AgentState.EXECUTING_TOOL

                    # Add assistant message with tool calls
                    self.history.add_message(Message.assistant(response_text, tool_calls))

                    for tool_call in tool_calls:
                        yield Event.create(EventType.TOOL_CALL_START, {"tool": tool_call.name})

                        try:
                            result = await self.tools.execute(
                                tool_call.name,
                                tool_call.arguments,
                                ToolContext(
                                    working_dir=str(self.config.working_dir),
                                    env={},
                                    timeout=60
                                )
                            )

                            # Add tool result to history
                            self.history.add_message(Message.tool(
                                tool_call_id=tool_call.id,
                                output=result,
                                name=tool_call.name
                            ))

                            yield Event.create(EventType.TOOL_RESULT, {
                                "tool": tool_call.name,
                                "result": result
                            })

                        except Exception as e:
                            error_msg = f"Error executing {tool_call.name}: {str(e)}"
                            yield Event.create(EventType.TOOL_ERROR, {
                                "tool": tool_call.name,
                                "error": error_msg
                            })

                        yield Event.create(EventType.TOOL_CALL_END, {"tool": tool_call.name})

                        # Check for steering after each tool
                        steering_msg = self.queue.peek()
                        if steering_msg and steering_msg.mode == DeliveryMode.STEERING:
                            break  # Exit tool loop to process steering
                else:
                    # Final response
                    self.history.add_message(Message.assistant(response_text))
                    yield Event.create(EventType.MESSAGE_END, {"text": response_text})

                    # Check for follow-up messages
                    follow_up = self.queue.get_next()
                    if follow_up and follow_up.mode == DeliveryMode.FOLLOW_UP:
                        self.history.add_message(Message.user(follow_up.content))
                        yield Event.create(EventType.FOLLOW_UP, {"content": follow_up.content})
                        continue  # Continue loop with follow-up

                    break

                yield Event.create(EventType.TURN_END, {"iteration": iteration})

                # Check compaction
                if self.config.enable_compaction and self.history.should_compact():
                    yield Event.create(EventType.COMPACTION_START)
                    result = self.history.compact()
                    yield Event.create(EventType.COMPACTION_END, {
                        "summary": result.summary,
                        "tokens_saved": result.tokens_saved
                    })

            else:
                # Max iterations reached
                yield Event.create(EventType.ERROR, {"message": "Max iterations reached"})
                self.state = AgentState.ERROR

        except Exception as e:
            yield Event.create(EventType.ERROR, {"message": str(e)})
            self.state = AgentState.ERROR

        finally:
            yield Event.create(EventType.AGENT_END)
            if self.state not in (AgentState.ERROR, AgentState.CANCELLED):
                self.state = AgentState.IDLE
            self._idle_event.set()

    def _build_messages(self) -> List[Message]:
        """Build message list for LLM"""
        # System message
        system_content = self._build_system_prompt()

        messages = [Message.system(system_content)]
        messages.extend(self.history.get_messages())

        return messages

    def _apply_transform(self, messages: List[Message]) -> List[Message]:
        """Apply context transformation"""
        from koda.ai.types import Context, Tool

        # Convert to Context for transform
        tools = None
        if self.tools:
            tools = [
                Tool(name=t.name, description=t.description, parameters=t.parameters)
                for t in [self.tools.get(name) for name in self.tools.list_tools()]
                if t
            ]

        context = Context(
            system_prompt=self._build_system_prompt(),
            messages=[],  # Will be populated from messages
            tools=tools
        )

        # Transform
        transform_config = TransformConfig(
            max_tokens=self.config.max_tokens,
        )

        result = transform_context(context, transform_config)

        return list(result.context.messages)

    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        lines = [
            "You are Koda, a helpful coding assistant.",
            "",
            "Available tools:",
        ]

        for name in self.tools.list_tools():
            tool = self.tools.get(name)
            lines.append(f"- {name}: {tool.description}")

        lines.extend([
            "",
            f"Working directory: {self.config.working_dir}",
            "",
            "Rules:",
            "1. Use tools to accomplish tasks",
            "2. Reference files with @filename",
            "3. Use bash for file operations when appropriate",
        ])

        # Load AGENTS.md
        agents_md = self._load_agents_md()
        if agents_md:
            lines.extend(["", "Context from AGENTS.md:", agents_md])

        return "\n".join(lines)

    def _load_agents_md(self) -> str:
        """Load AGENTS.md files"""
        content = []

        # Global
        global_path = Path.home() / ".koda" / "AGENTS.md"
        if global_path.exists():
            content.append(global_path.read_text(encoding="utf-8"))

        # Local
        local_path = self.config.working_dir / "AGENTS.md"
        if local_path.exists():
            content.append(local_path.read_text(encoding="utf-8"))

        return "\n\n".join(content)

    async def _call_llm(self, messages: List[Message]) -> AsyncIterator[StreamEvent]:
        """Call LLM provider"""
        tool_definitions = self.tools.get_definitions()

        async for event in self.llm.chat(
            messages=messages,
            tools=tool_definitions,
            temperature=self.config.temperature,
            stream=True
        ):
            yield event

    def cancel(self) -> None:
        """Cancel current execution"""
        self._cancelled = True

    def steer(self, content: Union[str, AgentMessage, UserMessage]) -> None:
        """
        Queue steering message.

        Steering messages interrupt current work and are processed
        immediately after the current tool call completes.

        Args:
            content: Message content (string, AgentMessage, or UserMessage)
        """
        if isinstance(content, AgentMessage):
            self.queue.queue_steering(content.content, content.metadata)
        elif isinstance(content, UserMessage):
            msg_content = content.content if isinstance(content.content, str) else str(content.content)
            self.queue.queue_steering(msg_content)
        else:
            self.queue.queue_steering(content)

    def follow_up(self, content: Union[str, AgentMessage, UserMessage]) -> None:
        """
        Queue follow-up message.

        Follow-up messages are processed after the agent completes
        its current task.

        Args:
            content: Message content (string, AgentMessage, or UserMessage)
        """
        if isinstance(content, AgentMessage):
            self.queue.queue_follow_up(content.content, content.metadata)
        elif isinstance(content, UserMessage):
            msg_content = content.content if isinstance(content.content, str) else str(content.content)
            self.queue.queue_follow_up(msg_content)
        else:
            self.queue.queue_follow_up(content)

    def queue_steering(self, content: str) -> None:
        """Queue steering message (backward compatible)"""
        self.queue.queue_steering(content)

    def queue_follow_up(self, content: str) -> None:
        """Queue follow-up message (backward compatible)"""
        self.queue.queue_follow_up(content)
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools"""
        from koda.coding.tools.file_tool import FileTool
        from koda.coding.tools.shell_tool import ShellTool
        from koda.coding.tools.grep_tool import GrepTool
        from koda.coding.tools.find_tool import FindTool
        from koda.coding.tools.ls_tool import LsTool
        from koda.agent.tools import Tool
        
        file_tool = FileTool()
        shell_tool = ShellTool()
        grep_tool = GrepTool()
        find_tool = FindTool()
        ls_tool = LsTool()
        
        tool_map = {
            "read": Tool(
                name="read",
                description="Read file contents",
                parameters={
                    "file_path": {"type": "string", "description": "Path to file"},
                    "offset": {"type": "integer", "default": 1},
                    "limit": {"type": "integer", "default": 100},
                },
                handler=file_tool.read,
            ),
            "write": Tool(
                name="write",
                description="Write content to file",
                parameters={
                    "file_path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                handler=file_tool.write,
                requires_confirmation=True,
            ),
            "edit": Tool(
                name="edit",
                description="Edit file by replacing text",
                parameters={
                    "file_path": {"type": "string", "description": "Path to file"},
                    "old_string": {"type": "string", "description": "Text to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                handler=file_tool.edit,
                requires_confirmation=True,
            ),
            "bash": Tool(
                name="bash",
                description="Execute bash command",
                parameters={
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "default": 60},
                },
                handler=shell_tool.execute,
                requires_confirmation=True,
            ),
            "grep": Tool(
                name="grep",
                description="Search for patterns in files",
                parameters={
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "path": {"type": "string", "description": "Directory or file"},
                },
                handler=grep_tool.search,
            ),
            "find": Tool(
                name="find",
                description="Find files by pattern",
                parameters={
                    "path": {"type": "string", "description": "Directory to search"},
                    "pattern": {"type": "string", "default": "*"},
                },
                handler=find_tool.find,
            ),
            "ls": Tool(
                name="ls",
                description="List directory contents",
                parameters={
                    "path": {"type": "string", "default": "."},
                },
                handler=ls_tool.list,
            ),
        }
        
        for name in self.config.default_tools:
            if name in tool_map:
                self.tools.register(tool_map[name])
    
    async def run(self, user_input: str) -> AsyncIterator[Event]:
        """
        Run agent with user input
        
        Args:
            user_input: User message
            
        Yields:
            Events during execution
        """
        self.state = AgentState.RUNNING
        self._cancelled = False
        
        # Emit start event
        yield Event.create(EventType.AGENT_START, {"input": user_input})
        
        # Add to history
        self.history.add_message(Message.user(user_input))
        
        try:
            # Agent loop
            for iteration in range(self.config.max_iterations):
                if self._cancelled:
                    yield Event.create(EventType.CANCELLED)
                    self.state = AgentState.CANCELLED
                    return
                
                # Emit turn start
                yield Event.create(EventType.TURN_START, {"iteration": iteration})
                
                # Build messages
                messages = self._build_messages()
                
                # Call LLM
                self.state = AgentState.THINKING
                yield Event.create(EventType.LLM_START)
                
                tool_calls = []
                response_text = ""
                
                async for event in self._call_llm(messages):
                    if event.type == "text":
                        response_text += event.data
                        yield Event.create(EventType.LLM_DELTA, {"text": event.data})
                    elif event.type == "tool_call":
                        tool_calls.append(event.data)
                    elif event.type == "stop":
                        break
                
                yield Event.create(EventType.LLM_END, {"text": response_text})
                
                # Handle tool calls
                if tool_calls:
                    self.state = AgentState.EXECUTING_TOOL
                    
                    # Add assistant message with tool calls
                    self.history.add_message(Message.assistant(response_text, tool_calls))
                    
                    for tool_call in tool_calls:
                        yield Event.create(EventType.TOOL_CALL_START, {"tool": tool_call.name})
                        
                        try:
                            result = await self.tools.execute(
                                tool_call.name,
                                tool_call.arguments,
                                ToolContext(
                                    working_dir=str(self.config.working_dir),
                                    env={},
                                    timeout=60
                                )
                            )
                            
                            # Add tool result to history
                            self.history.add_message(Message.tool(
                                tool_call_id=tool_call.id,
                                output=result,
                                name=tool_call.name
                            ))
                            
                            yield Event.create(EventType.TOOL_RESULT, {
                                "tool": tool_call.name,
                                "result": result
                            })
                            
                        except Exception as e:
                            error_msg = f"Error executing {tool_call.name}: {str(e)}"
                            yield Event.create(EventType.TOOL_ERROR, {
                                "tool": tool_call.name,
                                "error": error_msg
                            })
                        
                        yield Event.create(EventType.TOOL_CALL_END, {"tool": tool_call.name})
                else:
                    # Final response
                    self.history.add_message(Message.assistant(response_text))
                    yield Event.create(EventType.MESSAGE_END, {"text": response_text})
                    break
                
                yield Event.create(EventType.TURN_END, {"iteration": iteration})
                
                # Check compaction
                if self.config.enable_compaction and self.history.should_compact():
                    yield Event.create(EventType.COMPACTION_START)
                    result = self.history.compact()
                    yield Event.create(EventType.COMPACTION_END, {
                        "summary": result.summary,
                        "tokens_saved": result.tokens_saved
                    })
            
            else:
                # Max iterations reached
                yield Event.create(EventType.ERROR, {"message": "Max iterations reached"})
                self.state = AgentState.ERROR
                
        except Exception as e:
            yield Event.create(EventType.ERROR, {"message": str(e)})
            self.state = AgentState.ERROR
        
        finally:
            yield Event.create(EventType.AGENT_END)
            if self.state not in (AgentState.ERROR, AgentState.CANCELLED):
                self.state = AgentState.IDLE
    
    def _build_messages(self) -> List[Message]:
        """Build message list for LLM"""
        # System message
        system_content = self._build_system_prompt()
        
        messages = [Message.system(system_content)]
        messages.extend(self.history.get_messages())
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        lines = [
            "You are Koda, a helpful coding assistant.",
            "",
            "Available tools:",
        ]
        
        for name in self.tools.list_tools():
            tool = self.tools.get(name)
            lines.append(f"- {name}: {tool.description}")
        
        lines.extend([
            "",
            f"Working directory: {self.config.working_dir}",
            "",
            "Rules:",
            "1. Use tools to accomplish tasks",
            "2. Reference files with @filename",
            "3. Use bash for file operations when appropriate",
        ])
        
        # Load AGENTS.md
        agents_md = self._load_agents_md()
        if agents_md:
            lines.extend(["", "Context from AGENTS.md:", agents_md])
        
        return "\n".join(lines)
    
    def _load_agents_md(self) -> str:
        """Load AGENTS.md files"""
        content = []
        
        # Global
        global_path = Path.home() / ".koda" / "AGENTS.md"
        if global_path.exists():
            content.append(global_path.read_text(encoding="utf-8"))
        
        # Local
        local_path = self.config.working_dir / "AGENTS.md"
        if local_path.exists():
            content.append(local_path.read_text(encoding="utf-8"))
        
        return "\n\n".join(content)
    
    async def _call_llm(self, messages: List[Message]) -> AsyncIterator[StreamEvent]:
        """Call LLM provider"""
        tool_definitions = self.tools.get_definitions()
        
        async for event in self.llm.chat(
            messages=messages,
            tools=tool_definitions,
            temperature=self.config.temperature,
            stream=True
        ):
            yield event
    
    def cancel(self) -> None:
        """Cancel current execution"""
        self._cancelled = True
    
    def queue_steering(self, content: str) -> None:
        """Queue steering message"""
        self.queue.queue_steering(content)
    
    def queue_follow_up(self, content: str) -> None:
        """Queue follow-up message"""
        self.queue.queue_follow_up(content)
