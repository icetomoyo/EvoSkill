"""
Koda Coding Core Module

核心功能模块。
"""

from .event_bus import (
    Event,
    EventBus,
    EventHandler,
    AsyncEventHandler,
    EventLogger,
    get_event_bus,
    EventTypes,
)
from .diagnostics import (
    DiagnosticResult,
    Diagnostics,
    run_diagnostics,
)
from .exec import (
    # Core classes
    ToolExecutor,
    SyncToolExecutor,
    ExecutionConfig,
    RetryConfig,
    ExecutionContext,
    ExecutionResult,
    ExecutionError,
    ExecutionStatus,
    ErrorCategory,
    # Logging
    ExecutionLogger,
    ExecutionLog,
    # Formatting
    ResultFormatter,
    # Convenience functions
    execute_tool,
    execute_tool_sync,
)

__all__ = [
    # Event Bus
    "Event",
    "EventBus",
    "EventHandler",
    "AsyncEventHandler",
    "EventLogger",
    "get_event_bus",
    "EventTypes",
    # Diagnostics
    "DiagnosticResult",
    "Diagnostics",
    "run_diagnostics",
    # Tool Execution
    "ToolExecutor",
    "SyncToolExecutor",
    "ExecutionConfig",
    "RetryConfig",
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionError",
    "ExecutionStatus",
    "ErrorCategory",
    "ExecutionLogger",
    "ExecutionLog",
    "ResultFormatter",
    "execute_tool",
    "execute_tool_sync",
]
