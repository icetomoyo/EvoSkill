"""
Store - Persistent storage
Equivalent to Pi Mono's store.ts
"""
import json
from typing import Optional, Any, List
from pathlib import Path


class Store:
    """
    Persistent key-value storage
    
    Simple JSON-based storage for agent data
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self._load()
    
    def _load(self) -> None:
        """Load data from disk"""
        if self.db_path.exists():
            try:
                self._data = json.loads(self.db_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError):
                self._data = {}
    
    def _save(self) -> None:
        """Save data to disk"""
        self.db_path.write_text(json.dumps(self._data, indent=2), encoding='utf-8')
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        return self._data.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set value by key"""
        self._data[key] = value
        self._save()
    
    def delete(self, key: str) -> bool:
        """Delete key"""
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False
    
    def list(self, prefix: str = "") -> List[str]:
        """List keys with optional prefix"""
        if prefix:
            return [k for k in self._data.keys() if k.startswith(prefix)]
        return list(self._data.keys())
    
    def clear(self) -> None:
        """Clear all data"""
        self._data = {}
        self._save()
