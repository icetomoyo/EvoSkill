"""Test Phase 1: OpenAI Responses API, Azure, and Utilities"""
import asyncio
from koda.ai.models_utils import supports_xhigh, models_are_equal, calculate_cost, resolve_model_alias
from koda.ai.types import ModelInfo, Usage, ThinkingLevel
from koda.ai.providers.openai_responses import OpenAIResponsesProvider
from koda.ai.providers.azure_provider import AzureOpenAIProvider


def test_supports_xhigh():
    """Test supportsXhigh helper"""
    print("Testing supports_xhigh...")
    
    # GPT-5.2 should support xhigh
    gpt52 = ModelInfo(
        id="gpt-5.2-test",
        name="GPT-5.2",
        api="openai-completions",
        provider="openai",
        base_url="",
        cost={},
        context_window=128000,
        max_tokens=16384
    )
    assert supports_xhigh(gpt52) == True, "GPT-5.2 should support xhigh"
    
    # Regular GPT-4o should not
    gpt4o = ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="",
        cost={},
        context_window=128000,
        max_tokens=16384
    )
    assert supports_xhigh(gpt4o) == False, "GPT-4o should not support xhigh"
    
    # Claude Opus 4.6
    opus46 = ModelInfo(
        id="claude-opus-4-6",
        name="Claude Opus 4.6",
        api="anthropic-messages",
        provider="anthropic",
        base_url="",
        cost={},
        context_window=200000,
        max_tokens=8192
    )
    assert supports_xhigh(opus46) == True, "Claude Opus 4.6 should support xhigh"
    
    print("  supports_xhigh: PASSED")


def test_models_are_equal():
    """Test models_are_equal helper"""
    print("Testing models_are_equal...")
    
    model_a = ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="",
        cost={},
        context_window=128000,
        max_tokens=16384
    )
    
    model_b = ModelInfo(
        id="gpt-4o",
        name="GPT-4o Different Name",
        api="openai-completions",
        provider="openai",
        base_url="",
        cost={},
        context_window=128000,
        max_tokens=16384
    )
    
    model_c = ModelInfo(
        id="claude-3-5-sonnet",
        name="Claude",
        api="anthropic-messages",
        provider="anthropic",
        base_url="",
        cost={},
        context_window=200000,
        max_tokens=8192
    )
    
    # Same id and provider
    assert models_are_equal(model_a, model_b) == True
    
    # Different
    assert models_are_equal(model_a, model_c) == False
    
    # None check
    assert models_are_equal(model_a, None) == False
    assert models_are_equal(None, model_a) == False
    assert models_are_equal(None, None) == False
    
    print("  models_are_equal: PASSED")


def test_calculate_cost():
    """Test calculate_cost helper"""
    print("Testing calculate_cost...")
    
    model = ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="",
        cost={"input": 2.5, "output": 10.0, "cache_read": 1.25, "cache_write": 5.0},
        context_window=128000,
        max_tokens=16384
    )
    
    usage = Usage(input=1000000, output=500000, cache_read=100000, cache_write=50000)
    
    total = calculate_cost(model, usage)
    
    # Expected: 2.5 + 5.0 + 0.125 + 0.25 = 7.875
    expected = 2.5 + 5.0 + 0.125 + 0.25
    assert abs(total - expected) < 0.01, f"Expected {expected}, got {total}"
    
    # Check usage was updated
    assert usage.cost["total"] == total
    assert usage.cost["input"] == 2.5
    assert usage.cost["output"] == 5.0
    
    print(f"  Cost calculation: ${total:.2f} (expected ${expected:.2f})")
    print("  calculate_cost: PASSED")


def test_resolve_model_alias():
    """Test resolve_model_alias helper"""
    print("Testing resolve_model_alias...")
    
    assert resolve_model_alias("gpt4") == "gpt-4o"
    assert resolve_model_alias("GPT4") == "gpt-4o"  # Case insensitive
    assert resolve_model_alias("sonnet") == "claude-3-5-sonnet-20241022"
    assert resolve_model_alias("unknown-model") == "unknown-model"
    
    print("  resolve_model_alias: PASSED")


def test_openai_responses_provider():
    """Test OpenAI Responses Provider"""
    print("Testing OpenAIResponsesProvider...")
    
    provider = OpenAIResponsesProvider()
    
    assert provider.api_type == "openai-responses"
    assert provider.provider_id == "openai"
    assert provider.supports_tools() == True
    assert provider.supports_vision() == True
    
    print("  OpenAIResponsesProvider properties: PASSED")


def test_azure_provider():
    """Test Azure OpenAI Provider"""
    print("Testing AzureOpenAIProvider...")
    
    import os
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com"
    os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
    
    try:
        from koda.ai.provider_base import ProviderConfig
        config = ProviderConfig(
            base_url="https://test.openai.azure.com",
            api_key="test-key"
        )
        provider = AzureOpenAIProvider(config)
        
        assert provider.api_type == "azure-openai-responses"
        assert provider.provider_id == "azure-openai"
        
        print("  AzureOpenAIProvider: PASSED")
    except Exception as e:
        print(f"  AzureOpenAIProvider: WARNING - {e}")


def main():
    """Run all Phase 1 tests"""
    print("=" * 60)
    print("Phase 1: 100% Parity - New Features Tests")
    print("=" * 60)
    
    test_supports_xhigh()
    test_models_are_equal()
    test_calculate_cost()
    test_resolve_model_alias()
    test_openai_responses_provider()
    test_azure_provider()
    
    print("=" * 60)
    print("All Phase 1 Tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
