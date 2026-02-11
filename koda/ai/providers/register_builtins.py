"""
Register Built-in Providers
Equivalent to Pi Mono's packages/ai/src/providers/register-builtins.ts

Auto-registration of all built-in API providers.
"""
from typing import Dict, Type, List, Optional
from dataclasses import dataclass

from ..provider_base import BaseProvider


@dataclass
class ProviderRegistration:
    """Provider registration info"""
    name: str
    provider_class: Type[BaseProvider]
    api_type: str
    default_models: List[str]
    priority: int = 0


class BuiltinProviderRegistry:
    """
    Registry for built-in providers.
    
    Automatically registers and manages all built-in API providers.
    
    Example:
        >>> registry = BuiltinProviderRegistry()
        >>> registry.register_all()
        >>> provider = registry.get_provider("openai")
    """
    
    def __init__(self):
        self._providers: Dict[str, ProviderRegistration] = {}
        self._api_type_map: Dict[str, str] = {}  # api_type -> provider name
        self._registered = False
    
    def register_all(self):
        """Register all built-in providers"""
        if self._registered:
            return
        
        # Import and register each provider
        self._register_openai()
        self._register_anthropic()
        self._register_google()
        self._register_azure()
        self._register_bedrock()
        self._register_kimi()
        self._register_github_copilot()
        
        self._registered = True
    
    def _register_openai(self):
        """Register OpenAI providers"""
        try:
            from .openai_provider_v2 import OpenAIProviderV2
            from .openai_responses import OpenAIResponsesProvider
            from .openai_codex_provider import OpenAICodexProvider
            
            self._register(ProviderRegistration(
                name="openai",
                provider_class=OpenAIProviderV2,
                api_type="openai-completions",
                default_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                priority=100
            ))
            
            self._register(ProviderRegistration(
                name="openai-responses",
                provider_class=OpenAIResponsesProvider,
                api_type="openai-responses",
                default_models=["gpt-4o", "gpt-4o-mini"],
                priority=90
            ))
            
            self._register(ProviderRegistration(
                name="openai-codex",
                provider_class=OpenAICodexProvider,
                api_type="openai-codex-responses",
                default_models=["codex-latest"],
                priority=80
            ))
        except ImportError:
            pass
    
    def _register_anthropic(self):
        """Register Anthropic provider"""
        try:
            from .anthropic_provider_v2 import AnthropicProviderV2
            
            self._register(ProviderRegistration(
                name="anthropic",
                provider_class=AnthropicProviderV2,
                api_type="anthropic-messages",
                default_models=["claude-sonnet-4-5", "claude-opus-4-6"],
                priority=100
            ))
        except ImportError:
            pass
    
    def _register_google(self):
        """Register Google providers"""
        try:
            from .google_provider import GoogleProvider
            from .gemini_cli_provider import GeminiCLIProvider
            from .vertex_provider import VertexProvider
            
            self._register(ProviderRegistration(
                name="google",
                provider_class=GoogleProvider,
                api_type="google-generative-ai",
                default_models=["gemini-1.5-pro", "gemini-1.5-flash"],
                priority=100
            ))
            
            self._register(ProviderRegistration(
                name="google-gemini-cli",
                provider_class=GeminiCLIProvider,
                api_type="google-gemini-cli",
                default_models=["gemini-1.5-pro"],
                priority=90
            ))
            
            self._register(ProviderRegistration(
                name="google-vertex",
                provider_class=VertexProvider,
                api_type="google-vertex",
                default_models=["gemini-1.5-pro-001"],
                priority=80
            ))
        except ImportError:
            pass
    
    def _register_azure(self):
        """Register Azure OpenAI provider"""
        try:
            from .azure_provider import AzureOpenAIProvider
            
            self._register(ProviderRegistration(
                name="azure-openai",
                provider_class=AzureOpenAIProvider,
                api_type="azure-openai-responses",
                default_models=["gpt-4o", "gpt-4"],
                priority=90
            ))
        except ImportError:
            pass
    
    def _register_bedrock(self):
        """Register AWS Bedrock provider"""
        try:
            from .bedrock_provider import BedrockProvider
            
            self._register(ProviderRegistration(
                name="bedrock",
                provider_class=BedrockProvider,
                api_type="bedrock-converse-stream",
                default_models=["anthropic.claude-3-sonnet", "anthropic.claude-3-opus"],
                priority=80
            ))
        except ImportError:
            pass
    
    def _register_kimi(self):
        """Register Kimi provider"""
        try:
            from .kimi_provider import KimiProvider
            
            self._register(ProviderRegistration(
                name="kimi",
                provider_class=KimiProvider,
                api_type="openai-completions",
                default_models=["kimi-latest"],
                priority=70
            ))
        except ImportError:
            pass
    
    def _register_github_copilot(self):
        """Register GitHub Copilot provider"""
        try:
            # GitHub Copilot is handled specially
            self._register(ProviderRegistration(
                name="github-copilot",
                provider_class=None,  # Special handling
                api_type="github-copilot",
                default_models=["copilot-chat"],
                priority=70
            ))
        except ImportError:
            pass
    
    def _register(self, registration: ProviderRegistration):
        """Internal register method"""
        self._providers[registration.name] = registration
        self._api_type_map[registration.api_type] = registration.name
    
    def get_provider(self, name: str) -> Optional[ProviderRegistration]:
        """
        Get provider registration by name.
        
        Args:
            name: Provider name
            
        Returns:
            Registration or None
        """
        self.register_all()
        return self._providers.get(name)
    
    def get_provider_by_api_type(self, api_type: str) -> Optional[ProviderRegistration]:
        """
        Get provider by API type.
        
        Args:
            api_type: API type string
            
        Returns:
            Registration or None
        """
        self.register_all()
        name = self._api_type_map.get(api_type)
        if name:
            return self._providers.get(name)
        return None
    
    def list_providers(self) -> List[str]:
        """
        List all registered provider names.
        
        Returns:
            List of provider names
        """
        self.register_all()
        return list(self._providers.keys())
    
    def list_by_api_type(self, api_type: str) -> List[ProviderRegistration]:
        """
        List providers for specific API type.
        
        Args:
            api_type: API type
            
        Returns:
            List of matching registrations
        """
        self.register_all()
        return [
            reg for reg in self._providers.values()
            if reg.api_type == api_type
        ]
    
    def get_default_model(self, provider_name: str) -> Optional[str]:
        """
        Get default model for provider.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Default model ID or None
        """
        reg = self.get_provider(provider_name)
        if reg and reg.default_models:
            return reg.default_models[0]
        return None
    
    def get_priority_sorted(self) -> List[ProviderRegistration]:
        """
        Get providers sorted by priority.
        
        Returns:
            Sorted list of registrations
        """
        self.register_all()
        return sorted(
            self._providers.values(),
            key=lambda r: r.priority,
            reverse=True
        )


# Global registry
_registry: Optional[BuiltinProviderRegistry] = None


def get_registry() -> BuiltinProviderRegistry:
    """Get global registry instance"""
    global _registry
    if _registry is None:
        _registry = BuiltinProviderRegistry()
    return _registry


def register_all_providers():
    """Register all built-in providers (convenience)"""
    get_registry().register_all()


def get_provider_info(name: str) -> Optional[Dict]:
    """Get provider info dict (convenience)"""
    reg = get_registry().get_provider(name)
    if reg:
        return {
            "name": reg.name,
            "api_type": reg.api_type,
            "default_models": reg.default_models,
            "priority": reg.priority,
        }
    return None


__all__ = [
    "BuiltinProviderRegistry",
    "ProviderRegistration",
    "get_registry",
    "register_all_providers",
    "get_provider_info",
]
