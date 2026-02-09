"""
Koda AI - Unified LLM Interface

Supports 15+ providers: OpenAI, Anthropic, Google, Azure, 
Bedrock, Mistral, Groq, Cerebras, xAI, OpenRouter, 
Kimi For Coding, and custom providers.
"""
from koda.ai.provider import LLMProvider, Message, Model, ToolCall, ToolResult
from koda.ai.providers.openai_provider import OpenAIProvider
from koda.ai.providers.anthropic_provider import AnthropicProvider
from koda.ai.providers.kimi_provider import KimiProvider
from koda.ai.factory import create_provider, list_supported_providers
from koda.ai.registry import (
    ModelRegistry,
    ModelCapability,
    ModelInfo,
    get_registry,
)

try:
    from koda.ai.tokenizer import Tokenizer
    HAS_TOKENIZER = True
except ImportError:
    HAS_TOKENIZER = False

__all__ = [
    "LLMProvider",
    "Message",
    "Model",
    "ToolCall",
    "ToolResult",
    "OpenAIProvider",
    "AnthropicProvider",
    "KimiProvider",
    "create_provider",
    "list_supported_providers",
    "ModelRegistry",
    "ModelCapability",
    "ModelInfo",
    "get_registry",
]

if HAS_TOKENIZER:
    __all__.append("Tokenizer")
