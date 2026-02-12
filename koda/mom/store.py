"""
Store - Persistent storage with attachment handling
Equivalent to Pi Mono's store.ts
"""
import json
import base64
import hashlib
import time
from typing import Optional, Any, List, Dict, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import mimetypes
import shutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class Attachment:
    """
    File attachment data

    Equivalent to Pi Mono's Attachment
    """
    # Identification
    id: str
    filename: str
    mime_type: str

    # Content
    content: Optional[bytes] = None  # Binary content
    content_path: Optional[str] = None  # Path to file if stored separately
    content_url: Optional[str] = None  # URL if external

    # Metadata
    size_bytes: int = 0
    checksum: Optional[str] = None  # SHA256 hash
    created_at: float = field(default_factory=time.time)

    # Extra
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without binary content)"""
        return {
            "id": self.id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "content_path": self.content_path,
            "content_url": self.content_url,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attachment":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            filename=data["filename"],
            mime_type=data["mime_type"],
            content_path=data.get("content_path"),
            content_url=data.get("content_url"),
            size_bytes=data.get("size_bytes", 0),
            checksum=data.get("checksum"),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_file(
        cls,
        file_path: Union[str, Path],
        attachment_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Attachment":
        """
        Create attachment from file

        Args:
            file_path: Path to file
            attachment_id: Optional ID (generated if not provided)
            metadata: Optional metadata

        Returns:
            Attachment instance
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate ID if not provided
        if attachment_id is None:
            attachment_id = hashlib.sha256(
                f"{file_path.name}:{time.time()}".encode()
            ).hexdigest()[:16]

        # Detect mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Read content and compute checksum
        content = file_path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()

        return cls(
            id=attachment_id,
            filename=file_path.name,
            mime_type=mime_type,
            content=content,
            size_bytes=len(content),
            checksum=checksum,
            metadata=metadata or {},
        )

    def get_content(self) -> Optional[bytes]:
        """Get attachment content"""
        if self.content is not None:
            return self.content

        if self.content_path:
            path = Path(self.content_path)
            if path.exists():
                return path.read_bytes()

        return None

    def get_content_base64(self) -> Optional[str]:
        """Get content as base64 string"""
        content = self.get_content()
        if content:
            return base64.b64encode(content).decode('utf-8')
        return None


@dataclass
class LoggedMessage:
    """
    Logged message with metadata

    Equivalent to Pi Mono's LoggedMessage
    """
    # Message identification
    id: str
    role: str  # user, assistant, toolResult
    timestamp: float

    # Content
    content: Any  # Can be string or list of content parts
    content_type: str = "text"  # text, structured

    # Context
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    parent_message_id: Optional[str] = None

    # Tool information (for toolResult)
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None

    # Metadata
    token_count: Optional[int] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Attachments
    attachments: List[str] = field(default_factory=list)  # Attachment IDs

    # Flags
    is_error: bool = False
    is_flagged: bool = False
    is_deleted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "role": self.role,
            "timestamp": self.timestamp,
            "content": self.content,
            "content_type": self.content_type,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_message_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "token_count": self.token_count,
            "model": self.model,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
            "attachments": self.attachments,
            "is_error": self.is_error,
            "is_flagged": self.is_flagged,
            "is_deleted": self.is_deleted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggedMessage":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            role=data["role"],
            timestamp=data["timestamp"],
            content=data.get("content"),
            content_type=data.get("content_type", "text"),
            session_id=data.get("session_id"),
            conversation_id=data.get("conversation_id"),
            parent_message_id=data.get("parent_message_id"),
            tool_call_id=data.get("tool_call_id"),
            tool_name=data.get("tool_name"),
            token_count=data.get("token_count"),
            model=data.get("model"),
            provider=data.get("provider"),
            latency_ms=data.get("latency_ms"),
            metadata=data.get("metadata", {}),
            attachments=data.get("attachments", []),
            is_error=data.get("is_error", False),
            is_flagged=data.get("is_flagged", False),
            is_deleted=data.get("is_deleted", False),
        )


def processAttachments(
    attachments: List[Attachment],
    store_path: Optional[Path] = None,
    max_size_mb: float = 10.0,
    allowed_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Process and validate attachments

    Equivalent to Pi Mono's processAttachments

    Args:
        attachments: List of attachments to process
        store_path: Path to store attachment files
        max_size_mb: Maximum size per attachment in MB
        allowed_types: List of allowed MIME types (None = all allowed)

    Returns:
        Dictionary with processed attachments and any errors
    """
    result = {
        "processed": [],
        "errors": [],
        "total_size": 0,
    }

    for attachment in attachments:
        # Check size
        size_mb = attachment.size_bytes / (1024 * 1024)
        if size_mb > max_size_mb:
            result["errors"].append({
                "attachment_id": attachment.id,
                "error": f"Attachment too large: {size_mb:.2f}MB > {max_size_mb}MB",
            })
            continue

        # Check type
        if allowed_types and attachment.mime_type not in allowed_types:
            result["errors"].append({
                "attachment_id": attachment.id,
                "error": f"Type not allowed: {attachment.mime_type}",
            })
            continue

        # Store content if needed
        if store_path and attachment.content:
            att_dir = store_path / "attachments"
            att_dir.mkdir(parents=True, exist_ok=True)

            file_path = att_dir / f"{attachment.id}_{attachment.filename}"
            file_path.write_bytes(attachment.content)

            # Update attachment with stored path
            attachment.content_path = str(file_path)
            attachment.content = None  # Clear memory

        result["processed"].append(attachment)
        result["total_size"] += attachment.size_bytes

    return result


def logMessage(
    message: LoggedMessage,
    log_path: Optional[Path] = None,
    store: Optional["Store"] = None
) -> bool:
    """
    Log a message to storage

    Equivalent to Pi Mono's logMessage

    Args:
        message: Message to log
        log_path: Path to log file
        store: Store instance to use

    Returns:
        True if logged successfully
    """
    try:
        message_dict = message.to_dict()

        # Log to file
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Append to log file
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(message_dict) + "\n")

        # Log to store
        if store:
            store.set(f"message:{message.id}", message_dict)

            # Update message index
            index_key = f"messages:{message.session_id or 'default'}"
            existing = store.get(index_key) or []
            existing.append(message.id)
            store.set(index_key, existing)

        return True

    except Exception as e:
        logger.error(f"Failed to log message: {e}")
        return False


class MessageHistory:
    """
    Message history manager

    Manages conversation history with search and filtering
    """

    def __init__(
        self,
        store: "Store",
        session_id: Optional[str] = None,
        max_messages: int = 1000
    ):
        self.store = store
        self.session_id = session_id or "default"
        self.max_messages = max_messages
        self._cache: Dict[str, LoggedMessage] = {}

    def add_message(self, message: LoggedMessage) -> None:
        """Add message to history"""
        if message.session_id is None:
            message.session_id = self.session_id

        # Store message
        self.store.set(f"message:{message.id}", message.to_dict())

        # Update index
        index_key = f"messages:{self.session_id}"
        existing = self.store.get(index_key) or []
        existing.append(message.id)

        # Trim if needed
        if len(existing) > self.max_messages:
            # Remove oldest messages
            to_remove = existing[:-self.max_messages]
            for msg_id in to_remove:
                self.store.delete(f"message:{msg_id}")
            existing = existing[-self.max_messages:]

        self.store.set(index_key, existing)

        # Update cache
        self._cache[message.id] = message

    def get_message(self, message_id: str) -> Optional[LoggedMessage]:
        """Get message by ID"""
        # Check cache first
        if message_id in self._cache:
            return self._cache[message_id]

        # Load from store
        data = self.store.get(f"message:{message_id}")
        if data:
            message = LoggedMessage.from_dict(data)
            self._cache[message_id] = message
            return message

        return None

    def get_messages(
        self,
        limit: int = 100,
        before_id: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[LoggedMessage]:
        """
        Get messages from history

        Args:
            limit: Maximum number of messages
            before_id: Get messages before this ID
            role: Filter by role

        Returns:
            List of messages
        """
        index_key = f"messages:{self.session_id}"
        message_ids = self.store.get(index_key) or []

        messages = []
        found_before = before_id is None

        # Iterate in reverse (newest first)
        for msg_id in reversed(message_ids):
            if not found_before:
                if msg_id == before_id:
                    found_before = True
                continue

            message = self.get_message(msg_id)
            if message is None:
                continue

            # Filter by role
            if role and message.role != role:
                continue

            # Skip deleted
            if message.is_deleted:
                continue

            messages.append(message)

            if len(messages) >= limit:
                break

        return messages

    def search(
        self,
        query: str,
        limit: int = 50,
        role: Optional[str] = None
    ) -> List[LoggedMessage]:
        """
        Search messages

        Args:
            query: Search query
            limit: Maximum results
            role: Filter by role

        Returns:
            List of matching messages
        """
        index_key = f"messages:{self.session_id}"
        message_ids = self.store.get(index_key) or []

        results = []
        query_lower = query.lower()

        for msg_id in message_ids:
            message = self.get_message(msg_id)
            if message is None:
                continue

            # Skip deleted
            if message.is_deleted:
                continue

            # Filter by role
            if role and message.role != role:
                continue

            # Search in content
            content_str = ""
            if isinstance(message.content, str):
                content_str = message.content
            elif isinstance(message.content, list):
                content_str = " ".join(
                    str(item) for item in message.content
                )

            if query_lower in content_str.lower():
                results.append(message)

            if len(results) >= limit:
                break

        return results

    def delete_message(self, message_id: str) -> bool:
        """Soft delete a message"""
        message = self.get_message(message_id)
        if message:
            message.is_deleted = True
            self.store.set(f"message:{message_id}", message.to_dict())
            if message_id in self._cache:
                del self._cache[message_id]
            return True
        return False

    def clear_history(self) -> int:
        """
        Clear all history for this session

        Returns:
            Number of messages deleted
        """
        index_key = f"messages:{self.session_id}"
        message_ids = self.store.get(index_key) or []

        for msg_id in message_ids:
            self.store.delete(f"message:{msg_id}")
            if msg_id in self._cache:
                del self._cache[msg_id]

        self.store.delete(index_key)
        return len(message_ids)

    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics"""
        index_key = f"messages:{self.session_id}"
        message_ids = self.store.get(index_key) or []

        stats = {
            "total_messages": len(message_ids),
            "by_role": {},
            "total_tokens": 0,
            "date_range": None,
        }

        dates = []
        for msg_id in message_ids:
            message = self.get_message(msg_id)
            if message:
                # Count by role
                role = message.role
                stats["by_role"][role] = stats["by_role"].get(role, 0) + 1

                # Sum tokens
                if message.token_count:
                    stats["total_tokens"] += message.token_count

                # Track dates
                dates.append(datetime.fromtimestamp(message.timestamp))

        if dates:
            stats["date_range"] = {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat(),
            }

        return stats


class Store:
    """
    Persistent key-value storage

    Simple JSON-based storage for agent data with support for:
    - Key-value operations
    - Attachments
    - Message history
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self._attachments: Dict[str, Attachment] = {}
        self._message_history: Optional[MessageHistory] = None
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

    # Basic key-value operations
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
        self._attachments = {}
        self._save()

    # Attachment operations
    def store_attachment(self, attachment: Attachment) -> str:
        """
        Store an attachment

        Args:
            attachment: Attachment to store

        Returns:
            Attachment ID
        """
        self._attachments[attachment.id] = attachment

        # Store reference in data
        self._data[f"attachment:{attachment.id}"] = attachment.to_dict()
        self._save()

        return attachment.id

    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        """Get attachment by ID"""
        # Check memory cache
        if attachment_id in self._attachments:
            return self._attachments[attachment_id]

        # Load from data
        data = self._data.get(f"attachment:{attachment_id}")
        if data:
            attachment = Attachment.from_dict(data)
            self._attachments[attachment_id] = attachment
            return attachment

        return None

    def list_attachments(self) -> List[str]:
        """List all attachment IDs"""
        return [
            k.replace("attachment:", "")
            for k in self._data.keys()
            if k.startswith("attachment:")
        ]

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment"""
        if f"attachment:{attachment_id}" in self._data:
            del self._data[f"attachment:{attachment_id}"]
            if attachment_id in self._attachments:
                del self._attachments[attachment_id]
            self._save()
            return True
        return False

    # Message history operations
    def get_message_history(
        self,
        session_id: Optional[str] = None,
        max_messages: int = 1000
    ) -> MessageHistory:
        """Get or create message history for session"""
        if self._message_history is None or (session_id and session_id != self._message_history.session_id):
            self._message_history = MessageHistory(
                store=self,
                session_id=session_id,
                max_messages=max_messages
            )
        return self._message_history

    # Bulk operations
    def export_data(self) -> Dict[str, Any]:
        """Export all data"""
        return {
            "data": dict(self._data),
            "exported_at": datetime.now().isoformat(),
        }

    def import_data(self, data: Dict[str, Any], merge: bool = True) -> None:
        """
        Import data

        Args:
            data: Data to import
            merge: If True, merge with existing; if False, replace
        """
        if merge:
            self._data.update(data.get("data", {}))
        else:
            self._data = data.get("data", {})
        self._save()

    # Context manager support
    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *args) -> None:
        self._save()
