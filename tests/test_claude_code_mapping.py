"""
Tests for Claude Code Tool Name Mapping
"""
import pytest

from koda.ai.claude_code_mapping import (
    CLAUDE_CODE_TOOLS,
    to_claude_code_name,
    from_claude_code_name,
    ToolNameMapper,
)


class TestClaudeCodeTools:
    """Test CLAUDE_CODE_TOOLS constant"""
    
    def test_tools_list(self):
        """Test that CLAUDE_CODE_TOOLS contains all expected tools"""
        assert "Read" in CLAUDE_CODE_TOOLS
        assert "Write" in CLAUDE_CODE_TOOLS
        assert "Edit" in CLAUDE_CODE_TOOLS
        assert "Bash" in CLAUDE_CODE_TOOLS
        assert "AskUserQuestion" in CLAUDE_CODE_TOOLS
        assert len(CLAUDE_CODE_TOOLS) == 17


class TestToClaudeCodeName:
    """Test to_claude_code_name function"""
    
    def test_basic_conversion(self):
        """Test basic name conversion"""
        assert to_claude_code_name("read") == "Read"
        assert to_claude_code_name("write") == "Write"
        assert to_claude_code_name("edit") == "Edit"
        assert to_claude_code_name("bash") == "Bash"
    
    def test_complex_conversion(self):
        """Test complex name conversion"""
        assert to_claude_code_name("ask_user") == "AskUserQuestion"
        assert to_claude_code_name("enter_plan_mode") == "EnterPlanMode"
        assert to_claude_code_name("todo_write") == "TodoWrite"
        assert to_claude_code_name("web_fetch") == "WebFetch"
    
    def test_case_insensitive(self):
        """Test case-insensitive matching"""
        assert to_claude_code_name("READ") == "Read"
        assert to_claude_code_name("Read") == "Read"
        assert to_claude_code_name("ASK_USER") == "AskUserQuestion"
    
    def test_non_claude_code_tool(self):
        """Test non-CC tool returns original"""
        assert to_claude_code_name("custom_tool") == "custom_tool"
        assert to_claude_code_name("my_tool") == "my_tool"


class TestFromClaudeCodeName:
    """Test from_claude_code_name function"""
    
    def test_basic_conversion(self):
        """Test basic name conversion"""
        assert from_claude_code_name("Read") == "read"
        assert from_claude_code_name("Write") == "write"
        assert from_claude_code_name("Edit") == "edit"
    
    def test_complex_conversion(self):
        """Test complex name conversion"""
        assert from_claude_code_name("AskUserQuestion") == "ask_user"
        assert from_claude_code_name("EnterPlanMode") == "enter_plan_mode"
        assert from_claude_code_name("TodoWrite") == "todo_write"
    
    def test_with_tools_list(self):
        """Test conversion with tools list"""
        tools = [{"name": "read_file"}, {"name": "write_file"}]
        assert from_claude_code_name("Read", tools) == "read_file"
        assert from_claude_code_name("Write", tools) == "write_file"
    
    def test_with_tools_no_match(self):
        """Test with tools list but no match"""
        tools = [{"name": "custom"}]
        assert from_claude_code_name("Read", tools) == "custom"
        assert from_claude_code_name("Unknown", tools) == "unknown"


class TestToolNameMapper:
    """Test ToolNameMapper class"""
    
    def test_to_claude_code(self):
        """Test class method"""
        assert ToolNameMapper.to_claude_code("read") == "Read"
        assert ToolNameMapper.to_claude_code("grep") == "Grep"
    
    def test_from_claude_code(self):
        """Test class method"""
        assert ToolNameMapper.from_claude_code("Read") == "read"
        assert ToolNameMapper.from_claude_code("Grep") == "grep"
    
    def test_is_claude_code_tool(self):
        """Test tool detection"""
        assert ToolNameMapper.is_claude_code_tool("Read") is True
        assert ToolNameMapper.is_claude_code_tool("read") is True
        assert ToolNameMapper.is_claude_code_tool("Custom") is False
    
    def test_get_all_claude_code_tools(self):
        """Test getting all tools"""
        tools = ToolNameMapper.get_all_claude_code_tools()
        assert isinstance(tools, list)
        assert "Read" in tools
        assert "Write" in tools
        assert len(tools) == 17


class TestRoundTrip:
    """Test round-trip conversions"""
    
    def test_round_trip(self):
        """Test that to -> from returns original"""
        original = "read"
        converted = to_claude_code_name(original)
        back = from_claude_code_name(converted)
        assert back == original
    
    def test_round_trip_complex(self):
        """Test round-trip for complex names"""
        original = "ask_user"
        converted = to_claude_code_name(original)
        back = from_claude_code_name(converted)
        assert back == original
