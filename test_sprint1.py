"""Test Sprint 1: Types and Event Stream"""
import asyncio
from koda.ai.types import (
    KnownApi,
    KnownProvider,
    ThinkingLevel,
    StopReason,
    TextContent,
    ThinkingContent,
    ImageContent,
    ToolCall,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Tool,
    Context,
    Usage,
    StreamOptions,
    ModelInfo,
)
from koda.ai.event_stream import (
    EventType,
    AssistantMessageEventStream,
    create_event_stream,
)
from koda.ai.provider_base import (
    BaseProvider,
    ProviderConfig,
    ProviderRegistry,
    get_provider_registry,
)


def test_enums():
    """Test enum definitions"""
    print("Testing Enums...")
    
    assert KnownApi.OPENAI_COMPLETIONS.value == "openai-completions"
    assert KnownApi.ANTHROPIC_MESSAGES.value == "anthropic-messages"
    assert KnownProvider.OPENAI.value == "openai"
    assert KnownProvider.ANTHROPIC.value == "anthropic"
    assert ThinkingLevel.HIGH.value == "high"
    assert StopReason.TOOL_USE.value == "toolUse"
    
    print("  All enums: PASSED")


def test_content_types():
    """Test content types"""
    print("Testing Content Types...")
    
    text = TextContent(type="text", text="Hello", text_signature="sig123")
    assert text.type == "text"
    assert text.text == "Hello"
    
    thinking = ThinkingContent(type="thinking", thinking="Let me think...")
    assert thinking.type == "thinking"
    
    image = ImageContent(type="image", data="base64data", mime_type="image/jpeg")
    assert image.type == "image"
    
    tool_call = ToolCall(type="toolCall", id="call1", name="read", arguments={"path": "/tmp/file"})
    assert tool_call.type == "toolCall"
    
    print("  All content types: PASSED")


def test_messages():
    """Test message types"""
    print("Testing Messages...")
    
    user_msg = UserMessage(role="user", content="Hello", timestamp=1234567890)
    assert user_msg.role == "user"
    
    assistant_msg = AssistantMessage(
        role="assistant",
        content=[TextContent(text="Hi")],
        api="openai-completions",
        provider="openai",
        model="gpt-4o",
        usage=Usage(),
        stop_reason=StopReason.STOP,
    )
    assert assistant_msg.role == "assistant"
    assert len(assistant_msg.content) == 1
    
    tool_result = ToolResultMessage(
        role="toolResult",
        tool_call_id="call1",
        tool_name="read",
        content=[TextContent(text="File content")],
        is_error=False,
    )
    assert tool_result.role == "toolResult"
    
    print("  All message types: PASSED")


def test_usage():
    """Test usage calculation"""
    print("Testing Usage...")
    
    usage = Usage(input=1000, output=500, cache_read=200, cache_write=100)
    
    model_cost = {
        "input": 2.5,  # $2.5 per million
        "output": 10.0,
        "cache_read": 1.25,
        "cache_write": 5.0,
    }
    
    usage.calculate_cost(model_cost)
    
    assert usage.cost["input"] > 0
    assert usage.cost["output"] > 0
    assert usage.cost["total"] > 0
    
    print(f"  Cost calculation: input=${usage.cost['input']:.6f}, total=${usage.cost['total']:.6f}")
    print("  Usage calculation: PASSED")


def test_context():
    """Test context"""
    print("Testing Context...")
    
    tool = Tool(
        name="read",
        description="Read file",
        parameters={"type": "object", "properties": {}}
    )
    
    context = Context(
        system_prompt="You are a helpful assistant.",
        messages=[UserMessage(content="Hello")],
        tools=[tool],
    )
    
    assert context.system_prompt == "You are a helpful assistant."
    assert len(context.messages) == 1
    assert len(context.tools) == 1
    
    print("  Context: PASSED")


def test_model_info():
    """Test model info"""
    print("Testing ModelInfo...")
    
    model = ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com/v1",
        reasoning=False,
        input=["text", "image"],
        cost={"input": 2.5, "output": 10.0, "cache_read": 0, "cache_write": 0},
        context_window=128000,
        max_tokens=16384,
    )
    
    assert model.id == "gpt-4o"
    assert model.context_window == 128000
    assert "text" in model.input
    assert "image" in model.input
    
    print("  ModelInfo: PASSED")


def test_stream_options():
    """Test stream options"""
    print("Testing StreamOptions...")
    
    options = StreamOptions(
        temperature=0.7,
        max_tokens=1000,
        cache_retention="short",
        max_retry_delay_ms=60000,
    )
    
    assert options.temperature == 0.7
    assert options.max_tokens == 1000
    
    print("  StreamOptions: PASSED")


def test_event_stream():
    """Test event stream"""
    print("Testing EventStream...")
    
    stream = create_event_stream()
    
    # Test that stream can be created
    assert stream is not None
    
    # Test event types
    assert EventType.START.value == "start"
    assert EventType.TEXT_DELTA.value == "text_delta"
    assert EventType.DONE.value == "done"
    
    print("  EventStream: PASSED")


def test_provider_base():
    """Test provider base"""
    print("Testing Provider Base...")
    
    config = ProviderConfig(
        api_key="test-key",
        base_url="https://api.example.com",
        timeout=30.0,
        max_retries=3,
    )
    
    assert config.api_key == "test-key"
    assert config.timeout == 30.0
    
    # Test registry
    registry = get_provider_registry()
    assert registry is not None
    
    providers = registry.list_providers()
    assert isinstance(providers, list)
    
    print("  Provider Base: PASSED")


async def test_event_stream_async():
    """Test async event stream operations"""
    print("Testing EventStream Async...")
    
    stream = create_event_stream()
    
    events_received = []
    
    async def collect_events():
        async for event in stream:
            events_received.append(event.type)
            if event.type in ("done", "error"):
                break
    
    # Simulate pushing events
    from koda.ai.types import AssistantMessageEvent
    
    async def push_events():
        await asyncio.sleep(0.01)
        stream.push(AssistantMessageEvent(type="start"))
        await asyncio.sleep(0.01)
        stream.push(AssistantMessageEvent(type="text_start", content_index=0))
        await asyncio.sleep(0.01)
        stream.push(AssistantMessageEvent(type="text_delta", content_index=0, delta="Hello"))
        await asyncio.sleep(0.01)
        stream.push(AssistantMessageEvent(type="text_end", content_index=0))
        await asyncio.sleep(0.01)
        stream.push(AssistantMessageEvent(type="done", reason=StopReason.STOP))
    
    # Run both tasks
    await asyncio.gather(
        collect_events(),
        push_events(),
    )
    
    assert "start" in events_received
    assert "text_delta" in events_received
    assert "done" in events_received
    
    print(f"  Received {len(events_received)} events")
    print("  EventStream Async: PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Sprint 1: Types and Event Stream Tests")
    print("=" * 60)
    
    test_enums()
    test_content_types()
    test_messages()
    test_usage()
    test_context()
    test_model_info()
    test_stream_options()
    test_event_stream()
    test_provider_base()
    
    # Run async tests
    asyncio.run(test_event_stream_async())
    
    print("=" * 60)
    print("All Sprint 1 Tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
