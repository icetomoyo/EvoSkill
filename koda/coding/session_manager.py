"""
Session Manager - Full tree-based session management
Equivalent to Pi Mono's session-manager.ts
"""
import json
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum, auto

from koda.ai.types import Message, Context, Usage


class EntryType(Enum):
    """Session entry types"""
    MESSAGE = "message"
    COMPACTION = "compaction"
    MODEL_CHANGE = "model_change"
    THINKING_LEVEL_CHANGE = "thinking_level_change"
    CUSTOM = "custom"
    FILE = "file"


@dataclass
class SessionEntryBase:
    """Base session entry"""
    id: str
    type: EntryType
    timestamp: int
    branch_id: str = "main"
    parent_id: Optional[str] = None


@dataclass
class SessionMessageEntry(SessionEntryBase):
    """Message entry"""
    role: str = ""
    content: Any = None
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None
    usage: Optional[Usage] = None


@dataclass
class CompactionEntry(SessionEntryBase):
    """Compaction summary entry"""
    summary: str = ""
    original_count: int = 0
    compacted_count: int = 0
    tokens_saved: int = 0


@dataclass
class BranchSummaryEntry:
    """Branch summary"""
    branch_id: str
    summary: str
    entry_count: int
    file_operations: List[str] = field(default_factory=list)


@dataclass
class SessionInfo:
    """Session metadata"""
    id: str
    name: str
    created_at: int
    modified_at: int
    entry_count: int
    branch_count: int


@dataclass
class SessionContext:
    """Full session context"""
    id: str
    name: str
    created_at: int
    modified_at: int
    current_branch: str = "main"
    entries: List[SessionEntryBase] = field(default_factory=list)
    branch_summaries: Dict[str, BranchSummaryEntry] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


SessionEntry = Union[SessionMessageEntry, CompactionEntry, SessionEntryBase]


class SessionManager:
    """
    Full Session Manager
    
    Equivalent to Pi Mono's SessionManager
    
    Features:
    - Tree-based branch navigation
    - Session persistence
    - Import/Export
    - Tag system
    - Garbage collection
    """
    
    CURRENT_VERSION = 1
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, SessionContext] = {}
        self.current_session: Optional[SessionContext] = None
        self._tag_index: Dict[str, List[str]] = {}  # tag -> session_ids
    
    def create_session(self, name: Optional[str] = None) -> SessionContext:
        """Create new session"""
        session_id = str(uuid.uuid4())
        now = int(datetime.now().timestamp())
        
        session = SessionContext(
            id=session_id,
            name=name or f"Session {now}",
            created_at=now,
            modified_at=now,
            current_branch="main",
            entries=[],
            branch_summaries={},
            metadata={"version": self.CURRENT_VERSION}
        )
        
        self.sessions[session_id] = session
        self.current_session = session
        self.save_session(session)
        
        return session
    
    def load_session(self, session_id: str) -> Optional[SessionContext]:
        """Load session from disk"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
        
        try:
            data = json.loads(session_file.read_text(encoding='utf-8'))
            session = self._deserialize_session(data)
            self.sessions[session_id] = session
            return session
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None
    
    def save_session(self, session: SessionContext) -> None:
        """Save session to disk"""
        session.modified_at = int(datetime.now().timestamp())
        session_file = self.storage_dir / f"{session.id}.json"
        
        data = self._serialize_session(session)
        session_file.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')
    
    def fork_branch(
        self,
        session: SessionContext,
        from_entry_id: str,
        new_branch_name: str
    ) -> str:
        """
        Create new branch from specified entry
        
        Equivalent to Pi Mono's fork functionality
        """
        # Find entry index
        entry_idx = None
        for i, entry in enumerate(session.entries):
            if entry.id == from_entry_id:
                entry_idx = i
                break
        
        if entry_idx is None:
            raise ValueError(f"Entry {from_entry_id} not found")
        
        # Create branch summary for entries before fork
        if entry_idx > 0:
            summary = f"Branch {new_branch_name} forked at entry {from_entry_id}"
            branch_summary = BranchSummaryEntry(
                branch_id=new_branch_name,
                summary=summary,
                entry_count=entry_idx
            )
            session.branch_summaries[new_branch_name] = branch_summary
        
        # Update current branch
        session.current_branch = new_branch_name
        
        # Truncate entries to fork point
        session.entries = session.entries[:entry_idx + 1]
        
        self.save_session(session)
        return new_branch_name
    
    def switch_branch(self, session: SessionContext, branch_id: str) -> bool:
        """Switch to existing branch"""
        if branch_id not in session.branch_summaries and branch_id != "main":
            return False
        
        session.current_branch = branch_id
        self.save_session(session)
        return True
    
    def get_branch_history(
        self,
        session: SessionContext,
        branch_id: str
    ) -> List[SessionEntry]:
        """Get branch's full history"""
        if branch_id == "main":
            return [e for e in session.entries if e.branch_id == "main"]
        
        # For other branches, get entries from branch summary
        entries = []
        for entry in session.entries:
            if entry.branch_id == branch_id:
                entries.append(entry)
        
        return entries
    
    def add_entry(self, session: SessionContext, entry: SessionEntryBase) -> None:
        """Add entry to session"""
        entry.branch_id = session.current_branch
        session.entries.append(entry)
        self.save_session(session)
    
    def build_context(
        self,
        session: SessionContext,
        max_tokens: int = 128000
    ) -> Context:
        """
        Build LLM context with branch summary handling
        """
        messages: List[Message] = []
        
        # Get entries for current branch
        branch_entries = self.get_branch_history(session, session.current_branch)
        
        # Convert entries to messages
        for entry in branch_entries:
            if isinstance(entry, SessionMessageEntry):
                from koda.ai.types import UserMessage, AssistantMessage, ToolResultMessage
                
                if entry.role == "user":
                    messages.append(UserMessage(
                        role="user",
                        content=entry.content,
                        timestamp=entry.timestamp
                    ))
                elif entry.role == "assistant":
                    messages.append(AssistantMessage(
                        role="assistant",
                        content=entry.content,
                        timestamp=entry.timestamp
                    ))
                elif entry.role == "tool":
                    messages.append(ToolResultMessage(
                        role="toolResult",
                        tool_call_id=entry.tool_call_id or "",
                        tool_name="",
                        content=entry.content,
                        timestamp=entry.timestamp
                    ))
        
        return Context(
            system_prompt=None,
            messages=messages
        )
    
    def export_session(
        self,
        session: SessionContext,
        format: str = "json"
    ) -> str:
        """
        Export session
        
        Supports: json, markdown
        """
        if format == "json":
            return json.dumps(self._serialize_session(session), indent=2, default=str)
        
        elif format == "markdown":
            lines = [
                f"# {session.name}",
                f"",
                f"Created: {datetime.fromtimestamp(session.created_at)}",
                f"Modified: {datetime.fromtimestamp(session.modified_at)}",
                f"",
                "## Conversation",
                ""
            ]
            
            for entry in session.entries:
                if isinstance(entry, SessionMessageEntry):
                    if entry.role == "user":
                        lines.append(f"### User")
                        lines.append(f"{entry.content}")
                        lines.append("")
                    elif entry.role == "assistant":
                        lines.append(f"### Assistant")
                        lines.append(f"{entry.content}")
                        lines.append("")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def list_sessions(
        self,
        tag: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionInfo]:
        """List sessions with optional tag filtering"""
        sessions = []
        
        # Load all session files
        for session_file in self.storage_dir.glob("*.json"):
            try:
                session_id = session_file.stem
                session = self.load_session(session_id)
                if session:
                    # Filter by tag if specified
                    if tag and tag not in session.metadata.get("tags", []):
                        continue
                    
                    sessions.append(SessionInfo(
                        id=session.id,
                        name=session.name,
                        created_at=session.created_at,
                        modified_at=session.modified_at,
                        entry_count=len(session.entries),
                        branch_count=len(session.branch_summaries) + 1
                    ))
            except Exception:
                continue
        
        # Sort by modified date
        sessions.sort(key=lambda s: s.modified_at, reverse=True)
        return sessions[:limit]
    
    def delete_session(self, session_id: str, permanent: bool = False) -> bool:
        """Delete session (or move to trash)"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            return False
        
        if permanent:
            session_file.unlink()
        else:
            # Move to trash
            trash_dir = self.storage_dir / "trash"
            trash_dir.mkdir(exist_ok=True)
            session_file.rename(trash_dir / f"{session_id}.json")
        
        return True
    
    def gc_old_sessions(self, max_age_days: int = 30) -> int:
        """Clean up old sessions, return count deleted"""
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        deleted = 0
        
        for session_file in self.storage_dir.glob("*.json"):
            try:
                stat = session_file.stat()
                if stat.st_mtime < cutoff:
                    session_file.unlink()
                    deleted += 1
            except Exception:
                continue
        
        return deleted
    
    def _serialize_session(self, session: SessionContext) -> dict:
        """Serialize session to dict"""
        return {
            "version": self.CURRENT_VERSION,
            "id": session.id,
            "name": session.name,
            "created_at": session.created_at,
            "modified_at": session.modified_at,
            "current_branch": session.current_branch,
            "entries": [
                {
                    "id": e.id,
                    "type": e.type.value if isinstance(e.type, EntryType) else e.type,
                    "timestamp": e.timestamp,
                    "branch_id": e.branch_id,
                    "parent_id": e.parent_id,
                    **self._serialize_entry_data(e)
                }
                for e in session.entries
            ],
            "branch_summaries": {
                k: asdict(v) for k, v in session.branch_summaries.items()
            },
            "metadata": session.metadata
        }
    
    def _serialize_entry_data(self, entry: SessionEntryBase) -> dict:
        """Serialize entry-specific data"""
        if isinstance(entry, SessionMessageEntry):
            return {
                "role": entry.role,
                "content": entry.content,
                "tool_calls": entry.tool_calls,
                "tool_call_id": entry.tool_call_id,
                "usage": asdict(entry.usage) if entry.usage else None
            }
        elif isinstance(entry, CompactionEntry):
            return {
                "summary": entry.summary,
                "original_count": entry.original_count,
                "compacted_count": entry.compacted_count,
                "tokens_saved": entry.tokens_saved
            }
        return {}
    
    def _deserialize_session(self, data: dict) -> SessionContext:
        """Deserialize session from dict"""
        session = SessionContext(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            modified_at=data["modified_at"],
            current_branch=data.get("current_branch", "main"),
            entries=[],
            branch_summaries={
                k: BranchSummaryEntry(**v)
                for k, v in data.get("branch_summaries", {}).items()
            },
            metadata=data.get("metadata", {})
        )
        
        # Deserialize entries
        for entry_data in data.get("entries", []):
            entry_type = entry_data.get("type")
            base_fields = {
                "id": entry_data["id"],
                "type": EntryType(entry_type) if isinstance(entry_type, str) else entry_type,
                "timestamp": entry_data["timestamp"],
                "branch_id": entry_data.get("branch_id", "main"),
                "parent_id": entry_data.get("parent_id")
            }
            
            if entry_type == EntryType.MESSAGE.value or entry_type == "message":
                entry = SessionMessageEntry(
                    **base_fields,
                    role=entry_data.get("role", ""),
                    content=entry_data.get("content"),
                    tool_calls=entry_data.get("tool_calls"),
                    tool_call_id=entry_data.get("tool_call_id"),
                    usage=Usage(**entry_data["usage"]) if entry_data.get("usage") else None
                )
            elif entry_type == EntryType.COMPACTION.value or entry_type == "compaction":
                entry = CompactionEntry(
                    **base_fields,
                    summary=entry_data.get("summary", ""),
                    original_count=entry_data.get("original_count", 0),
                    compacted_count=entry_data.get("compacted_count", 0),
                    tokens_saved=entry_data.get("tokens_saved", 0)
                )
            else:
                entry = SessionEntryBase(**base_fields)
            
            session.entries.append(entry)
        
        return session
