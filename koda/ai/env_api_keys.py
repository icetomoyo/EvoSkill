"""
Environment API Keys
Equivalent to Pi Mono's packages/ai/src/env-api-keys.ts

Manage API keys from environment variables.
"""
import os
import re
from typing import Dict, Optional, Set
from dataclasses import dataclass


@dataclass
class APIKeyConfig:
    """API key configuration"""
    env_var: str
    provider: str
    key_prefix: str
    description: str


class EnvAPIKeyManager:
    """
    Manager for API keys from environment variables.
    
    Supports standard environment variable names and custom prefixes.
    
    Example:
        >>> manager = EnvAPIKeyManager()
        >>> key = manager.get_key("openai")
        >>> keys = manager.get_all_keys()
    """
    
    # Standard environment variable names
    DEFAULT_CONFIGS = {
        "openai": APIKeyConfig(
            env_var="OPENAI_API_KEY",
            provider="openai",
            key_prefix="sk-",
            description="OpenAI API Key"
        ),
        "anthropic": APIKeyConfig(
            env_var="ANTHROPIC_API_KEY",
            provider="anthropic",
            key_prefix="sk-ant-",
            description="Anthropic API Key"
        ),
        "google": APIKeyConfig(
            env_var="GOOGLE_API_KEY",
            provider="google",
            key_prefix="",
            description="Google API Key"
        ),
        "google_gemini": APIKeyConfig(
            env_var="GOOGLE_GEMINI_API_KEY",
            provider="google-gemini",
            key_prefix="",
            description="Google Gemini API Key"
        ),
        "azure_openai": APIKeyConfig(
            env_var="AZURE_OPENAI_API_KEY",
            provider="azure-openai",
            key_prefix="",
            description="Azure OpenAI API Key"
        ),
        "bedrock": APIKeyConfig(
            env_var="AWS_ACCESS_KEY_ID",
            provider="bedrock",
            key_prefix="AKIA",
            description="AWS Access Key for Bedrock"
        ),
        "bedrock_secret": APIKeyConfig(
            env_var="AWS_SECRET_ACCESS_KEY",
            provider="bedrock",
            key_prefix="",
            description="AWS Secret Key for Bedrock"
        ),
        "github_copilot": APIKeyConfig(
            env_var="GITHUB_COPILOT_API_KEY",
            provider="github-copilot",
            key_prefix="",
            description="GitHub Copilot API Key"
        ),
        "xai": APIKeyConfig(
            env_var="XAI_API_KEY",
            provider="xai",
            key_prefix="",
            description="xAI API Key"
        ),
        "groq": APIKeyConfig(
            env_var="GROQ_API_KEY",
            provider="groq",
            key_prefix="gsk_",
            description="Groq API Key"
        ),
        "cohere": APIKeyConfig(
            env_var="COHERE_API_KEY",
            provider="cohere",
            key_prefix="",
            description="Cohere API Key"
        ),
        "mistral": APIKeyConfig(
            env_var="MISTRAL_API_KEY",
            provider="mistral",
            key_prefix="",
            description="Mistral API Key"
        ),
        "huggingface": APIKeyConfig(
            env_var="HUGGINGFACE_API_KEY",
            provider="huggingface",
            key_prefix="hf_",
            description="Hugging Face API Key"
        ),
        "openrouter": APIKeyConfig(
            env_var="OPENROUTER_API_KEY",
            provider="openrouter",
            key_prefix="",
            description="OpenRouter API Key"
        ),
    }
    
    def __init__(self, custom_prefix: Optional[str] = None):
        """
        Initialize manager.
        
        Args:
            custom_prefix: Custom prefix for environment variables
        """
        self.custom_prefix = custom_prefix
        self._configs = dict(self.DEFAULT_CONFIGS)
    
    def get_key(self, provider: str, env_var: Optional[str] = None) -> Optional[str]:
        """
        Get API key for provider.
        
        Args:
            provider: Provider name
            env_var: Specific environment variable name
            
        Returns:
            API key or None
        """
        if env_var:
            return os.environ.get(env_var)
        
        # Try custom prefix first
        if self.custom_prefix:
            custom_key = os.environ.get(f"{self.custom_prefix}_{provider.upper()}_API_KEY")
            if custom_key:
                return custom_key
        
        # Try standard config
        config = self._configs.get(provider)
        if config:
            return os.environ.get(config.env_var)
        
        # Try generic env var
        return os.environ.get(f"{provider.upper()}_API_KEY")
    
    def get_all_keys(self) -> Dict[str, str]:
        """
        Get all available API keys.
        
        Returns:
            Dict of provider -> key
        """
        keys = {}
        for provider in self._configs:
            key = self.get_key(provider)
            if key:
                keys[provider] = key
        return keys
    
    def has_key(self, provider: str) -> bool:
        """
        Check if API key exists for provider.
        
        Args:
            provider: Provider name
            
        Returns:
            True if key exists
        """
        return self.get_key(provider) is not None
    
    def validate_key(self, provider: str, key: Optional[str] = None) -> bool:
        """
        Validate API key format.
        
        Args:
            provider: Provider name
            key: Key to validate (uses env if not provided)
            
        Returns:
            True if valid format
        """
        if key is None:
            key = self.get_key(provider)
        
        if not key:
            return False
        
        config = self._configs.get(provider)
        if not config:
            return len(key) > 10  # Generic validation
        
        # Check prefix if defined
        if config.key_prefix and not key.startswith(config.key_prefix):
            return False
        
        # Minimum length check
        return len(key) >= 20
    
    def register_config(self, name: str, config: APIKeyConfig):
        """
        Register custom API key configuration.
        
        Args:
            name: Config name
            config: Configuration
        """
        self._configs[name] = config
    
    def get_providers_with_keys(self) -> Set[str]:
        """
        Get set of providers that have keys configured.
        
        Returns:
            Set of provider names
        """
        return {provider for provider in self._configs if self.has_key(provider)}
    
    def get_key_info(self, provider: str) -> Optional[Dict]:
        """
        Get information about a key without exposing it.
        
        Args:
            provider: Provider name
            
        Returns:
            Key info dict or None
        """
        key = self.get_key(provider)
        if not key:
            return None
        
        config = self._configs.get(provider)
        
        return {
            "provider": provider,
            "configured": True,
            "valid_format": self.validate_key(provider, key),
            "masked_key": self._mask_key(key),
            "env_var": config.env_var if config else f"{provider.upper()}_API_KEY",
        }
    
    def _mask_key(self, key: str) -> str:
        """Mask API key for display"""
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"


# Convenience functions
_manager: Optional[EnvAPIKeyManager] = None


def get_manager() -> EnvAPIKeyManager:
    """Get global manager instance"""
    global _manager
    if _manager is None:
        _manager = EnvAPIKeyManager()
    return _manager


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for provider (convenience)"""
    return get_manager().get_key(provider)


def has_api_key(provider: str) -> bool:
    """Check if API key exists (convenience)"""
    return get_manager().has_key(provider)


def get_all_api_keys() -> Dict[str, str]:
    """Get all API keys (convenience)"""
    return get_manager().get_all_keys()


__all__ = [
    "EnvAPIKeyManager",
    "APIKeyConfig",
    "get_manager",
    "get_api_key",
    "has_api_key",
    "get_all_api_keys",
]
