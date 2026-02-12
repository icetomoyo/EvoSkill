"""
Mom Tools - Tool collection for Mom agent

Equivalent to Pi Mono's mom/tools/

Provides simplified tool implementations optimized for
multi-channel chatbot usage.

Tools:
- read: Read file contents (with pagination, image support)
- write: Write content to file (atomic writes, backups)
- edit: Precise file editing (string replacement, diff)
- bash: Execute shell commands (timeout, truncation)
- attach: Attach files to conversation (MIME detection, encoding)
- truncate: Output truncation utilities
"""
from typing import Dict, List, Any, Optional, Type, Callable
from dataclasses import dataclass, field
from pathlib import Path

# Import result types
from koda.mom.tools.read import ReadResult, ReadTool, read_file
from koda.mom.tools.write import WriteResult, WriteTool, write_file
from koda.mom.tools.edit import EditResult, EditTool, edit_file, EditOperation, create_edit
from koda.mom.tools.bash import BashResult, BashTool, execute_bash, execute_bash_async, AbortSignal
from koda.mom.tools.attach import AttachResult, AttachTool, attach_file, detect_mime_type, encode_file
from koda.mom.tools.truncate import (
    TruncationResult,
    truncate_head,
    truncate_tail,
    truncate_output,
    format_truncation_notice,
    format_size,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
)


@dataclass
class ToolResult:
    """
    Generic result from a tool execution.

    This is a unified result type that wraps the specific tool results.
    """
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_read(cls, result: ReadResult) -> "ToolResult":
        """Create from ReadResult."""
        return cls(
            success=result.success,
            output=result.content,
            error=result.error,
            metadata={
                "path": result.path,
                "start_line": result.start_line,
                "end_line": result.end_line,
                "total_lines": result.total_lines,
                "truncated": result.truncated,
                "is_image": result.is_image,
                "image_data": result.image_data,
                "mime_type": result.mime_type,
                **result.metadata,
            },
        )

    @classmethod
    def from_write(cls, result: WriteResult) -> "ToolResult":
        """Create from WriteResult."""
        return cls(
            success=result.success,
            output=f"Successfully wrote to {result.path}" if result.success else "",
            error=result.error,
            metadata={
                "path": result.path,
                "bytes_written": result.bytes_written,
                "backup_path": result.backup_path,
                **result.metadata,
            },
        )

    @classmethod
    def from_edit(cls, result: EditResult) -> "ToolResult":
        """Create from EditResult."""
        output = f"Successfully edited {result.path}"
        if result.diff:
            output += f"\n\nDiff:\n{result.diff}"
        return cls(
            success=result.success,
            output=output if result.success else "",
            error=result.error,
            metadata={
                "path": result.path,
                "diff": result.diff,
                "first_changed_line": result.first_changed_line,
                "occurrences_replaced": result.occurrences_replaced,
                **result.metadata,
            },
        )

    @classmethod
    def from_bash(cls, result: BashResult) -> "ToolResult":
        """Create from BashResult."""
        return cls(
            success=result.success,
            output=result.output,
            error=result.error,
            metadata={
                "exit_code": result.exit_code,
                "truncated": result.truncated,
                "total_lines": result.total_lines,
                "output_lines": result.output_lines,
                "full_output_path": result.full_output_path,
                **result.metadata,
            },
        )

    @classmethod
    def from_attach(cls, result: AttachResult) -> "ToolResult":
        """Create from AttachResult."""
        return cls(
            success=result.success,
            output=result.output,
            error=result.error,
            metadata={
                "path": result.path,
                "attachment_type": result.attachment_type,
                "mime_type": result.mime_type,
                "data": result.data,
                "content": result.content,
                "size": result.size,
                "description": result.description,
                **result.metadata,
            },
        )


# Tool registry
_tool_registry: Dict[str, Type] = {}


def register_tool(name: str, tool_class: Type) -> None:
    """
    Register a tool class.

    Args:
        name: Tool name
        tool_class: Tool class
    """
    _tool_registry[name] = tool_class


def get_registered_tools() -> Dict[str, Type]:
    """Get all registered tools."""
    return _tool_registry.copy()


def get_mom_tools(
    base_path: Optional[Path] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Get all Mom tools as instances.

    Args:
        base_path: Base directory for file operations
        **kwargs: Additional options for specific tools

    Returns:
        Dictionary mapping tool names to tool instances
    """
    base_path = base_path or Path.cwd()

    return {
        "read": ReadTool(base_path),
        "write": WriteTool(
            base_path,
            atomic=kwargs.get("atomic_write", True),
            backup=kwargs.get("backup", False),
        ),
        "edit": EditTool(base_path),
        "bash": BashTool(
            base_path,
            default_timeout=kwargs.get("default_timeout", 60),
        ),
        "attach": AttachTool(
            base_path,
            max_size=kwargs.get("max_attachment_size", 10 * 1024 * 1024),
        ),
    }


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all tool definitions for LLM.

    Returns:
        List of tool definitions in LLM-compatible format
    """
    tools = get_mom_tools()
    return [tool.get_definition() for tool in tools.values()]


def register_tools(registry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Register all tools to a registry.

    This is useful for integrating with external tool systems.

    Args:
        registry: Optional existing registry to add tools to

    Returns:
        Registry dictionary with all tools
    """
    if registry is None:
        registry = {}

    tools = get_mom_tools()
    for name, tool in tools.items():
        registry[name] = tool
        register_tool(name, type(tool))

    return registry


class MomTools:
    """
    Collection of tools for Mom agent.

    This is a convenience class that wraps all the individual tools
    and provides a unified interface for tool execution.

    Usage:
        tools = MomTools(working_dir=Path("/project"))
        result = tools.execute("read", {"file_path": "README.md"})
    """

    def __init__(self, working_dir: Optional[Path] = None, **kwargs):
        self.working_dir = working_dir or Path.cwd()
        self._tools = get_mom_tools(self.working_dir, **kwargs)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for LLM."""
        return get_tool_definitions()

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            ToolResult
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}",
            )

        try:
            # Execute based on tool type
            if tool_name == "read":
                result = tool.read(
                    arguments.get("file_path"),
                    offset=arguments.get("offset", 1),
                    limit=arguments.get("limit"),
                )
                return ToolResult.from_read(result)

            elif tool_name == "write":
                result = tool.write(
                    arguments.get("file_path"),
                    arguments.get("content"),
                )
                return ToolResult.from_write(result)

            elif tool_name == "edit":
                result = tool.edit(
                    arguments.get("file_path"),
                    arguments.get("old_string"),
                    arguments.get("new_string"),
                    replace_all=arguments.get("replace_all", False),
                )
                return ToolResult.from_edit(result)

            elif tool_name == "bash":
                result = tool.execute(
                    arguments.get("command"),
                    timeout=arguments.get("timeout"),
                )
                return ToolResult.from_bash(result)

            elif tool_name == "attach":
                result = tool.attach(
                    arguments.get("file_path"),
                    description=arguments.get("description"),
                )
                return ToolResult.from_attach(result)

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Tool not implemented: {tool_name}",
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    # Convenience methods for direct access
    def read(self, file_path: str, offset: int = 1, limit: Optional[int] = None) -> ReadResult:
        """Read a file."""
        return self._tools["read"].read(file_path, offset, limit)

    def write(self, file_path: str, content: str) -> WriteResult:
        """Write to a file."""
        return self._tools["write"].write(file_path, content)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit a file."""
        return self._tools["edit"].edit(file_path, old_string, new_string, replace_all)

    def bash(self, command: str, timeout: Optional[int] = None) -> BashResult:
        """Execute a bash command."""
        return self._tools["bash"].execute(command, timeout)

    def attach(self, file_path: str, description: Optional[str] = None) -> AttachResult:
        """Attach a file."""
        return self._tools["attach"].attach(file_path, description)


# Export all public symbols
__all__ = [
    # Result types
    "ToolResult",
    "ReadResult",
    "WriteResult",
    "EditResult",
    "BashResult",
    "AttachResult",
    "TruncationResult",
    "EditOperation",

    # Tool classes
    "MomTools",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "BashTool",
    "AttachTool",

    # Functions
    "get_mom_tools",
    "get_tool_definitions",
    "register_tools",
    "register_tool",
    "get_registered_tools",

    # Direct tool functions
    "read_file",
    "write_file",
    "edit_file",
    "create_edit",
    "execute_bash",
    "execute_bash_async",
    "attach_file",
    "detect_mime_type",
    "encode_file",

    # Truncation
    "truncate_head",
    "truncate_tail",
    "truncate_output",
    "format_truncation_notice",
    "format_size",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",

    # Supporting types
    "AbortSignal",
]
