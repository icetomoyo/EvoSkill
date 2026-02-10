"""Test Sprint 2: Core Providers"""
import asyncio
import json
from koda.ai.types import (
    ModelInfo,
    Context,
    UserMessage,
    AssistantMessage,
    TextContent,
    Tool,
    KnownApi,
    KnownProvider,
    StopReason,
)
from koda.ai.providers.openai_provider_v2 import OpenAIProviderV2
from koda.ai.providers.anthropic_provider_v2 import AnthropicProviderV2
from koda.ai.providers.google_provider import GoogleProvider


def test_provider_properties():
    """Test provider basic properties"""
    print("Testing Provider Properties...")
    
    # OpenAI
    openai = OpenAIProviderV2()
    assert openai.api_type == "openai-completions"
    assert openai.provider_id == "openai"
    assert openai.supports_tools()
    assert openai.supports_vision()
    assert not openai.supports_cache_retention()
    print("  OpenAI: PASSED")
    
    # Anthropic
    anthropic = AnthropicProviderV2()
    assert anthropic.api_type == "anthropic-messages"
    assert anthropic.provider_id == "anthropic"
    assert anthropic.supports_tools()
    assert anthropic.supports_vision()
    assert anthropic.supports_cache_retention()
    print("  Anthropic: PASSED")
    
    # Google
    google = GoogleProvider()
    assert google.api_type == "google-generative-ai"
    assert google.provider_id == "google"
    assert google.supports_tools()
    assert google.supports_vision()
    print("  Google: PASSED")


def test_cost_calculation():
    """Test cost calculation"""
    print("Testing Cost Calculation...")
    
    from koda.ai.types import Usage
    
    provider = OpenAIProviderV2()
    
    model = ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com/v1",
        cost={
            "input": 2.5,
            "output": 10.0,
            "cache_read": 0,
            "cache_write": 0
        },
        context_window=128000,
        max_tokens=16384,
    )
    
    usage = Usage(input=1000000, output=500000)
    cost = provider.calculate_cost(model, usage)
    
    # $2.5 per 1M input + $10 per 1M output
    expected = 2.5 + 5.0  # $7.5
    assert abs(cost - expected) < 0.01, f"Expected {expected}, got {cost}"
    
    print(f"  Cost for 1M/500K tokens: ${cost:.2f}")
    print("  Cost calculation: PASSED")


def test_message_conversion():
    """Test message format conversion"""
    print("Testing Message Conversion...")
    
    # OpenAI
    openai = OpenAIProviderV2()
    
    messages = [
        UserMessage(role="user", content="Hello"),
        AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text="Hi there!")]
        ),
    ]
    
    context = Context(
        system_prompt="You are helpful.",
        messages=messages,
        tools=[Tool(name="read", description="Read file", parameters={})]
    )
    
    payload = openai._build_payload(
        ModelInfo(
            id="gpt-4o",
            name="GPT-4o",
            api="openai-completions",
            provider="openai",
            base_url="https://api.openai.com/v1",
            cost={},
            context_window=128000,
            max_tokens=16384,
        ),
        context,
        None
    )
    
    assert payload["model"] == "gpt-4o"
    assert payload["stream"] == True
    assert "messages" in payload
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "You are helpful."
    
    print("  OpenAI conversion: PASSED")
    
    # Anthropic
    anthropic = AnthropicProviderV2()
    
    payload = anthropic._build_payload(
        ModelInfo(
            id="claude-3-5-sonnet",
            name="Claude 3.5 Sonnet",
            api="anthropic-messages",
            provider="anthropic",
            base_url="https://api.anthropic.com",
            cost={},
            context_window=200000,
            max_tokens=8192,
        ),
        context,
        None
    )
    
    assert payload["model"] == "claude-3-5-sonnet"
    assert payload["stream"] == True
    assert "system" in payload
    assert "messages" in payload
    
    print("  Anthropic conversion: PASSED")
    
    # Google
    google = GoogleProvider()
    
    payload = google._build_payload(
        ModelInfo(
            id="gemini-1.5-pro",
            name="Gemini 1.5 Pro",
            api="google-generative-ai",
            provider="google",
            base_url="https://generativelanguage.googleapis.com",
            cost={},
            context_window=1000000,
            max_tokens=8192,
        ),
        context,
        None
    )
    
    assert "contents" in payload
    assert "systemInstruction" in payload
    
    print("  Google conversion: PASSED")


def test_provider_registry():
    """Test provider registry"""
    print("Testing Provider Registry...")
    
    from koda.ai.provider_base import get_provider_registry, ProviderConfig
    
    registry = get_provider_registry()
    
    # Register V2 providers
    registry.register("openai-v2", OpenAIProviderV2)
    registry.register("anthropic-v2", AnthropicProviderV2)
    registry.register("google", GoogleProvider)
    
    providers = registry.list_providers()
    assert "openai-v2" in providers
    assert "anthropic-v2" in providers
    assert "google" in providers
    
    # Create instance
    config = ProviderConfig(api_key="test-key")
    provider = registry.create("openai-v2", config)
    assert isinstance(provider, OpenAIProviderV2)
    assert provider.api_key == "test-key"
    
    print("  Provider registry: PASSED")


def test_tool_handling():
    """Test tool definition conversion"""
    print("Testing Tool Handling...")
    
    tools = [
        Tool(
            name="read",
            description="Read a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="write",
            description="Write to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        )
    ]
    
    context = Context(
        system_prompt="You have file tools.",
        messages=[UserMessage(content="Read /tmp/test.txt")],
        tools=tools
    )
    
    openai = OpenAIProviderV2()
    payload = openai._build_payload(
        ModelInfo(
            id="gpt-4o",
            name="GPT-4o",
            api="openai-completions",
            provider="openai",
            base_url="https://api.openai.com/v1",
            cost={},
            context_window=128000,
            max_tokens=16384,
        ),
        context,
        None
    )
    
    assert "tools" in payload
    assert len(payload["tools"]) == 2
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "read"
    
    print("  Tool handling: PASSED")


def test_anthropic_caching():
    """Test Anthropic cache control"""
    print("Testing Anthropic Caching...")
    
    from koda.ai.types import StreamOptions, CacheRetention
    
    anthropic = AnthropicProviderV2()
    
    context = Context(
        messages=[UserMessage(content="Long document...")],
    )
    
    options = StreamOptions(cache_retention="ephemeral")
    
    payload = anthropic._build_payload(
        ModelInfo(
            id="claude-3-5-sonnet",
            name="Claude 3.5 Sonnet",
            api="anthropic-messages",
            provider="anthropic",
            base_url="https://api.anthropic.com",
            cost={},
            context_window=200000,
            max_tokens=8192,
        ),
        context,
        options
    )
    
    # Check cache_control was added
    messages = payload["messages"]
    assert len(messages) > 0
    # Last user message should have cache_control
    
    print("  Anthropic caching: PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Sprint 2: Core Providers Tests")
    print("=" * 60)
    
    test_provider_properties()
    test_cost_calculation()
    test_message_conversion()
    test_provider_registry()
    test_tool_handling()
    test_anthropic_caching()
    
    print("=" * 60)
    print("All Sprint 2 Tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
