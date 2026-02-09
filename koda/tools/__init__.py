"""
Koda Tools - 7 Pi-compatible built-in tools

Tools:
    read: Read files with offset/limit, supports images
    write: Write files, creates directories
    edit: Precise text replacement editing
    bash: Execute shell commands
    grep: Search text patterns
    find: Find files by name
    ls: List directory contents
"""

from koda.tools.file_tool import FileTool, ReadResult, EditResult, WriteResult
from koda.tools.shell_tool import ShellTool, ShellResult
from koda.tools.grep_tool import GrepTool, GrepResult
from koda.tools.find_tool import FindTool, FindResult
from koda.tools.ls_tool import LsTool, LsResult

__all__ = [
    # Tools
    "FileTool",
    "ShellTool",
    "GrepTool",
    "FindTool",
    "LsTool",
    # Results
    "ReadResult",
    "EditResult",
    "WriteResult",
    "ShellResult",
    "GrepResult",
    "FindResult",
    "LsResult",
]
