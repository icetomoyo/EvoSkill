"""
Message Formatting
Equivalent to Pi Mono's packages/coding-agent/src/core/messages.ts

Message formatting utilities for display.
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Types of messages"""
    TEXT = "text"
    CODE = "code"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    THINKING = "thinking"


@dataclass
class FormattedMessage:
    """Formatted message for display"""
    type: MessageType
    content: str
    metadata: Dict[str, Any]
    prefix: str = ""
    suffix: str = ""


class MessageFormatter:
    """
    Formatter for agent messages.
    
    Converts raw messages to formatted display versions.
    
    Example:
        >>> formatter = MessageFormatter()
        >>> formatted = formatter.format_assistant_message(message)
        >>> print(formatted.content)
    """
    
    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
    }
    
    def __init__(self, use_colors: bool = True, max_width: int = 80):
        """
        Initialize formatter.
        
        Args:
            use_colors: Enable ANSI colors
            max_width: Maximum line width
        """
        self.use_colors = use_colors
        self.max_width = max_width
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
    
    def format_assistant_message(self, message: Dict[str, Any]) -> FormattedMessage:
        """
        Format assistant message.
        
        Args:
            message: Raw message dict
            
        Returns:
            FormattedMessage
        """
        content = message.get("content", "")
        
        if isinstance(content, list):
            # Handle content blocks
            formatted_parts = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "text")
                    if block_type == "text":
                        formatted_parts.append(block.get("text", ""))
                    elif block_type == "thinking":
                        formatted_parts.append(self._format_thinking(block.get("thinking", "")))
                    elif block_type == "tool_use":
                        formatted_parts.append(self._format_tool_use(block))
            
            formatted_content = "\n\n".join(formatted_parts)
        else:
            formatted_content = str(content)
        
        return FormattedMessage(
            type=MessageType.TEXT,
            content=formatted_content,
            metadata=message.get("metadata", {})
        )
    
    def format_tool_result(
        self,
        tool_name: str,
        result: Any,
        is_error: bool = False
    ) -> FormattedMessage:
        """
        Format tool execution result.
        
        Args:
            tool_name: Name of tool
            result: Tool result
            is_error: Whether result is an error
            
        Returns:
            FormattedMessage
        """
        if is_error:
            prefix = self.colorize("✗", "red")
            content = f"{prefix} Tool '{tool_name}' failed: {result}"
            msg_type = MessageType.ERROR
        else:
            prefix = self.colorize("✓", "green")
            content = f"{prefix} Tool '{tool_name}' executed"
            if result:
                content += f"\n{self._indent(str(result))}"
            msg_type = MessageType.TOOL_RESULT
        
        return FormattedMessage(
            type=msg_type,
            content=content,
            metadata={"tool": tool_name, "error": is_error}
        )
    
    def format_tool_use(self, tool_name: str, arguments: Dict[str, Any]) -> FormattedMessage:
        """
        Format tool use call.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            FormattedMessage
        """
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in arguments.items())
        content = f"{self.colorize('▶', 'blue')} Using tool: {tool_name}({args_str})"
        
        return FormattedMessage(
            type=MessageType.TOOL_USE,
            content=content,
            metadata={"tool": tool_name, "arguments": arguments}
        )
    
    def format_code_block(
        self,
        code: str,
        language: Optional[str] = None,
        filename: Optional[str] = None
    ) -> FormattedMessage:
        """
        Format code block.
        
        Args:
            code: Code content
            language: Programming language
            filename: Source filename
            
        Returns:
            FormattedMessage
        """
        header = ""
        if filename:
            header = f"{self.colorize('─', 'dim') * 3} {filename} {self.colorize('─', 'dim') * 3}\n"
        
        # Add syntax highlighting hints if available
        lang_tag = language or ""
        content = f"{header}```{lang_tag}\n{code}\n```"
        
        return FormattedMessage(
            type=MessageType.CODE,
            content=content,
            metadata={"language": language, "filename": filename}
        )
    
    def format_error(self, error: str, context: Optional[str] = None) -> FormattedMessage:
        """
        Format error message.
        
        Args:
            error: Error message
            context: Additional context
            
        Returns:
            FormattedMessage
        """
        content = f"{self.colorize('Error:', 'red')} {error}"
        if context:
            content += f"\n{self.colorize('Context:', 'dim')} {context}"
        
        return FormattedMessage(
            type=MessageType.ERROR,
            content=content,
            metadata={"error": error}
        )
    
    def format_warning(self, warning: str) -> FormattedMessage:
        """
        Format warning message.
        
        Args:
            warning: Warning message
            
        Returns:
            FormattedMessage
        """
        content = f"{self.colorize('Warning:', 'yellow')} {warning}"
        
        return FormattedMessage(
            type=MessageType.WARNING,
            content=content,
            metadata={"warning": warning}
        )
    
    def format_info(self, info: str) -> FormattedMessage:
        """
        Format info message.
        
        Args:
            info: Info message
            
        Returns:
            FormattedMessage
        """
        content = f"{self.colorize('ℹ', 'blue')} {info}"
        
        return FormattedMessage(
            type=MessageType.INFO,
            content=content,
            metadata={}
        )
    
    def format_thinking(self, content: str) -> FormattedMessage:
        """
        Format thinking/reasoning content.
        
        Args:
            content: Thinking content
            
        Returns:
            FormattedMessage
        """
        header = self.colorize("💭 Thinking...", "dim")
        formatted = f"{header}\n{self._indent(content, prefix='│ ')}"
        
        return FormattedMessage(
            type=MessageType.THINKING,
            content=formatted,
            metadata={},
            prefix="<thinking>",
            suffix="</thinking>"
        )
    
    def format_diff(
        self,
        original: str,
        modified: str,
        filename: Optional[str] = None
    ) -> FormattedMessage:
        """
        Format code diff.
        
        Args:
            original: Original code
            modified: Modified code
            filename: Filename
            
        Returns:
            FormattedMessage
        """
        lines = []
        
        if filename:
            lines.append(self.colorize(f"--- {filename}", "dim"))
        
        # Simple line-by-line diff
        orig_lines = original.split('\n')
        mod_lines = modified.split('\n')
        
        for i, (old, new) in enumerate(zip(orig_lines, mod_lines)):
            if old != new:
                lines.append(self.colorize(f"- {old}", "red"))
                lines.append(self.colorize(f"+ {new}", "green"))
            else:
                lines.append(f"  {old}")
        
        # Handle remaining lines
        if len(orig_lines) > len(mod_lines):
            for old in orig_lines[len(mod_lines):]:
                lines.append(self.colorize(f"- {old}", "red"))
        elif len(mod_lines) > len(orig_lines):
            for new in mod_lines[len(orig_lines):]:
                lines.append(self.colorize(f"+ {new}", "green"))
        
        content = '\n'.join(lines)
        
        return FormattedMessage(
            type=MessageType.CODE,
            content=content,
            metadata={"diff": True}
        )
    
    def format_list(
        self,
        items: List[str],
        ordered: bool = False,
        bullet: str = "•"
    ) -> str:
        """
        Format a list.
        
        Args:
            items: List items
            ordered: Number the list
            bullet: Bullet character
            
        Returns:
            Formatted list string
        """
        lines = []
        for i, item in enumerate(items, 1):
            if ordered:
                prefix = f"{i}."
            else:
                prefix = bullet
            lines.append(f"{prefix} {item}")
        return '\n'.join(lines)
    
    def truncate(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate text to max length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix for truncated text
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    def _format_thinking(self, content: str) -> str:
        """Format thinking block"""
        return self.colorize(f"[Thinking: {content[:50]}...]", "dim")
    
    def _format_tool_use(self, block: Dict[str, Any]) -> str:
        """Format tool use block"""
        tool_name = block.get("name", "unknown")
        return self.colorize(f"[Using tool: {tool_name}]", "blue")
    
    def _indent(self, text: str, prefix: str = "    ") -> str:
        """Indent text"""
        lines = text.split('\n')
        return '\n'.join(prefix + line for line in lines)


# Markdown formatter
class MarkdownFormatter(MessageFormatter):
    """Formatter that outputs Markdown"""
    
    def __init__(self, max_width: int = 80):
        super().__init__(use_colors=False, max_width=max_width)
    
    def format_code_block(
        self,
        code: str,
        language: Optional[str] = None,
        filename: Optional[str] = None
    ) -> FormattedMessage:
        """Format as Markdown code block"""
        lang = language or ""
        content = f"```{lang}\n{code}\n```"
        
        if filename:
            content = f"**{filename}**\n\n{content}"
        
        return FormattedMessage(
            type=MessageType.CODE,
            content=content,
            metadata={"language": language, "filename": filename}
        )
    
    def format_tool_use(self, tool_name: str, arguments: Dict[str, Any]) -> FormattedMessage:
        """Format tool use as Markdown"""
        import json
        args_json = json.dumps(arguments, indent=2)
        content = f"**Tool:** `{tool_name}`\n\n```json\n{args_json}\n```"
        
        return FormattedMessage(
            type=MessageType.TOOL_USE,
            content=content,
            metadata={"tool": tool_name, "arguments": arguments}
        )


__all__ = [
    "MessageFormatter",
    "MarkdownFormatter",
    "FormattedMessage",
    "MessageType",
]
