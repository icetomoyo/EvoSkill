"""
Tests for P0 implementations:
- overflow.py: Context overflow detection
- sanitize_unicode.py: Unicode surrogate cleanup
- resolve_config_value.py: Config value resolution with !command syntax
- stream_proxy.py: HTTP stream proxy
"""
import pytest
import os
from unittest.mock import patch


class TestContextOverflow:
    """Test overflow.py - context overflow detection"""
    
    def test_is_context_overflow_anthropic(self):
        """Test Anthropic overflow detection"""
        from koda.ai import is_context_overflow
        from koda.ai.types import AssistantMessage
        
        msg = AssistantMessage(
            role="assistant",
            content=[],
            api="anthropic-messages",
            provider="anthropic",
            model="claude-3",
            usage={"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, 
                   "total_tokens": 0, "cost": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "total": 0}},
            stop_reason="error",
            error_message="prompt is too long: 213462 tokens > 200000 maximum",
            timestamp=0,
        )
        assert is_context_overflow(msg) is True
    
    def test_is_context_overflow_openai(self):
        """Test OpenAI overflow detection"""
        from koda.ai import is_context_overflow
        from koda.ai.types import AssistantMessage
        
        msg = AssistantMessage(
            role="assistant",
            content=[],
            api="openai-responses",
            provider="openai",
            model="gpt-4",
            usage={"input": 0, "output": 0, "cache_read": 0, "cache_write": 0,
                   "total_tokens": 0, "cost": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "total": 0}},
            stop_reason="error",
            error_message="Your input exceeds the context window of this model",
            timestamp=0,
        )
        assert is_context_overflow(msg) is True
    
    def test_is_context_overflow_not_error(self):
        """Test that normal stop is not overflow"""
        from koda.ai import is_context_overflow
        from koda.ai.types import AssistantMessage
        
        msg = AssistantMessage(
            role="assistant",
            content=[],
            api="openai-responses",
            provider="openai",
            model="gpt-4",
            usage={"input": 100, "output": 50, "cache_read": 0, "cache_write": 0,
                   "total_tokens": 150, "cost": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "total": 0}},
            stop_reason="stop",
            timestamp=0,
        )
        assert is_context_overflow(msg) is False
    
    def test_is_context_overflow_silent(self):
        """Test silent overflow detection (z.ai style)"""
        from koda.ai import is_context_overflow
        from koda.ai.types import AssistantMessage
        
        msg = AssistantMessage(
            role="assistant",
            content=[],
            api="openai-responses",
            provider="zai",
            model="zai-model",
            usage={"input": 150000, "output": 0, "cache_read": 0, "cache_write": 0,
                   "total_tokens": 150000, "cost": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "total": 0}},
            stop_reason="stop",
            timestamp=0,
        )
        # With context_window=128000, should detect overflow
        assert is_context_overflow(msg, context_window=128000) is True
    
    def test_get_overflow_patterns(self):
        """Test getting overflow patterns"""
        from koda.ai import get_overflow_patterns
        
        patterns = get_overflow_patterns()
        assert len(patterns) == 15  # 15 patterns defined


class TestSanitizeUnicode:
    """Test sanitize_unicode.py - Unicode surrogate cleanup"""
    
    def test_sanitize_orphaned_high_surrogate(self):
        """Test removal of orphaned high surrogate"""
        from koda.ai import sanitize_surrogates
        
        text = "Hello \ud800World"
        result = sanitize_surrogates(text)
        assert result == "Hello World"
    
    def test_sanitize_orphaned_low_surrogate(self):
        """Test removal of orphaned low surrogate"""
        from koda.ai import sanitize_surrogates
        
        text = "Hello \udc00World"
        result = sanitize_surrogates(text)
        assert result == "Hello World"
    
    def test_sanitize_valid_pair_preserved(self):
        """Test that valid surrogate pairs are preserved"""
        from koda.ai import sanitize_surrogates
        
        # Valid surrogate pair for emoji (U+1F600 = 😀)
        text = "Hello \ud83d\ude00World"
        result = sanitize_surrogates(text)
        assert result == "Hello \ud83d\ude00World"
    
    def test_sanitize_mixed(self):
        """Test mixed valid and invalid surrogates"""
        from koda.ai import sanitize_surrogates
        
        text = "\ud800\ud83d\ude00\udc00"  # orphan high, valid pair, orphan low
        result = sanitize_surrogates(text)
        assert result == "\ud83d\ude00"
    
    def test_sanitize_empty(self):
        """Test empty string"""
        from koda.ai import sanitize_surrogates
        
        assert sanitize_surrogates("") == ""
        assert sanitize_surrogates(None) is None
    
    def test_sanitize_for_json(self):
        """Test JSON sanitization"""
        from koda.ai import sanitize_for_json
        
        text = "Hello \ud800World\x00"
        result = sanitize_for_json(text)
        assert result == "Hello World"


class TestResolveConfigValue:
    """Test resolve_config_value.py - Config value resolution"""
    
    def test_resolve_literal(self):
        """Test literal value"""
        from koda.coding import resolve_config_value
        
        result = resolve_config_value("literal-value")
        assert result == "literal-value"
    
    def test_resolve_env_var(self, monkeypatch):
        """Test environment variable resolution"""
        from koda.coding import resolve_config_value
        
        monkeypatch.setenv("TEST_API_KEY", "test-key-123")
        result = resolve_config_value("TEST_API_KEY")
        assert result == "test-key-123"
    
    def test_resolve_command(self):
        """Test command execution with ! syntax"""
        from koda.coding import resolve_config_value, clear_config_value_cache
        
        clear_config_value_cache()
        
        # Use echo command
        result = resolve_config_value("!echo test-output")
        assert result == "test-output"
    
    def test_resolve_command_cached(self):
        """Test command result caching"""
        from koda.coding import resolve_config_value, is_cached, clear_config_value_cache
        
        clear_config_value_cache()
        
        # First call
        result1 = resolve_config_value("!echo cached")
        assert is_cached("!echo cached") is True
        
        # Second call should return cached result
        result2 = resolve_config_value("!echo cached")
        assert result1 == result2
    
    def test_resolve_command_failure(self):
        """Test command failure handling"""
        from koda.coding import resolve_config_value, clear_config_value_cache
        
        clear_config_value_cache()
        
        # Invalid command
        result = resolve_config_value("!invalid_command_that_does_not_exist")
        assert result is None
    
    def test_resolve_empty(self):
        """Test empty input"""
        from koda.coding import resolve_config_value
        
        assert resolve_config_value("") is None
        assert resolve_config_value(None) is None
    
    def test_resolve_headers(self, monkeypatch):
        """Test header resolution"""
        from koda.coding import resolve_headers
        
        monkeypatch.setenv("API_KEY", "secret-key")
        
        headers = {
            "Authorization": "Bearer !echo token123",  # Command
            "X-API-Key": "API_KEY",  # Env var
            "X-Custom": "literal",  # Literal
        }
        
        result = resolve_headers(headers)
        assert result["Authorization"] == "Bearer token123"
        assert result["X-API-Key"] == "secret-key"
        assert result["X-Custom"] == "literal"


class TestStreamProxy:
    """Test stream_proxy.py - HTTP stream proxy"""
    
    def test_proxy_stream_options(self):
        """Test ProxyStreamOptions creation"""
        from koda.agent import ProxyStreamOptions
        
        options = ProxyStreamOptions(
            auth_token="test-token",
            proxy_url="https://proxy.example.com",
            temperature=0.7,
            max_tokens=1000,
        )
        assert options.auth_token == "test-token"
        assert options.proxy_url == "https://proxy.example.com"
        assert options.temperature == 0.7
        assert options.max_tokens == 1000
    
    def test_create_proxy_stream(self):
        """Test proxy stream creation"""
        from koda.agent import ProxyMessageEventStream, stream_proxy
        
        stream = ProxyMessageEventStream()
        assert stream is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
