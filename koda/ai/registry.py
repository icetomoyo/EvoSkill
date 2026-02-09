"""
Model Registry - Dynamic model discovery and metadata management
Equivalent to Pi Mono's packages/ai/src/models.ts + packages/coding-agent/src/core/model-registry.ts
"""
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class ModelCapability(Enum):
    """Model capabilities"""
    CHAT = "chat"
    VISION = "vision"
    TOOLS = "tools"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    REASONING = "reasoning"
    FUNCTION_CALLING = "function_calling"


@dataclass
class ModelInfo:
    """Model metadata"""
    id: str
    name: str
    provider: str
    context_window: int
    max_output_tokens: Optional[int] = None
    capabilities: Set[ModelCapability] = field(default_factory=set)
    pricing_input_per_1k: Optional[float] = None  # USD per 1K input tokens
    pricing_output_per_1k: Optional[float] = None  # USD per 1K output tokens
    description: Optional[str] = None
    deprecated: bool = False
    
    def supports(self, capability: ModelCapability) -> bool:
        return capability in self.capabilities
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "capabilities": [c.value for c in self.capabilities],
            "pricing_input_per_1k": self.pricing_input_per_1k,
            "pricing_output_per_1k": self.pricing_output_per_1k,
            "description": self.description,
            "deprecated": self.deprecated,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelInfo":
        caps = set()
        for c in data.get("capabilities", []):
            try:
                caps.add(ModelCapability(c))
            except ValueError:
                pass
        
        return cls(
            id=data["id"],
            name=data["name"],
            provider=data["provider"],
            context_window=data["context_window"],
            max_output_tokens=data.get("max_output_tokens"),
            capabilities=caps,
            pricing_input_per_1k=data.get("pricing_input_per_1k"),
            pricing_output_per_1k=data.get("pricing_output_per_1k"),
            description=data.get("description"),
            deprecated=data.get("deprecated", False),
        )


class ModelRegistry:
    """
    Central registry for all available models.
    Supports dynamic discovery and metadata queries.
    """
    
    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._provider_discoverers: Dict[str, Callable[[], List[ModelInfo]]] = {}
        self._load_builtin_models()
    
    def _load_builtin_models(self):
        """Load built-in model definitions"""
        # OpenAI models
        self.register(ModelInfo(
            id="gpt-4o",
            name="GPT-4o",
            provider="openai",
            context_window=128000,
            max_output_tokens=16384,
            capabilities={
                ModelCapability.CHAT, ModelCapability.VISION, 
                ModelCapability.TOOLS, ModelCapability.STREAMING,
                ModelCapability.JSON_MODE, ModelCapability.FUNCTION_CALLING
            },
            pricing_input_per_1k=0.0025,
            pricing_output_per_1k=0.01,
            description="OpenAI's flagship model",
        ))
        
        self.register(ModelInfo(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider="openai",
            context_window=128000,
            max_output_tokens=16384,
            capabilities={
                ModelCapability.CHAT, ModelCapability.VISION,
                ModelCapability.TOOLS, ModelCapability.STREAMING,
                ModelCapability.JSON_MODE, ModelCapability.FUNCTION_CALLING
            },
            pricing_input_per_1k=0.00015,
            pricing_output_per_1k=0.0006,
            description="Fast, affordable small model",
        ))
        
        self.register(ModelInfo(
            id="o3-mini",
            name="o3 Mini",
            provider="openai",
            context_window=200000,
            max_output_tokens=100000,
            capabilities={
                ModelCapability.CHAT, ModelCapability.REASONING,
                ModelCapability.STREAMING
            },
            pricing_input_per_1k=0.0011,
            pricing_output_per_1k=0.0044,
            description="Reasoning model",
        ))
        
        self.register(ModelInfo(
            id="o1",
            name="o1",
            provider="openai",
            context_window=200000,
            max_output_tokens=100000,
            capabilities={
                ModelCapability.CHAT, ModelCapability.REASONING,
                ModelCapability.STREAMING
            },
            pricing_input_per_1k=0.015,
            pricing_output_per_1k=0.06,
            description="Advanced reasoning model",
        ))
        
        # Anthropic models
        self.register(ModelInfo(
            id="claude-3-5-sonnet-20241022",
            name="Claude 3.5 Sonnet",
            provider="anthropic",
            context_window=200000,
            max_output_tokens=8192,
            capabilities={
                ModelCapability.CHAT, ModelCapability.VISION,
                ModelCapability.TOOLS, ModelCapability.STREAMING,
                ModelCapability.FUNCTION_CALLING
            },
            pricing_input_per_1k=0.003,
            pricing_output_per_1k=0.015,
            description="Balanced intelligence and speed",
        ))
        
        self.register(ModelInfo(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            provider="anthropic",
            context_window=200000,
            max_output_tokens=8192,
            capabilities={
                ModelCapability.CHAT, ModelCapability.VISION,
                ModelCapability.TOOLS, ModelCapability.STREAMING
            },
            pricing_input_per_1k=0.0008,
            pricing_output_per_1k=0.004,
            description="Fast, cost-effective",
        ))
        
        self.register(ModelInfo(
            id="claude-3-opus-20240229",
            name="Claude 3 Opus",
            provider="anthropic",
            context_window=200000,
            max_output_tokens=4096,
            capabilities={
                ModelCapability.CHAT, ModelCapability.VISION,
                ModelCapability.TOOLS, ModelCapability.STREAMING
            },
            pricing_input_per_1k=0.015,
            pricing_output_per_1k=0.075,
            description="Most capable Claude model",
        ))
        
        # Kimi models
        self.register(ModelInfo(
            id="kimi-k2",
            name="Kimi K2",
            provider="kimi",
            context_window=256000,
            max_output_tokens=8192,
            capabilities={
                ModelCapability.CHAT, ModelCapability.VISION,
                ModelCapability.TOOLS, ModelCapability.STREAMING
            },
            description="Moonshot AI's Kimi K2 model",
        ))
        
        self.register(ModelInfo(
            id="kimi-k1-5",
            name="Kimi K1.5",
            provider="kimi",
            context_window=128000,
            max_output_tokens=4096,
            capabilities={
                ModelCapability.CHAT, ModelCapability.REASONING,
                ModelCapability.STREAMING
            },
            description="Kimi reasoning model",
        ))
    
    def register(self, model: ModelInfo) -> None:
        """Register a model"""
        self._models[model.id] = model
    
    def unregister(self, model_id: str) -> bool:
        """Unregister a model"""
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False
    
    def get(self, model_id: str) -> Optional[ModelInfo]:
        """Get model by ID"""
        return self._models.get(model_id)
    
    def list_models(
        self,
        provider: Optional[str] = None,
        capability: Optional[ModelCapability] = None,
        exclude_deprecated: bool = True
    ) -> List[ModelInfo]:
        """List models with optional filtering"""
        models = list(self._models.values())
        
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if capability:
            models = [m for m in models if capability in m.capabilities]
        
        if exclude_deprecated:
            models = [m for m in models if not m.deprecated]
        
        return sorted(models, key=lambda m: m.name)
    
    def list_providers(self) -> List[str]:
        """List all providers"""
        return sorted(set(m.provider for m in self._models.values()))
    
    def register_provider_discoverer(
        self, 
        provider: str, 
        discoverer: Callable[[], List[ModelInfo]]
    ) -> None:
        """
        Register a function to discover models from a provider.
        Called during refresh() to dynamically fetch available models.
        """
        self._provider_discoverers[provider] = discoverer
    
    async def refresh(self) -> int:
        """
        Refresh model list by calling all registered discoverers.
        Returns number of models discovered.
        """
        import asyncio
        discovered = 0
        
        for provider, discoverer in self._provider_discoverers.items():
            try:
                if asyncio.iscoroutinefunction(discoverer):
                    models = await discoverer()
                else:
                    models = discoverer()
                
                for model in models:
                    self.register(model)
                    discovered += 1
            except Exception as e:
                print(f"Failed to discover models from {provider}: {e}")
        
        return discovered
    
    def find_by_name(self, name: str) -> Optional[ModelInfo]:
        """Find model by name (fuzzy match)"""
        name_lower = name.lower()
        
        # Exact match first
        for model in self._models.values():
            if model.id.lower() == name_lower:
                return model
        
        # Partial match
        for model in self._models.values():
            if name_lower in model.id.lower() or name_lower in model.name.lower():
                return model
        
        return None
    
    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> Optional[float]:
        """Estimate cost for a request"""
        model = self.get(model_id)
        if not model:
            return None
        
        cost = 0.0
        if model.pricing_input_per_1k:
            cost += (input_tokens / 1000) * model.pricing_input_per_1k
        if model.pricing_output_per_1k:
            cost += (output_tokens / 1000) * model.pricing_output_per_1k
        
        return cost if cost > 0 else None
    
    def select_for_context(
        self, 
        context_size: int,
        capability: Optional[ModelCapability] = None,
        provider: Optional[str] = None
    ) -> List[ModelInfo]:
        """Select models that can handle given context size"""
        models = self.list_models(provider=provider, capability=capability)
        return [m for m in models if m.context_window >= context_size]
    
    def save_to_file(self, path: Path) -> None:
        """Save registry to JSON file"""
        data = {
            "models": [m.to_dict() for m in self._models.values()],
            "providers": self.list_providers(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, path: Path) -> int:
        """Load registry from JSON file"""
        with open(path) as f:
            data = json.load(f)
        
        count = 0
        for m_data in data.get("models", []):
            try:
                self.register(ModelInfo.from_dict(m_data))
                count += 1
            except Exception as e:
                print(f"Failed to load model: {e}")
        
        return count


# Global registry instance
_global_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get the global model registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)"""
    global _global_registry
    _global_registry = None
