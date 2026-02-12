"""
Modes System
Equivalent to Pi Mono's packages/coding-agent/src/modes/

Different operation modes for the coding agent.

Available Modes:
- InteractiveMode: Full interactive conversation with tool confirmation
- PrintMode: Non-interactive one-shot operation mode
- RPCServer/RPCClient: Remote procedure call mode for IDE integration
"""
from .interactive import (
    InteractiveMode,
    ModeContext,
    ModeResponse,
    ModeState,
    ConfirmationType,
    ConfirmationRequest,
    ToolCallInfo,
    SessionState,
    ContextDisplay,
    InputHandler,
    ToolConfirmationManager,
    SessionStateManager,
)
from .print_mode import PrintMode, PrintResult
from .rpc import (
    RPCServer,
    RPCRequest,
    RPCResponse,
    RPCClient,
    RPCClientConfig,
    RPCError,
    RPCHandlers,
)

__all__ = [
    # Interactive Mode
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
    # Print Mode
    "PrintMode",
    "PrintResult",
    # RPC Mode
    "RPCServer",
    "RPCRequest",
    "RPCResponse",
    "RPCClient",
    "RPCClientConfig",
    "RPCError",
    "RPCHandlers",
]
