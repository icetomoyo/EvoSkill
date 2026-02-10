"""
Tests for Claude Code Tool Name Mapping
"""
import pytest

from koda.ai.claude_code_mapping import (
    ClaudeCodeTool,
    ToolNameMapper,
    ToolTransformation,
    ClaudeCodeCompatibilityLayer,
    enable_claude_code_compatibility,
)


class TestClaudeCodeTool:
    """Test ClaudeCodeTool enum"""
    
    def test_tool_values(self):
        """Test enum values are correct PascalCase"""
        assert ClaudeCodeTool.READ == "Read"
        assert ClaudeCodeTool.WRITE == "Write"
        assert ClaudeCodeTool.BASH == "Bash"
        assert ClaudeCodeTool.ASK_USER == "AskUserQuestion"
    
    def test_tool_enum_iteration(self):
        """Test all tools are defined"""
        tools = list(ClaudeCodeTool)
        assert len(tools) >= 18
        assert ClaudeCodeTool.READ in tools
        assert ClaudeCodeTool.WEB_SEARCH in tools


class TestToolNameMapper:
    """Test ToolNameMapper class"""
    
    def test_to_claude_code_basic(self):
        """Test basic name conversion"""
        assert ToolNameMapper.to_claude_code("read") == "Read"
        assert ToolNameMapper.to_claude_code("write") == "Write"
        assert ToolNameMapper.to_claude_code("edit") == "Edit"
        assert ToolNameMapper.to_claude_code("bash") == "Bash"
    
    def test_to_claude_code_complex(self):
        """Test complex name conversion"""
        assert ToolNameMapper.to_claude_code("ask_user") == "AskUserQuestion"
        assert ToolNameMapper.to_claude_code("ask_user_question") == "AskUserQuestion"
        assert ToolNameMapper.to_claude_code("enter_plan") == "EnterPlanMode"
        assert ToolNameMapper.to_claude_code("todo_write") == "TodoWrite"
        assert ToolNameMapper.to_claude_code("web_fetch") == "WebFetch"
    
    def test_to_claude_code_aliases(self):
        """Test alias conversion"""
        assert ToolNameMapper.to_claude_code("shell") == "Bash"
        assert ToolNameMapper.to_claude_code("list") == "List"
        assert ToolNameMapper.to_claude_code("fetch") == "WebFetch"
        assert ToolNameMapper.to_claude_code("search") == "WebSearch"
    
    def test_to_claude_code_unknown(self):
        """Test unknown tool falls back to capitalized"""
        assert ToolNameMapper.to_claude_code("unknown_tool") == "Unknown_tool"
        assert ToolNameMapper.to_claude_code("custom") == "Custom"
    
    def test_from_claude_code_basic(self):
        """Test reverse basic conversion"""
        assert ToolNameMapper.from_claude_code("Read") == "read"
        assert ToolNameMapper.from_claude_code("Write") == "write"
        assert ToolNameMapper.from_claude_code("Edit") == "edit"
    
    def test_from_claude_code_complex(self):
        """Test reverse complex conversion"""
        assert ToolNameMapper.from_claude_code("AskUserQuestion") == "ask_user"
        assert ToolNameMapper.from_claude_code("EnterPlanMode") == "enter_plan"
        assert ToolNameMapper.from_claude_code("TodoWrite") == "todo_write"
    
    def test_is_claude_code_tool(self):
        """Test tool detection"""
        assert ToolNameMapper.is_claude_code_tool("Read") is True
        assert ToolNameMapper.is_claude_code_tool("AskUserQuestion") is True
        assert ToolNameMapper.is_claude_code_tool("read") is False  # Koda format
        assert ToolNameMapper.is_claude_code_tool("UnknownTool") is False
    
    def test_transform_arguments_read(self):
        """Test argument transformation for Read tool"""
        result = ToolNameMapper.transform_arguments("Read", {"path": "/tmp/test.txt"})
        assert result == {"file_path": "/tmp/test.txt"}
        
        # Also accepts file_path directly
        result = ToolNameMapper.transform_arguments("Read", {"file_path": "/tmp/test.txt"})
        assert result == {"file_path": "/tmp/test.txt"}
    
    def test_transform_arguments_write(self):
        """Test argument transformation for Write tool"""
        args = {"path": "/tmp/test.txt", "content": "hello"}
        result = ToolNameMapper.transform_arguments("Write", args)
        assert result == {"file_path": "/tmp/test.txt", "content": "hello"}
    
    def test_transform_arguments_edit(self):
        """Test argument transformation for Edit tool"""
        args = {"path": "/tmp/test.txt", "old": "hello", "new": "world"}
        result = ToolNameMapper.transform_arguments("Edit", args)
        assert result == {"file_path": "/tmp/test.txt", "old_string": "hello", "new_string": "world"}
    
    def test_transform_arguments_bash(self):
        """Test argument transformation for Bash tool"""
        args = {"cmd": "ls -la", "timeout": 30}
        result = ToolNameMapper.transform_arguments("Bash", args)
        assert result == {"command": "ls -la", "timeout": 30}
    
    def test_transform_arguments_no_transform(self):
        """Test tools without argument transforms pass through"""
        args = {"pattern": "test", "path": "/tmp"}
        result = ToolNameMapper.transform_arguments("Grep", args)
        assert result == args
    
    def test_transform_tool_for_anthropic(self):
        """Test complete tool transformation"""
        result = ToolNameMapper.transform_tool_for_anthropic(
            "read",
            {"path": "/tmp/test.txt"}
        )
        
        assert isinstance(result, ToolTransformation)
        assert result.name == "Read"
        assert result.arguments == {"file_path": "/tmp/test.txt"}
        assert result.original_name == "read"
    
    def test_get_all_claude_code_tools(self):
        """Test getting all tool names"""
        tools = ToolNameMapper.get_all_claude_code_tools()
        assert isinstance(tools, list)
        assert "Read" in tools
        assert "Write" in tools
        assert "AskUserQuestion" in tools
    
    def test_get_tool_description(self):
        """Test getting tool descriptions"""
        assert "Read" in ToolNameMapper.get_tool_description("Read")
        assert "bash" in ToolNameMapper.get_tool_description("Bash").lower()
        assert ToolNameMapper.get_tool_description("Unknown") is None


class TestClaudeCodeCompatibilityLayer:
    """Test ClaudeCodeCompatibilityLayer"""
    
    def test_wrap_tool_definition(self):
        """Test wrapping tool definition"""
        layer = ClaudeCodeCompatibilityLayer()
        
        tool = {
            "name": "read",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
        
        wrapped = layer.wrap_tool_definition(tool)
        
        assert wrapped["name"] == "Read"
        assert "file_path" in wrapped["parameters"]["properties"]
        assert "path" not in wrapped["parameters"]["properties"]
        assert wrapped["parameters"]["required"] == ["file_path"]
    
    def test_wrap_tool_definition_no_transform(self):
        """Test wrapping tool with no transforms"""
        layer = ClaudeCodeCompatibilityLayer()
        
        tool = {
            "name": "custom_tool",
            "description": "Custom tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                }
            }
        }
        
        wrapped = layer.wrap_tool_definition(tool)
        
        assert wrapped["name"] == "Custom_tool"
        assert "arg1" in wrapped["parameters"]["properties"]
    
    def test_unwrap_tool_result(self):
        """Test unwrapping tool result"""
        layer = ClaudeCodeCompatibilityLayer()
        
        name, result = layer.unwrap_tool_result("Read", {"content": "file contents"})
        
        assert name == "read"
        assert result == {"content": "file contents"}


class TestEnableClaudeCodeCompatibility:
    """Test enable_claude_code_compatibility function"""
    
    def test_enable_compatibility(self):
        """Test enabling compatibility for provider config"""
        config = {
            "provider": "anthropic",
            "tools": [
                {"name": "read", "parameters": {"properties": {"path": {}}}},
                {"name": "write", "parameters": {"properties": {"path": {}, "content": {}}}},
            ]
        }
        
        result = enable_claude_code_compatibility(config)
        
        assert result["tools"][0]["name"] == "Read"
        assert "file_path" in result["tools"][0]["parameters"]["properties"]
        assert result["tools"][1]["name"] == "Write"
    
    def test_enable_no_tools(self):
        """Test config without tools"""
        config = {"provider": "anthropic"}
        
        result = enable_claude_code_compatibility(config)
        
        assert result == config


class TestRoundTripConversion:
    """Test round-trip conversions"""
    
    def test_round_trip_basic(self):
        """Test basic round-trip conversion"""
        original = "read"
        converted = ToolNameMapper.to_claude_code(original)
        back = ToolNameMapper.from_claude_code(converted)
        assert back == original
    
    def test_round_trip_complex(self):
        """Test complex round-trip conversion"""
        original = "ask_user"
        converted = ToolNameMapper.to_claude_code(original)
        back = ToolNameMapper.from_claude_code(converted)
        assert back == original


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_string(self):
        """Test empty string handling"""
        assert ToolNameMapper.to_claude_code("") == ""
        assert ToolNameMapper.from_claude_code("") == ""
    
    def test_case_sensitivity(self):
        """Test case sensitivity"""
        assert ToolNameMapper.to_claude_code("READ") == "Read"
        assert ToolNameMapper.to_claude_code("Read") == "Read"
    
    def test_hyphen_conversion(self):
        """Test hyphen to underscore conversion"""
        # Note: hyphens are normalized to underscores
        result = ToolNameMapper.to_claude_code("ask-user")
        assert result == "AskUserQuestion"  # ask-user -> ask_user -> AskUserQuestion
