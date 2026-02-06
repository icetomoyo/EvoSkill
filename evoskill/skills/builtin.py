"""
内置工具集

提供基础的文件、代码、网络等工具
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from evoskill.core.session import AgentSession


async def read_file(path: str, offset: int = 0, limit: Optional[int] = None) -> str:
    """
    读取文件内容
    
    Args:
        path: 文件路径（相对工作区或绝对路径）
        offset: 起始行号（0-based）
        limit: 最大读取行数
        
    Returns:
        文件内容
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            lines = await f.readlines()
            
            if offset > 0:
                lines = lines[offset:]
            if limit:
                lines = lines[:limit]
            
            return "".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"


async def write_file(path: str, content: str, append: bool = False) -> str:
    """
    写入文件
    
    Args:
        path: 文件路径
        content: 文件内容
        append: 是否追加模式
        
    Returns:
        操作结果
    """
    file_path = Path(path)
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "a" if append else "w"
        async with aiofiles.open(file_path, mode, encoding="utf-8") as f:
            await f.write(content)
        
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


async def list_dir(path: str = ".", recursive: bool = False) -> str:
    """
    列出目录内容
    
    Args:
        path: 目录路径
        recursive: 是否递归列出
        
    Returns:
        目录内容列表
    """
    dir_path = Path(path)
    
    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        items = []
        
        if recursive:
            for item in dir_path.rglob("*"):
                rel_path = item.relative_to(dir_path)
                item_type = "📁" if item.is_dir() else "📄"
                items.append(f"{item_type} {rel_path}")
        else:
            for item in sorted(dir_path.iterdir()):
                item_type = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    size_bytes = item.stat().st_size
                    if size_bytes < 1024:
                        size = f" ({size_bytes}B)"
                    elif size_bytes < 1024 * 1024:
                        size = f" ({size_bytes / 1024:.1f}KB)"
                    else:
                        size = f" ({size_bytes / (1024 * 1024):.1f}MB)"
                
                items.append(f"{item_type} {item.name}{size}")
        
        return "\n".join(items) if items else "(empty directory)"
    
    except Exception as e:
        return f"Error listing directory: {e}"


async def search_files(
    pattern: str,
    path: str = ".",
    file_pattern: Optional[str] = None
) -> str:
    """
    搜索文件内容
    
    Args:
        pattern: 搜索模式（支持简单字符串匹配）
        path: 搜索路径
        file_pattern: 文件过滤模式（如 "*.py"）
        
    Returns:
        搜索结果
    """
    import fnmatch
    
    search_path = Path(path)
    results = []
    
    try:
        for root, dirs, files in os.walk(search_path):
            for filename in files:
                if file_pattern and not fnmatch.fnmatch(filename, file_pattern):
                    continue
                
                file_path = Path(root) / filename
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                        if pattern in content:
                            lines = content.split("\n")
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    rel_path = file_path.relative_to(search_path)
                                    results.append(f"{rel_path}:{i}: {line.strip()}")
                                    
                                    # 限制结果数量
                                    if len(results) >= 20:
                                        results.append("... (results truncated)")
                                        return "\n".join(results)
                
                except Exception:
                    continue
        
        return "\n".join(results) if results else f"No matches found for '{pattern}'"
    
    except Exception as e:
        return f"Error searching files: {e}"


async def execute_command(command: str, cwd: Optional[str] = None) -> str:
    """
    执行 shell 命令
    
    ⚠️ 危险操作，需要用户确认
    
    Args:
        command: 命令字符串
        cwd: 工作目录
        
    Returns:
        命令输出
    """
    import asyncio
    
    # 安全检查
    dangerous_commands = ["rm -rf /", "> /dev/sda", "dd if=/dev/zero"]
    for dangerous in dangerous_commands:
        if dangerous in command:
            return f"Error: Dangerous command blocked: {command}"
    
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        stdout, stderr = await proc.communicate()
        
        output = []
        if stdout:
            output.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            output.append("[stderr]\n" + stderr.decode("utf-8", errors="replace"))
        
        return "\n".join(output) or "(no output)"
    
    except Exception as e:
        return f"Error executing command: {e}"


async def view_code(
    path: str,
    view_range: Optional[List[int]] = None
) -> str:
    """
    查看代码文件，带行号
    
    Args:
        path: 文件路径
        view_range: 行号范围 [start, end]
        
    Returns:
        带行号的代码
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if view_range:
            start, end = view_range
            lines = lines[start - 1:end]
            line_offset = start - 1
        else:
            line_offset = 0
        
        # 添加行号
        result = []
        for i, line in enumerate(lines, line_offset + 1):
            result.append(f"{i:4d} | {line.rstrip()}")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error viewing code: {e}"


async def edit_code(
    path: str,
    old_string: str,
    new_string: str
) -> str:
    """
    编辑代码（SEARCH/REPLACE 风格）
    
    Args:
        path: 文件路径
        old_string: 要替换的旧代码
        new_string: 新代码
        
    Returns:
        操作结果
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if old_string not in content:
            return f"Error: Could not find the specified text in {path}"
        
        new_content = content.replace(old_string, new_string, 1)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return f"Successfully edited {path}"
    
    except Exception as e:
        return f"Error editing code: {e}"


async def fetch_url(url: str) -> str:
    """
    获取网页内容
    
    Args:
        url: URL 地址
        
    Returns:
        网页内容
    """
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    # 限制返回长度
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (content truncated)"
                    return content
                else:
                    return f"Error: HTTP {response.status}"
    
    except ImportError:
        return "Error: aiohttp not installed. Run: pip install aiohttp"
    except Exception as e:
        return f"Error fetching URL: {e}"


def register_builtin_tools(session: AgentSession) -> None:
    """
    注册所有内置工具到会话
    
    Args:
        session: Agent 会话实例
    """
    # 文件操作工具
    session.register_tool(
        name="read_file",
        description="读取文件内容，支持指定行号范围",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径（相对工作区或绝对路径）",
                "required": True
            },
            "offset": {
                "type": "integer",
                "description": "起始行号（0-based）",
                "required": False,
                "default": 0
            },
            "limit": {
                "type": "integer",
                "description": "最大读取行数",
                "required": False
            }
        },
        handler=read_file
    )
    
    session.register_tool(
        name="write_file",
        description="写入文件内容，自动创建目录",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径",
                "required": True
            },
            "content": {
                "type": "string",
                "description": "文件内容",
                "required": True
            },
            "append": {
                "type": "boolean",
                "description": "是否追加模式",
                "required": False,
                "default": False
            }
        },
        handler=write_file
    )
    
    session.register_tool(
        name="list_dir",
        description="列出目录内容",
        parameters={
            "path": {
                "type": "string",
                "description": "目录路径",
                "required": False,
                "default": "."
            },
            "recursive": {
                "type": "boolean",
                "description": "是否递归列出",
                "required": False,
                "default": False
            }
        },
        handler=list_dir
    )
    
    session.register_tool(
        name="search_files",
        description="在文件中搜索内容",
        parameters={
            "pattern": {
                "type": "string",
                "description": "搜索模式",
                "required": True
            },
            "path": {
                "type": "string",
                "description": "搜索路径",
                "required": False,
                "default": "."
            },
            "file_pattern": {
                "type": "string",
                "description": "文件过滤模式（如 '*.py'）",
                "required": False
            }
        },
        handler=search_files
    )
    
    # 代码工具
    session.register_tool(
        name="view_code",
        description="查看代码文件，带行号",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径",
                "required": True
            },
            "view_range": {
                "type": "array",
                "description": "行号范围 [start, end]",
                "required": False
            }
        },
        handler=view_code
    )
    
    session.register_tool(
        name="edit_code",
        description="编辑代码文件（SEARCH/REPLACE 风格）",
        parameters={
            "path": {
                "type": "string",
                "description": "文件路径",
                "required": True
            },
            "old_string": {
                "type": "string",
                "description": "要替换的旧代码",
                "required": True
            },
            "new_string": {
                "type": "string",
                "description": "新代码",
                "required": True
            }
        },
        handler=edit_code
    )
    
    # 网络工具
    session.register_tool(
        name="fetch_url",
        description="获取网页内容",
        parameters={
            "url": {
                "type": "string",
                "description": "URL 地址",
                "required": True
            }
        },
        handler=fetch_url
    )
    
    # Shell 工具（谨慎使用）
    session.register_tool(
        name="execute_command",
        description="执行 shell 命令（⚠️ 谨慎使用）",
        parameters={
            "command": {
                "type": "string",
                "description": "命令字符串",
                "required": True
            },
            "cwd": {
                "type": "string",
                "description": "工作目录",
                "required": False
            }
        },
        handler=execute_command
    )
