"""
Claude Code Tool Name Mapping

Maps tool names between Koda and Claude Code conventions.
Claude Code uses PascalCase tool names, while Koda uses lowercase_snake.

Reference: packages/ai/src/providers/anthropic.ts:90-120
"""
from enum import Enum
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass


class ClaudeCodeTool(str, Enum):
    """Claude Code canonical tool names (PascalCase)"""
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    BASH = "Bash"
    GREP = "Grep"
    GLOB = "Glob"
    LS = "List"
    ASK_USER = "AskUserQuestion"
    ENTER_PLAN = "EnterPlanMode"
    EXIT_PLAN = "ExitPlanMode"
    KILL_SHELL = "KillShell"
    NOTEBOOK_EDIT = "NotebookEdit"
    SKILL = "Skill"
    TASK = "Task"
    TASK_OUTPUT = "TaskOutput"
    TODO_WRITE = "TodoWrite"
    WEB_FETCH = "WebFetch"
    WEB_SEARCH = "WebSearch"


@dataclass
class ToolTransformation:
    """Result of tool transformation"""
    name: str
    arguments: Dict[str, Any]
    original_name: str


class ToolNameMapper:
    """
    Maps tool names between Koda and Claude Code conventions
    
    Claude Code uses PascalCase tool names like "Read", "AskUserQuestion"
    Koda uses lowercase_snake names like "read", "ask_user"
    
    Example:
        >>> mapper = ToolNameMapper()
        >>> mapper.to_claude_code("read")
        'Read'
        >>> mapper.to_claude_code("ask_user")
        'AskUserQuestion'
        >>> mapper.from_claude_code("Read")
        'read'
    """
    
    # Mapping from Koda (lowercase_snake) to Claude Code (PascalCase)
    _TO_CLAUDE_CODE: Dict[str, str] = {
        # Core tools
        "read": "Read",
        "write": "Write",
        "edit": "Edit",
        "bash": "Bash",
        "shell": "Bash",  # Alias
        "grep": "Grep",
        "glob": "Glob",
        "ls": "List",
        "list": "List",  # Alias
        
        # Interactive tools
        "ask_user": "AskUserQuestion",
        "ask_user_question": "AskUserQuestion",
        "enter_plan": "EnterPlanMode",
        "enter_plan_mode": "EnterPlanMode",
        "exit_plan": "ExitPlanMode",
        "exit_plan_mode": "ExitPlanMode",
        
        # Process management
        "kill_shell": "KillShell",
        
        # Notebook
        "notebook_edit": "NotebookEdit",
        
        # Skill/Task
        "skill": "Skill",
        "task": "Task",
        "task_output": "TaskOutput",
        "todo_write": "TodoWrite",
        
        # Web
        "web_fetch": "WebFetch",
        "fetch": "WebFetch",  # Alias
        "web_search": "WebSearch",
        "search": "WebSearch",  # Alias
    }
    
    # Reverse mapping (PascalCase -> lowercase_snake)
    _FROM_CLAUDE_CODE: Dict[str, str] = {
        v: k for k, v in _TO_CLAUDE_CODE.items()
        if not k.endswith("_mode") and k != "shell" and k not in ["list", "ask_user_question", "enter_plan_mode", "exit_plan_mode", "fetch", "search"]
    }
    
    # Argument transformations for specific tools
    _ARG_TRANSFORMS: Dict[str, Dict[str, str]] = {
        "Read": {
            "path": "file_path",
            "file": "file_path",
        },
        "Write": {
            "path": "file_path",
            "file": "file_path",
            "content": "content",
        },
        "Edit": {
            "path": "file_path",
            "file": "file_path",
            "old": "old_string",
            "old_string": "old_string",
            "new": "new_string",
            "new_string": "new_string",
        },
        "Bash": {
            "command": "command",
            "cmd": "command",
            "timeout": "timeout",
        },
    }
    
    @classmethod
    def to_claude_code(cls, name: str) -> str:
        """
        Convert Koda tool name to Claude Code format
        
        Args:
            name: Koda tool name (e.g., "read", "ask_user")
            
        Returns:
            Claude Code tool name (e.g., "Read", "AskUserQuestion")
            
        Example:
            >>> ToolNameMapper.to_claude_code("read")
            'Read'
            >>> ToolNameMapper.to_claude_code("ask_user")
            'AskUserQuestion'
        """
        normalized = name.lower().replace("-", "_")
        return cls._TO_CLAUDE_CODE.get(normalized, name.capitalize())
    
    @classmethod
    def from_claude_code(cls, name: str) -> str:
        """
        Convert Claude Code tool name to Koda format
        
        Args:
            name: Claude Code tool name (e.g., "Read", "AskUserQuestion")
            
        Returns:
            Koda tool name (e.g., "read", "ask_user")
            
        Example:
            >>> ToolNameMapper.from_claude_code("Read")
            'read'
            >>> ToolNameMapper.from_claude_code("AskUserQuestion")
            'ask_user'
        """
        return cls._FROM_CLAUDE_CODE.get(name, name.lower().replace(" ", "_"))
    
    @classmethod
    def is_claude_code_tool(cls, name: str) -> bool:
        """
        Check if name is a known Claude Code tool
        
        Args:
            name: Tool name to check
            
        Returns:
            True if it's a known Claude Code tool
        """
        return name in cls._FROM_CLAUDE_CODE
    
    @classmethod
    def transform_arguments(
        cls,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform argument names for specific tools
        
        Some tools have different argument names between Koda and Claude Code.
        For example, "read" tool uses "path" in Koda but "file_path" in Claude Code.
        
        Args:
            tool_name: Claude Code tool name
            arguments: Original arguments
            
        Returns:
            Transformed arguments
        """
        transforms = cls._ARG_TRANSFORMS.get(tool_name, {})
        
        if not transforms:
            return arguments
        
        result = {}
        for key, value in arguments.items():
            new_key = transforms.get(key, key)
            result[new_key] = value
        
        return result
    
    @classmethod
    def transform_tool_for_anthropic(
        cls,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolTransformation:
        """
        Transform a complete tool call for Anthropic API
        
        This combines name transformation and argument transformation.
        
        Args:
            tool_name: Koda tool name
            arguments: Tool arguments
            
        Returns:
            ToolTransformation with new name and arguments
            
        Example:
            >>> mapper = ToolNameMapper()
            >>> result = mapper.transform_tool_for_anthropic("read", {"path": "/tmp/test.txt"})
            >>> result.name
            'Read'
            >>> result.arguments
            {'file_path': '/tmp/test.txt'}
        """
        # Transform name
        new_name = cls.to_claude_code(tool_name)
        
        # Transform arguments
        new_arguments = cls.transform_arguments(new_name, arguments)
        
        return ToolTransformation(
            name=new_name,
            arguments=new_arguments,
            original_name=tool_name
        )
    
    @classmethod
    def get_all_claude_code_tools(cls) -> list:
        """Get list of all known Claude Code tool names"""
        return list(cls._FROM_CLAUDE_CODE.keys())
    
    @classmethod
    def get_tool_description(cls, claude_code_name: str) -> Optional[str]:
        """
        Get description for a Claude Code tool
        
        Args:
            claude_code_name: Claude Code tool name
            
        Returns:
            Tool description or None
        """
        descriptions = {
            "Read": "Read the contents of a file",
            "Write": "Write content to a file",
            "Edit": "Edit a file by replacing text",
            "Bash": "Execute a bash command",
            "Grep": "Search for patterns in files",
            "Glob": "Find files matching a pattern",
            "List": "List directory contents",
            "AskUserQuestion": "Ask the user a question",
            "EnterPlanMode": "Enter plan mode for complex tasks",
            "ExitPlanMode": "Exit plan mode",
            "KillShell": "Kill a running shell process",
            "NotebookEdit": "Edit a Jupyter notebook",
            "Skill": "Use a predefined skill",
            "Task": "Create a sub-task",
            "TaskOutput": "Output from a sub-task",
            "TodoWrite": "Write to a todo list",
            "WebFetch": "Fetch content from a URL",
            "WebSearch": "Search the web",
        }
        return descriptions.get(claude_code_name)


class ClaudeCodeCompatibilityLayer:
    """
    Compatibility layer for Claude Code API
    
    Wraps tool calls to ensure compatibility with Claude Code's expected format.
    """
    
    def __init__(self, mapper: Optional[ToolNameMapper] = None):
        self.mapper = mapper or ToolNameMapper()
    
    def wrap_tool_definition(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap a tool definition for Claude Code compatibility
        
        Args:
            tool: Original tool definition
            
        Returns:
            Wrapped tool definition
        """
        name = tool.get("name", "")
        
        # Transform name
        new_name = self.mapper.to_claude_code(name)
        
        # Transform parameter names in schema
        schema = tool.get("parameters", {})
        properties = schema.get("properties", {})
        
        # Handle argument name transformations
        arg_transforms = self.mapper._ARG_TRANSFORMS.get(new_name, {})
        
        new_properties = {}
        for key, value in properties.items():
            new_key = arg_transforms.get(key, key)
            new_properties[new_key] = value
        
        # Update required fields
        required = schema.get("required", [])
        new_required = [arg_transforms.get(r, r) for r in required]
        
        return {
            **tool,
            "name": new_name,
            "parameters": {
                **schema,
                "properties": new_properties,
                "required": new_required,
            }
        }
    
    def unwrap_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Unwrap a tool result from Claude Code format back to Koda format
        
        Args:
            tool_name: Claude Code tool name
            result: Tool result
            
        Returns:
            Tuple of (koda_tool_name, result)
        """
        koda_name = self.mapper.from_claude_code(tool_name)
        return koda_name, result


def enable_claude_code_compatibility(
    provider_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enable Claude Code compatibility for a provider configuration
    
    Args:
        provider_config: Provider configuration dict
        
    Returns:
        Modified configuration with Claude Code compatibility
    """
    compat = ClaudeCodeCompatibilityLayer()
    
    # Transform tool definitions if present
    if "tools" in provider_config:
        provider_config["tools"] = [
            compat.wrap_tool_definition(tool)
            for tool in provider_config["tools"]
        ]
    
    return provider_config
