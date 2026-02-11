"""
List Models
等效于 Pi-Mono 的 packages/coding-agent/src/cli/list-models.ts

模型列表展示和选择。
"""

from typing import List, Optional
from dataclasses import dataclass

from ...ai.models import ModelInfo, get_providers, get_models


@dataclass
class ModelFilter:
    """模型过滤器"""
    provider: Optional[str] = None
    supports_vision: Optional[bool] = None
    supports_tools: Optional[bool] = None
    max_cost: Optional[float] = None


class ModelLister:
    """
    模型列表器
    
    展示和选择可用模型。
    
    Example:
        >>> lister = ModelLister()
        >>> await lister.list_and_select()
    """
    
    def __init__(self, use_tui: bool = True):
        self.use_tui = use_tui
        self._tui_available = self._check_tui()
    
    def _check_tui(self) -> bool:
        """检查TUI库"""
        try:
            import questionary
            return True
        except ImportError:
            return False
    
    async def list_and_select(
        self,
        provider: Optional[str] = None,
        filter_criteria: Optional[ModelFilter] = None,
    ) -> Optional[ModelInfo]:
        """
        列出并选择模型
        
        Args:
            provider: 按provider筛选
            filter_criteria: 过滤条件
        
        Returns:
            选中的模型或None
        """
        # Get models
        if provider:
            models = get_models(provider)
        else:
            models = []
            for prov in get_providers():
                models.extend(get_models(prov))
        
        # Apply filters
        if filter_criteria:
            models = self._apply_filter(models, filter_criteria)
        
        if not models:
            print("No models found matching criteria.")
            return None
        
        # Display
        self.display_models(models, provider)
        
        # Select if TUI available
        if self.use_tui and self._tui_available:
            return await self._select_tui(models)
        else:
            return await self._select_cli(models)
    
    def display_models(
        self,
        models: List[ModelInfo],
        provider: Optional[str] = None,
    ) -> None:
        """
        显示模型列表
        
        Args:
            models: 模型列表
            provider: provider名称
        """
        if provider:
            print(f"\n{provider.upper()} Models:")
        else:
            print(f"\nAvailable Models:")
        
        print("-" * 100)
        print(f"{'ID':<35} {'Name':<25} {'Cost (in/out)':<20} {'Capabilities'}")
        print("-" * 100)
        
        # Sort by provider then cost
        sorted_models = sorted(
            models,
            key=lambda m: (m.provider, m.cost.input),
        )
        
        current_provider = None
        for model in sorted_models:
            # Provider separator
            if not provider and model.provider != current_provider:
                current_provider = model.provider
                print(f"\n[{current_provider}]")
            
            # Format fields
            model_id = model.id[:33] + ".." if len(model.id) > 35 else model.id
            name = model.name[:23] + ".." if len(model.name) > 25 else model.name
            cost = f"${model.cost.input:.2f}/${model.cost.output:.2f}"
            
            caps = []
            if model.capabilities.vision:
                caps.append("👁")
            if model.capabilities.tools:
                caps.append("🔧")
            if model.capabilities.reasoning:
                caps.append("🧠")
            
            cap_str = " ".join(caps)
            
            print(f"{model_id:<35} {name:<25} {cost:<20} {cap_str}")
        
        print()
    
    async def _select_tui(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """TUI选择"""
        import questionary
        
        choices = []
        for model in sorted(models, key=lambda m: (m.provider, m.cost.input)):
            cost_str = f"${model.cost.input:.2f}/${model.cost.output:.2f}"
            label = f"{model.name} ({model.provider}) - {cost_str}"
            choices.append(questionary.Choice(title=label, value=model))
        
        choices.append(questionary.Choice(title="Cancel", value=None))
        
        result = await questionary.select(
            "Select a model:",
            choices=choices,
        ).ask_async()
        
        return result
    
    async def _select_cli(self, models: List[ModelInfo]) -> Optional[ModelInfo]:
        """CLI选择"""
        print("\nSelect a model by number:")
        
        sorted_models = sorted(models, key=lambda m: (m.provider, m.cost.input))
        
        for i, model in enumerate(sorted_models, 1):
            print(f"  {i}. {model.name} ({model.provider})")
        
        print(f"  0. Cancel")
        print()
        
        try:
            choice = input(f"Enter number (0-{len(models)}): ").strip()
            idx = int(choice)
            
            if idx == 0:
                return None
            if 1 <= idx <= len(models):
                return sorted_models[idx - 1]
            
            print("Invalid selection")
            return None
            
        except (ValueError, KeyboardInterrupt):
            return None
    
    def _apply_filter(
        self,
        models: List[ModelInfo],
        criteria: ModelFilter,
    ) -> List[ModelInfo]:
        """应用过滤器"""
        result = models
        
        if criteria.provider:
            result = [m for m in result if m.provider == criteria.provider]
        
        if criteria.supports_vision is not None:
            result = [m for m in result if m.capabilities.vision == criteria.supports_vision]
        
        if criteria.supports_tools is not None:
            result = [m for m in result if m.capabilities.tools == criteria.supports_tools]
        
        if criteria.max_cost is not None:
            result = [m for m in result if m.cost.input <= criteria.max_cost]
        
        return result


def print_model_details(model: ModelInfo) -> None:
    """打印模型详细信息"""
    print(f"\nModel: {model.name}")
    print("=" * 50)
    print(f"ID: {model.id}")
    print(f"Provider: {model.provider}")
    print(f"API: {model.api}")
    print(f"\nCosts (per 1M tokens):")
    print(f"  Input: ${model.cost.input}")
    print(f"  Output: ${model.cost.output}")
    if model.cost.cache_read:
        print(f"  Cache Read: ${model.cost.cache_read}")
    if model.cost.cache_write:
        print(f"  Cache Write: ${model.cost.cache_write}")
    print(f"\nContext Window: {model.context_window:,} tokens")
    print(f"Max Output: {model.max_tokens:,} tokens")
    print(f"\nCapabilities:")
    print(f"  Vision: {'Yes' if model.capabilities.vision else 'No'}")
    print(f"  Tools: {'Yes' if model.capabilities.tools else 'No'}")
    print(f"  Reasoning: {'Yes' if model.capabilities.reasoning else 'No'}")
    print(f"  Streaming: {'Yes' if model.capabilities.streaming else 'No'}")


__all__ = [
    "ModelFilter",
    "ModelLister",
    "print_model_details",
]
