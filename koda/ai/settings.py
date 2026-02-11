"""
Settings Manager
Equivalent to Pi Mono's packages/ai/src/utils/settings.ts

Manages user settings and preferences.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class ModelSettings:
    """Settings for a specific model"""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: Optional[float] = None
    top_k: Optional[int] = None


@dataclass
class ProviderSettings:
    """Settings for a specific provider"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    models: Dict[str, ModelSettings] = field(default_factory=dict)


class SettingsManager:
    """
    Manages user settings and preferences.
    
    Settings are stored in a JSON file and support nested
    configuration for providers and models.
    
    Example:
        >>> settings = SettingsManager()
        >>> settings.get_provider("openai").api_key = "sk-..."
        >>> settings.save()
    """
    
    DEFAULT_CONFIG_DIR = Path.home() / ".koda"
    DEFAULT_SETTINGS_FILE = "settings.json"
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            config_dir: Configuration directory (default: ~/.koda)
        """
        self._config_dir = Path(config_dir) if config_dir else self.DEFAULT_CONFIG_DIR
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        self._settings_file = self._config_dir / self.DEFAULT_SETTINGS_FILE
        self._settings: Dict[str, Any] = {}
        self._providers: Dict[str, ProviderSettings] = {}
        
        self._load()
    
    def _load(self):
        """Load settings from file"""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._settings = {}
        
        # Parse provider settings
        for provider_name, provider_data in self._settings.get("providers", {}).items():
            self._providers[provider_name] = self._parse_provider_settings(provider_data)
    
    def _parse_provider_settings(self, data: Dict[str, Any]) -> ProviderSettings:
        """Parse provider settings from dict"""
        settings = ProviderSettings(
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            default_model=data.get("default_model"),
        )
        
        for model_name, model_data in data.get("models", {}).items():
            settings.models[model_name] = ModelSettings(**model_data)
        
        return settings
    
    def save(self):
        """Save settings to file"""
        # Update settings dict with current provider settings
        self._settings["providers"] = {}
        for name, provider in self._providers.items():
            self._settings["providers"][name] = {
                "api_key": provider.api_key,
                "base_url": provider.base_url,
                "default_model": provider.default_model,
                "models": {
                    model_name: asdict(model_settings)
                    for model_name, model_settings in provider.models.items()
                }
            }
        
        with open(self._settings_file, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)
    
    def get_provider(self, name: str) -> ProviderSettings:
        """
        Get settings for a provider.
        
        Args:
            name: Provider name
            
        Returns:
            Provider settings (creates default if not exists)
        """
        if name not in self._providers:
            self._providers[name] = ProviderSettings()
        return self._providers[name]
    
    def set_provider(self, name: str, settings: ProviderSettings):
        """
        Set settings for a provider.
        
        Args:
            name: Provider name
            settings: Provider settings
        """
        self._providers[name] = settings
    
    def get_model_settings(self, provider: str, model: str) -> ModelSettings:
        """
        Get settings for a specific model.
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            Model settings (creates default if not exists)
        """
        provider_settings = self.get_provider(provider)
        if model not in provider_settings.models:
            provider_settings.models[model] = ModelSettings()
        return provider_settings.models[model]
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.
        
        Args:
            key: Dot-separated key (e.g., "providers.openai.api_key")
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        parts = key.split(".")
        value = self._settings
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set a setting value by key.
        
        Args:
            key: Dot-separated key
            value: Value to set
        """
        parts = key.split(".")
        target = self._settings
        
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        
        target[parts[-1]] = value
    
    def list_providers(self) -> List[str]:
        """List all configured providers"""
        return list(self._providers.keys())
    
    def remove_provider(self, name: str):
        """
        Remove a provider's settings.
        
        Args:
            name: Provider name
        """
        if name in self._providers:
            del self._providers[name]
        
        if "providers" in self._settings and name in self._settings["providers"]:
            del self._settings["providers"][name]
    
    def export(self) -> Dict[str, Any]:
        """Export all settings as dict"""
        return dict(self._settings)
    
    def import_(self, data: Dict[str, Any], merge: bool = False):
        """
        Import settings from dict.
        
        Args:
            data: Settings data
            merge: If True, merge with existing settings
        """
        if merge:
            self._merge_settings(self._settings, data)
        else:
            self._settings = data
        
        # Re-parse providers
        self._providers = {}
        for provider_name, provider_data in self._settings.get("providers", {}).items():
            self._providers[provider_name] = self._parse_provider_settings(provider_data)
    
    def _merge_settings(self, target: Dict, source: Dict):
        """Recursively merge source into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_settings(target[key], value)
            else:
                target[key] = value


# Global settings instance
_settings: Optional[SettingsManager] = None


def get_settings() -> SettingsManager:
    """Get global settings manager"""
    global _settings
    if _settings is None:
        _settings = SettingsManager()
    return _settings


def set_settings(settings: SettingsManager):
    """Set global settings manager"""
    global _settings
    _settings = settings


__all__ = [
    "SettingsManager",
    "ModelSettings",
    "ProviderSettings",
    "get_settings",
    "set_settings",
]
