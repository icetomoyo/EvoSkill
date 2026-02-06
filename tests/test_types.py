"""
测试核心类型定义
"""

import pytest
from datetime import datetime

from evoskill.core.types import (
    Message,
    UserMessage,
    AssistantMessage,
    TextContent,
    ToolDefinition,
    ParameterSchema,
    TokenUsage,
)


class TestUserMessage:
    """测试用户消息"""
    
    def test_creation(self):
        """测试创建用户消息"""
        msg = UserMessage(
            id="test-1",
            content="Hello",
        )
        
        assert msg.id == "test-1"
        assert msg.content == "Hello"
        assert msg.role == "user"
        assert isinstance(msg.timestamp, datetime)
    
    def test_with_attachments(self):
        """测试带附件的消息"""
        from evoskill.core.types import ImageContent
        
        msg = UserMessage(
            id="test-2",
            content="Look at this",
            attachments=[ImageContent(source="http://example.com/img.png")],
        )
        
        assert len(msg.attachments) == 1


class TestAssistantMessage:
    """测试助手消息"""
    
    def test_creation(self):
        """测试创建助手消息"""
        msg = AssistantMessage(
            id="test-3",
            content=[TextContent(text="Hi there")],
            model="gpt-4",
        )
        
        assert msg.role == "assistant"
        assert msg.model == "gpt-4"
        assert msg.text == "Hi there"
    
    def test_text_property(self):
        """测试 text 属性"""
        msg = AssistantMessage(
            id="test-4",
            content=[
                TextContent(text="Hello "),
                TextContent(text="World"),
            ],
            model="gpt-4",
        )
        
        assert msg.text == "Hello World"


class TestToolDefinition:
    """测试工具定义"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={
                "param1": ParameterSchema(
                    type="string",
                    description="First param",
                    required=True,
                ),
                "param2": ParameterSchema(
                    type="integer",
                    description="Second param",
                    required=False,
                    default=42,
                ),
            },
        )
        
        result = tool.to_dict()
        
        assert result["name"] == "test_tool"
        assert result["description"] == "A test tool"
        assert "parameters" in result
        assert "param1" in result["parameters"]["properties"]
        assert "param1" in result["parameters"]["required"]
        assert "param2" not in result["parameters"]["required"]


class TestTokenUsage:
    """测试 Token 使用统计"""
    
    def test_total_tokens(self):
        """测试总 Token 计算"""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
        )
        
        assert usage.total_tokens == 150
