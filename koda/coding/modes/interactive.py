"""
Interactive Mode
Equivalent to Pi Mono's packages/coding-agent/src/modes/interactive/

Interactive conversation mode.
"""
from typing import Dict, List, Optional, Callable, Any, Iterator
from dataclasses import dataclass
from enum import Enum


class ModeState(Enum):
    """Interactive mode states"""
    IDLE = "idle"
    WAITING_INPUT = "waiting_input"
    PROCESSING = "processing"
    TOOL_CONFIRM = "tool_confirm"
    ERROR = "error"
    EXIT = "exit"


@dataclass
class ModeContext:
    """Context for interactive mode"""
    messages: List[Dict[str, Any]]
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ModeResponse:
    """Response from interactive mode"""
    content: str
    state: ModeState
    requires_input: bool = False
    tool_calls: Optional[List[Dict]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class InteractiveMode:
    """
    Interactive conversation mode.
    
    Manages back-and-forth conversation with user input.
    
    Example:
        >>> mode = InteractiveMode()
        >>> context = ModeContext(messages=[])
        >>> response = mode.start(context)
        >>> while response.state != ModeState.EXIT:
        ...     if response.requires_input:
        ...         user_input = input("> ")
        ...         response = mode.handle_input(user_input, context)
        ...     else:
        ...         print(response.content)
        ...         response = mode.continue_(context)
    """
    
    def __init__(self):
        self.state = ModeState.IDLE
        self._handlers: Dict[str, Callable] = {}
        self._history: List[Dict] = []
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default command handlers"""
        self._handlers["/exit"] = self._handle_exit
        self._handlers["/quit"] = self._handle_exit
        self._handlers["/clear"] = self._handle_clear
        self._handlers["/help"] = self._handle_help
    
    def start(self, context: ModeContext) -> ModeResponse:
        """
        Start interactive mode.
        
        Args:
            context: Initial context
            
        Returns:
            Initial response
        """
        self.state = ModeState.WAITING_INPUT
        return ModeResponse(
            content="Interactive mode started. Type /help for commands, /exit to quit.",
            state=self.state,
            requires_input=True
        )
    
    def handle_input(self, user_input: str, context: ModeContext) -> ModeResponse:
        """
        Handle user input.
        
        Args:
            user_input: User's input text
            context: Mode context
            
        Returns:
            Response
        """
        # Handle commands
        if user_input.startswith('/'):
            handler = self._handlers.get(user_input.split()[0])
            if handler:
                return handler(user_input, context)
            else:
                return ModeResponse(
                    content=f"Unknown command: {user_input}. Type /help for available commands.",
                    state=ModeState.WAITING_INPUT,
                    requires_input=True
                )
        
        # Regular input - add to context
        context.messages.append({"role": "user", "content": user_input})
        self._history.append({"role": "user", "content": user_input})
        
        self.state = ModeState.PROCESSING
        return ModeResponse(
            content="",
            state=self.state,
            requires_input=False
        )
    
    def handle_assistant_response(self, content: str, context: ModeContext) -> ModeResponse:
        """
        Handle assistant response.
        
        Args:
            content: Assistant's response
            context: Mode context
            
        Returns:
            Response
        """
        context.messages.append({"role": "assistant", "content": content})
        self._history.append({"role": "assistant", "content": content})
        
        self.state = ModeState.WAITING_INPUT
        return ModeResponse(
            content=content,
            state=self.state,
            requires_input=True
        )
    
    def handle_tool_confirmation(
        self,
        tool_calls: List[Dict],
        context: ModeContext
    ) -> ModeResponse:
        """
        Request confirmation for tool calls.
        
        Args:
            tool_calls: List of tool calls to confirm
            context: Mode context
            
        Returns:
            Response requiring confirmation
        """
        self.state = ModeState.TOOL_CONFIRM
        
        tool_list = "\n".join([
            f"  - {t.get('name', 'unknown')}: {t.get('arguments', {})}"
            for t in tool_calls
        ])
        
        return ModeResponse(
            content=f"The following tools will be executed:\n{tool_list}\n\nConfirm? (y/n)",
            state=self.state,
            requires_input=True,
            tool_calls=tool_calls
        )
    
    def confirm_tools(self, confirmed: bool, context: ModeContext) -> ModeResponse:
        """
        Handle tool confirmation response.
        
        Args:
            confirmed: Whether user confirmed
            context: Mode context
            
        Returns:
            Response
        """
        if confirmed:
            self.state = ModeState.PROCESSING
            return ModeResponse(
                content="Executing tools...",
                state=self.state,
                requires_input=False
            )
        else:
            self.state = ModeState.WAITING_INPUT
            return ModeResponse(
                content="Tools cancelled. What would you like to do instead?",
                state=self.state,
                requires_input=True
            )
    
    def _handle_exit(self, command: str, context: ModeContext) -> ModeResponse:
        """Handle exit command"""
        self.state = ModeState.EXIT
        return ModeResponse(
            content="Goodbye!",
            state=self.state,
            requires_input=False
        )
    
    def _handle_clear(self, command: str, context: ModeContext) -> ModeResponse:
        """Handle clear command"""
        context.messages.clear()
        self._history.clear()
        return ModeResponse(
            content="Conversation cleared.",
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )
    
    def _handle_help(self, command: str, context: ModeContext) -> ModeResponse:
        """Handle help command"""
        help_text = """Available commands:
  /exit, /quit  - Exit interactive mode
  /clear        - Clear conversation history
  /help         - Show this help
  
You can also type any message to chat with the AI."""
        
        return ModeResponse(
            content=help_text,
            state=ModeState.WAITING_INPUT,
            requires_input=True
        )
    
    def get_history(self) -> List[Dict]:
        """Get conversation history"""
        return list(self._history)
    
    def is_active(self) -> bool:
        """Check if mode is still active"""
        return self.state not in (ModeState.EXIT, ModeState.ERROR)


__all__ = [
    "InteractiveMode",
    "ModeContext",
    "ModeResponse",
    "ModeState",
]
