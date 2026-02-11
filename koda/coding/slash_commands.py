"""
Slash Commands
Equivalent to Pi Mono's packages/coding-agent/src/core/slash-commands.ts

/ command handling for quick actions.
"""
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum


class CommandResultType(Enum):
    """Command result types"""
    SUCCESS = "success"
    ERROR = "error"
    HELP = "help"
    CONFIRM = "confirm"


@dataclass
class CommandResult:
    """Slash command result"""
    type: CommandResultType
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class SlashCommand:
    """Slash command definition"""
    name: str
    description: str
    handler: Callable[..., CommandResult]
    aliases: List[str] = None
    args_help: str = ""
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class SlashCommandRegistry:
    """
    Registry for slash commands.
    
    Manages /command handlers and dispatch.
    
    Example:
        >>> registry = SlashCommandRegistry()
        >>> @registry.command("help")
        ... def cmd_help():
        ...     return CommandResult(CommandResultType.HELP, "Available commands...")
        >>> result = registry.execute("/help")
    """
    
    def __init__(self):
        self._commands: Dict[str, SlashCommand] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command name
    
    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., CommandResult],
        aliases: Optional[List[str]] = None,
        args_help: str = ""
    ) -> SlashCommand:
        """
        Register a slash command.
        
        Args:
            name: Command name (without /)
            description: Command description
            handler: Command handler function
            aliases: Alternative names
            args_help: Arguments help text
            
        Returns:
            Registered command
        """
        command = SlashCommand(
            name=name,
            description=description,
            handler=handler,
            aliases=aliases or [],
            args_help=args_help
        )
        
        self._commands[name] = command
        
        # Register aliases
        for alias in (aliases or []):
            self._aliases[alias] = name
        
        return command
    
    def command(
        self,
        name: str,
        description: str = "",
        aliases: Optional[List[str]] = None,
        args_help: str = ""
    ):
        """
        Decorator to register a command.
        
        Example:
            >>> @registry.command("compact", "Compact conversation")
            ... def cmd_compact():
            ...     return CommandResult(CommandResultType.SUCCESS, "Compacted!")
        """
        def decorator(func):
            self.register(name, description, func, aliases, args_help)
            return func
        return decorator
    
    def execute(self, input_text: str, context: Optional[Dict] = None) -> Optional[CommandResult]:
        """
        Execute a slash command.
        
        Args:
            input_text: Full command text (e.g., "/help" or "/model gpt-4")
            context: Optional context for command
            
        Returns:
            Command result or None if not a command
        """
        if not input_text.startswith('/'):
            return None
        
        # Parse command
        parts = input_text[1:].strip().split()
        if not parts:
            return None
        
        command_name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Resolve alias
        if command_name in self._aliases:
            command_name = self._aliases[command_name]
        
        # Find command
        command = self._commands.get(command_name)
        if not command:
            return CommandResult(
                type=CommandResultType.ERROR,
                message=f"Unknown command: /{command_name}"
            )
        
        # Execute
        try:
            return command.handler(*args, context=context)
        except TypeError as e:
            return CommandResult(
                type=CommandResultType.ERROR,
                message=f"Invalid arguments. Usage: /{command_name} {command.args_help}"
            )
        except Exception as e:
            return CommandResult(
                type=CommandResultType.ERROR,
                message=f"Command failed: {str(e)}"
            )
    
    def is_command(self, text: str) -> bool:
        """Check if text is a slash command"""
        return text.startswith('/')
    
    def get_commands(self) -> List[SlashCommand]:
        """Get all registered commands"""
        return list(self._commands.values())
    
    def get_help(self) -> str:
        """Generate help text"""
        lines = ["Available commands:", ""]
        
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            alias_str = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"  /{cmd.name}{alias_str}")
            lines.append(f"    {cmd.description}")
            if cmd.args_help:
                lines.append(f"    Usage: /{cmd.name} {cmd.args_help}")
            lines.append("")
        
        return "\n".join(lines)


# Built-in commands
class BuiltInCommands:
    """Built-in slash commands"""
    
    @staticmethod
    def register_defaults(registry: SlashCommandRegistry):
        """Register default commands"""
        
        @registry.command("help", "Show available commands", aliases=["h", "?"])
        def cmd_help(context=None):
            return CommandResult(
                type=CommandResultType.HELP,
                message=registry.get_help()
            )
        
        @registry.command("compact", "Compact conversation context", aliases=["c"])
        def cmd_compact(context=None):
            # This would trigger compaction
            return CommandResult(
                type=CommandResultType.SUCCESS,
                message="Context compacted successfully",
                data={"action": "compact"}
            )
        
        @registry.command("model", "Switch model", args_help="<model-name>")
        def cmd_model(model_name: str = None, context=None):
            if not model_name:
                return CommandResult(
                    type=CommandResultType.ERROR,
                    message="Please specify a model. Usage: /model <model-name>"
                )
            return CommandResult(
                type=CommandResultType.SUCCESS,
                message=f"Switched to model: {model_name}",
                data={"model": model_name}
            )
        
        @registry.command("clear", "Clear conversation", aliases=["cls"])
        def cmd_clear(context=None):
            return CommandResult(
                type=CommandResultType.SUCCESS,
                message="Conversation cleared",
                data={"action": "clear"}
            )
        
        @registry.command("undo", "Undo last action", aliases=["u"])
        def cmd_undo(context=None):
            return CommandResult(
                type=CommandResultType.SUCCESS,
                message="Last action undone",
                data={"action": "undo"}
            )


# Global registry
_default_registry: Optional[SlashCommandRegistry] = None


def get_default_registry() -> SlashCommandRegistry:
    """Get default command registry with built-in commands"""
    global _default_registry
    if _default_registry is None:
        _default_registry = SlashCommandRegistry()
        BuiltInCommands.register_defaults(_default_registry)
    return _default_registry


def execute_command(text: str, context: Optional[Dict] = None) -> Optional[CommandResult]:
    """Execute a slash command using default registry"""
    registry = get_default_registry()
    return registry.execute(text, context)


__all__ = [
    "SlashCommandRegistry",
    "SlashCommand",
    "CommandResult",
    "CommandResultType",
    "BuiltInCommands",
    "execute_command",
    "get_default_registry",
]
