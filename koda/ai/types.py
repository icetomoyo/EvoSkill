"""
Koda AI Types - 完整类型定义
等效于 Pi Mono 的 packages/ai/src/types.ts
"""
from typing import Literal, TypedDict, Optional, List, Union, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class KnownApi(Enum):
    """支持的 API 类型"""
    OPENAI_COMPLETIONS = "openai-completions"
    OPENAI_RESPONSES = "openai-responses"
    AZURE_OPENAI_RESPONSES = "azure-openai-responses"
    OPENAI_CODEX_RESPONSES = "openai-codex-responses"
    ANTHROPIC_MESSAGES = "anthropic-messages"
    BEDROCK_CONVERSE_STREAM = "bedrock-converse-stream"
    GOOGLE_GENERATIVE_AI = "google-generative-ai"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    GOOGLE_VERTEX = "google-vertex"


class KnownProvider(Enum):
    """已知的 Provider"""
    AMAZON_BEDROCK = "amazon-bedrock"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    GOOGLE_ANTIGRAVITY = "google-antigravity"
    GOOGLE_VERTEX = "google-vertex"
    OPENAI = "openai"
    AZURE_OPENAI = "azure-openai-responses"
    OPENAI_CODEX = "openai-codex"
    GITHUB_COPILOT = "github-copilot"
    XAI = "xai"
    GROQ = "groq"
    CEREBRAS = "cerebras"
    OPENROUTER = "openrouter"
    VERCEL_AI_GATEWAY = "vercel-ai-gateway"
    ZAI = "zai"
    MISTRAL = "mistral"
    MINIMAX = "minimax"
    MINIMAX_CN = "minimax-cn"
    HUGGINGFACE = "huggingface"
    OPENCODE = "opencode"
    KIMI_CODING = "kimi-coding"


class ThinkingLevel(Enum):
    """思考级别"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class CacheRetention(Enum):
    """缓存保留策略"""
    NONE = "none"
    SHORT = "short"
    LONG = "long"


class StopReason(Enum):
    """停止原因"""
    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "toolUse"
    ERROR = "error"
    ABORTED = "aborted"


@dataclass
class OpenRouterRouting:
    """OpenRouter 路由偏好"""
    only: Optional[List[str]] = None
    order: Optional[List[str]] = None


@dataclass
class VercelGatewayRouting:
    """Vercel AI Gateway 路由偏好"""
    only: Optional[List[str]] = None
    order: Optional[List[str]] = None


@dataclass
class OpenAICompletionsCompat:
    """OpenAI 兼容 API 设置"""
    supports_store: Optional[bool] = None
    supports_developer_role: Optional[bool] = None
    supports_reasoning_effort: Optional[bool] = None
    supports_usage_in_streaming: Optional[bool] = True
    max_tokens_field: Optional[Literal["max_completion_tokens", "max_tokens"]] = None
    requires_tool_result_name: Optional[bool] = None
    requires_assistant_after_tool_result: Optional[bool] = None
    requires_thinking_as_text: Optional[bool] = None
    requires_mistral_tool_ids: Optional[bool] = None
    thinking_format: Optional[Literal["openai", "zai", "qwen"]] = "openai"
    open_router_routing: Optional[OpenRouterRouting] = None
    vercel_gateway_routing: Optional[VercelGatewayRouting] = None
    supports_strict_mode: Optional[bool] = True


@dataclass
class OpenAIResponsesCompat:
    """OpenAI Responses API 兼容设置"""
    pass


@dataclass
class ThinkingBudgets:
    """思考级别 token 预算"""
    minimal: Optional[int] = None
    low: Optional[int] = None
    medium: Optional[int] = None
    high: Optional[int] = None


@dataclass
class Usage:
    """Token 使用统计"""
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost: Dict[str, float] = field(default_factory=lambda: {
        "input": 0.0,
        "output": 0.0,
        "cache_read": 0.0,
        "cache_write": 0.0,
        "total": 0.0
    })
    
    def calculate_cost(self, model_cost: Dict[str, float]) -> None:
        """根据模型成本计算总成本"""
        self.cost["input"] = (model_cost.get("input", 0) / 1000000) * self.input
        self.cost["output"] = (model_cost.get("output", 0) / 1000000) * self.output
        self.cost["cache_read"] = (model_cost.get("cache_read", 0) / 1000000) * self.cache_read
        self.cost["cache_write"] = (model_cost.get("cache_write", 0) / 1000000) * self.cache_write
        self.cost["total"] = (
            self.cost["input"] + 
            self.cost["output"] + 
            self.cost["cache_read"] + 
            self.cost["cache_write"]
        )


@dataclass
class TextContent:
    """文本内容"""
    type: Literal["text"] = "text"
    text: str = ""
    text_signature: Optional[str] = None  # 如 OpenAI 的 message ID


@dataclass
class ThinkingContent:
    """思考内容"""
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    thinking_signature: Optional[str] = None  # 如 OpenAI 的 reasoning item ID


@dataclass
class ImageContent:
    """图片内容"""
    type: Literal["image"] = "image"
    data: str = ""  # base64 编码
    mime_type: str = ""  # image/jpeg, image/png, image/gif, image/webp


@dataclass
class ToolCall:
    """工具调用"""
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    thought_signature: Optional[str] = None  # Google 特定的思考上下文签名


Content = Union[TextContent, ThinkingContent, ImageContent, ToolCall]


@dataclass
class UserMessage:
    """用户消息"""
    role: Literal["user"] = "user"
    content: Union[str, List[Union[TextContent, ImageContent]]] = field(default_factory=str)
    timestamp: int = 0


@dataclass
class AssistantMessage:
    """助手消息"""
    role: Literal["assistant"] = "assistant"
    content: List[Content] = field(default_factory=list)
    api: str = ""
    provider: str = ""
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_reason: StopReason = StopReason.STOP
    error_message: Optional[str] = None
    timestamp: int = 0


@dataclass
class ToolResultMessage:
    """工具结果消息"""
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: List[Union[TextContent, ImageContent]] = field(default_factory=list)
    details: Optional[Dict[str, Any]] = None
    is_error: bool = False
    timestamp: int = 0


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


@dataclass
class Context:
    """对话上下文"""
    system_prompt: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    tools: Optional[List[Tool]] = None


@dataclass
class StreamOptions:
    """流式选项基础"""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    signal: Optional[Any] = None  # AbortSignal
    api_key: Optional[str] = None
    cache_retention: CacheRetention = CacheRetention.SHORT
    session_id: Optional[str] = None
    on_payload: Optional[Callable[[Any], None]] = None
    headers: Optional[Dict[str, str]] = None
    max_retry_delay_ms: int = 60000


@dataclass
class SimpleStreamOptions(StreamOptions):
    """简化流式选项"""
    reasoning: Optional[ThinkingLevel] = None
    thinking_budgets: Optional[ThinkingBudgets] = None


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    api: str
    provider: str
    base_url: str
    reasoning: bool = False
    input: List[Literal["text", "image"]] = field(default_factory=lambda: ["text"])
    cost: Dict[str, float] = field(default_factory=lambda: {
        "input": 0.0,
        "output": 0.0,
        "cache_read": 0.0,
        "cache_write": 0.0
    })
    context_window: int = 128000
    max_tokens: int = 16384
    headers: Optional[Dict[str, str]] = None
    compat: Optional[Union[OpenAICompletionsCompat, OpenAIResponsesCompat]] = None


# 事件流类型
@dataclass
class AssistantMessageEvent:
    """助手消息事件"""
    type: str  # start, text_start, text_delta, text_end, thinking_start, thinking_delta, thinking_end, toolcall_start, toolcall_delta, toolcall_end, done, error
    partial: Optional[AssistantMessage] = None
    content_index: Optional[int] = None
    delta: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    reason: Optional[StopReason] = None
    error: Optional[Exception] = None


# 工具相关类型
@dataclass
class AgentTool:
    """Agent 工具"""
    name: str
    label: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable[..., Any]


# Agent 事件类型
class AgentEventType(Enum):
    """Agent 事件类型"""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Agent 事件"""
    type: AgentEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0
