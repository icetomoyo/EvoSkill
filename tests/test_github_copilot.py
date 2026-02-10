"""
Tests for GitHub Copilot Provider
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import urllib.request

from koda.ai.github_copilot import (
    GitHubCopilotProvider,
    GitHubCopilotConfig,
    GITHUB_COPILOT_MODELS,
    create_copilot_provider,
    register_copilot_models,
)
from koda.ai.oauth import GitHubCopilotOAuth, OAuthError
from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    UserMessage,
    StopReason,
    KnownApi,
)


@pytest.fixture
def mock_oauth():
    """Create mock OAuth"""
    oauth = Mock(spec=GitHubCopilotOAuth)
    oauth.is_authenticated = True
    oauth.get_access_token.return_value = "mock_token_123"
    return oauth


@pytest.fixture
def copilot_provider(mock_oauth):
    """Create Copilot provider with mock OAuth"""
    config = GitHubCopilotConfig(oauth=mock_oauth)
    return GitHubCopilotProvider(config)


@pytest.fixture
def mock_model():
    """Create mock model"""
    return ModelInfo(
        id="gpt-4o-copilot",
        name="GPT-4o Copilot",
        provider="github-copilot",
        api=KnownApi.OPENAI_COMPLETIONS.value,
        base_url="https://api.githubcopilot.com",
        context_window=128000,
        max_tokens=4096,
        cost={"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
    )


@pytest.fixture
def sample_context():
    """Create sample context"""
    return Context(
        system_prompt="You are a helpful assistant",
        messages=[
            UserMessage(role="user", content="Hello")
        ]
    )


class TestGitHubCopilotProvider:
    """Test GitHub Copilot Provider"""
    
    def test_provider_properties(self, copilot_provider):
        """Test provider properties"""
        assert copilot_provider.api_type == "github-copilot"
        assert copilot_provider.provider_id == "github-copilot"
    
    def test_is_authenticated(self, copilot_provider, mock_oauth):
        """Test authentication check"""
        mock_oauth.is_authenticated = True
        assert copilot_provider.is_authenticated is True
        
        mock_oauth.is_authenticated = False
        assert copilot_provider.is_authenticated is False
    
    @pytest.mark.asyncio
    async def test_authenticate(self, copilot_provider, mock_oauth):
        """Test authenticate method"""
        mock_oauth.authenticate = AsyncMock(return_value=Mock())
        
        await copilot_provider.authenticate()
        
        mock_oauth.authenticate.assert_called_once()
    
    def test_build_headers(self, copilot_provider, mock_oauth):
        """Test building request headers"""
        headers = copilot_provider._build_headers()
        
        assert headers["Authorization"] == "Bearer mock_token_123"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "text/event-stream"
        assert "Copilot-Integration-Id" in headers
        assert headers["User-Agent"] == "Koda/1.0"
    
    def test_build_payload_basic(self, copilot_provider, mock_model, sample_context):
        """Test building basic payload"""
        payload = copilot_provider._build_payload(mock_model, sample_context, None)
        
        assert payload["model"] == "gpt-4o-copilot"
        assert payload["stream"] is True
        assert len(payload["messages"]) == 2  # System + user
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
    
    def test_build_payload_with_options(self, copilot_provider, mock_model, sample_context):
        """Test building payload with options"""
        from koda.ai.types import StreamOptions
        
        options = StreamOptions(
            temperature=0.5,
            max_tokens=100
        )
        
        payload = copilot_provider._build_payload(mock_model, sample_context, options)
        
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100
    
    def test_calculate_cost(self, copilot_provider, mock_model):
        """Test cost calculation"""
        usage = Usage(input=100, output=50)
        cost = copilot_provider.calculate_cost(mock_model, usage)
        
        # Copilot is subscription-based, cost should be 0
        assert cost == 0.0
    
    def test_supports_tools(self, copilot_provider):
        """Test tool support"""
        assert copilot_provider.supports_tools() is True
    
    def test_supports_vision(self, copilot_provider):
        """Test vision support"""
        assert copilot_provider.supports_vision() is True
    
    def test_get_available_models(self, copilot_provider):
        """Test getting available models"""
        models = copilot_provider.get_available_models()
        
        assert len(models) == 2
        assert models[0]["id"] == "gpt-4o-copilot"
        assert models[1]["id"] == "gpt-4-copilot"
    
    @pytest.mark.asyncio
    async def test_complete_not_authenticated(self, mock_model, sample_context):
        """Test complete when not authenticated"""
        mock_oauth = Mock(spec=GitHubCopilotOAuth)
        mock_oauth.is_authenticated = False
        mock_oauth.get_access_token.side_effect = OAuthError("Not authenticated")
        
        config = GitHubCopilotConfig(oauth=mock_oauth)
        provider = GitHubCopilotProvider(config)
        
        result = await provider.complete(mock_model, sample_context)
        
        assert result.stop_reason == StopReason.ERROR
        assert "Not authenticated" in result.error_message


class TestGitHubCopilotModels:
    """Test GitHub Copilot model definitions"""
    
    def test_model_count(self):
        """Test correct number of models"""
        assert len(GITHUB_COPILOT_MODELS) == 2
    
    def test_gpt4o_copilot_model(self):
        """Test GPT-4o Copilot model"""
        model = GITHUB_COPILOT_MODELS[0]
        
        assert model.id == "gpt-4o-copilot"
        assert model.name == "GPT-4o Copilot"
        assert model.provider == "github-copilot"
        assert model.context_window == 128000
        assert model.max_tokens == 4096
        assert "text" in model.input
        assert "image" in model.input
    
    def test_gpt4_copilot_model(self):
        """Test GPT-4 Copilot model"""
        model = GITHUB_COPILOT_MODELS[1]
        
        assert model.id == "gpt-4-copilot"
        assert model.name == "GPT-4 Copilot"
        assert model.context_window == 8192
        assert model.input == ["text"]


class TestCreateCopilotProvider:
    """Test factory function"""
    
    def test_create_without_oauth(self):
        """Test creating provider without OAuth"""
        provider = create_copilot_provider()
        
        assert isinstance(provider, GitHubCopilotProvider)
        assert provider._oauth is not None
    
    def test_create_with_oauth(self, mock_oauth):
        """Test creating provider with OAuth"""
        provider = create_copilot_provider(oauth=mock_oauth)
        
        assert isinstance(provider, GitHubCopilotProvider)
        assert provider._oauth is mock_oauth


class TestRegisterCopilotModels:
    """Test model registration"""
    
    def test_register_models(self):
        """Test registering models with registry"""
        registry = Mock()
        registry.register = Mock()
        
        register_copilot_models(registry)
        
        assert registry.register.call_count == 2


class TestGitHubCopilotConfig:
    """Test GitHub Copilot Config"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = GitHubCopilotConfig()
        
        assert config.api_base == "https://api.githubcopilot.com"
        assert config.chat_endpoint == "/chat/completions"
        assert config.oauth is None
    
    def test_custom_config(self):
        """Test custom configuration"""
        mock_oauth = Mock()
        config = GitHubCopilotConfig(
            oauth=mock_oauth,
            api_base="https://custom.api.com"
        )
        
        assert config.oauth is mock_oauth
        assert config.api_base == "https://custom.api.com"


class TestParseResponse:
    """Test response parsing"""
    
    def test_parse_simple_response(self, copilot_provider, mock_model):
        """Test parsing simple response"""
        data = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help?"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        result = copilot_provider._parse_response(mock_model, data)
        
        assert result.role == "assistant"
        assert len(result.content) == 1
        assert result.content[0].text == "Hello! How can I help?"
        assert result.stop_reason == StopReason.STOP
        assert result.usage.input == 10
        assert result.usage.output == 5
        assert result.usage.total_tokens == 15
    
    def test_parse_tool_call_response(self, copilot_provider, mock_model):
        """Test parsing tool call response"""
        data = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.py"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
        
        result = copilot_provider._parse_response(mock_model, data)
        
        assert result.stop_reason == StopReason.TOOL_USE
        assert len(result.content) == 1
        assert result.content[0].type == "toolCall"
        assert result.content[0].name == "read_file"
        assert result.content[0].arguments == {"path": "test.py"}
    
    def test_parse_length_stop(self, copilot_provider, mock_model):
        """Test parsing response with length stop"""
        data = {
            "choices": [{
                "message": {"content": "Truncated..."},
                "finish_reason": "length"
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 4096, "total_tokens": 4196}
        }
        
        result = copilot_provider._parse_response(mock_model, data)
        
        assert result.stop_reason == StopReason.LENGTH


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_complete_with_error(self, copilot_provider, mock_model, sample_context):
        """Test handling errors in complete"""
        # Make provider not authenticated
        copilot_provider._oauth.is_authenticated = False
        copilot_provider._oauth.get_access_token.side_effect = OAuthError("Not authenticated")
        
        result = await copilot_provider.complete(mock_model, sample_context)
        
        assert result.stop_reason == StopReason.ERROR
        assert "Not authenticated" in result.error_message
