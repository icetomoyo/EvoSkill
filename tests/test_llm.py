"""
LLM Provider 测试

包含 Mock 测试，无需真实 API Key
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from evoskill.core.llm import (
    OpenAIProvider,
    AnthropicProvider,
    create_llm_provider,
)
from evoskill.core.types import (
    LLMConfig,
    UserMessage,
    AssistantMessage,
    TextContent,
)


class TestOpenAIProvider:
    """测试 OpenAI Provider"""
    
    def test_init_sets_headers(self, mock_llm_config):
        """测试初始化时设置正确的 HTTP 头"""
        with patch('evoskill.core.llm.AsyncOpenAI') as mock_client:
            provider = OpenAIProvider(mock_llm_config)
            
            # 验证客户端被创建
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            
            # 验证基本参数
            assert call_kwargs['api_key'] == "sk-test-mock-key"
            assert call_kwargs['base_url'] == "https://api.mock.com/v1"
            
            # 验证默认头
            headers = call_kwargs['default_headers']
            assert "Accept" in headers
            assert "Accept-Encoding" in headers
    
    def test_init_kimi_coding_headers(self, mock_kimi_coding_config):
        """测试 Kimi For Coding 的特殊 User-Agent"""
        with patch('evoskill.core.llm.AsyncOpenAI') as mock_client:
            provider = OpenAIProvider(mock_kimi_coding_config)
            
            call_kwargs = mock_client.call_args.kwargs
            headers = call_kwargs['default_headers']
            
            # 验证 Kimi For Coding 的特殊 User-Agent
            assert headers.get("User-Agent") == "KimiCLI/0.77"
    
    @pytest.mark.asyncio
    async def test_chat_streaming(self, mock_llm_config):
        """测试流式对话"""
        # 创建 mock chunk
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta = Mock(content="Hello", tool_calls=None)
        
        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta = Mock(content=" world", tool_calls=None)
        
        mock_chunk3 = Mock()
        mock_chunk3.choices = [Mock()]
        mock_chunk3.choices[0].delta = Mock(content=None, tool_calls=None)
        
        # 创建 mock 响应流
        mock_response = AsyncMock()
        mock_response.__aiter__ = Mock(return_value=iter([mock_chunk1, mock_chunk2, mock_chunk3]))
        
        with patch('evoskill.core.llm.AsyncOpenAI') as mock_client:
            mock_client.return_value.chat.completions.create = Mock(return_value=mock_response)
            
            provider = OpenAIProvider(mock_llm_config)
            messages = [UserMessage(content="Hi")]
            
            events = []
            async for event in provider.chat(messages, stream=True):
                events.append(event)
            
            # 验证收到了文本增量事件
            assert len(events) == 2
            assert events[0]['type'] == 'text_delta'
            assert events[0]['content'] == 'Hello'
            assert events[1]['content'] == ' world'
    
    @pytest.mark.asyncio
    async def test_chat_empty_choices(self, mock_llm_config):
        """测试处理空 choices 的 chunk（如心跳包）"""
        # 模拟包含空 choices 的 chunk
        mock_chunk_empty = Mock()
        mock_chunk_empty.choices = []  # 空 choices
        
        mock_chunk_valid = Mock()
        mock_chunk_valid.choices = [Mock()]
        mock_chunk_valid.choices[0].delta = Mock(content="Hi", tool_calls=None)
        
        mock_response = AsyncMock()
        mock_response.__aiter__ = Mock(return_value=iter([mock_chunk_empty, mock_chunk_valid]))
        
        with patch('evoskill.core.llm.AsyncOpenAI') as mock_client:
            mock_client.return_value.chat.completions.create = Mock(return_value=mock_response)
            
            provider = OpenAIProvider(mock_llm_config)
            messages = [UserMessage(content="Test")]
            
            events = []
            async for event in provider.chat(messages, stream=True):
                events.append(event)
            
            # 应该跳过空 choices，只处理有效 chunk
            assert len(events) == 1
            assert events[0]['content'] == 'Hi'
    
    @pytest.mark.asyncio
    async def test_chat_tool_calls(self, mock_llm_config):
        """测试工具调用"""
        # 创建工具调用 chunk
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = Mock(name="get_weather", arguments='{"location": "Beijing"}')
        
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock(content=None, tool_calls=[mock_tool_call])
        
        mock_response = AsyncMock()
        mock_response.__aiter__ = Mock(return_value=iter([mock_chunk]))
        
        with patch('evoskill.core.llm.AsyncOpenAI') as mock_client:
            mock_client.return_value.chat.completions.create = Mock(return_value=mock_response)
            
            provider = OpenAIProvider(mock_llm_config)
            messages = [UserMessage(content="What's the weather?")]
            
            events = []
            async for event in provider.chat(messages, stream=True):
                events.append(event)
            
            assert len(events) == 1
            assert events[0]['type'] == 'tool_call_delta'
            assert events[0]['tool_call_id'] == 'call_123'
            assert events[0]['name'] == 'get_weather'


class TestLLMProviderFactory:
    """测试 LLM Provider 工厂函数"""
    
    def test_create_openai_provider(self, mock_llm_config):
        """测试创建 OpenAI provider"""
        with patch('evoskill.core.llm.AsyncOpenAI'):
            provider = create_llm_provider(mock_llm_config)
            assert isinstance(provider, OpenAIProvider)
    
    def test_create_anthropic_provider(self):
        """测试创建 Anthropic provider"""
        config = LLMConfig(provider="anthropic", model="claude-3-sonnet", api_key="sk-test")
        with patch('evoskill.core.llm.AsyncAnthropic'):
            provider = create_llm_provider(config)
            assert isinstance(provider, AnthropicProvider)
    
    def test_create_kimi_coding_provider(self, mock_kimi_coding_config):
        """测试创建 Kimi Coding provider（应该是 OpenAIProvider）"""
        with patch('evoskill.core.llm.AsyncOpenAI'):
            provider = create_llm_provider(mock_kimi_coding_config)
            assert isinstance(provider, OpenAIProvider)
    
    def test_create_default_provider(self):
        """测试默认创建 OpenAI provider"""
        config = LLMConfig(provider="unknown", model="test", api_key="sk-test")
        with patch('evoskill.core.llm.AsyncOpenAI'):
            provider = create_llm_provider(config)
            assert isinstance(provider, OpenAIProvider)


class TestMessageConversion:
    """测试消息格式转换"""
    
    def test_user_message_to_openai_format(self, mock_llm_config):
        """测试用户消息转换为 OpenAI 格式"""
        with patch('evoskill.core.llm.AsyncOpenAI'):
            provider = OpenAIProvider(mock_llm_config)
            
            messages = [UserMessage(content="Hello")]
            result = provider._messages_to_provider_format(messages)
            
            assert len(result) == 1
            assert result[0]['role'] == 'user'
            assert result[0]['content'] == 'Hello'
    
    def test_assistant_message_with_tools(self, mock_llm_config):
        """测试助手消息（包含工具调用）转换"""
        with patch('evoskill.core.llm.AsyncOpenAI'):
            provider = OpenAIProvider(mock_llm_config)
            
            from evoskill.core.types import ToolCallContent
            messages = [
                AssistantMessage(
                    content=[
                        TextContent(text="I'll check that"),
                        ToolCallContent(
                            tool_call_id="call_1",
                            name="get_weather",
                            arguments={"location": "Beijing"}
                        )
                    ]
                )
            ]
            result = provider._messages_to_provider_format(messages)
            
            assert result[0]['role'] == 'assistant'
            assert 'tool_calls' in result[0]
            assert len(result[0]['tool_calls']) == 1
            assert result[0]['tool_calls'][0]['function']['name'] == 'get_weather'
