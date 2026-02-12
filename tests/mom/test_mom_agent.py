"""
Tests for Mom Module
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path

from koda.mom.agent import (
    MomAgent,
    MomAgentConfig,
    ChannelConfig,
    ChannelMemory,
)
from koda.mom.events import (
    EventsWatcher,
    CronParser,
    ScheduledEvent,
)
from koda.mom.log import (
    StructuredLogger,
    LogLevel,
    LogEntry,
)
from koda.mom.tools import MomTools, ToolResult


class TestChannelMemory:
    """Test ChannelMemory"""

    def test_create_memory(self):
        """Test creating channel memory"""
        memory = ChannelMemory(
            channel_id="test-channel",
            summary="Test summary",
            key_facts=["fact1", "fact2"],
        )

        assert memory.channel_id == "test-channel"
        assert memory.summary == "Test summary"
        assert len(memory.key_facts) == 2

    def test_memory_serialization(self):
        """Test memory serialization"""
        memory = ChannelMemory(
            channel_id="test",
            summary="Summary",
            key_facts=["fact"],
            message_count=10,
        )

        data = memory.to_dict()
        restored = ChannelMemory.from_dict(data)

        assert restored.channel_id == memory.channel_id
        assert restored.summary == memory.summary
        assert restored.key_facts == memory.key_facts
        assert restored.message_count == memory.message_count


class TestMomAgentConfig:
    """Test MomAgentConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = MomAgentConfig()

        assert config.default_model == "claude-sonnet-4"
        assert config.max_channels == 100
        assert config.auto_memory_update is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = MomAgentConfig(
            default_model="gpt-4o",
            max_channels=50,
            auto_memory_update=False,
        )

        assert config.default_model == "gpt-4o"
        assert config.max_channels == 50
        assert config.auto_memory_update is False


class TestMomAgent:
    """Test MomAgent"""

    def test_create_agent(self):
        """Test creating mom agent"""
        mock_provider = MagicMock()
        config = MomAgentConfig()

        agent = MomAgent(mock_provider, config)

        assert agent.provider == mock_provider
        assert agent.config == config

    @pytest.mark.asyncio
    async def test_load_memory(self):
        """Test loading memory"""
        mock_provider = MagicMock()
        agent = MomAgent(mock_provider)

        memory = await agent.load_memory("test-channel")

        assert memory is not None
        assert memory.channel_id == "test-channel"

    @pytest.mark.asyncio
    async def test_save_memory(self):
        """Test saving memory"""
        mock_provider = MagicMock()
        agent = MomAgent(mock_provider)

        memory = ChannelMemory(
            channel_id="test",
            summary="Test summary",
        )

        # Should not raise
        await agent.save_memory("test", memory)

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping agent"""
        mock_provider = MagicMock()
        agent = MomAgent(mock_provider)

        await agent.start()
        assert agent._running is True

        await agent.stop()
        assert agent._running is False


class TestCronParser:
    """Test CronParser"""

    def test_parse_every_minute(self):
        """Test parsing every minute"""
        parsed = CronParser.parse("* * * * *")

        assert len(parsed["minute"]) == 60
        assert len(parsed["hour"]) == 24

    def test_parse_hourly(self):
        """Test parsing hourly"""
        parsed = CronParser.parse("0 * * * *")

        assert parsed["minute"] == [0]
        assert len(parsed["hour"]) == 24

    def test_parse_specific_time(self):
        """Test parsing specific time"""
        parsed = CronParser.parse("30 14 * * *")

        assert parsed["minute"] == [30]
        assert parsed["hour"] == [14]

    def test_parse_range(self):
        """Test parsing range"""
        parsed = CronParser.parse("0 9-17 * * *")

        assert parsed["hour"] == list(range(9, 18))

    def test_parse_step(self):
        """Test parsing step"""
        parsed = CronParser.parse("*/15 * * * *")

        assert parsed["minute"] == [0, 15, 30, 45]

    def test_get_next_run(self):
        """Test getting next run time"""
        from datetime import datetime

        parsed = CronParser.parse("0 * * * *")  # Every hour
        now = datetime(2024, 1, 1, 10, 30)  # 10:30

        next_run = CronParser.get_next_run(parsed, now)

        assert next_run.hour == 11
        assert next_run.minute == 0


class TestEventsWatcher:
    """Test EventsWatcher"""

    def test_create_watcher(self):
        """Test creating watcher"""
        watcher = EventsWatcher()
        assert watcher._running is False

    @pytest.mark.asyncio
    async def test_schedule_immediate(self):
        """Test scheduling immediate callback"""
        watcher = EventsWatcher()
        called = []

        async def callback(metadata):
            called.append(True)

        event_id = watcher.schedule_immediate(callback)

        assert event_id is not None
        assert event_id in watcher._events

    @pytest.mark.asyncio
    async def test_schedule_one_shot(self):
        """Test scheduling one-shot callback"""
        watcher = EventsWatcher()

        callback = MagicMock()
        trigger_time = datetime(2024, 12, 25, 12, 0)

        event_id = watcher.schedule_one_shot(trigger_time, callback)

        assert event_id is not None
        event = watcher._events[event_id]
        assert event.trigger_time == trigger_time
        assert event.repeat is False

    @pytest.mark.asyncio
    async def test_schedule_periodic(self):
        """Test scheduling periodic callback"""
        watcher = EventsWatcher()

        callback = MagicMock()
        cron_expr = "0 * * * *"  # Hourly

        event_id = watcher.schedule_periodic(cron_expr, callback)

        assert event_id is not None
        event = watcher._events[event_id]
        assert event.repeat is True
        assert event.cron_expression == cron_expr
        assert event.next_run is not None

    def test_cancel_event(self):
        """Test cancelling an event"""
        watcher = EventsWatcher()

        event_id = watcher.schedule_immediate(lambda: None)
        assert event_id in watcher._events

        result = watcher.cancel(event_id)
        assert result is True
        assert event_id not in watcher._events


class TestStructuredLogger:
    """Test StructuredLogger"""

    def test_create_logger(self):
        """Test creating logger"""
        logger = StructuredLogger("test")

        assert logger.name == "test"
        assert logger.level == LogLevel.INFO

    def test_set_level(self):
        """Test setting log level"""
        logger = StructuredLogger("test")
        logger.set_level(LogLevel.DEBUG)

        assert logger.level == LogLevel.DEBUG

    def test_set_context(self):
        """Test setting context"""
        logger = StructuredLogger("test")
        logger.set_context({"service": "api", "version": "1.0"})

        assert logger._context["service"] == "api"
        assert logger._context["version"] == "1.0"

    def test_log_entry(self):
        """Test creating log entry"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message="Test message",
            context={"key": "value"},
            source="test",
        )

        data = entry.to_dict()
        assert data["level"] == "info"
        assert data["message"] == "Test message"
        assert data["context"]["key"] == "value"


class TestMomTools:
    """Test MomTools"""

    def test_get_tool_definitions(self):
        """Test getting tool definitions"""
        tools = MomTools()
        definitions = tools.get_tool_definitions()

        assert len(definitions) > 0
        names = [d["name"] for d in definitions]
        assert "read" in names
        assert "write" in names
        assert "bash" in names

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file"""
        tools = MomTools()
        result = tools.read("/nonexistent/file.txt")

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_write_and_read_file(self, tmp_path):
        """Test writing and reading a file"""
        tools = MomTools(working_dir=tmp_path)

        # Write
        write_result = tools.write("test.txt", "Hello, World!")
        assert write_result.success is True

        # Read
        read_result = tools.read("test.txt")
        assert read_result.success is True
        assert "Hello, World!" in read_result.output

    def test_edit_file(self, tmp_path):
        """Test editing a file"""
        tools = MomTools(working_dir=tmp_path)

        # Create file
        tools.write("test.txt", "Hello, World!")

        # Edit
        edit_result = tools.edit("test.txt", "World", "Python")
        assert edit_result.success is True

        # Verify
        read_result = tools.read("test.txt")
        assert "Hello, Python!" in read_result.output

    def test_bash_command(self):
        """Test bash command execution"""
        tools = MomTools()
        result = tools.bash("echo 'test'")

        assert result.success is True
        assert "test" in result.output

    def test_bash_timeout(self):
        """Test bash command timeout"""
        tools = MomTools()
        result = tools.bash("sleep 10", timeout=1)

        assert result.success is False
        assert "timeout" in result.error.lower()
