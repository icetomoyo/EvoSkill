"""
Tests for Agent Transform
"""
import pytest

from koda.agent.transform import (
    convert_to_llm,
    transform_context,
    estimate_tokens,
    estimate_message_tokens,
    get_model_context_window,
    filter_tool_results,
    extract_text_content,
    TransformStrategy,
    TransformConfig,
    TransformResult,
)
from koda.ai.types import (
    Context,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
    ToolCall,
    StopReason,
)


class TestEstimateTokens:
    """Test token estimation"""

    def test_estimate_string(self):
        """Test estimating tokens for a string"""
        # ~4 characters per token
        text = "Hello world, this is a test."
        tokens = len(text) // 4
        assert tokens > 0

    def test_estimate_context(self):
        """Test estimating tokens for a context"""
        context = Context(
            system_prompt="You are a helpful assistant.",
            messages=[
                UserMessage(role="user", content="Hello"),
                AssistantMessage(
                    role="assistant",
                    content=[TextContent(type="text", text="Hi there!")],
                    stop_reason=StopReason.STOP,
                ),
            ]
        )

        tokens = estimate_tokens(context)
        assert tokens > 0

    def test_estimate_user_message(self):
        """Test estimating tokens for user message"""
        msg = UserMessage(role="user", content="This is a test message")
        tokens = estimate_message_tokens(msg)
        assert tokens > 0

    def test_estimate_assistant_message(self):
        """Test estimating tokens for assistant message"""
        msg = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text="Response text")],
            stop_reason=StopReason.STOP,
        )
        tokens = estimate_message_tokens(msg)
        assert tokens > 0

    def test_estimate_tool_result(self):
        """Test estimating tokens for tool result"""
        msg = ToolResultMessage(
            role="toolResult",
            tool_call_id="123",
            tool_name="test",
            content=[TextContent(type="text", text="Tool output")],
        )
        tokens = estimate_message_tokens(msg)
        assert tokens > 0


class TestGetModelContextWindow:
    """Test model context window detection"""

    def test_claude_models(self):
        """Test Claude model context windows"""
        assert get_model_context_window("claude-3-opus-20240229") == 200000
        assert get_model_context_window("claude-3-5-sonnet-20241022") == 200000
        assert get_model_context_window("claude-sonnet-4") == 200000

    def test_openai_models(self):
        """Test OpenAI model context windows"""
        assert get_model_context_window("gpt-4") == 8192
        assert get_model_context_window("gpt-4-turbo") == 128000
        assert get_model_context_window("gpt-4o") == 128000

    def test_unknown_model(self):
        """Test unknown model returns default"""
        assert get_model_context_window("unknown-model") == 128000


class TestTransformContext:
    """Test context transformation"""

    def test_no_transform_needed(self):
        """Test when no transformation is needed"""
        context = Context(
            messages=[UserMessage(role="user", content="Hello")]
        )

        config = TransformConfig(max_tokens=1000)
        result = transform_context(context, config)

        assert result.original_tokens == result.new_tokens
        assert result.tokens_saved == 0
        assert result.messages_removed == 0

    def test_truncate_strategy(self):
        """Test truncate strategy"""
        # Create context with many messages
        messages = []
        for i in range(100):
            messages.append(UserMessage(role="user", content=f"Message {i}" * 100))

        context = Context(messages=messages)
        config = TransformConfig(
            max_tokens=1000,
            strategy=TransformStrategy.TRUNCATE
        )

        result = transform_context(context, config)

        assert result.tokens_saved > 0
        assert result.messages_removed > 0

    def test_smart_strategy(self):
        """Test smart strategy"""
        messages = []
        for i in range(50):
            messages.append(UserMessage(role="user", content=f"Message {i}" * 50))
            messages.append(AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text=f"Response {i}" * 50)],
                stop_reason=StopReason.STOP,
            ))

        context = Context(messages=messages)
        config = TransformConfig(
            max_tokens=500,
            strategy=TransformStrategy.SMART
        )

        result = transform_context(context, config)

        # Smart strategy should preserve recent messages
        assert len(result.context.messages) > 0


class TestConvertToLlm:
    """Test convert_to_llm function"""

    def test_convert_basic(self):
        """Test basic conversion"""
        context = Context(
            system_prompt="Test prompt",
            messages=[UserMessage(role="user", content="Hello")]
        )

        result = convert_to_llm(context, "anthropic", "claude-sonnet-4")

        assert result is not None
        assert isinstance(result, Context)

    def test_convert_with_compaction(self):
        """Test conversion triggers compaction when needed"""
        # Create large context
        messages = []
        for i in range(100):
            messages.append(UserMessage(role="user", content="A" * 1000))

        context = Context(messages=messages)

        # Small max_tokens should trigger compaction
        result = convert_to_llm(
            context,
            "anthropic",
            "claude-sonnet-4",
            max_tokens=1000
        )

        assert len(result.messages) < len(messages)


class TestFilterToolResults:
    """Test filter_tool_results function"""

    def test_filter_keeps_errors(self):
        """Test that errors are kept"""
        messages = [
            UserMessage(role="user", content="Test"),
            ToolResultMessage(
                role="toolResult",
                tool_call_id="1",
                tool_name="test",
                content=[TextContent(type="text", text="Error")],
                is_error=True,
            ),
            ToolResultMessage(
                role="toolResult",
                tool_call_id="2",
                tool_name="test",
                content=[TextContent(type="text", text="Success")],
                is_error=False,
            ),
        ]

        context = Context(messages=messages)
        result = filter_tool_results(context, keep_errors=True)

        tool_results = [m for m in result.messages if isinstance(m, ToolResultMessage)]
        assert len(tool_results) == 2  # Both kept

    def test_filter_removes_non_errors(self):
        """Test filtering removes non-errors"""
        messages = [
            ToolResultMessage(
                role="toolResult",
                tool_call_id="1",
                tool_name="test",
                content=[TextContent(type="text", text="Success")],
                is_error=False,
            ),
        ]

        context = Context(messages=messages)
        result = filter_tool_results(context, keep_errors=False)

        tool_results = [m for m in result.messages if isinstance(m, ToolResultMessage)]
        assert len(tool_results) == 0


class TestExtractTextContent:
    """Test extract_text_content function"""

    def test_extract_basic(self):
        """Test basic text extraction"""
        context = Context(
            system_prompt="System prompt",
            messages=[
                UserMessage(role="user", content="Hello"),
                AssistantMessage(
                    role="assistant",
                    content=[TextContent(type="text", text="Hi there!")],
                    stop_reason=StopReason.STOP,
                ),
            ]
        )

        text = extract_text_content(context)

        assert "System" in text
        assert "Hello" in text
        assert "Hi there!" in text
