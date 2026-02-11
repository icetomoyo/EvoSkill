"""
Footer Data Provider
Equivalent to Pi Mono's packages/coding-agent/src/core/footer-data-provider.ts

Provides data for UI footer display.
"""
import os
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FooterData:
    """Data for footer display"""
    model: str = ""
    provider: str = ""
    tokens_used: int = 0
    tokens_remaining: int = 0
    cost: float = 0.0
    status: str = "ready"
    git_branch: Optional[str] = None
    git_status: str = ""
    filename: Optional[str] = None
    line_count: int = 0
    column: int = 0
    mode: str = "insert"
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class FooterDataProvider:
    """
    Provider for footer information display.
    
    Aggregates data from various sources for UI footer.
    
    Example:
        >>> provider = FooterDataProvider()
        >>> provider.update_model("gpt-4", "openai")
        >>> provider.update_tokens(1500, 4000)
        >>> data = provider.get_data()
        >>> print(f"{data.model} | {data.tokens_used} tokens")
    """
    
    def __init__(self):
        self._data = FooterData()
        self._providers: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register default data providers"""
        self.register_provider("git", self._get_git_info)
        self.register_provider("system", self._get_system_info)
    
    def register_provider(self, name: str, provider: Callable[[], Dict[str, Any]]):
        """
        Register a data provider function.
        
        Args:
            name: Provider name
            provider: Function returning data dict
        """
        self._providers[name] = provider
    
    def update_model(self, model: str, provider: str):
        """Update model information"""
        self._data.model = model
        self._data.provider = provider
    
    def update_tokens(self, used: int, remaining: int):
        """Update token usage"""
        self._data.tokens_used = used
        self._data.tokens_remaining = remaining
    
    def update_cost(self, cost: float):
        """Update cost information"""
        self._data.cost = cost
    
    def update_status(self, status: str):
        """Update status message"""
        self._data.status = status
    
    def update_cursor(self, line: int, column: int):
        """Update cursor position"""
        self._data.line_count = line
        self._data.column = column
    
    def update_filename(self, filename: Optional[str]):
        """Update current filename"""
        self._data.filename = filename
    
    def update_mode(self, mode: str):
        """Update editor mode"""
        self._data.mode = mode
    
    def get_data(self) -> FooterData:
        """
        Get current footer data.
        
        Returns:
            FooterData with all current values
        """
        # Update timestamp
        self._data.timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Collect data from providers
        for name, provider in self._providers.items():
            try:
                data = provider()
                for key, value in data.items():
                    if hasattr(self._data, key):
                        setattr(self._data, key, value)
            except Exception:
                pass  # Ignore provider errors
        
        return self._data
    
    def get_formatted(self, format_str: Optional[str] = None) -> str:
        """
        Get formatted footer string.
        
        Args:
            format_str: Format string with {placeholders}
            
        Returns:
            Formatted footer string
        """
        data = self.get_data()
        
        if format_str is None:
            # Default format
            parts = []
            
            if data.model:
                parts.append(f"{data.model}")
            
            if data.tokens_used:
                parts.append(f"{data.tokens_used}T")
            
            if data.git_branch:
                git_info = f"{data.git_branch}"
                if data.git_status:
                    git_info += f" {data.git_status}"
                parts.append(git_info)
            
            if data.filename:
                parts.append(f"{data.filename}:{data.line_count}:{data.column}")
            
            parts.append(data.mode)
            parts.append(data.timestamp)
            
            return " | ".join(parts)
        
        return format_str.format(
            model=data.model,
            provider=data.provider,
            tokens_used=data.tokens_used,
            tokens_remaining=data.tokens_remaining,
            cost=f"${data.cost:.4f}",
            status=data.status,
            git_branch=data.git_branch or "",
            git_status=data.git_status,
            filename=data.filename or "",
            line=data.line_count,
            column=data.column,
            mode=data.mode,
            timestamp=data.timestamp
        )
    
    def _get_git_info(self) -> Dict[str, Any]:
        """Get git information"""
        try:
            from .utils.git import GitUtils
            git = GitUtils()
            
            if not git.is_git_repo():
                return {}
            
            info = git.get_info()
            status = git.get_status()
            
            git_status = ""
            if status["modified"] or status["staged"]:
                git_status = "*"
            if status["untracked"]:
                git_status += "+"
            
            return {
                "git_branch": info.branch,
                "git_status": git_status
            }
        except Exception:
            return {}
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {}


class StatusBarManager:
    """
    Manager for status bar with multiple sections.
    
    Example:
        >>> manager = StatusBarManager()
        >>> manager.add_section("model", "gpt-4", color="blue")
        >>> manager.add_section("tokens", "1500/4000")
        >>> print(manager.render())
    """
    
    def __init__(self, width: int = 80):
        self.width = width
        self._sections: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []
    
    def add_section(
        self,
        id: str,
        content: str,
        color: Optional[str] = None,
        align: str = "left"
    ):
        """
        Add or update a section.
        
        Args:
            id: Section identifier
            content: Display content
            color: Color name
            align: "left", "right", or "center"
        """
        self._sections[id] = {
            "content": content,
            "color": color,
            "align": align
        }
        if id not in self._order:
            self._order.append(id)
    
    def update_section(self, id: str, content: str):
        """Update section content"""
        if id in self._sections:
            self._sections[id]["content"] = content
    
    def remove_section(self, id: str):
        """Remove a section"""
        if id in self._sections:
            del self._sections[id]
            self._order.remove(id)
    
    def render(self) -> str:
        """
        Render status bar.
        
        Returns:
            Formatted status bar string
        """
        left_parts = []
        right_parts = []
        
        for id in self._order:
            section = self._sections[id]
            content = section["content"]
            
            if section.get("color"):
                content = self._colorize(content, section["color"])
            
            if section.get("align") == "right":
                right_parts.append(content)
            else:
                left_parts.append(content)
        
        left_text = " ".join(left_parts)
        right_text = " ".join(right_parts)
        
        # Calculate padding
        padding = self.width - len(left_text) - len(right_text) - 2
        if padding < 1:
            padding = 1
        
        return f"{left_text}{ ' ' * padding }{right_text}"
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply ANSI color"""
        colors = {
            "black": "\033[30m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "magenta": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m",
            "reset": "\033[0m"
        }
        return f"{colors.get(color, '')}{text}{colors['reset']}"


# Global instance
_default_provider: Optional[FooterDataProvider] = None


def get_default_provider() -> FooterDataProvider:
    """Get default footer data provider"""
    global _default_provider
    if _default_provider is None:
        _default_provider = FooterDataProvider()
    return _default_provider


def get_footer() -> str:
    """Get formatted footer using default provider"""
    provider = get_default_provider()
    return provider.get_formatted()


__all__ = [
    "FooterDataProvider",
    "FooterData",
    "StatusBarManager",
    "get_default_provider",
    "get_footer",
]
