"""
Extensions System
Equivalent to Pi Mono's packages/coding-agent/src/extensions/

Plugin system for extending Koda functionality.

Components:
- types.py: Extension types, events, API definitions
- loader.py: Extension discovery and loading
- runner.py: Extension lifecycle and execution management
- wrapper.py: Extension instance wrappers
- registry.py: Extension registry
- extension.py: Base extension class
- hooks.py: Hook system
"""

# Core types and base classes
from .types import (
    ExtensionEventType,
    ExtensionEvent,
    ExtensionManifest,
    ExtensionConfig,
    ExtensionAPI,
    Extension,
    EventFilter,
    EventSubscription,
    ToolDefinition,
    HookPriority,
    HookRegistration,
    Permission,
    ExtensionContext,
    ExtensionResult,
    HookPoint,
    ExtensionCapability,
    ExtensionStatus,
)

# Loader
from .loader import (
    ExtensionLoader,
    DiscoveredExtension,
    LoadResult,
    ValidationResult,
    get_extension_loader,
    reset_extension_loader,
)

# Runner
from .runner import (
    ExtensionRunner,
    RunnerStats,
    ExtensionState,
    get_extension_runner,
    reset_extension_runner,
)

# Wrapper
from .wrapper import (
    ExtensionWrapper,
    WrappedExtensionRegistry,
    ExtensionInvocation,
    ExtensionMetrics,
)

# Registry
from .registry import (
    ExtensionRegistry,
    get_extension_registry,
)

# Hooks
from .hooks import (
    HookManager,
    on_message_receive,
    on_response_send,
    on_tool_call,
)

__all__ = [
    # Types
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

    # Loader
    "ExtensionLoader",
    "DiscoveredExtension",
    "LoadResult",
    "ValidationResult",
    "get_extension_loader",
    "reset_extension_loader",

    # Runner
    "ExtensionRunner",
    "RunnerStats",
    "ExtensionState",
    "get_extension_runner",
    "reset_extension_runner",

    # Wrapper
    "ExtensionWrapper",
    "WrappedExtensionRegistry",
    "ExtensionInvocation",
    "ExtensionMetrics",

    # Registry
    "ExtensionRegistry",
    "get_extension_registry",

    # Hooks
    "HookManager",
    "on_message_receive",
    "on_response_send",
    "on_tool_call",
]
