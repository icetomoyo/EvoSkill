"""
Tools - Pi-compatible tool implementations

All core tools from Pi Coding Agent:
- read: File reading with image support
- write: File writing
- edit: File editing with fuzzy matching
- bash: Shell execution
- grep: Content search (ripgrep)
- find: File search (fd)
- ls: Directory listing
"""

from koda.tools.file_tool import FileTool, ReadResult, WriteResult, EditResult
from koda.tools.shell_tool import ShellTool, ShellResult
from koda.tools.grep_tool import GrepTool, GrepResult
from koda.tools.find_tool import FindTool, FindResult
from koda.tools.ls_tool import LsTool, LsResult

# Default tool instances (for backwards compatibility)
file_tool = FileTool()
shell_tool = ShellTool()
grep_tool = GrepTool()
find_tool = FindTool()
ls_tool = LsTool()

# Tool collections (matching Pi's codingTools, readOnlyTools, allTools)
coding_tools = [file_tool, shell_tool]  # Core tools
read_only_tools = [file_tool, grep_tool, find_tool, ls_tool]  # Read-only exploration
all_tools = {
    "read": file_tool,
    "write": file_tool,
    "edit": file_tool,
    "bash": shell_tool,
    "grep": grep_tool,
    "find": find_tool,
    "ls": ls_tool,
}

__all__ = [
    # Classes
    "FileTool",
    "ShellTool",
    "GrepTool",
    "FindTool",
    "LsTool",
    # Results
    "ReadResult",
    "WriteResult",
    "EditResult",
    "ShellResult",
    "GrepResult",
    "FindResult",
    "LsResult",
    # Default instances
    "file_tool",
    "shell_tool",
    "grep_tool",
    "find_tool",
    "ls_tool",
    # Collections
    "coding_tools",
    "read_only_tools",
    "all_tools",
]
