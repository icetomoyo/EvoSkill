"""
Context Manager - Dynamic context management
Equivalent to Pi Mono's context.ts
"""
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import asyncio
import time

from koda.ai.types import Message, Context, Tool


@dataclass
class MomSettings:
    """
    Mom settings configuration

    Equivalent to Pi Mono's MomSettings
    """
    # Context management settings
    max_tokens: int = 128000
    compact_threshold: float = 0.9
    keep_recent_messages: int = 3

    # Logging settings
    log_to_session_manager: bool = True
    log_level: str = "info"

    # Session settings
    session_id: Optional[str] = None
    session_dir: Optional[Path] = None

    # Behavior settings
    auto_compact: bool = True
    persist_context: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_tokens": self.max_tokens,
            "compact_threshold": self.compact_threshold,
            "keep_recent_messages": self.keep_recent_messages,
            "log_to_session_manager": self.log_to_session_manager,
            "log_level": self.log_level,
            "session_id": self.session_id,
            "session_dir": str(self.session_dir) if self.session_dir else None,
            "auto_compact": self.auto_compact,
            "persist_context": self.persist_context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MomSettings":
        """Create from dictionary"""
        if data.get("session_dir"):
            data["session_dir"] = Path(data["session_dir"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MomSettingsManager:
    """
    Manager for Mom settings

    Handles loading, saving, and validating settings
    """

    DEFAULT_SETTINGS_FILE = "mom_settings.json"

    def __init__(self, settings_dir: Optional[Path] = None):
        """
        Initialize settings manager

        Args:
            settings_dir: Directory to store settings (default: current directory)
        """
        self.settings_dir = settings_dir or Path.cwd()
        self._settings: Dict[str, MomSettings] = {}
        self._global_settings: Optional[MomSettings] = None

    def get_settings(self, name: str = "default") -> MomSettings:
        """
        Get settings by name

        Args:
            name: Settings name

        Returns:
            MomSettings instance
        """
        if name not in self._settings:
            self._settings[name] = self._load_settings(name)
        return self._settings[name]

    def set_settings(self, name: str, settings: MomSettings) -> None:
        """
        Set settings by name

        Args:
            name: Settings name
            settings: MomSettings instance
        """
        self._settings[name] = settings
        self._save_settings(name, settings)

    def get_global_settings(self) -> MomSettings:
        """Get global settings"""
        if self._global_settings is None:
            self._global_settings = self.get_settings("global")
        return self._global_settings

    def update_settings(self, name: str, updates: Dict[str, Any]) -> MomSettings:
        """
        Update settings with partial updates

        Args:
            name: Settings name
            updates: Dictionary of updates

        Returns:
            Updated MomSettings
        """
        current = self.get_settings(name)
        current_dict = current.to_dict()
        current_dict.update(updates)
        new_settings = MomSettings.from_dict(current_dict)
        self.set_settings(name, new_settings)
        return new_settings

    def reset_settings(self, name: str = "default") -> MomSettings:
        """
        Reset settings to defaults

        Args:
            name: Settings name

        Returns:
            Default MomSettings
        """
        default = MomSettings()
        self.set_settings(name, default)
        return default

    def _load_settings(self, name: str) -> MomSettings:
        """Load settings from file"""
        settings_file = self.settings_dir / f"{name}_{self.DEFAULT_SETTINGS_FILE}"

        if settings_file.exists():
            try:
                data = json.loads(settings_file.read_text(encoding='utf-8'))
                return MomSettings.from_dict(data)
            except (json.JSONDecodeError, IOError):
                pass

        return MomSettings()

    def _save_settings(self, name: str, settings: MomSettings) -> None:
        """Save settings to file"""
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        settings_file = self.settings_dir / f"{name}_{self.DEFAULT_SETTINGS_FILE}"
        settings_file.write_text(
            json.dumps(settings.to_dict(), indent=2),
            encoding='utf-8'
        )


class SessionManagerClient:
    """
    Client for communicating with session manager

    Handles syncing logs and context to external session manager
    """

    def __init__(self, session_id: Optional[str] = None, endpoint: Optional[str] = None):
        self.session_id = session_id
        self.endpoint = endpoint
        self._log_buffer: List[Dict[str, Any]] = []
        self._sync_interval: float = 5.0
        self._last_sync: float = 0

    async def sync_logs(self, logs: List[Dict[str, Any]]) -> bool:
        """
        Sync logs to session manager

        Args:
            logs: List of log entries

        Returns:
            True if sync successful
        """
        if not self.endpoint:
            # Buffer logs if no endpoint configured
            self._log_buffer.extend(logs)
            return True

        # In a real implementation, this would make HTTP request
        # For now, just buffer the logs
        self._log_buffer.extend(logs)
        return True

    async def sync_context(self, context_data: Dict[str, Any]) -> bool:
        """
        Sync context to session manager

        Args:
            context_data: Context data to sync

        Returns:
            True if sync successful
        """
        if not self.endpoint:
            return True

        # In a real implementation, this would make HTTP request
        return True

    def get_pending_logs(self) -> List[Dict[str, Any]]:
        """Get pending logs that haven't been synced"""
        return list(self._log_buffer)

    def clear_buffer(self) -> None:
        """Clear log buffer"""
        self._log_buffer.clear()


class ContextManager:
    """
    Dynamic context management

    Manages conversation context with automatic window management
    """

    def __init__(
        self,
        max_tokens: int = 128000,
        settings: Optional[MomSettings] = None
    ):
        self.max_tokens = max_tokens
        self.settings = settings or MomSettings(max_tokens=max_tokens)
        self._messages: List[Message] = []
        self._metadata: Dict[str, Any] = {}
        self._session_client: Optional[SessionManagerClient] = None
        self._log_buffer: List[Dict[str, Any]] = []

    def set_session_client(self, client: SessionManagerClient) -> None:
        """Set session manager client"""
        self._session_client = client

    def add(self, message: Message) -> None:
        """Add message, auto-manage context window"""
        self._messages.append(message)

        # Log the message
        self._log_message_add(message)

        # Check if we need to compact
        if self.settings.auto_compact:
            tokens = self._estimate_tokens()
            if tokens > self.max_tokens * self.settings.compact_threshold:
                self._compact()

    async def syncLogToSessionManager(self) -> bool:
        """
        Sync logs to session manager

        Equivalent to Pi Mono's syncLogToSessionManager

        Returns:
            True if sync successful
        """
        if not self._session_client:
            return False

        # Prepare logs to sync
        logs_to_sync = list(self._log_buffer)

        if not logs_to_sync:
            return True

        # Sync to session manager
        success = await self._session_client.sync_logs(logs_to_sync)

        if success:
            # Clear synced logs
            self._log_buffer.clear()

            # Also sync context if we have a session
            if self.settings.session_id:
                context_data = {
                    "session_id": self.settings.session_id,
                    "message_count": len(self._messages),
                    "token_estimate": self._estimate_tokens(),
                    "metadata": self._metadata,
                }
                await self._session_client.sync_context(context_data)

        return success

    def get_context(
        self,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Tool]] = None
    ) -> Context:
        """Get current context"""
        return Context(
            system_prompt=system_prompt,
            messages=list(self._messages),
            tools=tools
        )

    def clear(self) -> None:
        """Clear context"""
        self._messages = []
        self._metadata = {}
        self._log_message_action("clear", {"message_count": len(self._messages)})

    def get_messages(self) -> List[Message]:
        """Get message list"""
        return list(self._messages)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata"""
        self._metadata[key] = value

    def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata"""
        return self._metadata.get(key)

    def get_token_estimate(self) -> int:
        """Get estimated token count"""
        return self._estimate_tokens()

    def get_message_count(self) -> int:
        """Get number of messages"""
        return len(self._messages)

    def remove_message(self, index: int) -> Optional[Message]:
        """
        Remove message at index

        Args:
            index: Message index

        Returns:
            Removed message or None
        """
        if 0 <= index < len(self._messages):
            removed = self._messages.pop(index)
            self._log_message_action("remove", {"index": index})
            return removed
        return None

    def insert_message(self, index: int, message: Message) -> None:
        """
        Insert message at index

        Args:
            index: Position to insert
            message: Message to insert
        """
        self._messages.insert(index, message)
        self._log_message_action("insert", {"index": index})

    def compact(self) -> int:
        """
        Manually trigger compaction

        Returns:
            Number of messages removed
        """
        return self._compact()

    def _estimate_tokens(self) -> int:
        """Estimate token count"""
        total = 0
        for msg in self._messages:
            content = getattr(msg, 'content', '')
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for item in content:
                    if hasattr(item, 'text'):
                        total += len(item.text) // 4
                    elif hasattr(item, 'thinking'):
                        total += len(item.thinking) // 4
                    else:
                        total += 4
            else:
                total += 4
        return total + len(self._messages) * 4

    def _compact(self) -> int:
        """Compact context by removing oldest messages"""
        original_count = len(self._messages)
        keep_count = max(
            len(self._messages) // 2,
            self.settings.keep_recent_messages
        )
        removed = original_count - keep_count

        if removed > 0:
            self._messages = self._messages[-keep_count:]
            self._log_message_action("compact", {
                "removed": removed,
                "remaining": keep_count
            })

        return removed

    def _log_message_add(self, message: Message) -> None:
        """Log message addition"""
        log_entry = {
            "timestamp": time.time(),
            "action": "add",
            "role": getattr(message, 'role', 'unknown'),
            "token_estimate": self._estimate_message_tokens(message),
        }
        self._log_buffer.append(log_entry)

    def _log_message_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log message action"""
        log_entry = {
            "timestamp": time.time(),
            "action": action,
            **details,
        }
        self._log_buffer.append(log_entry)

    def _estimate_message_tokens(self, message: Message) -> int:
        """Estimate tokens for a single message"""
        content = getattr(message, 'content', '')
        if isinstance(content, str):
            return len(content) // 4 + 4
        elif isinstance(content, list):
            total = 4
            for item in content:
                if hasattr(item, 'text'):
                    total += len(item.text) // 4
                elif hasattr(item, 'thinking'):
                    total += len(item.thinking) // 4
            return total
        return 4

    def save_context(self, path: Path) -> None:
        """
        Save context to file

        Args:
            path: File path to save to
        """
        # Note: In a full implementation, we'd serialize messages properly
        # For now, save basic info
        data = {
            "max_tokens": self.max_tokens,
            "message_count": len(self._messages),
            "metadata": self._metadata,
            "settings": self.settings.to_dict(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def load_context(self, path: Path) -> bool:
        """
        Load context from file

        Args:
            path: File path to load from

        Returns:
            True if loaded successfully
        """
        if not path.exists():
            return False

        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            self.max_tokens = data.get("max_tokens", self.max_tokens)
            self._metadata = data.get("metadata", {})
            if "settings" in data:
                self.settings = MomSettings.from_dict(data["settings"])
            return True
        except (json.JSONDecodeError, IOError):
            return False
