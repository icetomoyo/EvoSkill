"""
上下文压缩器测试
"""
import pytest
from unittest.mock import Mock, AsyncMock

from evoskill.core.context_compactor import ContextCompactor, CompactResult
from evoskill.core.types import UserMessage, AssistantMessage, TextContent


class TestContextCompactor:
    """测试 ContextCompactor"""
    
    def test_estimate_tokens(self):
        """测试 token 估算"""
        mock_llm = Mock()
        compactor = ContextCompactor(mock_llm, max_context_tokens=1000)
        
        # 测试简单文本
        text = "Hello World"  # 11 chars
        tokens = compactor.estimate_tokens(text)
        assert tokens == 5  # 11 // 2
        
        # 测试中文
        text = "你好世界"  # 4 chars
        tokens = compactor.estimate_tokens(text)
        assert tokens == 2  # 4 // 2
    
    def test_check_status_no_compact_needed(self):
        """测试不需要压缩的情况"""
        mock_llm = Mock()
        compactor = ContextCompactor(mock_llm, max_context_tokens=10000)
        
        # 少量消息
        messages = [
            UserMessage(content="Hello"),
            AssistantMessage(content=[TextContent(text="Hi")]),
        ]
        
        status = compactor.check_status(messages)
        
        assert status["should_warn"] is False
        assert status["should_compact"] is False
        assert status["current_ratio"] < 0.75
    
    def test_check_status_warning_threshold(self):
        """测试达到警告阈值"""
        mock_llm = Mock()
        # 设置较小的 max_tokens 以便测试
        compactor = ContextCompactor(mock_llm, max_context_tokens=100)
        
        # 生成足够多的消息以达到 75% 阈值
        messages = []
        for i in range(10):
            messages.append(UserMessage(content=f"Message {i} " * 10))  # ~60 tokens each
        
        status = compactor.check_status(messages)
        
        # 应该达到警告阈值（75%）
        assert status["should_warn"] is True
        assert status["current_tokens"] >= compactor.warning_threshold
    
    def test_split_messages(self):
        """测试消息分割"""
        mock_llm = Mock()
        compactor = ContextCompactor(mock_llm, max_context_tokens=10000)
        
        # 创建 10 轮对话（20 条消息）
        messages = []
        for i in range(10):
            messages.append(UserMessage(content=f"User {i}"))
            messages.append(AssistantMessage(content=[TextContent(text=f"Assistant {i}")]))
        
        history, recent = compactor.split_messages(messages)
        
        # 应该保留最近 3 轮（6 条消息）
        assert len(recent) == 6
        assert len(history) == 14
        
        # 验证最近的消息是正确的
        assert "User 7" in str(recent[0].content)
        assert "Assistant 9" in str(recent[-1].content)
    
    def test_split_messages_too_few(self):
        """测试消息太少时不分割"""
        mock_llm = Mock()
        compactor = ContextCompactor(mock_llm, max_context_tokens=10000)
        
        # 只有 2 轮对话（4 条消息）
        messages = [
            UserMessage(content="User 1"),
            AssistantMessage(content=[TextContent(text="Assistant 1")]),
            UserMessage(content="User 2"),
            AssistantMessage(content=[TextContent(text="Assistant 2")]),
        ]
        
        history, recent = compactor.split_messages(messages)
        
        # 消息太少，全部作为 history，recent 为空
        assert len(history) == 4
        assert len(recent) == 0
    
    @pytest.mark.asyncio
    async def test_compact(self):
        """测试压缩功能"""
        # Mock LLM 返回摘要
        mock_llm = Mock()
        
        async def mock_chat(messages, **kwargs):
            yield {"type": "text_delta", "content": "用户询问了项目结构并创建了一个测试文件。"}
        
        mock_llm.chat = mock_chat
        
        compactor = ContextCompactor(mock_llm, max_context_tokens=10000)
        
        # 创建测试消息
        messages = []
        for i in range(10):
            messages.append(UserMessage(content=f"User message {i} with some content"))
            messages.append(AssistantMessage(content=[TextContent(text=f"Assistant response {i}")]))
        
        result = await compactor.compact(messages)
        
        assert isinstance(result, CompactResult)
        assert result.summary != ""
        assert result.compacted_count == 14  # 10 轮 - 3 轮保留 = 7 轮历史，但实际是 14 条消息
        assert len(result.new_messages) < len(messages)
    
    def test_get_warning_message(self):
        """测试警告信息生成"""
        mock_llm = Mock()
        compactor = ContextCompactor(mock_llm, max_context_tokens=10000)
        
        status = {
            "current_tokens": 7500,
            "max_tokens": 10000,
            "current_ratio": 0.75,
        }
        
        msg = compactor.get_warning_message(status)
        
        assert "7500" in msg
        assert "10000" in msg
        assert "75.0%" in msg or "80%" in msg


class TestContextCompactorIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_compact_integration(self):
        """测试完整压缩流程"""
        # 这里可以测试与真实 LLM 的集成（需要 API Key）
        pass
