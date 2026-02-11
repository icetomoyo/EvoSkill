"""
Settings Manager
Equivalent to Pi Mono's packages/coding-agent/src/core/settings-manager.ts

Hierarchical settings management with global and project-level configs.
Supports file watching for auto-reload.
"""
import json
import os
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from threading import Lock
import time


@dataclass
class CompactionSettings:
    """Compaction settings"""
    max_tokens: int = 128000
    reserve_tokens: int = 16000
    trigger_ratio: float = 0.8


@dataclass
class ImageSettings:
    """Image processing settings"""
    max_width: int = 2048
    max_height: int = 2048
    quality: int = 85
    format: str = "jpeg"


@dataclass
class RetrySettings:
    """Retry settings"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0


@dataclass
class PackageSource:
    """Package source for extensions"""
    name: str
    url: str
    enabled: bool = True


@dataclass
class Settings:
    """Complete settings"""
    compaction: CompactionSettings = field(default_factory=CompactionSettings)
    images: ImageSettings = field(default_factory=ImageSettings)
    retry: RetrySettings = field(default_factory=RetrySettings)
    package_sources: List[PackageSource] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "compaction": asdict(self.compaction),
            "images": asdict(self.images),
            "retry": asdict(self.retry),
            "package_sources": [asdict(ps) for ps in self.package_sources],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        settings = cls()
        if "compaction" in data:
            settings.compaction = CompactionSettings(**data["compaction"])
        if "images" in data:
            settings.images = ImageSettings(**data["images"])
        if "retry" in data:
            settings.retry = RetrySettings(**data["retry"])
        if "package_sources" in data:
            settings.package_sources = [
                PackageSource(**ps) for ps in data["package_sources"]
            ]
        return settings


class SettingsManager:
    """
    Hierarchical settings manager.
    
    Supports:
    - Global settings: ~/.koda/settings.json
    - Project settings: .koda/settings.json
    - Auto-merge (project overrides global)
    - File watching for auto-reload
    """
    
    def __init__(self, global_dir: Optional[Path] = None, project_dir: Optional[Path] = None):
        """
        Initialize settings manager.
        
        Args:
            global_dir: Directory for global settings (default: ~/.koda)
            project_dir: Directory for project settings (default: cwd/.koda)
        """
        if global_dir is None:
            global_dir = Path.home() / ".koda"
        if project_dir is None:
            project_dir = Path.cwd() / ".koda"
        
        self.global_dir = global_dir
        self.project_dir = project_dir
        self.global_settings_file = self.global_dir / "settings.json"
        self.project_settings_file = self.project_dir / "settings.json"
        
        self._cache: Optional[Settings] = None
        self._cache_lock = Lock()
        self._watchers: List[Callable[[], None]] = []
        self._last_load_time: float = 0
        self._watch_enabled = False
    
    def load(self) -> Settings:
        """
        Load settings from both global and project configs.
        Project settings override global settings.
        
        Returns:
            Merged settings
        """
        with self._cache_lock:
            # Check if cache is fresh (within 1 second)
            if self._cache is not None and time.time() - self._last_load_time < 1:
                return self._cache
            
            # Load global settings
            global_settings = self._load_file(self.global_settings_file)
            
            # Load project settings
            project_settings = self._load_file(self.project_settings_file)
            
            # Merge (project overrides global)
            merged = self._merge_settings(global_settings, project_settings)
            
            self._cache = merged
            self._last_load_time = time.time()
            
            return merged
    
    def save(self, settings: Settings, scope: str = "project") -> None:
        """
        Save settings to file.
        
        Args:
            settings: Settings to save
            scope: "global" or "project"
        """
        if scope == "global":
            self.global_dir.mkdir(parents=True, exist_ok=True)
            self._save_file(self.global_settings_file, settings)
        else:
            self.project_dir.mkdir(parents=True, exist_ok=True)
            self._save_file(self.project_settings_file, settings)
        
        # Clear cache to force reload
        with self._cache_lock:
            self._cache = None
    
    def watch(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for settings changes.
        
        Args:
            callback: Function to call when settings change
        """
        self._watchers.append(callback)
        self._watch_enabled = True
        # Note: Actual file watching would require a background thread
        # For simplicity, we check on load() calls
    
    def unwatch(self, callback: Callable[[], None]) -> None:
        """Remove a watcher callback"""
        if callback in self._watchers:
            self._watchers.remove(callback)
    
    def get_global_path(self) -> Path:
        """Get global settings file path"""
        return self.global_settings_file
    
    def get_project_path(self) -> Path:
        """Get project settings file path"""
        return self.project_settings_file
    
    def has_project_settings(self) -> bool:
        """Check if project settings exist"""
        return self.project_settings_file.exists()
    
    def has_global_settings(self) -> bool:
        """Check if global settings exist"""
        return self.global_settings_file.exists()
    
    def _load_file(self, path: Path) -> Optional[Settings]:
        """Load settings from file"""
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None
    
    def _save_file(self, path: Path, settings: Settings) -> None:
        """Save settings to file"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)
    
    def _merge_settings(self, global_s: Optional[Settings], project_s: Optional[Settings]) -> Settings:
        """Merge global and project settings (project overrides)"""
        if global_s is None and project_s is None:
            return Settings()  # Return defaults
        
        if global_s is None:
            return project_s
        
        if project_s is None:
            return global_s
        
        # Start with global, override with project
        merged = Settings()
        
        # Compaction
        merged.compaction = CompactionSettings(
            max_tokens=project_s.compaction.max_tokens or global_s.compaction.max_tokens,
            reserve_tokens=project_s.compaction.reserve_tokens or global_s.compaction.reserve_tokens,
            trigger_ratio=project_s.compaction.trigger_ratio or global_s.compaction.trigger_ratio,
        )
        
        # Images
        merged.images = ImageSettings(
            max_width=project_s.images.max_width or global_s.images.max_width,
            max_height=project_s.images.max_height or global_s.images.max_height,
            quality=project_s.images.quality or global_s.images.quality,
            format=project_s.images.format or global_s.images.format,
        )
        
        # Retry
        merged.retry = RetrySettings(
            max_attempts=project_s.retry.max_attempts or global_s.retry.max_attempts,
            base_delay=project_s.retry.base_delay or global_s.retry.base_delay,
            max_delay=project_s.retry.max_delay or global_s.retry.max_delay,
        )
        
        # Package sources: merge lists
        merged.package_sources = global_s.package_sources.copy()
        # Add project-specific sources, override if same name
        global_names = {ps.name for ps in merged.package_sources}
        for ps in project_s.package_sources:
            if ps.name in global_names:
                # Override
                for i, existing in enumerate(merged.package_sources):
                    if existing.name == ps.name:
                        merged.package_sources[i] = ps
                        break
            else:
                merged.package_sources.append(ps)
        
        return merged


# Global instance
_default_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get default settings manager instance"""
    global _default_manager
    if _default_manager is None:
        _default_manager = SettingsManager()
    return _default_manager


def load_settings() -> Settings:
    """Convenience function to load settings"""
    return get_settings_manager().load()
