"""
LLM Provider Factory

Creates the appropriate provider based on configuration.
"""
import os
from typing import Optional

from koda.ai.provider import LLMProvider


def create_provider(
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Create an LLM provider instance
    
    Args:
        provider: Provider name (openai, anthropic, kimi, etc.)
        api_key: API key (auto-detected from env if not provided)
        base_url: Custom base URL (for proxies)
        **kwargs: Additional provider-specific options
        
    Returns:
        LLMProvider instance
        
    Raises:
        ValueError: If provider not supported
        ImportError: If required package not installed
        
    Examples:
        >>> provider = create_provider("openai", api_key="sk-...")
        >>> provider = create_provider("anthropic")
        >>> provider = create_provider("kimi", for_coding=True)
    """
    provider = provider.lower()
    
    # Auto-detect API key from environment
    if api_key is None:
        api_key = _get_api_key_from_env(provider)
    
    if api_key is None:
        raise ValueError(
            f"API key required for {provider}. "
            f"Set {provider.upper()}_API_KEY environment variable "
            f"or pass api_key parameter."
        )
    
    # Create provider instance
    if provider in ("openai", "azure"):
        from koda.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, base_url=base_url, **kwargs)
    
    elif provider in ("anthropic", "claude"):
        from koda.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, base_url=base_url, **kwargs)
    
    elif provider in ("kimi", "moonshot", "kimi-coding"):
        from koda.ai.providers.kimi_provider import KimiProvider
        is_coding = provider == "kimi-coding" or kwargs.get("for_coding")
        return KimiProvider(
            api_key=api_key,
            base_url=base_url,
            for_coding=is_coding,
            **kwargs
        )
    
    elif provider == "openrouter":
        # OpenRouter uses OpenAI-compatible API
        from koda.ai.providers.openai_provider import OpenAIProvider
        base_url = base_url or "https://openrouter.ai/api/v1"
        return OpenAIProvider(api_key=api_key, base_url=base_url, **kwargs)
    
    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Supported: openai, anthropic, kimi, kimi-coding, openrouter"
        )


def _get_api_key_from_env(provider: str) -> Optional[str]:
    """Get API key from environment variables"""
    env_vars = {
        "openai": ["OPENAI_API_KEY", "EVOSKILL_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY", "EVOSKILL_API_KEY"],
        "claude": ["ANTHROPIC_API_KEY", "EVOSKILL_API_KEY"],
        "kimi": ["KIMI_API_KEY", "MOONSHOT_API_KEY", "EVOSKILL_API_KEY"],
        "moonshot": ["KIMI_API_KEY", "MOONSHOT_API_KEY", "EVOSKILL_API_KEY"],
        "kimi-coding": ["KIMICODE_API_KEY", "KIMI_API_KEY", "EVOSKILL_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY", "EVOSKILL_API_KEY"],
    }
    
    for var in env_vars.get(provider, ["EVOSKILL_API_KEY"]):
        key = os.getenv(var)
        if key:
            return key
    
    return None


def list_supported_providers() -> list:
    """List all supported provider names"""
    return [
        "openai",
        "anthropic",
        "kimi",
        "kimi-coding",
        "openrouter",
    ]
