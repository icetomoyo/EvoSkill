"""
LLM Provider Abstract Base Class

Defines the unified interface for all LLM providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from datetime import datetime


@dataclass
class ToolCall:
    """Tool call from assistant"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Tool execution result"""
    tool_call_id: str
    output: str
    error: Optional[str] = None


@dataclass
class Message:
    """
    Unified message format
    
    Supports text, images, tool calls, and tool results.
    """
    role: str  # "system", "user", "assistant", "tool"
    content: Union[str, List[Dict[str, Any]]]
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # For tool messages
    
    @classmethod
    def system(cls, content: str) -> "Message":
        """Create system message"""
        return cls(role="system", content=content)
    
    @classmethod
    def user(cls, content: str, images: Optional[List[str]] = None) -> "Message":
        """Create user message (optionally with images)"""
        if images:
            content_parts = [{"type": "text", "text": content}]
            for img in images:
                content_parts.append({"type": "image_url", "image_url": {"url": img}})
            return cls(role="user", content=content_parts)
        return cls(role="user", content=content)
    
    @classmethod
    def assistant(cls, content: str, tool_calls: Optional[List[ToolCall]] = None) -> "Message":
        """Create assistant message"""
        return cls(role="assistant", content=content, tool_calls=tool_calls)
    
    @classmethod
    def tool(cls, tool_call_id: str, output: str, name: Optional[str] = None) -> "Message":
        """Create tool result message"""
        return cls(role="tool", content=output, tool_call_id=tool_call_id, name=name)


@dataclass
class Model:
    """Model information"""
    id: str
    provider: str
    name: str
    context_window: int
    max_output_tokens: Optional[int] = None
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True


@dataclass
class Usage:
    """Token usage information"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    @property
    def cost(self, price_per_1k_prompt: float = 0.0, price_per_1k_completion: float = 0.0) -> float:
        """Calculate estimated cost"""
        return (self.prompt_tokens / 1000 * price_per_1k_prompt + 
                self.completion_tokens / 1000 * price_per_1k_completion)


@dataclass
class StreamEvent:
    """Streaming event from LLM"""
    type: str  # "text", "tool_call", "thinking", "usage", "stop"
    data: Any
    
    @classmethod
    def text(cls, content: str) -> "StreamEvent":
        return cls(type="text", data=content)
    
    @classmethod
    def tool_call(cls, tool_call: ToolCall) -> "StreamEvent":
        return cls(type="tool_call", data=tool_call)
    
    @classmethod
    def thinking(cls, content: str) -> "StreamEvent":
        return cls(type="thinking", data=content)
    
    @classmethod
    def usage(cls, usage: Usage) -> "StreamEvent":
        return cls(type="usage", data=usage)
    
    @classmethod
    def stop(cls, reason: str = "stop") -> "StreamEvent":
        return cls(type="stop", data=reason)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers
    
    All providers must implement:
    - chat(): Main chat interface with streaming support
    - get_models(): List available models
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[StreamEvent]:
        """
        Main chat interface
        
        Args:
            messages: List of conversation messages
            model: Model ID (uses default if not specified)
            tools: Available tools for function calling
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream responses
            **kwargs: Additional provider-specific options
            
        Yields:
            StreamEvent objects (text, tool_call, thinking, usage, stop)
        """
        pass
    
    @abstractmethod
    async def get_models(self) -> List[Model]:
        """Get list of available models"""
        pass
    
    def get_default_model(self) -> str:
        """Get default model ID"""
        return "gpt-4o-mini"  # Override in subclasses
    
    def supports_feature(self, feature: str) -> bool:
        """Check if provider supports a feature"""
        features = {
            "streaming": True,
            "tools": True,
            "vision": True,
            "thinking": False,  # Override for Claude
        }
        return features.get(feature, False)
