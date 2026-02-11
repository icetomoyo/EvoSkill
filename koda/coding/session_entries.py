"""
Session Entry Types
Equivalent to Pi Mono's packages/coding-agent/src/core/session-manager.ts entry types

All session entry types for complete session history.
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EntryType(Enum):
    """Session entry types"""
    MESSAGE = "message"
    COMPACTION = "compaction"
    MODEL_CHANGE = "model_change"
    THINKING_LEVEL_CHANGE = "thinking_level_change"
    CUSTOM = "custom"
    FILE = "file"


@dataclass
class SessionEntry:
    """Base session entry"""
    id: str
    type: EntryType
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    branch: str = "main"


@dataclass
class SessionMessageEntry(SessionEntry):
    """Message entry (user or assistant)"""
    role: str = "user"
    content: str = ""
    
    def __post_init__(self):
        self.type = EntryType.MESSAGE


@dataclass
class CompactionEntry(SessionEntry):
    """Compaction event entry"""
    summary: str = ""
    cut_point: int = 0
    entries_summarized: int = 0
    
    def __post_init__(self):
        self.type = EntryType.COMPACTION


@dataclass
class ModelChangeEntry(SessionEntry):
    """Model change entry"""
    old_model: str = ""
    new_model: str = ""
    old_provider: str = ""
    new_provider: str = ""
    
    def __post_init__(self):
        self.type = EntryType.MODEL_CHANGE


@dataclass
class ThinkingLevelChangeEntry(SessionEntry):
    """Thinking level change entry"""
    old_level: str = "medium"
    new_level: str = "medium"
    
    def __post_init__(self):
        self.type = EntryType.THINKING_LEVEL_CHANGE


@dataclass
class CustomEntry(SessionEntry):
    """Custom entry for extensions"""
    name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.type = EntryType.CUSTOM


@dataclass
class FileEntry(SessionEntry):
    """File operation entry"""
    operation: str = ""  # read, write, edit
    file_path: str = ""
    content_hash: Optional[str] = None
    
    def __post_init__(self):
        self.type = EntryType.FILE


@dataclass
class BranchSummaryEntry:
    """Branch summary for compaction"""
    branch: str
    summary: str
    timestamp: int
    entry_count: int


# Type alias for all entry types
SessionEntryUnion = (
    SessionMessageEntry | 
    CompactionEntry | 
    ModelChangeEntry | 
    ThinkingLevelChangeEntry | 
    CustomEntry | 
    FileEntry
)


def entry_to_dict(entry: SessionEntry) -> Dict[str, Any]:
    """Convert entry to dictionary"""
    base = {
        "id": entry.id,
        "type": entry.type.value,
        "timestamp": entry.timestamp,
        "branch": entry.branch,
    }
    
    if isinstance(entry, SessionMessageEntry):
        base.update({"role": entry.role, "content": entry.content})
    elif isinstance(entry, CompactionEntry):
        base.update({
            "summary": entry.summary,
            "cut_point": entry.cut_point,
            "entries_summarized": entry.entries_summarized,
        })
    elif isinstance(entry, ModelChangeEntry):
        base.update({
            "old_model": entry.old_model,
            "new_model": entry.new_model,
            "old_provider": entry.old_provider,
            "new_provider": entry.new_provider,
        })
    elif isinstance(entry, ThinkingLevelChangeEntry):
        base.update({
            "old_level": entry.old_level,
            "new_level": entry.new_level,
        })
    elif isinstance(entry, CustomEntry):
        base.update({"name": entry.name, "data": entry.data})
    elif isinstance(entry, FileEntry):
        base.update({
            "operation": entry.operation,
            "file_path": entry.file_path,
            "content_hash": entry.content_hash,
        })
    
    return base


def entry_from_dict(data: Dict[str, Any]) -> SessionEntry:
    """Create entry from dictionary"""
    entry_type = EntryType(data.get("type", "message"))
    
    if entry_type == EntryType.MESSAGE:
        return SessionMessageEntry(
            id=data["id"],
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", 0),
            branch=data.get("branch", "main"),
        )
    elif entry_type == EntryType.COMPACTION:
        return CompactionEntry(
            id=data["id"],
            summary=data.get("summary", ""),
            cut_point=data.get("cut_point", 0),
            entries_summarized=data.get("entries_summarized", 0),
            timestamp=data.get("timestamp", 0),
            branch=data.get("branch", "main"),
        )
    elif entry_type == EntryType.MODEL_CHANGE:
        return ModelChangeEntry(
            id=data["id"],
            old_model=data.get("old_model", ""),
            new_model=data.get("new_model", ""),
            old_provider=data.get("old_provider", ""),
            new_provider=data.get("new_provider", ""),
            timestamp=data.get("timestamp", 0),
            branch=data.get("branch", "main"),
        )
    elif entry_type == EntryType.THINKING_LEVEL_CHANGE:
        return ThinkingLevelChangeEntry(
            id=data["id"],
            old_level=data.get("old_level", "medium"),
            new_level=data.get("new_level", "medium"),
            timestamp=data.get("timestamp", 0),
            branch=data.get("branch", "main"),
        )
    elif entry_type == EntryType.CUSTOM:
        return CustomEntry(
            id=data["id"],
            name=data.get("name", ""),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", 0),
            branch=data.get("branch", "main"),
        )
    elif entry_type == EntryType.FILE:
        return FileEntry(
            id=data["id"],
            operation=data.get("operation", ""),
            file_path=data.get("file_path", ""),
            content_hash=data.get("content_hash"),
            timestamp=data.get("timestamp", 0),
            branch=data.get("branch", "main"),
        )
    else:
        raise ValueError(f"Unknown entry type: {entry_type}")
