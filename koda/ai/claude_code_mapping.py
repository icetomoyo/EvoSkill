"""
Claude Code Tool Name Mapping

Maps tool names between Koda and Claude Code conventions.
Claude Code uses PascalCase tool names, while Koda uses lowercase_snake.

Reference: packages/ai/src/providers/anthropic.ts:69-97
"""
from typing import Dict, List, Optional, Any

# Claude Code 2.x tool names (canonical casing)
# From: packages/ai/src/providers/anthropic.ts:69-87
CLAUDE_CODE_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Grep",
    "Glob",
    "AskUserQuestion",
    "EnterPlanMode",
    "ExitPlanMode",
    "KillShell",
    "NotebookEdit",
    "Skill",
    "Task",
    "TaskOutput",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
]

# Lookup map for case-insensitive matching
# From: packages/ai/src/providers/anthropic.ts:89
_CC_TOOL_LOOKUP: Dict[str, str] = {
    tool.lower(): tool for tool in CLAUDE_CODE_TOOLS
}

# Koda to Claude Code tool name mapping
# Koda uses snake_case, Claude Code uses PascalCase
_KODA_TO_CC: Dict[str, str] = {
    # Core tools
    "read": "Read",
    "write": "Write", 
    "edit": "Edit",
    "bash": "Bash",
    "grep": "Grep",
    "glob": "Glob",
    "ls": "Glob",  # Koda's ls maps to Glob
    "list": "Glob",
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
    "web_search": "WebSearch",
}

# Claude Code to Koda tool name mapping (canonical versions)
# Manually defined to ensure correct mappings (avoiding dict comprehension key conflicts)
_CC_TO_KODA: Dict[str, str] = {
    "AskUserQuestion": "ask_user",
    "EnterPlanMode": "enter_plan_mode",
    "ExitPlanMode": "exit_plan_mode",
    "KillShell": "kill_shell",
    "NotebookEdit": "notebook_edit",
    "TodoWrite": "todo_write",
    "WebFetch": "web_fetch",
    "WebSearch": "web_search",
    "TaskOutput": "task_output",
}


def to_claude_code_name(name: str) -> str:
    """
    Convert tool name to Claude Code canonical casing if it matches (case-insensitive)
    
    From: packages/ai/src/providers/anthropic.ts:92
    
    First checks if it's a Koda tool name (snake_case), then checks if it's a 
    CC tool name (PascalCase).
    
    Args:
        name: Tool name (e.g., "read", "READ", "Read")
        
    Returns:
        Claude Code canonical name (e.g., "Read") or original name if not a CC tool
        
    Example:
        >>> to_claude_code_name("read")
        'Read'
        >>> to_claude_code_name("ask_user")
        'AskUserQuestion'
        >>> to_claude_code_name("custom_tool")
        'custom_tool'
    """
    normalized = name.lower()
    # First check Koda mapping
    if normalized in _KODA_TO_CC:
        return _KODA_TO_CC[normalized]
    # Then check CC direct mapping
    return _CC_TOOL_LOOKUP.get(normalized, name)


def from_claude_code_name(name: str, tools: Optional[List[Any]] = None) -> str:
    """
    Convert Claude Code tool name back to the original tool name from tools list
    
    From: packages/ai/src/providers/anthropic.ts:93-98
    
    Args:
        name: Claude Code tool name (e.g., "Read")
        tools: List of available tools to match against
        
    Returns:
        Original tool name from tools list, or lowercased name if no match
        
    Example:
        >>> from_claude_code_name("Read", [{"name": "read"}])
        'read'
    """
    normalized = name.lower()
    
    # First, determine the Koda name from CC name
    # Check if it's a known CC tool
    cc_canonical = _CC_TOOL_LOOKUP.get(normalized)
    is_cc_tool = cc_canonical is not None
    if is_cc_tool:
        # It's a CC tool - use complex mapping if available, otherwise lowercase
        koda_name = _CC_TO_KODA.get(cc_canonical, cc_canonical.lower())
    else:
        # Not a known CC tool, use lowercase
        koda_name = normalized
    
    # If tools list provided, search for matching tool
    if tools and len(tools) > 0:
        # First try exact match with koda_name
        for tool in tools:
            tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            if tool_name and tool_name.lower() == koda_name:
                return tool_name
        
        # Then try prefix match (e.g., "read" matches "read_file")
        for tool in tools:
            tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            if tool_name and tool_name.lower().startswith(koda_name):
                return tool_name
        
        # Finally try match with original normalized name
        for tool in tools:
            tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            if tool_name and tool_name.lower() == normalized:
                return tool_name
        
        # If no match found and it's a known CC tool, return first tool from list
        # (This handles edge cases where CC tool name doesn't directly map)
        if is_cc_tool:
            first_tool = tools[0]
            first_tool_name = first_tool.get("name") if isinstance(first_tool, dict) else getattr(first_tool, "name", None)
            if first_tool_name:
                return first_tool_name
    
    return koda_name


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
    
    @classmethod
    def to_claude_code(cls, name: str) -> str:
        """Convert tool name to Claude Code format"""
        return to_claude_code_name(name)
    
    @classmethod
    def from_claude_code(cls, name: str) -> str:
        """Convert Claude Code tool name to Koda format"""
        return from_claude_code_name(name)
    
    @classmethod
    def is_claude_code_tool(cls, name: str) -> bool:
        """Check if name is a known Claude Code tool"""
        return name.lower() in _CC_TOOL_LOOKUP
    
    @classmethod
    def get_all_claude_code_tools(cls) -> List[str]:
        """Get list of all known Claude Code tool names"""
        return CLAUDE_CODE_TOOLS.copy()


# Export the key functions and constants
__all__ = [
    "CLAUDE_CODE_TOOLS",
    "to_claude_code_name",
    "from_claude_code_name",
    "ToolNameMapper",
]
