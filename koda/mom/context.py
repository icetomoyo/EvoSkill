"""
Context Manager - Dynamic context management
Equivalent to Pi Mono's context.ts
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from koda.ai.types import Message, Context, Tool


class ContextManager:
    """
    Dynamic context management
    
    Manages conversation context with automatic window management
    """
    
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self._messages: List[Message] = []
        self._metadata: Dict[str, Any] = {}
    
    def add(self, message: Message) -> None:
        """Add message, auto-manage context window"""
        self._messages.append(message)
        
        # Check if we need to compact
        tokens = self._estimate_tokens()
        if tokens > self.max_tokens * 0.9:
            self._compact()
    
    def get_context(self, system_prompt: Optional[str] = None, tools: Optional[List[Tool]] = None) -> Context:
        """Get current context"""
        return Context(
            system_prompt=system_prompt,
            messages=list(self._messages),
            tools=tools
        )
    
    def clear(self) -> None:
        """Clear context"""
        self._messages = []
        self._metadata = {}
    
    def get_messages(self) -> List[Message]:
        """Get message list"""
        return list(self._messages)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata"""
        self._metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata"""
        return self._metadata.get(key)
    
    def _estimate_tokens(self) -> int:
        """Estimate token count"""
        total = 0
        for msg in self._messages:
            content = getattr(msg, 'content', '')
            if isinstance(content, str):
                total += len(content) // 4
            else:
                total += 4
        return total + len(self._messages) * 4
    
    def _compact(self) -> None:
        """Compact context by removing oldest messages"""
        keep_count = max(len(self._messages) // 2, 3)
        self._messages = self._messages[-keep_count:]
