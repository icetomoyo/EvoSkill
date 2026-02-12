"""
Mom Agent - Multi-channel agent runner
Equivalent to Pi Mono's mom/agent.ts

Provides:
- Multi-channel agent management
- Per-channel memory
- Agent session lifecycle
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional
import json
import uuid

from koda.ai.types import Context, Message, UserMessage, AssistantMessage
from koda.ai.provider_base import BaseProvider
from koda.ai.models.registry import ModelRegistry, get_model_registry
from koda.coding.core.agent_session import AgentSession, AgentSessionConfig, SessionEvent
from koda.mom.store import MomStore
from koda.mom.context import ContextManager


@dataclass
class ChannelConfig:
    """Per-channel configuration"""
    channel_id: str
    model: str = "claude-sonnet-4"
    system_prompt: Optional[str] = None
    memory_enabled: bool = True
    max_context_tokens: int = 180000

    # Channel-specific settings
    auto_response: bool = True
    response_delay: float = 0.0


@dataclass
class ChannelMemory:
    """Channel memory/state"""
    channel_id: str
    summary: str = ""
    key_facts: List[str] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "summary": self.summary,
            "key_facts": self.key_facts,
            "last_activity": self.last_activity.isoformat(),
            "message_count": self.message_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelMemory":
        return cls(
            channel_id=data["channel_id"],
            summary=data.get("summary", ""),
            key_facts=data.get("key_facts", []),
            last_activity=datetime.fromisoformat(data["last_activity"]) if "last_activity" in data else datetime.now(),
            message_count=data.get("message_count", 0),
        )


@dataclass
class MomAgentConfig:
    """Mom agent configuration"""
    default_model: str = "claude-sonnet-4"
    max_channels: int = 100
    memory_dir: Path = field(default_factory=lambda: Path.home() / ".koda" / "mom" / "memory")
    session_dir: Path = field(default_factory=lambda: Path.home() / ".koda" / "mom" / "sessions")

    # Memory settings
    auto_memory_update: bool = True
    memory_update_interval: float = 300.0  # 5 minutes

    # Response settings
    default_response_timeout: float = 120.0


class MomAgent:
    """
    Mom Agent - Multi-channel agent runner.

    Manages multiple agent sessions across different channels,
    with per-channel memory and state persistence.

    Usage:
        mom = MomAgent(provider, config)

        # Handle incoming message
        async for event in mom.handle_message(channel_id, user_id, content):
            print(event)

        # Get or create a runner for a channel
        session = await mom.get_or_create_runner(channel_id)

        # Load/save channel memory
        memory = await mom.load_memory(channel_id)
        await mom.save_memory(channel_id, memory)
    """

    def __init__(
        self,
        provider: BaseProvider,
        config: Optional[MomAgentConfig] = None
    ):
        self.provider = provider
        self.config = config or MomAgentConfig()

        # Ensure directories exist
        self.config.memory_dir.mkdir(parents=True, exist_ok=True)
        self.config.session_dir.mkdir(parents=True, exist_ok=True)

        # Channel sessions
        self._sessions: Dict[str, AgentSession] = {}

        # Channel memories
        self._memories: Dict[str, ChannelMemory] = {}

        # Channel configs
        self._channel_configs: Dict[str, ChannelConfig] = {}

        # Store
        self._store = MomStore(self.config.memory_dir)

        # Model registry
        self._model_registry = get_model_registry()

        # Background tasks
        self._memory_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the mom agent"""
        self._running = True

        # Start background memory update task
        if self.config.auto_memory_update:
            self._memory_task = asyncio.create_task(self._memory_update_loop())

    async def stop(self) -> None:
        """Stop the mom agent"""
        self._running = False

        # Cancel background tasks
        if self._memory_task:
            self._memory_task.cancel()

        # Save all memories
        for channel_id, memory in self._memories.items():
            await self.save_memory(channel_id, memory)

        # Close all sessions
        for session in self._sessions.values():
            # Could add session cleanup here
            pass

    async def get_or_create_runner(self, channel_id: str) -> AgentSession:
        """
        Get or create an agent session for a channel.

        Args:
            channel_id: Channel identifier

        Returns:
            AgentSession for the channel
        """
        if channel_id in self._sessions:
            return self._sessions[channel_id]

        # Get channel config
        channel_config = self._channel_configs.get(channel_id, ChannelConfig(
            channel_id=channel_id,
            model=self.config.default_model
        ))

        # Get model info
        model_info = self._model_registry.get_model_info(channel_config.model)
        if not model_info:
            raise ValueError(f"Unknown model: {channel_config.model}")

        # Create session config
        session_config = AgentSessionConfig(
            model=channel_config.model,
            provider=self.provider.provider_id,
            max_context_tokens=channel_config.max_context_tokens,
            session_id=f"mom_{channel_id}",
            working_dir=Path.cwd(),
        )

        # Create session
        session = AgentSession(self.provider, model_info, session_config)

        # Load memory if enabled
        if channel_config.memory_enabled:
            memory = await self.load_memory(channel_id)
            if memory.summary:
                # Add memory to session context
                # This could be added as a system message or context
                pass

        self._sessions[channel_id] = session
        return session

    async def handle_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[SessionEvent]:
        """
        Handle an incoming message from a user in a channel.

        Args:
            channel_id: Channel identifier
            user_id: User identifier
            content: Message content
            metadata: Optional metadata

        Yields:
            SessionEvent objects
        """
        # Get or create session
        session = await self.get_or_create_runner(channel_id)

        # Update memory
        memory = self._memories.get(channel_id)
        if memory:
            memory.message_count += 1
            memory.last_activity = datetime.now()

        # Build enhanced prompt with context
        enhanced_content = self._build_enhanced_content(
            channel_id, user_id, content, metadata
        )

        # Stream response
        async for event in session.prompt(enhanced_content):
            yield event

    def _build_enhanced_content(
        self,
        channel_id: str,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build enhanced content with context"""
        parts = []

        # Add memory context if available
        memory = self._memories.get(channel_id)
        if memory and memory.summary:
            parts.append(f"[Context: {memory.summary}]")

        # Add user attribution if useful
        if metadata and metadata.get("is_dm"):
            parts.append(f"[Direct message]")
        else:
            parts.append(f"[{user_id}]")

        parts.append(content)

        return "\n".join(parts)

    async def load_memory(self, channel_id: str) -> ChannelMemory:
        """
        Load memory for a channel.

        Args:
            channel_id: Channel identifier

        Returns:
            ChannelMemory object
        """
        if channel_id in self._memories:
            return self._memories[channel_id]

        # Try to load from store
        memory_data = await self._store.load(f"{channel_id}_memory.json")

        if memory_data:
            memory = ChannelMemory.from_dict(memory_data)
        else:
            memory = ChannelMemory(channel_id=channel_id)

        self._memories[channel_id] = memory
        return memory

    async def save_memory(
        self,
        channel_id: str,
        memory: Optional[ChannelMemory] = None
    ) -> None:
        """
        Save memory for a channel.

        Args:
            channel_id: Channel identifier
            memory: Memory to save (uses cached if None)
        """
        memory = memory or self._memories.get(channel_id)
        if not memory:
            return

        await self._store.save(f"{channel_id}_memory.json", memory.to_dict())

    def set_channel_config(self, channel_id: str, config: ChannelConfig) -> None:
        """Set configuration for a channel"""
        self._channel_configs[channel_id] = config

    def get_channel_config(self, channel_id: str) -> Optional[ChannelConfig]:
        """Get configuration for a channel"""
        return self._channel_configs.get(channel_id)

    async def get_channel_stats(self, channel_id: str) -> Dict[str, Any]:
        """Get statistics for a channel"""
        session = self._sessions.get(channel_id)
        memory = self._memories.get(channel_id)

        return {
            "channel_id": channel_id,
            "has_session": session is not None,
            "is_idle": session.is_idle if session else True,
            "memory": memory.to_dict() if memory else None,
            "stats": session.get_stats() if session else None,
        }

    async def list_active_channels(self) -> List[str]:
        """List all channels with active sessions"""
        return list(self._sessions.keys())

    async def close_channel(self, channel_id: str) -> None:
        """Close a channel session"""
        if channel_id in self._sessions:
            del self._sessions[channel_id]

        # Save memory before closing
        if channel_id in self._memories:
            await self.save_memory(channel_id)
            del self._memories[channel_id]

    async def _memory_update_loop(self) -> None:
        """Background task to periodically update memories"""
        while self._running:
            try:
                await asyncio.sleep(self.config.memory_update_interval)

                # Save all dirty memories
                for channel_id, memory in self._memories.items():
                    await self.save_memory(channel_id, memory)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Memory update error: {e}")

    async def update_memory_summary(
        self,
        channel_id: str,
        summary: str,
        key_facts: Optional[List[str]] = None
    ) -> None:
        """
        Update memory summary for a channel.

        This can be called after important conversations to
        maintain context across sessions.

        Args:
            channel_id: Channel identifier
            summary: New summary
            key_facts: Key facts to remember
        """
        memory = await self.load_memory(channel_id)
        memory.summary = summary

        if key_facts:
            # Merge with existing facts, avoiding duplicates
            existing = set(memory.key_facts)
            for fact in key_facts:
                if fact not in existing:
                    memory.key_facts.append(fact)
                    existing.add(fact)

            # Keep only last 20 facts
            memory.key_facts = memory.key_facts[-20:]

        await self.save_memory(channel_id, memory)
