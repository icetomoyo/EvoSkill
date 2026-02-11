"""
Config Selector
等效于 Pi-Mono 的 packages/coding-agent/src/cli/config-selector.ts

交互式配置选择器。
"""

from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass


@dataclass
class Config:
    """配置项"""
    id: str
    name: str
    description: str
    provider: str
    model: str
    settings: Dict[str, Any]


class ConfigSelector:
    """
    配置选择器
    
    提供交互式配置选择界面。
    
    Example:
        >>> selector = ConfigSelector()
        >>> config = await selector.select([config1, config2, config3])
    """
    
    def __init__(self, use_tui: bool = True):
        self.use_tui = use_tui
        self._tui_available = self._check_tui()
    
    def _check_tui(self) -> bool:
        """检查是否可以使用TUI库"""
        try:
            import questionary
            return True
        except ImportError:
            return False
    
    async def select(
        self,
        configs: List[Config],
        title: str = "Select configuration",
    ) -> Optional[Config]:
        """
        选择配置
        
        Args:
            configs: 配置列表
            title: 选择标题
        
        Returns:
            选中的配置或None
        """
        if not configs:
            return None
        
        if len(configs) == 1:
            return configs[0]
        
        if self.use_tui and self._tui_available:
            return await self._select_tui(configs, title)
        else:
            return await self._select_cli(configs, title)
    
    async def _select_tui(
        self,
        configs: List[Config],
        title: str,
    ) -> Optional[Config]:
        """使用TUI选择"""
        import questionary
        
        choices = []
        for config in configs:
            label = f"{config.name} ({config.provider}/{config.model})"
            choices.append(questionary.Choice(title=label, value=config))
        
        choices.append(questionary.Choice(title="Cancel", value=None))
        
        result = await questionary.select(
            title,
            choices=choices,
        ).ask_async()
        
        return result
    
    async def _select_cli(
        self,
        configs: List[Config],
        title: str,
    ) -> Optional[Config]:
        """使用CLI选择"""
        print(f"\n{title}:\n")
        
        for i, config in enumerate(configs, 1):
            print(f"  {i}. {config.name}")
            print(f"     Provider: {config.provider}")
            print(f"     Model: {config.model}")
            print(f"     {config.description}")
            print()
        
        print(f"  0. Cancel")
        print()
        
        try:
            choice = input(f"Enter number (0-{len(configs)}): ").strip()
            idx = int(choice)
            
            if idx == 0:
                return None
            if 1 <= idx <= len(configs):
                return configs[idx - 1]
            
            print("Invalid selection")
            return None
            
        except (ValueError, KeyboardInterrupt):
            return None
    
    async def select_with_preview(
        self,
        configs: List[Config],
        preview_func: Callable[[Config], str],
        title: str = "Select configuration",
    ) -> Optional[Config]:
        """
        带预览的选择
        
        Args:
            configs: 配置列表
            preview_func: 预览生成函数
            title: 标题
        """
        if self.use_tui and self._tui_available:
            return await self._select_preview_tui(configs, preview_func, title)
        else:
            return await self.select(configs, title)
    
    async def _select_preview_tui(
        self,
        configs: List[Config],
        preview_func: Callable[[Config], str],
        title: str,
    ) -> Optional[Config]:
        """使用TUI带预览选择"""
        import questionary
        
        # For now, use simple select
        # Could be enhanced with custom widget
        return await self._select_tui(configs, title)
    
    async def multi_select(
        self,
        configs: List[Config],
        title: str = "Select configurations",
    ) -> List[Config]:
        """
        多选配置
        
        Args:
            configs: 配置列表
            title: 标题
        
        Returns:
            选中的配置列表
        """
        if self.use_tui and self._tui_available:
            import questionary
            
            choices = [
                questionary.Choice(
                    title=f"{c.name} ({c.provider})",
                    value=c,
                    checked=False,
                )
                for c in configs
            ]
            
            result = await questionary.checkbox(
                title,
                choices=choices,
            ).ask_async()
            
            return result or []
        else:
            # CLI fallback - select one at a time
            selected = []
            remaining = configs.copy()
            
            while remaining:
                config = await self._select_cli(
                    remaining + [Config("done", "Done", "", "", "", {})],
                    title,
                )
                
                if config is None or config.id == "done":
                    break
                
                selected.append(config)
                remaining.remove(config)
            
            return selected


def format_config_table(configs: List[Config]) -> str:
    """
    格式化配置表格
    
    Args:
        configs: 配置列表
    
    Returns:
        格式化字符串
    """
    if not configs:
        return "No configurations available."
    
    lines = []
    lines.append(f"{'Name':<20} {'Provider':<15} {'Model':<25} {'Description'}")
    lines.append("-" * 85)
    
    for config in configs:
        name = config.name[:18] + ".." if len(config.name) > 20 else config.name
        provider = config.provider[:13] + ".." if len(config.provider) > 15 else config.provider
        model = config.model[:23] + ".." if len(config.model) > 25 else config.model
        desc = config.description[:30] + "..." if len(config.description) > 33 else config.description
        
        lines.append(f"{name:<20} {provider:<15} {model:<25} {desc}")
    
    return "\n".join(lines)


__all__ = [
    "Config",
    "ConfigSelector",
    "format_config_table",
]
