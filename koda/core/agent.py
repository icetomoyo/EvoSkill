"""
Koda Agent - Pi Coding Agent 的 Python 实现

极简设计：
- 只负责 Agent 循环
- 工具调用
- 会话管理
- 无验证、无扩展、无计划模式
"""
import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, AsyncIterator, Union

from koda.tools.file_tool import FileTool
from koda.tools.shell_tool import ShellTool
from koda.tools.grep_tool import GrepTool
from koda.tools.find_tool import FindTool
from koda.tools.ls_tool import LsTool


@dataclass
class Message:
    """消息基类"""
    id: str
    role: str  # "user", "assistant", "system", "tool"
    content: Any
    parent_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(**data)


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_call_id: str
    name: str
    output: str
    error: Optional[str] = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable


class Session:
    """
    会话管理 - JSONL 格式 + 树状结构
    
    参考 Pi Coding Agent 的会话设计
    """
    
    def __init__(self, session_id: Optional[str] = None, workspace: Optional[Path] = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.workspace = workspace or Path.cwd()
        self.messages: List[Message] = []
        self.current_branch: str = "main"
        
        # 会话文件路径
        self._session_dir = Path.home() / ".koda" / "sessions"
        self._session_file = self._session_dir / f"{self.session_id}.jsonl"
    
    def add_message(self, role: str, content: Any, parent_id: Optional[str] = None) -> Message:
        """添加消息"""
        msg = Message(
            id=str(uuid.uuid4())[:8],
            role=role,
            content=content,
            parent_id=parent_id or (self.messages[-1].id if self.messages else None),
        )
        self.messages.append(msg)
        self._save()
        return msg
    
    def _save(self) -> None:
        """保存到 JSONL"""
        self._session_dir.mkdir(parents=True, exist_ok=True)
        with open(self._session_file, "w", encoding="utf-8") as f:
            for msg in self.messages:
                f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")
    
    @classmethod
    def load(cls, session_id: str) -> "Session":
        """从 JSONL 加载会话"""
        session = cls(session_id)
        if session._session_file.exists():
            with open(session._session_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        session.messages.append(Message.from_dict(data))
        return session
    
    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取消息历史（用于 LLM 调用）"""
        history = []
        for msg in self.messages[-limit:]:
            if msg.role == "tool":
                history.append({
                    "role": "tool",
                    "tool_call_id": msg.content.get("tool_call_id"),
                    "content": msg.content.get("output", ""),
                })
            elif msg.role == "assistant" and isinstance(msg.content, dict) and "tool_calls" in msg.content:
                history.append({
                    "role": "assistant",
                    "content": msg.content.get("text", ""),
                    "tool_calls": msg.content.get("tool_calls", []),
                })
            else:
                history.append({
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                })
        return history
    
    def fork(self, message_id: str, new_session_id: Optional[str] = None) -> "Session":
        """从指定消息创建分支"""
        new_session = Session(new_session_id, self.workspace)
        
        # 找到 message_id 之前的所有消息
        for msg in self.messages:
            new_session.messages.append(msg)
            if msg.id == message_id:
                break
        
        new_session._save()
        return new_session


class Agent:
    """
    Koda Agent - 极简 Agent 实现
    
    核心功能：
    1. 工具注册与调用
    2. 会话管理
    3. LLM 交互（通过外部传入）
    """
    
    def __init__(
        self,
        llm_provider: Any,
        workspace: Optional[Path] = None,
        session: Optional[Session] = None,
        tools: Optional[List[str]] = None,
    ):
        self.llm = llm_provider
        self.workspace = workspace or Path.cwd()
        self.session = session or Session(workspace=self.workspace)
        
        # 工具注册
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_builtin_tools(tools or ["read", "write", "edit", "bash"])
    
    def _register_builtin_tools(self, tool_names: List[str]) -> None:
        """注册内置工具"""
        file_tool = FileTool()
        shell_tool = ShellTool()
        grep_tool = GrepTool()
        find_tool = FindTool()
        ls_tool = LsTool()
        
        tool_map = {
            "read": ToolDefinition(
                name="read",
                description="Read file contents. Use @ to reference files in the message.",
                parameters={
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "offset": {"type": "integer", "description": "Line offset to start reading", "default": 1},
                    "limit": {"type": "integer", "description": "Number of lines to read", "default": 100},
                },
                handler=file_tool.read,
            ),
            "write": ToolDefinition(
                name="write",
                description="Write content to a file. Creates parent directories if needed.",
                parameters={
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                handler=file_tool.write,
            ),
            "edit": ToolDefinition(
                name="edit",
                description="Edit a file by replacing text. Use for small changes.",
                parameters={
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "old_string": {"type": "string", "description": "Text to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                handler=file_tool.edit,
            ),
            "bash": ToolDefinition(
                name="bash",
                description="Execute a bash command. Use !command to run and send output to LLM.",
                parameters={
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 60},
                },
                handler=shell_tool.execute,
            ),
            "grep": ToolDefinition(
                name="grep",
                description="Search for patterns in files",
                parameters={
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "path": {"type": "string", "description": "Directory or file to search"},
                },
                handler=grep_tool.search,
            ),
            "find": ToolDefinition(
                name="find",
                description="Find files by name pattern",
                parameters={
                    "path": {"type": "string", "description": "Directory to search"},
                    "pattern": {"type": "string", "description": "File name pattern", "default": "*"},
                },
                handler=find_tool.find,
            ),
            "ls": ToolDefinition(
                name="ls",
                description="List directory contents",
                parameters={
                    "path": {"type": "string", "description": "Directory path", "default": "."},
                },
                handler=ls_tool.list,
            ),
        }
        
        for name in tool_names:
            if name in tool_map:
                self.tools[name] = tool_map[name]
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取工具定义（用于 LLM）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": [k for k, v in tool.parameters.items() if isinstance(v, dict) and "default" not in v],
                    },
                },
            }
            for tool in self.tools.values()
        ]
    
    async def run(self, user_input: str) -> AsyncIterator[Dict[str, Any]]:
        """
        运行 Agent 循环
        
        1. 添加用户消息
        2. 调用 LLM
        3. 处理工具调用
        4. 返回结果
        """
        # 添加用户消息
        self.session.add_message("user", user_input)
        
        max_iterations = 10
        for iteration in range(max_iterations):
            # 构建消息
            messages = self._build_messages()
            
            # 调用 LLM
            response = await self._call_llm(messages)
            
            # 检查是否有工具调用
            if "tool_calls" in response and response["tool_calls"]:
                # 添加助手消息
                self.session.add_message("assistant", response)
                
                # 执行工具
                for tool_call in response["tool_calls"]:
                    result = await self._execute_tool(tool_call)
                    self.session.add_message("tool", {
                        "tool_call_id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "output": result,
                    })
                    
                    yield {
                        "type": "tool_execution",
                        "tool": tool_call["function"]["name"],
                        "result": result,
                    }
            else:
                # 直接返回文本响应
                content = response.get("content", "")
                self.session.add_message("assistant", content)
                
                yield {"type": "message", "content": content}
                break
    
    def _build_messages(self) -> List[Dict[str, Any]]:
        """构建 LLM 消息"""
        # 系统提示词
        system_prompt = self._load_system_prompt()
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.session.get_message_history())
        
        return messages
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        # 加载 AGENTS.md
        agents_content = self._load_agents_md()
        
        base_prompt = f"""You are Koda, a helpful coding assistant.

You have access to the following tools:
{self._format_tools()}

Working directory: {self.workspace}

Rules:
1. Use tools to accomplish tasks
2. Always verify file contents after editing
3. Use bash for file operations when appropriate
4. Reference files with @filename in messages

{agents_content}
"""
        return base_prompt
    
    def _format_tools(self) -> str:
        """格式化工具列表"""
        lines = []
        for tool in self.tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)
    
    def _load_agents_md(self) -> str:
        """加载 AGENTS.md 文件"""
        content = []
        
        # 全局 AGENTS.md
        global_agents = Path.home() / ".koda" / "AGENTS.md"
        if global_agents.exists():
            content.append(global_agents.read_text(encoding="utf-8"))
        
        # 工作目录 AGENTS.md
        local_agents = self.workspace / "AGENTS.md"
        if local_agents.exists():
            content.append(local_agents.read_text(encoding="utf-8"))
        
        return "\n\n".join(content) if content else ""
    
    async def _call_llm(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用 LLM"""
        # 这里应该调用外部 LLM provider
        # 简化实现：返回一个模拟响应
        if hasattr(self.llm, 'chat'):
            return await self.llm.chat(messages, tools=self.get_tool_definitions())
        
        # 默认模拟响应
        return {"content": "I'm a mock LLM. Please provide a real LLM provider."}
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """执行工具"""
        function = tool_call.get("function", {})
        name = function.get("name")
        arguments = json.loads(function.get("arguments", "{}"))
        
        if name not in self.tools:
            return f"Error: Tool '{name}' not found"
        
        tool = self.tools[name]
        
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            
            # 处理结果
            if hasattr(result, 'output'):
                return result.output
            elif hasattr(result, 'content'):
                return result.content
            else:
                return str(result)
                
        except Exception as e:
            return f"Error: {str(e)}"


# 导入 asyncio 用于类型检查
import asyncio
