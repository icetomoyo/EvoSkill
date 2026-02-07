"""
EvoSkill 核心类型定义

参考 Pi Agent 和 OpenClaw 的事件/消息模型
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Literal, Optional, Union


# ============== 消息类型 ==============


# 使用 dataclass 的 kw_only 参数解决继承问题

@dataclass(kw_only=True)
class ContentBlock:
    """内容块基类"""
    type: str = ""


@dataclass(kw_only=True)
class TextContent(ContentBlock):
    """文本内容"""
    text: str = ""
    type: str = "text"


@dataclass(kw_only=True)
class ThinkingContent(ContentBlock):
    """思考过程内容（如 Claude 的 thinking）"""
    thinking: str = ""
    signature: Optional[str] = None
    type: str = "thinking"


@dataclass(kw_only=True)
class ToolCallContent(ContentBlock):
    """工具调用内容"""
    tool_call_id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    type: str = "tool_call"


@dataclass(kw_only=True)
class ImageContent(ContentBlock):
    """图片内容"""
    source: Union[str, Dict[str, str]] = ""  # URL 或 base64
    media_type: Optional[str] = None
    type: str = "image"


ContentBlockType = Union[TextContent, ThinkingContent, ToolCallContent, ImageContent]


@dataclass
class TokenUsage:
    """Token 使用量统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(kw_only=True)
class Message(ABC):
    """消息基类"""
    id: str = ""
    role: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None  # 支持会话分支


@dataclass(kw_only=True)
class UserMessage(Message):
    """用户消息"""
    content: str = ""
    attachments: List[ImageContent] = field(default_factory=list)
    role: str = "user"


@dataclass(kw_only=True)
class AssistantMessage(Message):
    """助手消息"""
    content: List[ContentBlockType] = field(default_factory=list)
    model: str = ""
    usage: Optional[TokenUsage] = None
    stop_reason: Optional[str] = None  # "stop", "length", "tool_use", "error"
    role: str = "assistant"
    
    @property
    def text(self) -> str:
        """获取文本内容（方便使用）"""
        texts = []
        for block in self.content:
            if isinstance(block, TextContent):
                texts.append(block.text)
        return "".join(texts)


@dataclass(kw_only=True)
class ToolResultMessage(Message):
    """工具执行结果消息"""
    tool_call_id: str = ""
    tool_name: str = ""
    content: List[ContentBlockType] = field(default_factory=list)
    is_error: bool = False
    role: str = "tool"


# ============== 事件类型 ==============


class EventType(Enum):
    """事件类型（参考 Pi Agent）"""
    # 生命周期事件
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    
    # 消息事件
    MESSAGE_START = "message_start"
    MESSAGE_UPDATE = "message_update"
    MESSAGE_END = "message_end"
    
    # 工具事件
    TOOL_EXECUTION_START = "tool_execution_start"
    TOOL_EXECUTION_UPDATE = "tool_execution_update"
    TOOL_EXECUTION_END = "tool_execution_end"
    
    # 上下文事件
    CONTEXT_WARNING = "context_warning"      # 上下文即将达到上限警告
    CONTEXT_COMPACTED = "context_compacted"  # 上下文已压缩
    
    # Skill 事件
    SKILL_CREATED = "skill_created"
    SKILL_UPDATED = "skill_updated"
    SKILL_LOADED = "skill_loaded"
    
    # 系统事件
    AUTO_COMPACTION_START = "auto_compaction_start"
    AUTO_COMPACTION_END = "auto_compaction_end"
    
    # 流式事件
    TEXT_DELTA = "text_delta"
    THINKING_DELTA = "thinking_delta"
    TOOL_CALL_DELTA = "tool_call_delta"


@dataclass
class Event:
    """事件基类"""
    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


# ============== Skill 类型 ==============


@dataclass
class ParameterSchema:
    """工具参数模式"""
    type: str  # string, integer, number, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, ParameterSchema]
    handler: Optional[Callable] = None  # 实际执行函数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 OpenAI 工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {
                            "type": param.type,
                            "description": param.description,
                            **({"enum": param.enum} if param.enum else {}),
                        }
                        for name, param in self.parameters.items()
                    },
                    "required": [
                        name for name, param in self.parameters.items()
                        if param.required
                    ],
                },
            }
        }


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    version: str
    author: str
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Skill:
    """Skill 定义"""
    name: str
    description: str
    tools: List[ToolDefinition]
    metadata: SkillMetadata
    source_path: Path
    readme: str = ""  # SKILL.md 内容
    
    @property
    def all_tools_dict(self) -> Dict[str, ToolDefinition]:
        """获取所有工具的字典"""
        return {tool.name: tool for tool in self.tools}


# ============== 会话元数据 ==============


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    workspace: Path
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    total_tokens_used: int = 0
    skills_loaded: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


# ============== 工具执行相关 ==============


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
    tool_name: str
    content: Any
    is_error: bool = False
    execution_time_ms: Optional[int] = None


# ============== Skill 进化相关 ==============


@dataclass
class NeedAnalysis:
    """需求分析结果"""
    user_need: str
    core_features: List[str]
    inputs: List[str]
    outputs: List[str]
    dependencies: List[str]
    feasible: bool
    reason: Optional[str] = None


@dataclass
class SkillDesign:
    """Skill 设计方案"""
    name: str
    description: str
    tools: List[ToolDefinition]
    file_structure: List[str]
    implementation_plan: str


@dataclass
class GeneratedSkill:
    """生成的 Skill"""
    skill_md: str
    main_code: str
    test_code: str
    requirements: str
    design: SkillDesign


@dataclass
class ValidationResult:
    """验证结果"""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DeployResult:
    """部署结果"""
    success: bool
    skill_path: Optional[Path] = None
    error: Optional[str] = None


# ============== Agent 响应 ==============


@dataclass
class AgentResponse:
    """Agent 响应"""
    message: AssistantMessage
    events: List[Event] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)


# ============== LLM 相关 ==============


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str  # "openai", "anthropic", "kimi-coding", "custom"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    thinking_level: Optional[str] = None  # "low", "medium", "high"
    headers: Optional[Dict[str, str]] = None  # 自定义 HTTP 头（如 User-Agent）


# ============== 流式响应 ==============


@dataclass
class TextDelta:
    """文本增量"""
    content: str
    index: int = 0


@dataclass
class ToolCallDelta:
    """工具调用增量"""
    tool_call_id: str
    name: Optional[str] = None
    arguments_delta: Optional[str] = None


# 类型别名
MessageType = Union[UserMessage, AssistantMessage, ToolResultMessage]
EventStream = AsyncIterator[Event]
