"""
Session 集成测试
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from evoskill.core.session import AgentSession
from evoskill.core.types import (
    LLMConfig,
    UserMessage,
    AssistantMessage,
    TextContent,
    ToolCallContent,
    ToolResultMessage,
    EventType,
)


class TestAgentSessionInit:
    """测试 Session 初始化"""
    
    def test_default_init(self, temp_dir):
        """测试默认初始化"""
        session = AgentSession(workspace=temp_dir)
        
        assert session.session_id is not None
        assert session.workspace == temp_dir
        assert len(session.messages) == 0
        assert len(session._tools) > 0  # 应该加载内置工具
    
    def test_custom_init(self, temp_dir, mock_llm_config):
        """测试自定义初始化"""
        session = AgentSession(
            session_id="test-session-123",
            workspace=temp_dir,
            llm_config=mock_llm_config,
            system_prompt="Custom system prompt",
        )
        
        assert session.session_id == "test-session-123"
        assert session.llm_config == mock_llm_config
        assert session.system_prompt == "Custom system prompt"


class TestAgentSessionTools:
    """测试 Session 工具管理"""
    
    def test_register_builtin_tools(self, temp_dir):
        """测试内置工具自动注册"""
        session = AgentSession(workspace=temp_dir)
        
        # 验证内置工具已注册
        assert "read_file" in session._tools
        assert "edit_code" in session._tools
        assert "list_dir" in session._tools
        assert "search_files" in session._tools
        assert "execute_command" in session._tools
        assert "fetch_url" in session._tools
    
    def test_get_available_tools(self, temp_dir):
        """测试获取可用工具列表"""
        session = AgentSession(workspace=temp_dir)
        tools = session.get_available_tools()
        
        assert len(tools) >= 6  # 至少内置工具数量
        tool_names = [t.name for t in tools]
        assert "read_file" in tool_names
        assert "edit_code" in tool_names


class TestAgentSessionPrompt:
    """测试 Session 对话流程"""
    
    @pytest.mark.asyncio
    async def test_simple_prompt(self, temp_dir, mock_llm_config):
        """测试简单对话"""
        # Mock LLM provider
        mock_provider = Mock()
        mock_provider.chat = AsyncMock(return_value=self._mock_text_stream("Hello!"))
        
        with patch('evoskill.core.session.create_llm_provider', return_value=mock_provider):
            session = AgentSession(
                workspace=temp_dir,
                llm_config=mock_llm_config
            )
            
            events = []
            async for event in session.prompt("Hi there"):
                events.append(event)
            
            # 验证事件
            assert len(events) > 0
            assert events[0].type == EventType.TEXT_DELTA
            assert "Hello" in events[0].data.get("content", "")
            
            # 验证消息历史
            assert len(session.messages) == 2  # user + assistant
            assert session.messages[0].role == "user"
            assert session.messages[1].role == "assistant"
    
    @pytest.mark.asyncio
    async def test_prompt_with_tool_call(self, temp_dir, mock_llm_config):
        """测试包含工具调用的对话"""
        # Mock 工具执行结果
        mock_tool_result = {"success": True, "content": "File content here"}
        
        # Mock LLM 响应：先返回工具调用，再返回最终结果
        mock_responses = [
            # 第一轮：工具调用
            {"type": "tool_call_start", "tool_call_id": "call_1", "name": "read_file"},
            {"type": "tool_call_delta", "tool_call_id": "call_1", "arguments": '{"path": "test.txt"}'},
            {"type": "finish", "finish_reason": "tool_calls"},
            # 第二轮：文本响应（工具执行后）
            {"type": "text_delta", "content": "The file contains: File content here"},
            {"type": "finish", "finish_reason": "stop"},
        ]
        
        mock_provider = Mock()
        mock_provider.chat = AsyncMock(side_effect=[
            self._mock_event_stream(mock_responses[:3]),  # 第一次调用
            self._mock_event_stream(mock_responses[3:]),  # 第二次调用（工具执行后）
        ])
        
        # Mock 工具执行
        with patch('evoskill.core.session.create_llm_provider', return_value=mock_provider):
            with patch.object(AgentSession, '_execute_tool', return_value=mock_tool_result):
                session = AgentSession(
                    workspace=temp_dir,
                    llm_config=mock_llm_config
                )
                
                events = []
                async for event in session.prompt("Read test.txt"):
                    events.append(event)
                
                # 验证工具调用事件
                tool_start_events = [e for e in events if e.type == EventType.TOOL_CALL_START]
                assert len(tool_start_events) > 0
                
                # 验证工具执行事件
                tool_exec_events = [e for e in events if e.type == EventType.TOOL_EXECUTION_START]
                assert len(tool_exec_events) > 0
    
    @staticmethod
    def _mock_text_stream(text):
        """创建模拟文本流"""
        async def generator():
            yield {"type": "text_delta", "content": text}
            yield {"type": "finish", "finish_reason": "stop"}
        return generator()
    
    @staticmethod
    def _mock_event_stream(events):
        """创建模拟事件流"""
        async def generator():
            for event in events:
                yield event
        return generator()


class TestAgentSessionContext:
    """测试 Session 上下文管理"""
    
    def test_message_history(self, temp_dir):
        """测试消息历史记录"""
        session = AgentSession(workspace=temp_dir)
        
        # 添加一些消息
        session.messages.append(UserMessage(content="Message 1"))
        session.messages.append(AssistantMessage(content=[TextContent(text="Reply 1")]))
        session.messages.append(UserMessage(content="Message 2"))
        
        assert len(session.messages) == 3
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"
        assert session.messages[2].role == "user"
    
    def test_clear_history(self, temp_dir):
        """测试清空历史"""
        session = AgentSession(workspace=temp_dir)
        session.messages.append(UserMessage(content="Test"))
        
        assert len(session.messages) == 1
        
        session.messages.clear()
        assert len(session.messages) == 0


class TestAgentSessionPersistence:
    """测试 Session 持久化（可选功能）"""
    
    def test_export_state(self, temp_dir):
        """测试导出会话状态"""
        session = AgentSession(
            session_id="test-export",
            workspace=temp_dir
        )
        
        # 添加一些状态
        session.messages.append(UserMessage(content="Hello"))
        
        # 导出状态
        state = {
            "session_id": session.session_id,
            "workspace": str(session.workspace),
            "message_count": len(session.messages),
            "tool_count": len(session._tools),
        }
        
        assert state["session_id"] == "test-export"
        assert state["message_count"] == 1
        assert state["tool_count"] >= 6
