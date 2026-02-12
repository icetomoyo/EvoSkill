"""
Tests for Agent Loop
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from koda.agent.loop import (
    AgentLoop,
    AgentLoopConfig,
    AgentTool,
    agent_loop_continue,
)
from koda.ai.types import (
    Context,
    AssistantMessage,
    UserMessage,
    TextContent,
    ToolCall,
    ToolResultMessage,
    StopReason,
)


class TestAgentLoopConfig:
    """Test AgentLoopConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = AgentLoopConfig()
        assert config.max_iterations == 50
        assert config.max_tool_calls_per_turn == 32
        assert config.retry_attempts == 3
        assert config.tool_timeout == 600.0
        assert config.enable_parallel_tools is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = AgentLoopConfig(
            max_iterations=100,
            retry_attempts=5,
            enable_parallel_tools=False
        )
        assert config.max_iterations == 100
        assert config.retry_attempts == 5
        assert config.enable_parallel_tools is False


class TestAgentTool:
    """Test AgentTool"""

    def test_tool_creation(self):
        """Test creating a tool"""
        def my_handler(arg1: str) -> str:
            return f"handled: {arg1}"

        tool = AgentTool(
            name="test_tool",
            description="A test tool",
            parameters={"arg1": {"type": "string"}},
            execute=my_handler,
            label="Test Tool"
        )

        assert tool.name == "test_tool"
        assert tool.label == "Test Tool"
        assert tool.description == "A test tool"

    def test_tool_default_label(self):
        """Test tool with default label"""
        tool = AgentTool(
            name="my_tool",
            description="Test",
            parameters={},
            execute=lambda: None
        )

        assert tool.label == "my_tool"


class TestAgentLoop:
    """Test AgentLoop"""

    def test_loop_creation(self):
        """Test creating an agent loop"""
        mock_provider = MagicMock()
        mock_model = MagicMock()
        mock_model.id = "test-model"

        tools = [
            AgentTool(
                name="echo",
                description="Echo input",
                parameters={},
                execute=lambda x: x
            )
        ]

        loop = AgentLoop(mock_provider, mock_model, tools)

        assert loop.provider == mock_provider
        assert loop.model == mock_model
        assert "echo" in loop.tools
        assert loop.is_idle is True

    @pytest.mark.asyncio
    async def test_wait_for_idle(self):
        """Test wait_for_idle"""
        mock_provider = MagicMock()
        mock_model = MagicMock()
        mock_model.id = "test-model"

        loop = AgentLoop(mock_provider, mock_model, [])

        # Should return immediately since loop is idle
        result = await loop.wait_for_idle(timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_run_simple(self):
        """Test simple run without tools"""
        mock_provider = MagicMock()
        mock_provider.api_type = "test-api"
        mock_provider.provider_id = "test-provider"

        mock_model = MagicMock()
        mock_model.id = "test-model"

        # Mock complete to return a simple response
        async def mock_complete(model, context, **kwargs):
            return AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text="Hello!")],
                api="test-api",
                provider="test-provider",
                model="test-model",
                stop_reason=StopReason.STOP,
            )

        mock_provider.complete = mock_complete

        loop = AgentLoop(mock_provider, mock_model, [])
        context = Context(
            messages=[UserMessage(role="user", content="Hi")]
        )

        result = await loop.run(context)

        assert result is not None
        assert result.stop_reason == StopReason.STOP


class TestAgentLoopContinue:
    """Test agent_loop_continue function"""

    @pytest.mark.asyncio
    async def test_loop_continue(self):
        """Test continue function"""
        mock_provider = MagicMock()
        mock_model = MagicMock()
        mock_model.id = "test-model"

        loop = AgentLoop(mock_provider, mock_model, [])
        context = Context(messages=[])

        # agent_loop_continue should call run_continue
        with patch.object(loop, 'run_continue') as mock_run_continue:
            mock_run_continue.return_value = AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text="Continued")],
                stop_reason=StopReason.STOP,
            )

            result = await agent_loop_continue(loop, context)

            assert result is not None
            mock_run_continue.assert_called_once()
