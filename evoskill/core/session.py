"""
Agent 会话管理器

参考 Pi Agent 的 Session 设计
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Callable

from evoskill.core.types import (
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    ToolCallContent,
    ToolCall,
    ToolResult,
    ContentBlock,
    TextContent,
    ThinkingContent,
    Event,
    EventType,
    ToolDefinition,
    Skill,
    SessionMetadata,
    LLMConfig,
    TokenUsage,
)
from evoskill.core.events import EventEmitter
from evoskill.core.llm import create_llm_provider, LLMProvider
from evoskill.core.context_compactor import ContextCompactor, CompactResult


class AgentSession:
    """
    Agent 会话核心类
    
    负责:
    1. 维护对话状态
    2. 管理工具调用
    3. 流式事件输出
    4. 会话持久化
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        workspace: Optional[Path] = None,
        llm_config: Optional[LLMConfig] = None,
        system_prompt: Optional[str] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.workspace = workspace or Path.cwd()
        self.llm_config = llm_config or LLMConfig(provider="openai", model="gpt-4")
        
        # 工具注册
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        
        # 状态（必须在 _default_system_prompt 之前）
        self.messages: List[Message] = []
        self.metadata = SessionMetadata(
            session_id=self.session_id,
            workspace=self.workspace,
        )
        
        # 系统提示词（依赖上面的属性）
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # 事件
        self.events = EventEmitter()
        
        # LLM 提供商
        self._llm_provider: Optional[LLMProvider] = None
        
        # 上下文压缩器
        max_context = getattr(llm_config, 'max_context_tokens', 128000)
        self._compactor = ContextCompactor(
            llm_provider=self.llm_provider,
            max_context_tokens=max_context,
        )
        self._warning_issued = False  # 是否已发出警告
        
        # 统计
        self._total_tokens = 0
    
    @property
    def llm_provider(self) -> LLMProvider:
        """获取或创建 LLM 提供商"""
        if self._llm_provider is None:
            self._llm_provider = create_llm_provider(self.llm_config)
        return self._llm_provider
    
    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        from evoskill.core.prompts import get_full_system_prompt
        
        skills_info = []
        for name, tool_def in self._tools.items():
            skills_info.append({
                "name": name,
                "description": tool_def.description,
                "tools": [{"name": name, "description": tool_def.description}]
            })
        
        return get_full_system_prompt(
            session_id=self.session_id,
            workspace_dir=str(self.workspace),
            skills=skills_info,
            turn_count=self.metadata.message_count,
            include_examples=True,
        )
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
    ) -> None:
        """
        注册工具
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数定义
            handler: 处理函数
        """
        from evoskill.core.types import ParameterSchema
        
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters={
                k: ParameterSchema(
                    type=v.get("type", "string"),
                    description=v.get("description", ""),
                    required=v.get("required", True),
                    default=v.get("default"),
                )
                for k, v in parameters.items()
            },
            handler=handler,
        )
        
        self._tools[name] = tool_def
        self._tool_handlers[name] = handler
    
    def register_skill(self, skill: Skill) -> None:
        """
        注册 Skill
        
        Args:
            skill: Skill 对象
        """
        for tool in skill.tools:
            if tool.handler:
                self._tools[tool.name] = tool
                self._tool_handlers[tool.name] = tool.handler
        
        if skill.name not in self.metadata.skills_loaded:
            self.metadata.skills_loaded.append(skill.name)
    
    async def prompt(
        self,
        user_input: str,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Event]:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入文本
            images: 可选的图片附件
            
        Yields:
            Event 事件流
        """
        # 启动事件系统
        await self.events.start()
        
        try:
            # 0. 检查上下文状态（压缩/警告）
            await self._check_and_compact_context()
            
            # 1. 添加用户消息
            user_msg = UserMessage(
                id=str(uuid.uuid4()),
                content=user_input,
                attachments=images or [],
            )
            self.messages.append(user_msg)
            self.metadata.message_count += 1
            
            # 2. 发射 Agent 开始事件
            await self.events.emit(Event(
                type=EventType.AGENT_START,
                data={"message_count": len(self.messages)}
            ))
            
            # 3. 构建完整的消息列表（包含系统提示词）
            all_messages = self._build_message_list()
            
            # 4. 调用 LLM
            tools_list = list(self._tools.values()) if self._tools else None
            
            current_content: List[ContentBlock] = []
            current_tool_calls: List[ToolCall] = []
            current_tool_call = None
            current_arguments = ""
            
            # 发射消息开始事件
            await self.events.emit(Event(
                type=EventType.MESSAGE_START,
                data={"role": "assistant"}
            ))
            
            async for chunk in self.llm_provider.chat(
                messages=all_messages,
                tools=tools_list,
                stream=True
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "text_delta":
                    # 文本增量
                    content = chunk.get("content", "")
                    current_content.append(TextContent(text=content))
                    
                    await self.events.emit(Event(
                        type=EventType.TEXT_DELTA,
                        data={"content": content}
                    ))
                    
                    yield Event(
                        type=EventType.TEXT_DELTA,
                        data={"content": content}
                    )
                
                elif chunk_type == "thinking_delta":
                    # 思考过程
                    content = chunk.get("content", "")
                    current_content.append(ThinkingContent(thinking=content))
                    
                    await self.events.emit(Event(
                        type=EventType.THINKING_DELTA,
                        data={"content": content}
                    ))
                
                elif chunk_type == "tool_call_start":
                    # 工具调用开始
                    current_tool_call = {
                        "id": chunk.get("tool_call_id"),
                        "name": chunk.get("name"),
                    }
                    current_arguments = ""
                
                elif chunk_type == "tool_call_delta":
                    # 工具调用增量
                    if not current_tool_call:
                        current_tool_call = {
                            "id": chunk.get("tool_call_id"),
                            "name": chunk.get("name"),
                        }
                    
                    args = chunk.get("arguments", "")
                    if args:
                        current_arguments += args
                
                elif chunk_type == "finish":
                    # 完成
                    usage = chunk.get("usage", {})
                    if usage:
                        self._total_tokens += usage.get("input_tokens", 0)
                        self._total_tokens += usage.get("output_tokens", 0)
            
            # 处理工具调用
            if current_tool_call and current_arguments:
                try:
                    args = json.loads(current_arguments) if current_arguments else {}
                except json.JSONDecodeError:
                    args = {}
                
                tool_call = ToolCall(
                    id=current_tool_call["id"],
                    name=current_tool_call["name"],
                    arguments=args
                )
                current_tool_calls.append(tool_call)
                
                # 添加到内容块
                current_content.append(ToolCallContent(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    arguments=tool_call.arguments
                ))
            
            # 5. 创建助手消息
            assistant_msg = AssistantMessage(
                id=str(uuid.uuid4()),
                content=current_content,
                model=self.llm_config.model,
                usage=TokenUsage(
                    input_tokens=0,  # 需要实际统计
                    output_tokens=0
                ),
            )
            self.messages.append(assistant_msg)
            
            # 发射消息结束事件
            await self.events.emit(Event(
                type=EventType.MESSAGE_END,
                data={"message": assistant_msg}
            ))
            
            yield Event(
                type=EventType.MESSAGE_END,
                data={"message": assistant_msg}
            )
            
            # 6. 执行工具调用
            for tool_call in current_tool_calls:
                async for event in self._execute_tool(tool_call):
                    yield event
            
            # 7. Agent 结束
            await self.events.emit(Event(
                type=EventType.AGENT_END,
                data={"message_count": len(self.messages)}
            ))
            
            yield Event(
                type=EventType.AGENT_END,
                data={"message_count": len(self.messages)}
            )
            
        finally:
            await self.events.stop()
    
    async def _execute_tool(self, tool_call: ToolCall) -> AsyncIterator[Event]:
        """
        执行工具调用
        
        Args:
            tool_call: 工具调用信息
            
        Yields:
            Event 事件
        """
        tool_name = tool_call.name
        
        # 发射工具执行开始事件
        event = Event(
            type=EventType.TOOL_EXECUTION_START,
            data={
                "tool_call_id": tool_call.id,
                "tool_name": tool_name,
                "arguments": tool_call.arguments
            }
        )
        await self.events.emit(event)
        yield event
        
        # 查找工具处理器
        handler = self._tool_handlers.get(tool_name)
        
        if not handler:
            # 工具不存在
            error_result = ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                content=f"Error: Tool '{tool_name}' not found",
                is_error=True
            )
        else:
            try:
                # 执行工具
                import inspect
                if inspect.iscoroutinefunction(handler):
                    result = await handler(**tool_call.arguments)
                else:
                    result = handler(**tool_call.arguments)
                
                # 格式化结果
                if isinstance(result, str):
                    content = result
                elif isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    content = str(result)
                
                error_result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=content,
                    is_error=False
                )
            
            except Exception as e:
                error_result = ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=f"Error: {str(e)}",
                    is_error=True
                )
        
        # 添加工具结果到消息历史
        tool_result_msg = ToolResultMessage(
            id=str(uuid.uuid4()),
            tool_call_id=error_result.tool_call_id,
            tool_name=error_result.tool_name,
            content=[TextContent(text=str(error_result.content))],
            is_error=error_result.is_error
        )
        self.messages.append(tool_result_msg)
        
        # 发射工具执行结束事件
        event = Event(
            type=EventType.TOOL_EXECUTION_END,
            data={
                "tool_call_id": tool_call.id,
                "tool_name": tool_name,
                "result": error_result,
                "is_error": error_result.is_error
            }
        )
        await self.events.emit(event)
        yield event
    
    def _build_message_list(self) -> List[Message]:
        """构建完整的消息列表（包含系统提示词）"""
        from evoskill.core.types import Message as BaseMessage
        
        # 系统消息作为特殊的 user/assistant 对
        messages = []
        
        if self.system_prompt:
            # 系统提示词作为第一条消息
            messages.append(UserMessage(
                id="system_prompt",
                content=f"[System]\n{self.system_prompt}",
            ))
            messages.append(AssistantMessage(
                id="system_ack",
                content=[TextContent(text="Got it. I'll follow these instructions.")],
                model="system",
            ))
        
        messages.extend(self.messages)
        return messages
    
    async def _check_and_compact_context(self) -> None:
        """
        检查上下文状态，必要时执行压缩
        
        策略：
        - 75%: 发出警告（只警告一次）
        - 80%: 自动执行压缩
        """
        if not self.messages:
            return
        
        status = self._compactor.check_status(self.messages)
        
        # 检查是否达到压缩阈值（80%）
        if status["should_compact"]:
            await self.events.emit(Event(
                type=EventType.CONTEXT_WARNING,
                data={
                    "message": "上下文即将达到上限，正在自动压缩...",
                    "current_tokens": status["current_tokens"],
                    "max_tokens": status["max_tokens"],
                    "ratio": status["current_ratio"],
                }
            ))
            
            try:
                # 执行压缩
                result = await self._compactor.compact(
                    messages=self.messages,
                    system_prompt=self.system_prompt,
                    tools=list(self._tools.values()),
                )
                
                # 替换消息列表
                self.messages = result.new_messages
                self._warning_issued = False  # 重置警告状态
                
                # 发送压缩完成事件
                await self.events.emit(Event(
                    type=EventType.CONTEXT_COMPACTED,
                    data={
                        "original_tokens": result.original_token_count,
                        "new_tokens": result.new_token_count,
                        "saved_ratio": result.saved_ratio,
                        "compacted_count": result.compacted_count,
                        "summary": result.summary[:200] + "..." if len(result.summary) > 200 else result.summary,
                    }
                ))
                
            except Exception as e:
                # 压缩失败，发送警告
                await self.events.emit(Event(
                    type=EventType.CONTEXT_WARNING,
                    data={
                        "message": f"上下文压缩失败: {e}",
                        "current_tokens": status["current_tokens"],
                        "max_tokens": status["max_tokens"],
                    }
                ))
        
        # 检查是否达到警告阈值（75%），且未发出过警告
        elif status["should_warn"] and not self._warning_issued:
            warning_msg = self._compactor.get_warning_message(status)
            
            await self.events.emit(Event(
                type=EventType.CONTEXT_WARNING,
                data={
                    "message": warning_msg,
                    "current_tokens": status["current_tokens"],
                    "max_tokens": status["max_tokens"],
                    "ratio": status["current_ratio"],
                    "will_compact_at": self._compactor.compact_threshold,
                }
            ))
            
            self._warning_issued = True
    
    async def save(self, path: Optional[Path] = None) -> Path:
        """
        保存会话到文件
        
        Args:
            path: 保存路径，默认使用 workspace/.evoskill/sessions/
            
        Returns:
            保存的文件路径
        """
        if path is None:
            path = self.workspace / ".evoskill" / "sessions" / f"{self.session_id}.jsonl"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            for msg in self.messages:
                f.write(json.dumps(self._message_to_dict(msg), ensure_ascii=False) + "\n")
        
        return path
    
    async def load(self, path: Path) -> None:
        """
        从文件加载会话
        
        Args:
            path: 会话文件路径
        """
        self.messages = []
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                data = json.loads(line)
                msg = self._dict_to_message(data)
                if msg:
                    self.messages.append(msg)
    
    def _message_to_dict(self, msg: Message) -> Dict[str, Any]:
        """将消息转换为字典"""
        return {
            "id": msg.id,
            "role": msg.role,
            "timestamp": msg.timestamp.isoformat(),
            "parent_id": msg.parent_id,
            "data": msg.__dict__
        }
    
    def _dict_to_message(self, data: Dict[str, Any]) -> Optional[Message]:
        """将字典转换为消息"""
        # 简化的实现，实际需要完整解析
        role = data.get("role")
        msg_data = data.get("data", {})
        
        if role == "user":
            return UserMessage(
                id=data.get("id", ""),
                content=msg_data.get("content", ""),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                parent_id=data.get("parent_id"),
            )
        elif role == "assistant":
            # 简化处理
            return AssistantMessage(
                id=data.get("id", ""),
                content=[TextContent(text="[Loaded from session]")],
                model=msg_data.get("model", "unknown"),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                parent_id=data.get("parent_id"),
            )
        
        return None
    
    async def compact(self, custom_instructions: Optional[str] = None) -> None:
        """
        压缩上下文
        
        Args:
            custom_instructions: 自定义压缩指令
        """
        # TODO: 实现上下文压缩
        pass
    
    def get_history(self, limit: Optional[int] = None) -> List[Message]:
        """
        获取对话历史
        
        Args:
            limit: 限制返回的消息数量
            
        Returns:
            消息列表
        """
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.messages = []
