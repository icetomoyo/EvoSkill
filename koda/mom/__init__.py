"""
Mom - Multi-channel agent runner with memory persistence

This module provides the Mom agent system, equivalent to Pi Mono's mom package.

Key Components:
- MomAgent: Multi-channel agent runner with per-channel memory
- ContextManager: Dynamic context management with auto-compaction
- EventsWatcher: Event scheduling and file watching
- StructuredLogger: Rich structured logging
- Sandbox: Isolated execution environment
- Store: Persistent storage with attachment handling

Tools:
- attach: File attachment handling
- bash: Shell command execution
- edit: File editing with diff support
- read: File reading with image support
- truncate: Output truncation
- write: File writing

Usage:
    from koda.mom import MomAgent, ContextManager, EventsWatcher
    from koda.mom import StructuredLogger, Sandbox, Store

    # Create mom agent
    mom = MomAgent(provider, config)
    await mom.start()

    # Handle message
    async for event in mom.handle_message(channel_id, user_id, content):
        print(event)

    # Stop
    await mom.stop()
"""

# Core components
from koda.mom.agent import (
    MomAgent,
    MomAgentConfig,
    ChannelConfig,
    ChannelMemory,
)
from koda.mom.context import (
    ContextManager,
    MomSettings,
    MomSettingsManager,
    SessionManagerClient,
)
from koda.mom.events import (
    EventsWatcher,
    ScheduledEvent,
    CronParser,
)
from koda.mom.log import (
    StructuredLogger,
    LogEntry,
    LogLevel,
    get_logger,
    configure_logging,
    print_table,
    print_kv,
)
from koda.mom.sandbox import (
    Sandbox,
    SandboxConfig,
    ResourceLimits,
    ExecutionResult,
    BaseExecutor,
    HostExecutor,
    DockerExecutor,
    VolumeMount,
    NetworkConfig,
    killProcessTree,
    execute_in_sandbox,
)
from koda.mom.store import (
    Store,
    Attachment,
    LoggedMessage,
    MessageHistory,
    processAttachments,
    logMessage,
)

# Tools - Result types
from koda.mom.tools import (
    ToolResult,
    ReadResult,
    WriteResult,
    EditResult,
    BashResult,
    AttachResult,
    TruncationResult,
    EditOperation,
)

# Tools - Classes
from koda.mom.tools import (
    MomTools,
    ReadTool,
    WriteTool,
    EditTool,
    BashTool,
    AttachTool,
)

# Tools - Functions
from koda.mom.tools import (
    get_mom_tools,
    get_tool_definitions,
    register_tools,
    register_tool,
    get_registered_tools,
    read_file,
    write_file,
    edit_file,
    create_edit,
    execute_bash,
    execute_bash_async,
    attach_file,
    detect_mime_type,
    encode_file,
    truncate_head,
    truncate_tail,
    truncate_output,
    format_truncation_notice,
    format_size,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    AbortSignal,
)

__all__ = [
    # Agent
    "MomAgent",
    "MomAgentConfig",
    "ChannelConfig",
    "ChannelMemory",
    # Context
    "ContextManager",
    "MomSettings",
    "MomSettingsManager",
    "SessionManagerClient",
    # Events
    "EventsWatcher",
    "ScheduledEvent",
    "CronParser",
    # Log
    "StructuredLogger",
    "LogEntry",
    "LogLevel",
    "get_logger",
    "configure_logging",
    "print_table",
    "print_kv",
    # Sandbox
    "Sandbox",
    "SandboxConfig",
    "ResourceLimits",
    "ExecutionResult",
    "BaseExecutor",
    "HostExecutor",
    "DockerExecutor",
    "VolumeMount",
    "NetworkConfig",
    "killProcessTree",
    "execute_in_sandbox",
    # Store
    "Store",
    "Attachment",
    "LoggedMessage",
    "MessageHistory",
    "processAttachments",
    "logMessage",
    # Tools - Result types
    "ToolResult",
    "ReadResult",
    "WriteResult",
    "EditResult",
    "BashResult",
    "AttachResult",
    "TruncationResult",
    "EditOperation",
    # Tools - Classes
    "MomTools",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "BashTool",
    "AttachTool",
    # Tools - Functions
    "get_mom_tools",
    "get_tool_definitions",
    "register_tools",
    "register_tool",
    "get_registered_tools",
    "read_file",
    "write_file",
    "edit_file",
    "create_edit",
    "execute_bash",
    "execute_bash_async",
    "attach_file",
    "detect_mime_type",
    "encode_file",
    "truncate_head",
    "truncate_tail",
    "truncate_output",
    "format_truncation_notice",
    "format_size",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "AbortSignal",
]

__version__ = "1.0.0"
