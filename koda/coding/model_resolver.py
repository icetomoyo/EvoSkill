"""
Model Resolver
Equivalent to Pi Mono's packages/coding-agent/src/core/model-resolver.ts

Resolves model aliases and selects appropriate models.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ResolvedModel:
    """Resolved model information"""
    id: str
    provider: str
    api: str
    name: str
    is_fallback: bool = False


class ModelResolver:
    """
    Resolves model references to actual model configurations.
    
    Supports:
    - Model aliases (e.g., "gpt-4" -> "gpt-4o")
    - Provider selection
    - Fallback chains
    """
    
    # Model aliases for convenience
    ALIASES: Dict[str, str] = {
        "gpt-4": "gpt-4o",
        "gpt-4-turbo": "gpt-4o",
        "claude": "claude-sonnet-4-5",
        "claude-opus": "claude-opus-4-6",
    }
    
    # Fallback chain when primary model unavailable
    FALLBACKS: Dict[str, List[str]] = {
        "gpt-4o": ["gpt-4o-mini", "gpt-3.5-turbo"],
        "claude-opus-4-6": ["claude-sonnet-4-5", "claude-haiku-4-5"],
    }
    
    def __init__(self, registry=None):
        """
        Initialize resolver.
        
        Args:
            registry: Optional model registry
        """
        self._registry = registry
        self._custom_aliases: Dict[str, str] = {}
        self._custom_fallbacks: Dict[str, List[str]] = {}
    
    def register_alias(self, alias: str, model_id: str):
        """Register a custom model alias"""
        self._custom_aliases[alias] = model_id
    
    def register_fallbacks(self, model_id: str, fallbacks: List[str]):
        """Register fallback chain for a model"""
        self._custom_fallbacks[model_id] = fallbacks
    
    def resolve(self, model_ref: str) -> Optional[ResolvedModel]:
        """
        Resolve a model reference to actual model.
        
        Args:
            model_ref: Model ID or alias (e.g., "gpt-4", "claude")
            
        Returns:
            Resolved model info or None if not found
            
        Example:
            >>> resolver = ModelResolver()
            >>> model = resolver.resolve("gpt-4")
            >>> model.id
            'gpt-4o'
        """
        # Check custom aliases first
        if model_ref in self._custom_aliases:
            model_id = self._custom_aliases[model_ref]
        elif model_ref in self.ALIASES:
            model_id = self.ALIASES[model_ref]
        else:
            model_id = model_ref
        
        # Try to get from registry if available
        if self._registry:
            model_info = self._registry.get(model_id)
            if model_info:
                return ResolvedModel(
                    id=model_info.id,
                    provider=model_info.provider,
                    api=getattr(model_info, "api", "unknown"),
                    name=getattr(model_info, "name", model_id),
                )
        
        # Return basic resolution without registry
        provider = self._infer_provider(model_id)
        api = self._infer_api(model_id)
        
        return ResolvedModel(
            id=model_id,
            provider=provider,
            api=api,
            name=model_id,
        )
    
    def resolve_with_fallback(
        self,
        model_ref: str,
        available_models: Optional[List[str]] = None
    ) -> Optional[ResolvedModel]:
        """
        Resolve model with fallback chain.
        
        Args:
            model_ref: Primary model reference
            available_models: List of available model IDs
            
        Returns:
            Best available model
            
        Example:
            >>> resolver = ModelResolver()
            >>> model = resolver.resolve_with_fallback(
            ...     "gpt-4o",
            ...     available_models=["gpt-4o-mini", "gpt-3.5-turbo"]
            ... )
            >>> model.is_fallback
            True
        """
        # Try primary
        primary = self.resolve(model_ref)
        if primary:
            if available_models is None or primary.id in available_models:
                return primary
        
        # Try fallbacks
        model_id = self._resolve_alias(model_ref)
        fallbacks = self._get_fallbacks(model_id)
        
        for fallback_id in fallbacks:
            if available_models is None or fallback_id in available_models:
                resolved = self.resolve(fallback_id)
                if resolved:
                    resolved.is_fallback = True
                    return resolved
        
        return None
    
    def _resolve_alias(self, model_ref: str) -> str:
        """Resolve alias to model ID"""
        if model_ref in self._custom_aliases:
            return self._custom_aliases[model_ref]
        if model_ref in self.ALIASES:
            return self.ALIASES[model_ref]
        return model_ref
    
    def _get_fallbacks(self, model_id: str) -> List[str]:
        """Get fallback chain for model"""
        if model_id in self._custom_fallbacks:
            return self._custom_fallbacks[model_id]
        if model_id in self.FALLBACKS:
            return self.FALLBACKS[model_id]
        return []
    
    def _infer_provider(self, model_id: str) -> str:
        """Infer provider from model ID"""
        model_lower = model_id.lower()
        
        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "google"
        elif "command" in model_lower:
            return "cohere"
        elif "llama" in model_lower:
            return "meta"
        else:
            return "unknown"
    
    def _infer_api(self, model_id: str) -> str:
        """Infer API type from model ID"""
        provider = self._infer_provider(model_id)
        
        api_map = {
            "openai": "openai-responses",
            "anthropic": "anthropic-messages",
            "google": "google-generative-ai",
            "cohere": "cohere-chat",
            "meta": "openai-completions",  # Often uses OpenAI-compatible API
        }
        
        return api_map.get(provider, "unknown")
    
    def list_available_aliases(self) -> Dict[str, str]:
        """List all available aliases"""
        return {**self.ALIASES, **self._custom_aliases}


__all__ = [
    "ModelResolver",
    "ResolvedModel",
]
