"""
Key Bindings
Equivalent to Pi Mono's packages/coding-agent/src/core/keybindings.ts

Keyboard shortcut management for interactive mode.
"""
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum
import re


class KeyModifier(Enum):
    """Key modifiers"""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    META = "meta"  # Cmd on Mac, Win on Windows


@dataclass
class KeyBinding:
    """Key binding definition"""
    key: str
    action: str
    modifiers: Set[KeyModifier] = None
    description: str = ""
    context: str = "global"  # global, input, chat, etc.
    
    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = set()
    
    def matches(self, key: str, modifiers: Set[KeyModifier]) -> bool:
        """Check if key combination matches this binding"""
        return self.key.lower() == key.lower() and self.modifiers == modifiers
    
    def __str__(self) -> str:
        """String representation like 'Ctrl+C'"""
        parts = []
        if KeyModifier.CTRL in self.modifiers:
            parts.append("Ctrl")
        if KeyModifier.ALT in self.modifiers:
            parts.append("Alt")
        if KeyModifier.SHIFT in self.modifiers:
            parts.append("Shift")
        if KeyModifier.META in self.modifiers:
            parts.append("Cmd" if is_mac() else "Win")
        parts.append(self.key.upper())
        return "+".join(parts)


def is_mac() -> bool:
    """Check if running on macOS"""
    import sys
    return sys.platform == "darwin"


class KeyBindingManager:
    """
    Manager for keyboard shortcuts.
    
    Handles key binding registration, lookup, and execution.
    
    Example:
        >>> manager = KeyBindingManager()
        >>> manager.bind("ctrl+c", "copy", copy_handler)
        >>> manager.bind("ctrl+v", "paste", paste_handler)
        >>> action = manager.lookup("c", {KeyModifier.CTRL})
        >>> if action:
        ...     action.handler()
    """
    
    def __init__(self):
        self._bindings: Dict[str, KeyBinding] = {}  # action -> binding
        self._handlers: Dict[str, Callable] = {}  # action -> handler
        self._context_bindings: Dict[str, List[str]] = {}  # context -> actions
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default key bindings"""
        defaults = [
            # Global bindings
            KeyBinding("c", "copy", {KeyModifier.CTRL}, "Copy selection"),
            KeyBinding("v", "paste", {KeyModifier.CTRL}, "Paste"),
            KeyBinding("x", "cut", {KeyModifier.CTRL}, "Cut"),
            KeyBinding("z", "undo", {KeyModifier.CTRL}, "Undo"),
            KeyBinding("y", "redo", {KeyModifier.CTRL}, "Redo"),
            KeyBinding("a", "select_all", {KeyModifier.CTRL}, "Select all"),
            KeyBinding("f", "find", {KeyModifier.CTRL}, "Find"),
            
            # Chat bindings
            KeyBinding("enter", "submit", set(), "Submit message", "input"),
            KeyBinding("enter", "newline", {KeyModifier.SHIFT}, "New line", "input"),
            KeyBinding("escape", "cancel", set(), "Cancel", "input"),
            KeyBinding("up", "history_prev", set(), "Previous history", "input"),
            KeyBinding("down", "history_next", set(), "Next history", "input"),
            KeyBinding("tab", "complete", set(), "Autocomplete", "input"),
            
            # Navigation
            KeyBinding("k", "clear", {KeyModifier.CTRL}, "Clear screen", "chat"),
            KeyBinding("l", "focus_input", {KeyModifier.CTRL}, "Focus input", "chat"),
            KeyBinding("q", "quit", {KeyModifier.CTRL}, "Quit application", "global"),
            KeyBinding("n", "new_chat", {KeyModifier.CTRL}, "New chat", "global"),
            
            # Help
            KeyBinding("h", "help", {KeyModifier.CTRL}, "Show help", "global"),
            KeyBinding("?", "help", {KeyModifier.SHIFT}, "Show help", "global"),
        ]
        
        for binding in defaults:
            self._bindings[binding.action] = binding
            if binding.context not in self._context_bindings:
                self._context_bindings[binding.context] = []
            self._context_bindings[binding.context].append(binding.action)
    
    def bind(
        self,
        key_combo: str,
        action: str,
        handler: Optional[Callable] = None,
        description: str = "",
        context: str = "global"
    ):
        """
        Register a key binding.
        
        Args:
            key_combo: Key combination like "ctrl+c" or "ctrl+shift+a"
            action: Action identifier
            handler: Function to execute
            description: Human-readable description
            context: Binding context
        """
        # Parse key combo
        parts = key_combo.lower().split("+")
        key = parts[-1]
        modifiers = set()
        
        for part in parts[:-1]:
            if part == "ctrl":
                modifiers.add(KeyModifier.CTRL)
            elif part == "alt":
                modifiers.add(KeyModifier.ALT)
            elif part == "shift":
                modifiers.add(KeyModifier.SHIFT)
            elif part in ("cmd", "meta", "win"):
                modifiers.add(KeyModifier.META)
        
        binding = KeyBinding(
            key=key,
            action=action,
            modifiers=modifiers,
            description=description,
            context=context
        )
        
        self._bindings[action] = binding
        
        if handler:
            self._handlers[action] = handler
        
        if context not in self._context_bindings:
            self._context_bindings[context] = []
        if action not in self._context_bindings[context]:
            self._context_bindings[context].append(action)
    
    def unbind(self, action: str):
        """Remove a key binding"""
        if action in self._bindings:
            binding = self._bindings[action]
            del self._bindings[action]
            
            if action in self._handlers:
                del self._handlers[action]
            
            if binding.context in self._context_bindings:
                if action in self._context_bindings[binding.context]:
                    self._context_bindings[binding.context].remove(action)
    
    def lookup(
        self,
        key: str,
        modifiers: Optional[Set[KeyModifier]] = None,
        context: str = "global"
    ) -> Optional[str]:
        """
        Look up action for key combination.
        
        Args:
            key: Key pressed
            modifiers: Active modifiers
            context: Current context
            
        Returns:
            Action identifier or None
        """
        modifiers = modifiers or set()
        
        # Check context-specific bindings first
        if context in self._context_bindings:
            for action in self._context_bindings[context]:
                binding = self._bindings.get(action)
                if binding and binding.matches(key, modifiers):
                    return action
        
        # Check global bindings
        if context != "global" and "global" in self._context_bindings:
            for action in self._context_bindings["global"]:
                binding = self._bindings.get(action)
                if binding and binding.matches(key, modifiers):
                    return action
        
        return None
    
    def execute(self, action: str, *args, **kwargs) -> bool:
        """
        Execute action handler.
        
        Args:
            action: Action to execute
            *args, **kwargs: Arguments for handler
            
        Returns:
            True if handler executed
        """
        handler = self._handlers.get(action)
        if handler:
            handler(*args, **kwargs)
            return True
        return False
    
    def get_binding(self, action: str) -> Optional[KeyBinding]:
        """Get binding for action"""
        return self._bindings.get(action)
    
    def get_handler(self, action: str) -> Optional[Callable]:
        """Get handler for action"""
        return self._handlers.get(action)
    
    def list_bindings(self, context: Optional[str] = None) -> List[KeyBinding]:
        """
        List all bindings, optionally filtered by context.
        
        Args:
            context: Filter by context
            
        Returns:
            List of bindings
        """
        if context:
            actions = self._context_bindings.get(context, [])
            return [self._bindings[a] for a in actions if a in self._bindings]
        
        return list(self._bindings.values())
    
    def get_help_text(self, context: Optional[str] = None) -> str:
        """
        Generate help text for bindings.
        
        Args:
            context: Filter by context
            
        Returns:
            Formatted help text
        """
        lines = ["Keyboard Shortcuts:", ""]
        
        bindings = self.list_bindings(context)
        
        # Group by context
        by_context: Dict[str, List[KeyBinding]] = {}
        for binding in bindings:
            ctx = binding.context
            if ctx not in by_context:
                by_context[ctx] = []
            by_context[ctx].append(binding)
        
        for ctx, ctx_bindings in sorted(by_context.items()):
            lines.append(f"[{ctx.upper()}]")
            for binding in sorted(ctx_bindings, key=lambda b: str(b)):
                lines.append(f"  {str(binding):<20} {binding.description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def parse_key_input(self, input_str: str) -> tuple:
        """
        Parse key input string.
        
        Args:
            input_str: Input like "ctrl+c" or "escape"
            
        Returns:
            (key, modifiers)
        """
        parts = input_str.lower().split("+")
        key = parts[-1]
        modifiers = set()
        
        for part in parts[:-1]:
            if part == "ctrl":
                modifiers.add(KeyModifier.CTRL)
            elif part == "alt":
                modifiers.add(KeyModifier.ALT)
            elif part == "shift":
                modifiers.add(KeyModifier.SHIFT)
            elif part in ("cmd", "meta", "win"):
                modifiers.add(KeyModifier.META)
        
        return key, modifiers


# Default key binding manager instance
_default_manager: Optional[KeyBindingManager] = None


def get_default_manager() -> KeyBindingManager:
    """Get default key binding manager"""
    global _default_manager
    if _default_manager is None:
        _default_manager = KeyBindingManager()
    return _default_manager


def bind(
    key_combo: str,
    action: str,
    handler: Optional[Callable] = None,
    description: str = "",
    context: str = "global"
):
    """Bind key using default manager"""
    manager = get_default_manager()
    manager.bind(key_combo, action, handler, description, context)


def lookup(key: str, modifiers: Optional[Set[KeyModifier]] = None, context: str = "global") -> Optional[str]:
    """Lookup action using default manager"""
    manager = get_default_manager()
    return manager.lookup(key, modifiers, context)


__all__ = [
    "KeyBindingManager",
    "KeyBinding",
    "KeyModifier",
    "get_default_manager",
    "bind",
    "lookup",
]
