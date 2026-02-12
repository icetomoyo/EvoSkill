"""
Interactive Mode
Equivalent to Pi Mono's packages/coding-agent/src/modes/interactive/

Interactive conversation mode with full user input handling,
tool confirmation, session state management, and multi-turn dialog support.
"""
import asyncio
import uuid
from typing import Dict, List, Optional, Callable, Any, Iterator, Union, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class ModeState(Enum):
    """Interactive mode states"""
    IDLE = "idle"
    WAITING_INPUT = "waiting_input"
    PROCESSING = "processing"
    TOOL_CONFIRM = "tool_confirm"
    THINKING = "thinking"
    EXECUTING = "executing"
    STREAMING = "streaming"
    ERROR = "error"
    EXIT = "exit"


class ConfirmationType(Enum):
    """Types of confirmation requests"""
    TOOL_CALL = "tool_call"
    FILE_WRITE = "file_write"
    SHELL_COMMAND = "shell_command"
    DANGEROUS_OPERATION = "dangerous_operation"


@dataclass
class ToolCallInfo:
    """Information about a pending tool call"""
    id: str
    name: str
    arguments: Dict[str, Any]
    description: str = ""
    is_dangerous: bool = False
    requires_confirmation: bool = True


@dataclass
class ConfirmationRequest:
    """Request for user confirmation"""
    id: str
    type: ConfirmationType
    title: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=lambda: ["y", "n", "a(abort)"])
    default: str = "y"
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


@dataclass
class ModeContext:
    """Context for interactive mode"""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    working_directory: str = "."
    model: str = "claude-sonnet-4"
    max_tokens: int = 4096
    temperature: float = 0.7

    def __post_init__(self):
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())


@dataclass
class ModeResponse:
    """Response from interactive mode"""
    content: str
    state: ModeState
    requires_input: bool = False
    tool_calls: Optional[List[ToolCallInfo]] = None
    confirmation_request: Optional[ConfirmationRequest] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    thinking: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    stop_reason: Optional[str] = None


@dataclass
class SessionState:
    """Full session state for persistence"""
    session_id: str
    created_at: int
    updated_at: int
    message_count: int
    tool_call_count: int
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    branches: Dict[str, str] = field(default_factory=dict)
    current_branch: str = "main"


@dataclass
class ContextDisplay:
    """Context information for display to user"""
    current_files: List[str] = field(default_factory=list)
    recent_tools: List[str] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    active_branch: str = "main"


class InputHandler:
    """Handles user input processing"""

    def __init__(self):
        self._input_buffer: List[str] = []
        self._multiline_mode: bool = False
        self._multiline_buffer: List[str] = []

    def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and return parsed result.

        Returns:
            Dict with keys: 'type', 'content', 'command', 'args'
        """
        user_input = user_input.strip()

        # Handle multiline mode
        if self._multiline_mode:
            if user_input == '"""' or user_input == "'''":
                self._multiline_mode = False
                content = "\n".join(self._multiline_buffer)
                self._multiline_buffer = []
                return {
                    "type": "message",
                    "content": content,
                    "command": None,
                    "args": None
                }
            else:
                self._multiline_buffer.append(user_input)
                return {
                    "type": "multiline_continue",
                    "content": None,
                    "command": None,
                    "args": None
                }

        # Check for multiline start
        if user_input == '"""' or user_input == "'''":
            self._multiline_mode = True
            return {
                "type": "multiline_start",
                "content": None,
                "command": None,
                "args": None
            }

        # Check for commands
        if user_input.startswith('/'):
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            return {
                "type": "command",
                "content": user_input,
                "command": command,
                "args": args
            }

        # Regular message
        return {
            "type": "message",
            "content": user_input,
            "command": None,
            "args": None
        }

    def is_multiline_active(self) -> bool:
        """Check if multiline mode is active"""
        return self._multiline_mode

    def cancel_multiline(self) -> None:
        """Cancel multiline mode"""
        self._multiline_mode = False
        self._multiline_buffer = []


class ToolConfirmationManager:
    """Manages tool confirmation workflow"""

    # Tools that always require confirmation
    DANGEROUS_TOOLS = {
        "shell_execute",
        "file_write",
        "file_delete",
        "git_push",
        "git_reset",
        "npm_publish",
        "docker_push",
    }

    # Tools that are always safe
    SAFE_TOOLS = {
        "file_read",
        "grep",
        "ls",
        "file_info",
        "git_status",
        "git_log",
    }

    def __init__(self, auto_approve_safe: bool = True):
        self.auto_approve_safe = auto_approve_safe
        self._pending_confirmations: Dict[str, ConfirmationRequest] = {}
        self._confirmed_tools: set = set()  # Tools confirmed for session

    def needs_confirmation(self, tool_call: ToolCallInfo) -> bool:
        """Check if a tool call needs confirmation"""
        # Already confirmed this session
        if tool_call.name in self._confirmed_tools:
            return False

        # Auto-approve safe tools
        if self.auto_approve_safe and tool_call.name in self.SAFE_TOOLS:
            return False

        # Always confirm dangerous tools
        if tool_call.name in self.DANGEROUS_TOOLS:
            return True

        # Respect tool's own flag
        return tool_call.requires_confirmation

    def create_confirmation_request(
        self,
        tool_calls: List[ToolCallInfo]
    ) -> ConfirmationRequest:
        """Create a confirmation request for tool calls"""
        request_id = str(uuid.uuid4())

        # Build description
        descriptions = []
        for tc in tool_calls:
            if tc.description:
                descriptions.append(f"- {tc.name}: {tc.description}")
            else:
                args_str = str(tc.arguments)[:100]
                descriptions.append(f"- {tc.name}: {args_str}")

        has_dangerous = any(tc.name in self.DANGEROUS_TOOLS for tc in tool_calls)

        request = ConfirmationRequest(
            id=request_id,
            type=ConfirmationType.TOOL_CALL,
            title="Confirm Tool Execution" if not has_dangerous else "Confirm Dangerous Operations",
            description="\n".join(descriptions),
            details={
                "tools": [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                        "is_dangerous": tc.name in self.DANGEROUS_TOOLS
                    }
                    for tc in tool_calls
                ]
            },
            options=["y", "n", "a(always for session)"],
            default="y"
        )

        self._pending_confirmations[request_id] = request
        return request

    def process_confirmation(
        self,
        request_id: str,
        response: str
    ) -> Dict[str, Any]:
        """
        Process user's confirmation response.

        Returns:
            Dict with 'confirmed' bool and 'always' bool
        """
        request = self._pending_confirmations.get(request_id)
        if not request:
            return {"confirmed": False, "always": False, "error": "Invalid request"}

        response = response.lower().strip()

        # Parse response
        if response in ("y", "yes"):
            return {"confirmed": True, "always": False}
        elif response in ("a", "always"):
            # Mark all tools in request as confirmed for session
            for tool in request.details.get("tools", []):
                self._confirmed_tools.add(tool["name"])
            return {"confirmed": True, "always": True}
        else:
            return {"confirmed": False, "always": False}

    def clear_pending(self) -> None:
        """Clear all pending confirmations"""
        self._pending_confirmations.clear()


class SessionStateManager:
    """Manages session state for persistence and branching"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self._state = SessionState(
            session_id=self.session_id,
            created_at=int(datetime.now().timestamp() * 1000),
            updated_at=int(datetime.now().timestamp() * 1000),
            message_count=0,
            tool_call_count=0
        )
        self._snapshots: Dict[str, List[Dict]] = {}
        self._current_messages: List[Dict] = []

    def record_message(self, role: str, content: Any) -> None:
        """Record a message in the session"""
        self._current_messages.append({
            "role": role,
            "content": content,
            "timestamp": int(datetime.now().timestamp() * 1000)
        })
        self._state.message_count += 1
        self._state.updated_at = int(datetime.now().timestamp() * 1000)

    def record_tool_call(self, tool_name: str, arguments: Dict, result: Any) -> None:
        """Record a tool call"""
        self._state.tool_call_count += 1
        self._state.updated_at = int(datetime.now().timestamp() * 1000)

    def create_branch(self, name: str) -> str:
        """Create a new branch from current state"""
        branch_id = str(uuid.uuid4())
        self._snapshots[branch_id] = list(self._current_messages)
        self._state.branches[branch_id] = name
        return branch_id

    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a branch"""
        if branch_id in self._snapshots:
            self._current_messages = list(self._snapshots[branch_id])
            self._state.current_branch = branch_id
            return True
        return False

    def get_state(self) -> SessionState:
        """Get current session state"""
        return self._state

    def get_messages(self) -> List[Dict]:
        """Get all messages"""
        return list(self._current_messages)

    def update_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Update token usage"""
        self._state.total_tokens_input += input_tokens
        self._state.total_tokens_output += output_tokens


class InteractiveMode:
    """
    Interactive conversation mode with full feature support.

    Features:
    - Complete user input handling with multiline support
    - Tool confirmation workflow with dangerous operation detection
    - Session state management with branching
    - Multi-turn dialog support
    - Context display for user awareness
    - Asynchronous streaming support

    Example:
        >>> mode = InteractiveMode()
        >>> context = ModeContext(messages=[])
        >>> response = mode.start(context)
        >>> while response.state != ModeState.EXIT:
        ...     if response.requires_input:
        ...         user_input = input("> ")
        ...         response = mode.handle_input(user_input, context)
        ...         if response.state == ModeState.TOOL_CONFIRM:
        ...             confirmation = input("Confirm? ")
        ...             response = mode.process_confirmation(response, confirmation)
        ...     else:
        ...         print(response.content)
        ...         response = mode.continue_(context)
    """

    def __init__(
        self,
        auto_approve_safe_tools: bool = False,
        enable_multiline: bool = True,
        max_history: int = 1000
    ):
        """
        Initialize InteractiveMode.

        Args:
            auto_approve_safe_tools: Auto-approve safe tools without confirmation
            enable_multiline: Enable multiline input mode
            max_history: Maximum number of history entries
        """
        self.state = ModeState.IDLE
        self._handlers: Dict[str, Callable] = {}
        self._history: List[Dict] = []
        self._max_history = max_history

        # Component managers
        self.input_handler = InputHandler()
        self.tool_confirmation = ToolConfirmationManager(auto_approve_safe_tools)
        self.session_state = SessionStateManager()

        # Configuration
        self._enable_multiline = enable_multiline
        self._pending_tool_calls: List[ToolCallInfo] = []
        self._current_confirmation: Optional[ConfirmationRequest] = None
        self._context_display = ContextDisplay()

        # Async support
        self._streaming = False
        self._stream_buffer: List[str] = []
        self._cancel_requested = False

        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Setup default command handlers"""
        self._handlers["/exit"] = self._handle_exit
        self._handlers["/quit"] = self._handle_exit
        self._handlers["/q"] = self._handle_exit
        self._handlers["/clear"] = self._handle_clear
        self._handlers["/help"] = self._handle_help
        self._handlers["/?"] = self._handle_help
        self._handlers["/history"] = self._handle_history
        self._handlers["/h"] = self._handle_history
        self._handlers["/undo"] = self._handle_undo
        self._handlers["/redo"] = self._handle_redo
        self._handlers["/branch"] = self._handle_branch
        self._handlers["/switch"] = self._handle_switch
        self._handlers["/context"] = self._handle_context
        self._handlers["/status"] = self._handle_status
        self._handlers["/save"] = self._handle_save
        self._handlers["/load"] = self._handle_load
        self._handlers["/export"] = self._handle_export
        self._handlers["/model"] = self._handle_model
        self._handlers["/temp"] = self._handle_temperature
        self._handlers["/cancel"] = self._handle_cancel
        self._handlers["/confirm"] = self._handle_confirm_settings

    def start(self, context: ModeContext) -> ModeResponse:
        """
        Start interactive mode.

        Args:
            context: Initial context

        Returns:
            Initial response
        """
        self.state = ModeState.WAITING_INPUT
        self.session_state = SessionStateManager(context.session_id)

        welcome = self._build_welcome_message()
        return ModeResponse(
            content=welcome,
            state=self.state,
            requires_input=True,
            metadata={"session_id": self.session_state.session_id}
        )

    def _build_welcome_message(self) -> str:
        """Build welcome message"""
        return """Interactive mode started.

Commands:
  /help, /?      - Show all commands
  /clear         - Clear conversation history
  /history, /h   - Show conversation history
  /undo          - Undo last exchange
  /context       - Show current context info
  /status        - Show session status
  /model         - Change model
  /exit, /quit   - Exit interactive mode

Type your message to chat with the AI.
Use ''' or \"\"\" for multiline input."""

    def handle_input(self, user_input: str, context: ModeContext) -> ModeResponse:
        """
        Handle user input.

        Args:
            user_input: User's input text
            context: Mode context

        Returns:
            Response
        """
        # Process input
        parsed = self.input_handler.process(user_input)

        # Handle multiline continue
        if parsed["type"] == "multiline_start":
            return ModeResponse(
                content="Multiline mode. End with ''' or \"\"\"",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        if parsed["type"] == "multiline_continue":
            return ModeResponse(
                content="...",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        # Handle commands
        if parsed["type"] == "command":
            handler = self._handlers.get(parsed["command"])
            if handler:
                return handler(parsed["args"] or "", context)
            else:
                return ModeResponse(
                    content=f"Unknown command: {parsed['command']}. Type /help for available commands.",
                    state=ModeState.WAITING_INPUT,
                    requires_input=True
                )

        # Regular message - add to context
        content = parsed["content"]
        context.messages.append({"role": "user", "content": content})
        self._add_to_history("user", content)
        self.session_state.record_message("user", content)

        self.state = ModeState.PROCESSING
        return ModeResponse(
            content="",
            state=self.state,
            requires_input=False
        )

    def handle_assistant_response(
        self,
        content: str,
        context: ModeContext,
        thinking: Optional[str] = None,
        usage: Optional[Dict[str, int]] = None,
        stop_reason: Optional[str] = None
    ) -> ModeResponse:
        """
        Handle assistant response.

        Args:
            content: Assistant's response
            context: Mode context
            thinking: Optional thinking content
            usage: Token usage information
            stop_reason: Reason for stopping

        Returns:
            Response
        """
        context.messages.append({"role": "assistant", "content": content})
        self._add_to_history("assistant", content)
        self.session_state.record_message("assistant", content)

        if usage:
            self.session_state.update_usage(
                usage.get("input", 0),
                usage.get("output", 0)
            )

        self.state = ModeState.WAITING_INPUT
        return ModeResponse(
            content=content,
            state=self.state,
            requires_input=True,
            thinking=thinking,
            usage=usage,
            stop_reason=stop_reason
        )

    def handle_tool_call(
        self,
        tool_calls: List[Dict],
        context: ModeContext
    ) -> ModeResponse:
        """
        Handle tool call request from assistant.

        Args:
            tool_calls: List of tool call dicts with name, arguments, id
            context: Mode context

        Returns:
            Response - either confirmation request or ready to execute
        """
        # Convert to ToolCallInfo
        tool_call_infos = []
        for tc in tool_calls:
            info = ToolCallInfo(
                id=tc.get("id", str(uuid.uuid4())),
                name=tc.get("name", "unknown"),
                arguments=tc.get("arguments", {}),
                description=tc.get("description", ""),
                is_dangerous=tc.get("name") in self.tool_confirmation.DANGEROUS_TOOLS,
                requires_confirmation=tc.get("requires_confirmation", True)
            )
            tool_call_infos.append(info)

        # Check which need confirmation
        needs_confirm = [tc for tc in tool_call_infos if self.tool_confirmation.needs_confirmation(tc)]

        if needs_confirm:
            self.state = ModeState.TOOL_CONFIRM
            self._pending_tool_calls = needs_confirm

            confirmation = self.tool_confirmation.create_confirmation_request(needs_confirm)
            self._current_confirmation = confirmation

            return ModeResponse(
                content=f"{confirmation.title}\n\n{confirmation.description}\n\nConfirm? [{', '.join(confirmation.options)}] (default: {confirmation.default})",
                state=self.state,
                requires_input=True,
                tool_calls=needs_confirm,
                confirmation_request=confirmation
            )
        else:
            # Auto-approved, ready to execute
            self.state = ModeState.EXECUTING
            return ModeResponse(
                content="Executing tools...",
                state=self.state,
                requires_input=False,
                tool_calls=tool_call_infos
            )

    def process_confirmation(
        self,
        response: ModeResponse,
        user_confirmation: str
    ) -> ModeResponse:
        """
        Process user's confirmation for tool calls.

        Args:
            response: The response that requested confirmation
            user_confirmation: User's confirmation input

        Returns:
            Response indicating whether to proceed
        """
        if not response.confirmation_request:
            return ModeResponse(
                content="No pending confirmation.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        result = self.tool_confirmation.process_confirmation(
            response.confirmation_request.id,
            user_confirmation
        )

        if result["confirmed"]:
            self.state = ModeState.EXECUTING
            always_msg = " (approved for this session)" if result.get("always") else ""
            return ModeResponse(
                content=f"Executing tools{always_msg}...",
                state=self.state,
                requires_input=False,
                tool_calls=self._pending_tool_calls
            )
        else:
            self.state = ModeState.WAITING_INPUT
            self._pending_tool_calls = []
            return ModeResponse(
                content="Tools cancelled. What would you like to do instead?",
                state=self.state,
                requires_input=True
            )

    def handle_tool_result(
        self,
        tool_name: str,
        result: Any,
        is_error: bool,
        context: ModeContext
    ) -> ModeResponse:
        """
        Handle tool execution result.

        Args:
            tool_name: Name of the executed tool
            result: Tool result
            is_error: Whether execution failed
            context: Mode context

        Returns:
            Response
        """
        self.session_state.record_tool_call(tool_name, {}, result)
        self._context_display.recent_tools.append(tool_name)
        if len(self._context_display.recent_tools) > 10:
            self._context_display.recent_tools.pop(0)

        # Add to messages
        context.messages.append({
            "role": "tool",
            "name": tool_name,
            "content": str(result),
            "is_error": is_error
        })

        self.state = ModeState.PROCESSING
        return ModeResponse(
            content="",
            state=self.state,
            requires_input=False,
            metadata={"tool_name": tool_name, "is_error": is_error}
        )

    def continue_(self, context: ModeContext) -> ModeResponse:
        """
        Continue processing after handling previous response.

        Args:
            context: Mode context

        Returns:
            Next response
        """
        if self.state == ModeState.PROCESSING:
            # Still processing, return empty response
            return ModeResponse(
                content="",
                state=self.state,
                requires_input=False
            )

        # Default to waiting for input
        self.state = ModeState.WAITING_INPUT
        return ModeResponse(
            content="",
            state=self.state,
            requires_input=True
        )

    # Command handlers

    def _handle_exit(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle exit command"""
        self.state = ModeState.EXIT

        state = self.session_state.get_state()
        summary = f"\nSession summary:\n"
        summary += f"  Messages: {state.message_count}\n"
        summary += f"  Tool calls: {state.tool_call_count}\n"
        summary += f"  Tokens: {state.total_tokens_input} in / {state.total_tokens_output} out\n"

        return ModeResponse(
            content=f"Goodbye!{summary}",
            state=self.state,
            requires_input=False
        )

    def _handle_clear(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle clear command"""
        context.messages.clear()
        self._history.clear()
        self.session_state = SessionStateManager()
        self.tool_confirmation.clear_pending()
        return ModeResponse(
            content="Conversation cleared. Session reset.",
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_help(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle help command"""
        help_text = """Available commands:

Session Management:
  /clear         - Clear conversation and reset session
  /save [file]   - Save session to file
  /load [file]   - Load session from file
  /export [fmt]  - Export (json, markdown)

Navigation:
  /history, /h   - Show conversation history
  /undo          - Undo last exchange
  /redo          - Redo undone exchange
  /branch [name] - Create branch from current point
  /switch [id]   - Switch to branch

Information:
  /context       - Show current context info
  /status        - Show session statistics

Settings:
  /model [name]  - View or change model
  /temp [value]  - View or change temperature
  /confirm       - Toggle confirmation settings

Control:
  /cancel        - Cancel current operation
  /exit, /quit   - Exit interactive mode

Input:
  ''' or \"\"\"   - Start/end multiline input"""

        return ModeResponse(
            content=help_text,
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_history(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle history command"""
        if not self._history:
            return ModeResponse(
                content="No history yet.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        lines = []
        for i, entry in enumerate(self._history[-50:]):  # Last 50 entries
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            lines.append(f"{i+1}. [{role}] {content}")

        return ModeResponse(
            content="Conversation history:\n" + "\n".join(lines),
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_undo(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle undo command"""
        if len(context.messages) < 2:
            return ModeResponse(
                content="Nothing to undo.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        # Remove last exchange (user + assistant)
        context.messages.pop()  # Remove assistant
        context.messages.pop()  # Remove user

        if self._history:
            self._history.pop()  # Remove assistant history
        if self._history:
            self._history.pop()  # Remove user history

        return ModeResponse(
            content="Last exchange undone.",
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_redo(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle redo command"""
        return ModeResponse(
            content="Redo not implemented yet. Please re-enter your message.",
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_branch(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle branch command"""
        name = args.strip() or f"branch-{datetime.now().strftime('%H%M%S')}"
        branch_id = self.session_state.create_branch(name)

        return ModeResponse(
            content=f"Created branch '{name}' (id: {branch_id[:8]}...).\nUse /switch {branch_id[:8]} to return to this point.",
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_switch(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle switch command"""
        branch_id = args.strip()
        if not branch_id:
            # List branches
            state = self.session_state.get_state()
            branches = "\n".join([
                f"  {bid[:8]}... : {name}"
                for bid, name in state.branches.items()
            ])
            return ModeResponse(
                content=f"Available branches:\n{branches}\nCurrent: {state.current_branch}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        if self.session_state.switch_branch(branch_id):
            context.messages = self.session_state.get_messages()
            return ModeResponse(
                content=f"Switched to branch {branch_id[:8]}...",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        else:
            return ModeResponse(
                content=f"Branch {branch_id[:8]}... not found.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    def _handle_context(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle context command"""
        state = self.session_state.get_state()

        info = [
            "Current Context:",
            f"  Session ID: {state.session_id[:16]}...",
            f"  Branch: {self._context_display.active_branch}",
            f"  Messages: {len(context.messages)}",
            f"  Tool calls: {state.tool_call_count}",
            "",
            f"  Tokens: {state.total_tokens_input} in / {state.total_tokens_output} out",
        ]

        if self._context_display.recent_tools:
            info.append(f"  Recent tools: {', '.join(self._context_display.recent_tools[-5:])}")

        if self._context_display.current_files:
            info.append(f"  Files: {', '.join(self._context_display.current_files[:5])}")

        return ModeResponse(
            content="\n".join(info),
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_status(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle status command"""
        state = self.session_state.get_state()

        created = datetime.fromtimestamp(state.created_at / 1000)
        updated = datetime.fromtimestamp(state.updated_at / 1000)
        duration = updated - created

        status = [
            "Session Status:",
            f"  ID: {state.session_id}",
            f"  Created: {created.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Last activity: {updated.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Duration: {str(duration).split('.')[0]}",
            f"  Messages: {state.message_count}",
            f"  Tool calls: {state.tool_call_count}",
            f"  Tokens: {state.total_tokens_input} in, {state.total_tokens_output} out",
            f"  Branches: {len(state.branches)}",
            f"  Current state: {self.state.value}",
        ]

        return ModeResponse(
            content="\n".join(status),
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_save(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle save command"""
        import json
        from pathlib import Path

        filename = args.strip() or f"session-{self.session_state.session_id[:8]}.json"

        try:
            data = {
                "session_id": self.session_state.session_id,
                "messages": context.messages,
                "history": self._history,
                "state": {
                    "message_count": self.session_state.get_state().message_count,
                    "tool_call_count": self.session_state.get_state().tool_call_count,
                },
                "saved_at": datetime.now().isoformat()
            }

            Path(filename).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

            return ModeResponse(
                content=f"Session saved to {filename}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        except Exception as e:
            return ModeResponse(
                content=f"Failed to save: {e}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    def _handle_load(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle load command"""
        import json
        from pathlib import Path

        filename = args.strip()
        if not filename:
            return ModeResponse(
                content="Usage: /load <filename>",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        try:
            data = json.loads(Path(filename).read_text(encoding='utf-8'))

            context.messages = data.get("messages", [])
            self._history = data.get("history", [])
            self.session_state = SessionStateManager(data.get("session_id"))

            return ModeResponse(
                content=f"Session loaded from {filename}\nMessages: {len(context.messages)}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        except FileNotFoundError:
            return ModeResponse(
                content=f"File not found: {filename}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        except Exception as e:
            return ModeResponse(
                content=f"Failed to load: {e}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    def _handle_export(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle export command"""
        format = args.strip().lower() or "markdown"

        if format == "json":
            import json
            data = {
                "session_id": self.session_state.session_id,
                "messages": context.messages,
                "exported_at": datetime.now().isoformat()
            }
            return ModeResponse(
                content=json.dumps(data, indent=2, ensure_ascii=False),
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        elif format in ("markdown", "md"):
            lines = [
                f"# Session Export",
                f"",
                f"Session ID: {self.session_state.session_id}",
                f"Exported: {datetime.now().isoformat()}",
                f"",
                "## Conversation",
                ""
            ]

            for msg in context.messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"### {role.title()}")
                lines.append(content)
                lines.append("")

            return ModeResponse(
                content="\n".join(lines),
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        else:
            return ModeResponse(
                content=f"Unknown format: {format}. Use 'json' or 'markdown'.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    def _handle_model(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle model command"""
        if args.strip():
            context.model = args.strip()
            return ModeResponse(
                content=f"Model changed to: {context.model}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        else:
            return ModeResponse(
                content=f"Current model: {context.model}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    def _handle_temperature(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle temperature command"""
        if args.strip():
            try:
                temp = float(args.strip())
                if 0 <= temp <= 2:
                    context.temperature = temp
                    return ModeResponse(
                        content=f"Temperature set to: {context.temperature}",
                        state=ModeState.WAITING_INPUT,
                        requires_input=True
                    )
                else:
                    return ModeResponse(
                        content="Temperature must be between 0 and 2",
                        state=ModeState.WAITING_INPUT,
                        requires_input=True
                    )
            except ValueError:
                return ModeResponse(
                    content="Invalid temperature value",
                    state=ModeState.WAITING_INPUT,
                    requires_input=True
                )
        else:
            return ModeResponse(
                content=f"Current temperature: {context.temperature}",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    def _handle_cancel(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle cancel command"""
        self._cancel_requested = True
        self.state = ModeState.WAITING_INPUT

        if self.input_handler.is_multiline_active():
            self.input_handler.cancel_multiline()
            return ModeResponse(
                content="Multiline input cancelled.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

        return ModeResponse(
            content="Current operation cancelled.",
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )

    def _handle_confirm_settings(self, args: str, context: ModeContext) -> ModeResponse:
        """Handle confirm settings command"""
        if args.strip() == "off":
            self.tool_confirmation.auto_approve_safe = True
            return ModeResponse(
                content="Auto-approve enabled for safe tools. Dangerous tools still require confirmation.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        elif args.strip() == "on":
            self.tool_confirmation.auto_approve_safe = False
            return ModeResponse(
                content="All tools require confirmation.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )
        else:
            status = "enabled" if self.tool_confirmation.auto_approve_safe else "disabled"
            return ModeResponse(
                content=f"Auto-approve for safe tools: {status}\nUse /confirm on or /confirm off to change.",
                state=ModeState.WAITING_INPUT,
                requires_input=True
            )

    # Utility methods

    def _add_to_history(self, role: str, content: str) -> None:
        """Add entry to history with limit"""
        self._history.append({"role": role, "content": content})
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(self) -> List[Dict]:
        """Get conversation history"""
        return list(self._history)

    def is_active(self) -> bool:
        """Check if mode is still active"""
        return self.state not in (ModeState.EXIT, ModeState.ERROR)

    def get_context_display(self) -> ContextDisplay:
        """Get current context display info"""
        return self._context_display

    def register_command(self, command: str, handler: Callable) -> None:
        """Register a custom command handler"""
        self._handlers[command] = handler

    # Async support for streaming

    async def start_streaming(self) -> None:
        """Start streaming mode"""
        self._streaming = True
        self._stream_buffer = []
        self.state = ModeState.STREAMING

    async def append_stream(self, delta: str) -> None:
        """Append to stream buffer"""
        self._stream_buffer.append(delta)

    async def end_stream(self) -> str:
        """End streaming and return full content"""
        self._streaming = False
        content = "".join(self._stream_buffer)
        self._stream_buffer = []
        return content

    def is_streaming(self) -> bool:
        """Check if currently streaming"""
        return self._streaming

    def request_cancel(self) -> None:
        """Request cancellation of current operation"""
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        """Check if cancel was requested"""
        return self._cancel_requested

    def clear_cancel(self) -> None:
        """Clear cancel flag"""
        self._cancel_requested = False


__all__ = [
    "InteractiveMode",
    "ModeContext",
    "ModeResponse",
    "ModeState",
    "ConfirmationType",
    "ConfirmationRequest",
    "ToolCallInfo",
    "SessionState",
    "ContextDisplay",
    "InputHandler",
    "ToolConfirmationManager",
    "SessionStateManager",
]
