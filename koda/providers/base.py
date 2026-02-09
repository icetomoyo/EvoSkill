"""
Base Provider - Abstract base class for LLM providers

Based on Pi's ApiProvider interface
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional
from dataclasses import dataclass

from koda.core.multimodal_types import (
    Model, Message, AssistantMessage, StreamOptions, SimpleStreamOptions
)


@dataclass
class StreamEvent:
    """Base class for stream events"""
    type: str


@dataclass
class TextDeltaEvent(StreamEvent):
    """Text generation delta event"""
    type: str = "text_delta"
    delta: str = ""
    content_index: int = 0


@dataclass
class ThinkingDeltaEvent(StreamEvent):
    """Thinking/reasoning delta event"""
    type: str = "thinking_delta"
    delta: str = ""
    content_index: int = 0


@dataclass 
class ToolCallEvent(StreamEvent):
    """Tool call event"""
    type: str = "tool_call"
    tool_call: Any = None


@dataclass
class DoneEvent(StreamEvent):
    """Stream completed successfully"""
    type: str = "done"
    message: AssistantMessage = None


@dataclass
class ErrorEvent(StreamEvent):
    """Stream error"""
    type: str = "error"
    error: str = ""


class BaseProvider(ABC):
    """Abstract base class for LLM API providers"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property
    @abstractmethod
    def api_type(self) -> str:
        """API type identifier"""
        pass
    
    @abstractmethod
    async def stream(
        self,
        model: Model,
        messages: list[Message],
        options: StreamOptions
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream LLM response
        
        Yields StreamEvent objects:
        - TextDeltaEvent: Text generation progress
        - ThinkingDeltaEvent: Thinking/reasoning progress
        - ToolCallEvent: Tool call generated
        - DoneEvent: Completion successful
        - ErrorEvent: Error occurred
        """
        pass
    
    @abstractmethod
    def convert_messages(self, messages: list[Message]) -> list[Dict[str, Any]]:
        """
        Convert internal messages to provider-specific format
        """
        pass
    
    def supports_feature(self, feature: str) -> bool:
        """Check if provider supports a specific feature"""
        features = {
            'images': False,
            'thinking': False,
            'tool_calls': True,
            'streaming': True,
            'cache': False,
        }
        return features.get(feature, False)


class ProviderRegistry:
    """Registry of available providers"""
    
    _providers: Dict[str, BaseProvider] = {}
    
    @classmethod
    def register(cls, provider: BaseProvider) -> None:
        """Register a provider"""
        cls._providers[provider.name] = provider
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseProvider]:
        """Get a provider by name"""
        return cls._providers.get(name)
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names"""
        return list(cls._providers.keys())


def convert_content_to_provider_format(
    content,
    provider_type: str
) -> Any:
    """
    Convert content blocks to provider-specific format
    
    Args:
        content: str or list of TextContent/ImageContent
        provider_type: "openai", "anthropic", or "google"
        
    Returns:
        Provider-specific content format
    """
    from koda.core.multimodal_types import TextContent, ImageContent
    
    if isinstance(content, str):
        if provider_type == "anthropic":
            return [{"type": "text", "text": content}]
        elif provider_type == "google":
            return [{"text": content}]
        else:  # openai
            return content  # OpenAI accepts string for simple text
    
    # List of content blocks
    result = []
    for item in content:
        if isinstance(item, TextContent):
            if provider_type == "openai":
                result.append({"type": "text", "text": item.text})
            elif provider_type == "anthropic":
                result.append({"type": "text", "text": item.text})
            elif provider_type == "google":
                result.append({"text": item.text})
                
        elif isinstance(item, ImageContent):
            if provider_type == "openai":
                result.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{item.mimeType};base64,{item.data}"
                    }
                })
            elif provider_type == "anthropic":
                result.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": item.mimeType,
                        "data": item.data
                    }
                })
            elif provider_type == "google":
                result.append({
                    "inline_data": {
                        "mime_type": item.mimeType,
                        "data": item.data
                    }
                })
    
    return result
