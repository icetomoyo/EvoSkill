"""
Extension Types - Complete extension API definitions
Equivalent to Pi Mono's extension types

Provides:
- 30+ event types for extension hooks
- Extension interface definition
- Extension API for interacting with Koda
- Configuration and manifest types
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from koda.coding.core.agent_session import AgentSession


class ExtensionEventType(Enum):
    """All extension event types - 30+ event types"""

    # Lifecycle events
    EXTENSION_LOADED = "extension_loaded"
    EXTENSION_ACTIVATED = "extension_activated"
    EXTENSION_DEACTIVATED = "extension_deactivated"
    EXTENSION_ERROR = "extension_error"
    EXTENSION_CONFIGURED = "extension_configured"

    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_PAUSE = "session_pause"
    SESSION_RESUME = "session_resume"
    SESSION_SAVE = "session_save"
    SESSION_LOAD = "session_load"
    SESSION_CLEAR = "session_clear"
    SESSION_ARCHIVE = "session_archive"

    # Message events
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    SYSTEM_MESSAGE = "system_message"
    MESSAGE_EDIT = "message_edit"
    MESSAGE_DELETE = "message_delete"
    MESSAGE_APPEND = "message_append"

    # LLM events
    LLM_START = "llm_start"
    LLM_STREAM = "llm_stream"
    LLM_COMPLETE = "llm_complete"
    LLM_ERROR = "llm_error"
    LLM_RETRY = "llm_retry"
    LLM_THINKING = "llm_thinking"

    # Tool events
    TOOL_REGISTER = "tool_register"
    TOOL_UNREGISTER = "tool_unregister"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_END = "tool_call_end"
    TOOL_CALL_ERROR = "tool_call_error"
    TOOL_CALL_CANCEL = "tool_call_cancel"
    TOOL_CONFIRMATION_REQUIRED = "tool_confirmation_required"

    # Context events
    CONTEXT_UPDATE = "context_update"
    CONTEXT_COMPACT_START = "context_compact_start"
    CONTEXT_COMPACT_END = "context_compact_end"
    CONTEXT_OVERFLOW = "context_overflow"
    CONTEXT_PRUNE = "context_prune"
    CONTEXT_TOKEN_COUNT = "context_token_count"

    # Steering/Follow-up events
    STEERING_QUEUED = "steering_queued"
    STEERING_DELIVERED = "steering_delivered"
    FOLLOW_UP_QUEUED = "follow_up_queued"
    FOLLOW_UP_DELIVERED = "follow_up_delivered"

    # File events
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"
    FILE_CREATE = "file_create"
    FILE_RENAME = "file_rename"

    # Shell events
    SHELL_START = "shell_start"
    SHELL_OUTPUT = "shell_output"
    SHELL_END = "shell_end"
    SHELL_ERROR = "shell_error"
    SHELL_INTERRUPT = "shell_interrupt"

    # Agent state events
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"
    AGENT_IDLE = "agent_idle"
    AGENT_BUSY = "agent_busy"
    AGENT_THINKING = "agent_thinking"
    AGENT_WAITING = "agent_waiting"

    # Permission events
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"

    # Config events
    CONFIG_CHANGE = "config_change"
    CONFIG_RELOAD = "config_reload"


@dataclass
class ExtensionEvent:
    """Extension event data"""
    type: ExtensionEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None  # Extension name that emitted the event

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


@dataclass
class ExtensionManifest:
    """Extension manifest defining metadata and capabilities"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = "MIT"

    # Capabilities
    provides_tools: List[str] = field(default_factory=list)
    provides_hooks: List[ExtensionEventType] = field(default_factory=list)

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)

    # Configuration
    config_schema: Optional[Dict[str, Any]] = None
    default_config: Optional[Dict[str, Any]] = None

    # Permissions
    permissions: List[str] = field(default_factory=list)  # e.g., "file:read", "shell:execute"


@dataclass
class ExtensionConfig:
    """Extension configuration"""
    enabled: bool = True
    priority: int = 100  # Lower = higher priority
    settings: Dict[str, Any] = field(default_factory=dict)


class ExtensionAPI:
    """
    API provided to extensions for interacting with Koda.

    This is the main interface extensions use to:
    - Register hooks and tools
    - Emit events
    - Access session state
    - Log messages
    """

    def __init__(self, session: Optional["AgentSession"] = None, registry=None):
        self._session = session
        self._registry = registry
        self._hooks: Dict[ExtensionEventType, List[Callable]] = {}
        self._tools: Dict[str, Callable] = {}

    def register_hook(
        self,
        event_type: ExtensionEventType,
        callback: Callable[[ExtensionEvent], Optional[ExtensionEvent]]
    ) -> None:
        """
        Register a hook for an event type.

        Hooks can modify events before they're processed.
        Return None to cancel the event.

        Args:
            event_type: Type of event to hook
            callback: Function to call with event, returns modified event or None
        """
        if event_type not in self._hooks:
            self._hooks[event_type] = []
        self._hooks[event_type].append(callback)

    def unregister_hook(
        self,
        event_type: ExtensionEventType,
        callback: Callable
    ) -> None:
        """Unregister a hook"""
        if event_type in self._hooks and callback in self._hooks[event_type]:
            self._hooks[event_type].remove(callback)

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a tool that the agent can use.

        Args:
            name: Tool name
            handler: Async function to execute tool
            description: Tool description for LLM
            parameters: JSON Schema for parameters
        """
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "parameters": parameters or {},
        }

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool"""
        self._tools.pop(name, None)

    def emit_event(self, event: ExtensionEvent) -> None:
        """
        Emit an event to the event bus.

        Args:
            event: Event to emit
        """
        # This will be handled by the extension runner
        if self._registry:
            self._registry.emit_event(event)

    def get_session(self) -> Optional["AgentSession"]:
        """Get current session"""
        return self._session

    def get_context(self) -> Optional[Dict[str, Any]]:
        """Get current context summary"""
        if self._session:
            return {
                "message_count": len(self._session.messages),
                "state": self._session.state.value,
            }
        return None

    def log(self, message: str, level: str = "info") -> None:
        """Log a message"""
        print(f"[Extension] [{level.upper()}] {message}")

    def log_debug(self, message: str) -> None:
        """Log debug message"""
        self.log(message, "debug")

    def log_info(self, message: str) -> None:
        """Log info message"""
        self.log(message, "info")

    def log_warning(self, message: str) -> None:
        """Log warning message"""
        self.log(message, "warning")

    def log_error(self, message: str) -> None:
        """Log error message"""
        self.log(message, "error")


class Extension(ABC):
    """
    Base class for Koda extensions.

    Extensions can hook into various points of the agent lifecycle
    and modify behavior, add tools, or observe events.

    Lifecycle:
    1. Extension class is discovered
    2. get_manifest() is called to get metadata
    3. activate() is called with ExtensionAPI
    4. Extension registers hooks and tools
    5. Hooks are called as events occur
    6. deactivate() is called when unloading
    """

    def __init__(self):
        self.manifest = self.get_manifest()
        self._api: Optional[ExtensionAPI] = None
        self._config: ExtensionConfig = ExtensionConfig()

    @abstractmethod
    def get_manifest(self) -> ExtensionManifest:
        """Return extension manifest with metadata and capabilities"""
        pass

    def activate(self, api: ExtensionAPI) -> None:
        """
        Called when extension is activated.

        Override this to register hooks and tools.

        Args:
            api: API for interacting with Koda
        """
        self._api = api

    def deactivate(self) -> None:
        """Called when extension is deactivated. Override for cleanup."""
        self._api = None

    def configure(self, config: ExtensionConfig) -> None:
        """Configure extension with settings"""
        self._config = config

    # Convenience hook methods that can be overridden

    def on_user_message(self, content: str) -> Optional[str]:
        """
        Hook: Called when user message is received.
        Can modify or return None to cancel.
        """
        return content

    def on_assistant_message(self, content: str) -> Optional[str]:
        """
        Hook: Called before assistant response is sent.
        Can modify or return None to cancel.
        """
        return content

    def on_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Hook: Called before tool execution.
        Can modify arguments or return None to cancel.
        """
        return arguments

    def on_tool_result(
        self,
        tool_name: str,
        result: Any
    ) -> Any:
        """
        Hook: Called after tool execution.
        Can modify the result.
        """
        return result

    def on_llm_start(self, messages: List[Any]) -> Optional[List[Any]]:
        """
        Hook: Called before LLM request.
        Can modify messages or return None to cancel.
        """
        return messages

    def on_llm_complete(self, response: Any) -> Any:
        """
        Hook: Called after LLM response.
        Can modify the response.
        """
        return response

    def on_context_compact(
        self,
        original_tokens: int,
        new_tokens: int
    ) -> None:
        """Hook: Called when context is compacted"""
        pass

    def on_session_start(self) -> None:
        """Hook: Called when session starts"""
        pass

    def on_session_end(self) -> None:
        """Hook: Called when session ends"""
        pass

    def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Hook: Called when an error occurs"""
        pass


# Event filter types
EventFilter = Callable[[ExtensionEvent], bool]


@dataclass
class EventSubscription:
    """Subscription to extension events"""
    event_types: List[ExtensionEventType]
    callback: Callable[[ExtensionEvent], None]
    filter: Optional[EventFilter] = None

    def matches(self, event: ExtensionEvent) -> bool:
        """Check if subscription matches event"""
        if event.type not in self.event_types:
            return False
        if self.filter and not self.filter(event):
            return False
        return True


# Tool definition types
@dataclass
class ToolDefinition:
    """Tool definition for registration"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable
    requires_confirmation: bool = False
    timeout: float = 60.0
    examples: List[Dict[str, Any]] = field(default_factory=list)


# Hook priority levels
class HookPriority(Enum):
    """Priority levels for hooks"""
    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class HookRegistration:
    """Registration for a hook"""
    event_type: ExtensionEventType
    callback: Callable
    priority: int = HookPriority.NORMAL.value
    extension_name: Optional[str] = None


# Permission constants
class Permission:
    """Extension permissions"""
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    SHELL_EXECUTE = "shell:execute"
    NETWORK_ACCESS = "network:access"
    CONTEXT_READ = "context:read"
    CONTEXT_MODIFY = "context:modify"
    TOOL_REGISTER = "tool:register"
    EVENT_EMIT = "event:emit"
    SESSION_READ = "session:read"
    SESSION_MODIFY = "session:modify"
    SETTINGS_READ = "settings:read"
    SETTINGS_MODIFY = "settings:modify"


@dataclass
class ExtensionContext:
    """
    Context provided to extensions during execution.

    Contains current session state, message history, and agent state.
    """
    # Session info
    session_id: Optional[str] = None
    session_path: Optional[str] = None

    # Current state
    message_count: int = 0
    current_tokens: int = 0
    max_tokens: int = 200000

    # Agent state
    agent_state: str = "idle"  # idle, busy, thinking, waiting, error

    # Working directory
    working_directory: Optional[str] = None

    # Current configuration
    model: Optional[str] = None
    provider: Optional[str] = None

    # Tool state
    pending_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    completed_tool_calls: int = 0

    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None

    # Custom data
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "session_id": self.session_id,
            "session_path": self.session_path,
            "message_count": self.message_count,
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "agent_state": self.agent_state,
            "working_directory": self.working_directory,
            "model": self.model,
            "provider": self.provider,
            "pending_tool_calls": len(self.pending_tool_calls),
            "completed_tool_calls": self.completed_tool_calls,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "custom": self.custom,
        }

    @property
    def token_usage_percent(self) -> float:
        """Get token usage percentage"""
        if self.max_tokens == 0:
            return 0.0
        return (self.current_tokens / self.max_tokens) * 100

    @property
    def is_context_full(self) -> bool:
        """Check if context is near capacity"""
        return self.token_usage_percent > 90


@dataclass
class ExtensionResult:
    """
    Result from extension hook execution.

    Can modify data, cancel events, or request actions.
    """
    # Modified data (if applicable)
    data: Any = None

    # Whether to cancel the event
    cancel: bool = False

    # Error message (if any)
    error: Optional[str] = None

    # Actions to take
    actions: List[str] = field(default_factory=list)

    # Metadata
    extension_name: Optional[str] = None
    duration_ms: float = 0.0

    @classmethod
    def ok(cls, data: Any = None) -> "ExtensionResult":
        """Create successful result"""
        return cls(data=data)

    @classmethod
    def cancel_event(cls, reason: str = "") -> "ExtensionResult":
        """Create cancellation result"""
        return cls(cancel=True, error=reason)

    @classmethod
    def error(cls, message: str) -> "ExtensionResult":
        """Create error result"""
        return cls(error=message)


class HookPoint(Enum):
    """
    Hook points for extension injection.

    Each hook point represents a specific moment in the agent lifecycle
    where extensions can intercept and modify behavior.
    """
    # Pre-processing hooks
    BEFORE_USER_MESSAGE = "before_user_message"
    BEFORE_ASSISTANT_MESSAGE = "before_assistant_message"
    BEFORE_LLM_CALL = "before_llm_call"
    BEFORE_TOOL_CALL = "before_tool_call"
    BEFORE_FILE_READ = "before_file_read"
    BEFORE_FILE_WRITE = "before_file_write"
    BEFORE_SHELL_EXECUTE = "before_shell_execute"

    # Post-processing hooks
    AFTER_USER_MESSAGE = "after_user_message"
    AFTER_ASSISTANT_MESSAGE = "after_assistant_message"
    AFTER_LLM_CALL = "after_llm_call"
    AFTER_TOOL_CALL = "after_tool_call"
    AFTER_FILE_READ = "after_file_read"
    AFTER_FILE_WRITE = "after_file_write"
    AFTER_SHELL_EXECUTE = "after_shell_execute"

    # Transformation hooks
    TRANSFORM_MESSAGES = "transform_messages"
    TRANSFORM_CONTEXT = "transform_context"
    TRANSFORM_TOOLS = "transform_tools"

    # Decision hooks
    SHOULD_COMPACT = "should_compact"
    SHOULD_RETRY = "should_retry"
    SHOULD_CONTINUE = "should_continue"

    # State hooks
    ON_STATE_CHANGE = "on_state_change"
    ON_ERROR = "on_error"
    ON_WARNING = "on_warning"


@dataclass
class ExtensionCapability:
    """Describes an extension's capability"""
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True
    config_schema: Optional[Dict[str, Any]] = None


# Extension status enum
class ExtensionStatus(Enum):
    """Extension status"""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


# Export all types
__all__ = [
    "ExtensionEventType",
    "ExtensionEvent",
    "ExtensionManifest",
    "ExtensionConfig",
    "ExtensionAPI",
    "Extension",
    "EventFilter",
    "EventSubscription",
    "ToolDefinition",
    "HookPriority",
    "HookRegistration",
    "Permission",
    "ExtensionContext",
    "ExtensionResult",
    "HookPoint",
    "ExtensionCapability",
    "ExtensionStatus",
]
