"""
Tests for AI Unified API
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from koda.ai.unified import (
    stream,
    complete,
    stream_simple,
    complete_simple,
    UnifiedClient,
    create_client,
)
from koda.ai.types import AssistantMessage, TextContent, StopReason


class TestUnifiedClient:
    """Test UnifiedClient"""

    def test_create_client(self):
        """Test client creation"""
        client = create_client()
        assert client is not None
        assert isinstance(client, UnifiedClient)

    def test_client_with_options(self):
        """Test client with custom options"""
        from koda.ai.types import SimpleStreamOptions, ThinkingLevel

        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        client = UnifiedClient(
            default_model="claude-opus-4-5",
            default_options=options
        )

        assert client.default_model == "claude-opus-4-5"
        assert client.default_options.reasoning == ThinkingLevel.HIGH


class TestStreamSimple:
    """Test stream_simple function"""

    @pytest.mark.asyncio
    async def test_stream_simple_basic(self):
        """Test basic streaming"""
        # Mock the registry and provider
        with patch('koda.ai.unified.get_model_registry') as mock_registry:
            mock_provider = MagicMock()
            mock_provider.supports_thinking_level.return_value = False

            mock_stream = AsyncMock()
            mock_stream.__aiter__ = AsyncMock(return_value=iter([]))

            mock_provider.stream = AsyncMock(return_value=mock_stream)

            mock_model_info = MagicMock()
            mock_model_info.id = "test-model"

            mock_registry_instance = MagicMock()
            mock_registry_instance.get_default.return_value = mock_model_info
            mock_registry_instance.get_provider_for_model.return_value = mock_provider

            mock_registry.return_value = mock_registry_instance

            # Just verify the function can be called
            # The actual streaming behavior is tested elsewhere
            result = []
            async for chunk in stream_simple("test prompt", "auto"):
                result.append(chunk)

            # Should complete without error (may be empty if stream is empty)
            assert isinstance(result, list)


class TestCompleteSimple:
    """Test complete_simple function"""

    @pytest.mark.asyncio
    async def test_complete_simple(self):
        """Test simple completion"""
        # This is mostly a smoke test
        with patch('koda.ai.unified.stream_simple') as mock_stream:
            # Mock stream_simple to yield some chunks
            async def mock_generator():
                yield "Hello"
                yield " "
                yield "World"

            mock_stream.return_value = mock_generator()

            result = await complete_simple("test")
            assert result == "Hello World"
