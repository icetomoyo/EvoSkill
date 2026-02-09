"""
Koda AI - Unified LLM Interface

完全等效于 Pi Mono 的 packages/ai
支持 20+ providers, OAuth, Streaming, Tools, Vision
"""

# 基础类型
from koda.ai.types import (
    # Enums
    KnownApi,
    KnownProvider,
    ThinkingLevel,
    CacheRetention,
    StopReason,
    # Content types
    TextContent,
    ThinkingContent,
    ImageContent,
    ToolCall,
    Content,
    # Message types
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Message,
    # Context and Tools
    Tool,
    Context,
    Usage,
    # Options
    StreamOptions,
    SimpleStreamOptions,
    ThinkingBudgets,
    OpenRouterRouting,
    VercelGatewayRouting,
    OpenAICompletionsCompat,
    OpenAIResponsesCompat,
    # Model
    ModelInfo,
    # Events
    AssistantMessageEvent,
    AgentEventType,
    AgentEvent,
    AgentTool,
)

# Provider 基础
from koda.ai.provider_base import (
    BaseProvider,
    ProviderConfig,
    ProviderRegistry,
    get_provider_registry,
)

# Event Stream
from koda.ai.event_stream import (
    EventType,
    AssistantMessageEventStream,
    StreamBuffer,
    create_event_stream,
    stream_to_string,
    stream_to_messages,
)

# Registry
from koda.ai.registry import (
    ModelRegistry,
    ModelCapability,
    get_registry,
)

# Tokenizer
try:
    from koda.ai.tokenizer import Tokenizer
    HAS_TOKENIZER = True
except ImportError:
    HAS_TOKENIZER = False

# Legacy providers (will be refactored)
from koda.ai.providers.openai_provider import OpenAIProvider
from koda.ai.providers.anthropic_provider import AnthropicProvider
from koda.ai.providers.kimi_provider import KimiProvider

__all__ = [
    # Enums
    "KnownApi",
    "KnownProvider",
    "ThinkingLevel",
    "CacheRetention",
    "StopReason",
    "EventType",
    "AgentEventType",
    
    # Content
    "TextContent",
    "ThinkingContent", 
    "ImageContent",
    "ToolCall",
    "Content",
    
    # Messages
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    
    # Context
    "Tool",
    "Context",
    "Usage",
    
    # Options
    "StreamOptions",
    "SimpleStreamOptions",
    "ThinkingBudgets",
    "OpenRouterRouting",
    "VercelGatewayRouting",
    "OpenAICompletionsCompat",
    "OpenAIResponsesCompat",
    
    # Model
    "ModelInfo",
    
    # Events
    "AssistantMessageEvent",
    "AssistantMessageEventStream",
    "StreamBuffer",
    "AgentEvent",
    "AgentTool",
    
    # Provider
    "BaseProvider",
    "ProviderConfig",
    "ProviderRegistry",
    "get_provider_registry",
    
    # Registry
    "ModelRegistry",
    "ModelCapability",
    "get_registry",
    
    # Stream utils
    "create_event_stream",
    "stream_to_string",
    "stream_to_messages",
    
    # Legacy providers
    "OpenAIProvider",
    "AnthropicProvider",
    "KimiProvider",
]

if HAS_TOKENIZER:
    __all__.append("Tokenizer")
