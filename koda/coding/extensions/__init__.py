"""
Extensions System
Equivalent to Pi Mono's packages/coding-agent/src/extensions/

Plugin system for extending Koda functionality.
"""
from .registry import ExtensionRegistry, get_extension_registry
from .extension import Extension, ExtensionMetadata, ExtensionAPI
from .hooks import HookPoint, HookManager

__all__ = [
    "Extension",
    "ExtensionMetadata",
    "ExtensionAPI",
    "ExtensionRegistry",
    "get_extension_registry",
    "HookPoint",
    "HookManager",
]
