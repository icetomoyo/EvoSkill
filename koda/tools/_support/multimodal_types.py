"""
Multimodal Types - Pi AI compatible type system

Complete implementation of Pi's type system for multimodal LLM support.
Based on: packages/ai/src/types.ts
"""
from typing import Literal, Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum


class StopReason(Enum):
    """Reason why the assistant stopped generating"""
    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "toolUse"
    ERROR = "error"
    ABORTED = "aborted"


class ThinkingLevel(Enum):
    """Thinking/reasoning levels"""
    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class CacheRetention(Enum):
    """Prompt cache retention preference"""
    NONE = "none"
    SHORT = "short"
    LONG = "long"


# ============================================================================
# Content Blocks
# ============================================================================

@dataclass
class TextContent:
    """Text content block - Pi compatible"""
    type: Literal["text"] = "text"
    text: str = ""
    textSignature: Optional[str] = None  # e.g., for OpenAI responses, the message ID


@dataclass
class ThinkingContent:
    """Thinking/reasoning content block"""
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    thinkingSignature: Optional[str] = None  # e.g., for OpenAI responses, the reasoning item ID


@dataclass
class ImageContent:
    """Image content block - Pi compatible"""
    type: Literal["image"] = "image"
    data: str = ""  # base64 encoded image data
    mimeType: str = ""  # e.g., "image/jpeg", "image/png"


@dataclass
class ToolCall:
    """Tool call content block"""
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    thoughtSignature: Optional[str] = None  # Google-specific: opaque signature for reusing thought context


# Content block union type
ContentBlock = Union[TextContent, ThinkingContent, ImageContent, ToolCall]


# ============================================================================
# Usage and Cost
# ============================================================================

@dataclass
class CostBreakdown:
    """Cost breakdown per token type"""
    input: float = 0.0
    output: float = 0.0
    cacheRead: float = 0.0
    cacheWrite: float = 0.0
    total: float = 0.0


@dataclass
class Usage:
    """Token usage statistics"""
    input: int = 0
    output: int = 0
    cacheRead: int = 0
    cacheWrite: int = 0
    totalTokens: int = 0
    cost: CostBreakdown = field(default_factory=CostBreakdown)


# ============================================================================
# Messages
# ============================================================================

@dataclass
class UserMessage:
    """User message - supports text and multimodal content"""
    role: Literal["user"] = "user"
    content: Union[str, List[Union[TextContent, ImageContent]]] = field(default_factory=str)
    timestamp: int = 0  # Unix timestamp in milliseconds


@dataclass
class AssistantMessage:
    """Assistant message - supports text, thinking, and tool calls"""
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextContent, ThinkingContent, ToolCall]] = field(default_factory=list)
    api: str = ""  # Api type
    provider: str = ""  # Provider name
    model: str = ""  # Model ID
    usage: Usage = field(default_factory=Usage)
    stopReason: StopReason = StopReason.STOP
    errorMessage: Optional[str] = None
    timestamp: int = 0


@dataclass
class ToolResultMessage:
    """Tool result message - supports text and images"""
    role: Literal["toolResult"] = "toolResult"
    toolCallId: str = ""
    toolName: str = ""
    content: List[Union[TextContent, ImageContent]] = field(default_factory=list)
    details: Optional[Any] = None
    isError: bool = False
    timestamp: int = 0


# Message union type
Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


# ============================================================================
# Custom Message Types (Coding Agent specific)
# ============================================================================

@dataclass
class BashExecutionMessage:
    """Bash execution message via the ! command"""
    role: Literal["bashExecution"] = "bashExecution"
    command: str = ""
    output: str = ""
    exitCode: Optional[int] = None
    cancelled: bool = False
    truncated: bool = False
    fullOutputPath: Optional[str] = None
    timestamp: int = 0
    excludeFromContext: bool = False  # If true, excluded from LLM context (!! prefix)


@dataclass
class CustomMessage:
    """Extension-injected custom message"""
    role: Literal["custom"] = "custom"
    customType: str = ""
    content: Union[str, List[Union[TextContent, ImageContent]]] = field(default_factory=str)
    display: bool = True
    details: Optional[Any] = None
    timestamp: int = 0


@dataclass
class BranchSummaryMessage:
    """Branch summary message"""
    role: Literal["branchSummary"] = "branchSummary"
    summary: str = ""
    fromId: str = ""
    timestamp: int = 0


@dataclass
class CompactionSummaryMessage:
    """Compaction summary message"""
    role: Literal["compactionSummary"] = "compactionSummary"
    summary: str = ""
    tokensBefore: int = 0
    timestamp: int = 0


# Extended message type
ExtendedMessage = Union[
    Message,
    BashExecutionMessage,
    CustomMessage,
    BranchSummaryMessage,
    CompactionSummaryMessage
]


# ============================================================================
# Tool Definition
# ============================================================================

@dataclass
class Tool:
    """Tool definition"""
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)  # JSON Schema


# ============================================================================
# Context
# ============================================================================

@dataclass
class Context:
    """LLM context"""
    messages: List[Message] = field(default_factory=list)
    systemPrompt: Optional[str] = None
    tools: Optional[List[Tool]] = None


# ============================================================================
# Model Definition
# ============================================================================

@dataclass
class ModelCost:
    """Model pricing per million tokens"""
    input: float = 0.0
    output: float = 0.0
    cacheRead: float = 0.0
    cacheWrite: float = 0.0


@dataclass
class OpenAICompletionsCompat:
    """OpenAI-compatible API compatibility settings"""
    supportsStore: Optional[bool] = None
    supportsDeveloperRole: Optional[bool] = None
    supportsReasoningEffort: Optional[bool] = None
    supportsUsageInStreaming: bool = True
    maxTokensField: Optional[str] = None  # "max_completion_tokens" or "max_tokens"
    requiresToolResultName: Optional[bool] = None
    requiresAssistantAfterToolResult: Optional[bool] = None
    requiresThinkingAsText: Optional[bool] = None
    requiresMistralToolIds: Optional[bool] = None
    thinkingFormat: str = "openai"  # "openai", "zai", "qwen"
    supportsStrictMode: bool = True


@dataclass
class Model:
    """Model configuration"""
    id: str = ""
    name: str = ""
    api: str = ""  # "openai-completions", "anthropic-messages", etc.
    provider: str = ""
    baseUrl: str = ""
    reasoning: bool = False
    input: List[str] = field(default_factory=lambda: ["text"])  # ["text", "image"]
    cost: ModelCost = field(default_factory=ModelCost)
    contextWindow: int = 0
    maxTokens: int = 0
    headers: Optional[Dict[str, str]] = None
    compat: Optional[OpenAICompletionsCompat] = None


# ============================================================================
# Stream Options
# ============================================================================

@dataclass
class StreamOptions:
    """Options for streaming LLM responses"""
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    signal: Optional[Any] = None  # AbortSignal
    apiKey: Optional[str] = None
    cacheRetention: CacheRetention = CacheRetention.SHORT
    sessionId: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    maxRetryDelayMs: int = 60000


@dataclass
class SimpleStreamOptions(StreamOptions):
    """Simplified streaming options with reasoning"""
    reasoning: Optional[ThinkingLevel] = None
    thinkingBudgets: Optional[Dict[str, int]] = None  # token budgets per level


# ============================================================================
# Constants
# ============================================================================

COMPACTION_SUMMARY_PREFIX = """The conversation history before this point was compacted into the following summary:

"""

COMPACTION_SUMMARY_SUFFIX = """
"""

BRANCH_SUMMARY_PREFIX = """The following is a summary of a branch that this conversation came back from:

"""

BRANCH_SUMMARY_SUFFIX = ""


THINKING_LEVELS = [ThinkingLevel.OFF, ThinkingLevel.MINIMAL, ThinkingLevel.LOW, 
                   ThinkingLevel.MEDIUM, ThinkingLevel.HIGH]

THINKING_LEVELS_WITH_XHIGH = THINKING_LEVELS + [ThinkingLevel.XHIGH]


# Default thinking level
DEFAULT_THINKING_LEVEL = ThinkingLevel.MEDIUM
