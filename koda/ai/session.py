"""
Session Management
Equivalent to Pi Mono's packages/ai/src/session.ts

Session management with typed entries.
"""
import json
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


class SessionEntryType(Enum):
    """Types of session entries"""
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMMAND = "command"
    FILE_CHANGE = "file_change"
    SYSTEM = "system"


@dataclass
class SessionEntry:
    """A single session entry"""
    type: SessionEntryType
    data: Dict[str, Any]
    timestamp: int = field(default_factory=lambda: int(time.time()))
    id: str = field(default_factory=lambda: str(int(time.time() * 1000)))


class SessionManager:
    """
    Manages conversation sessions.
    
    Stores and retrieves session history with typed entries.
    
    Example:
        >>> manager = SessionManager()
        >>> manager.add_entry(SessionEntryType.MESSAGE, {"role": "user", "content": "hi"})
        >>> entries = manager.get_entries()
    """
    
    def __init__(self, session_id: Optional[str] = None, storage_path: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            session_id: Unique session ID (default: auto-generated)
            storage_path: Path to store session data
        """
        self.session_id = session_id or self._generate_session_id()
        self._entries: List[SessionEntry] = []
        self._storage_path = Path(storage_path) if storage_path else None
        
        if self._storage_path:
            self._load()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"session_{int(time.time())}"
    
    def _get_session_file(self) -> Path:
        """Get path to session storage file"""
        if self._storage_path:
            return self._storage_path / f"{self.session_id}.json"
        raise ValueError("No storage path configured")
    
    def _load(self):
        """Load session from storage"""
        session_file = self._get_session_file()
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._entries = [
                        SessionEntry(
                            type=SessionEntryType(e["type"]),
                            data=e["data"],
                            timestamp=e.get("timestamp", 0),
                            id=e.get("id", "")
                        )
                        for e in data.get("entries", [])
                    ]
            except (json.JSONDecodeError, KeyError, ValueError):
                self._entries = []
    
    def save(self):
        """Save session to storage"""
        if not self._storage_path:
            return
        
        session_file = self._get_session_file()
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "session_id": self.session_id,
            "entries": [
                {
                    "type": e.type.value,
                    "data": e.data,
                    "timestamp": e.timestamp,
                    "id": e.id
                }
                for e in self._entries
            ]
        }
        
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def add_entry(self, entry_type: SessionEntryType, data: Dict[str, Any]) -> SessionEntry:
        """
        Add an entry to the session.
        
        Args:
            entry_type: Type of entry
            data: Entry data
            
        Returns:
            Created entry
        """
        entry = SessionEntry(type=entry_type, data=data)
        self._entries.append(entry)
        self.save()
        return entry
    
    def get_entries(
        self,
        entry_type: Optional[SessionEntryType] = None,
        limit: Optional[int] = None
    ) -> List[SessionEntry]:
        """
        Get session entries.
        
        Args:
            entry_type: Filter by type (optional)
            limit: Maximum number of entries
            
        Returns:
            List of entries
        """
        entries = self._entries
        
        if entry_type:
            entries = [e for e in entries if e.type == entry_type]
        
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def clear(self):
        """Clear all entries"""
        self._entries = []
        self.save()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            "session_id": self.session_id,
            "entry_count": len(self._entries),
            "entry_types": list(set(e.type.value for e in self._entries)),
        }


__all__ = [
    "SessionManager",
    "SessionEntry",
    "SessionEntryType",
]
