"""
Agent Types - P1/P2 Enhancement Types

Defines AgentMessage union type, ThinkingBudget configuration,
and PendingToolCall data class for enhanced agent functionality.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable

from koda.ai.types import UserMessage, AssistantMessage, TextContent, ImageContent


# AgentMessage union type - supports str, dict, or Message objects
AgentMessage = Union[
    str,
    Dict[str, Any],
    UserMessage,
    AssistantMessage,
]


@dataclass
class ThinkingBudget:
    """
    Thinking budget configuration for models that support extended thinking.

    This allows controlling the depth of reasoning/thinking the model performs
    before generating a response.

    Attributes:
        max_thinking_tokens: Maximum tokens for thinking phase
        budget_tokens: Budget tokens (Claude-style)
        enabled: Whether thinking is enabled
        level: Thinking level ("minimal", "low", "medium", "high", "xhigh")
    """
    max_thinking_tokens: Optional[int] = None
    budget_tokens: Optional[int] = None
    enabled: bool = True
    level: str = "medium"  # minimal, low, medium, high, xhigh

    @classmethod
    def minimal(cls) -> "ThinkingBudget":
        """Create minimal thinking budget"""
        return cls(max_thinking_tokens=1024, level="minimal")

    @classmethod
    def low(cls) -> "ThinkingBudget":
        """Create low thinking budget"""
        return cls(max_thinking_tokens=4096, level="low")

    @classmethod
    def medium(cls) -> "ThinkingBudget":
        """Create medium thinking budget"""
        return cls(max_thinking_tokens=16384, level="medium")

    @classmethod
    def high(cls) -> "ThinkingBudget":
        """Create high thinking budget"""
        return cls(max_thinking_tokens=65536, level="high")

    @classmethod
    def xhigh(cls) -> "ThinkingBudget":
        """Create extra high thinking budget"""
        return cls(max_thinking_tokens=131072, level="xhigh")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        result = {"enabled": self.enabled, "level": self.level}
        if self.max_thinking_tokens is not None:
            result["max_thinking_tokens"] = self.max_thinking_tokens
        if self.budget_tokens is not None:
            result["budget_tokens"] = self.budget_tokens
        return result


@dataclass
class PendingToolCall:
    """
    Tracks a pending tool call that hasn't been executed yet.

    Used for tracking tool calls in progress and managing
    the execution queue.

    Attributes:
        id: Unique identifier for the tool call
        name: Name of the tool to call
        arguments: Arguments to pass to the tool
        status: Current status ("pending", "running", "completed", "failed")
        result: Result of tool execution (if completed)
        error: Error message (if failed)
        created_at: Timestamp when call was created
        started_at: Timestamp when execution started
        completed_at: Timestamp when execution completed
        retry_count: Number of retry attempts
        metadata: Additional metadata
    """
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_running(self) -> None:
        """Mark tool call as running"""
        import time
        self.status = "running"
        self.started_at = time.time()

    def mark_completed(self, result: Any) -> None:
        """Mark tool call as completed with result"""
        import time
        self.status = "completed"
        self.result = result
        self.completed_at = time.time()

    def mark_failed(self, error: str) -> None:
        """Mark tool call as failed with error"""
        import time
        self.status = "failed"
        self.error = error
        self.completed_at = time.time()

    def increment_retry(self) -> None:
        """Increment retry count and reset status"""
        self.retry_count += 1
        self.status = "pending"
        self.started_at = None
        self.completed_at = None

    @property
    def is_pending(self) -> bool:
        """Check if call is pending"""
        return self.status == "pending"

    @property
    def is_running(self) -> bool:
        """Check if call is running"""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """Check if call is completed"""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if call has failed"""
        return self.status == "failed"

    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class ImageInput:
    """
    Image input for multimodal messages.

    Supports base64-encoded images and URLs.

    Attributes:
        data: Base64-encoded image data or URL
        mime_type: MIME type (image/jpeg, image/png, etc.)
        is_url: Whether data is a URL
    """
    data: str
    mime_type: str = "image/jpeg"
    is_url: bool = False

    @classmethod
    def from_base64(cls, data: str, mime_type: str = "image/jpeg") -> "ImageInput":
        """Create from base64-encoded data"""
        return cls(data=data, mime_type=mime_type, is_url=False)

    @classmethod
    def from_url(cls, url: str) -> "ImageInput":
        """Create from URL"""
        return cls(data=url, mime_type="", is_url=True)

    def to_content(self) -> Dict[str, Any]:
        """Convert to content dict for API"""
        if self.is_url:
            return {
                "type": "image_url",
                "image_url": {"url": self.data}
            }
        else:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": self.mime_type,
                    "data": self.data
                }
            }


def normalize_agent_message(message: AgentMessage) -> Union[str, List[Dict[str, Any]]]:
    """
    Normalize AgentMessage to a format suitable for LLM providers.

    Args:
        message: AgentMessage (str, dict, UserMessage, or AssistantMessage)

    Returns:
        Normalized content (string or list of content parts)
    """
    if isinstance(message, str):
        return message

    if isinstance(message, dict):
        # Already a dict, return as-is or extract content
        if "content" in message:
            return message["content"]
        return message

    if isinstance(message, UserMessage):
        content = message.content
        if isinstance(content, str):
            return content
        # List of content parts
        parts = []
        for part in content:
            if isinstance(part, TextContent):
                parts.append({"type": "text", "text": part.text})
            elif isinstance(part, ImageContent):
                parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": part.mime_type,
                        "data": part.data
                    }
                })
        return parts

    if isinstance(message, AssistantMessage):
        # Extract text from assistant message
        text_parts = []
        for content in message.content:
            if hasattr(content, 'text'):
                text_parts.append(content.text)
        return " ".join(text_parts)

    # Fallback
    return str(message)


def create_user_message(
    content: Union[str, List[Union[str, ImageInput]]],
    **metadata
) -> UserMessage:
    """
    Create a UserMessage from various input formats.

    Args:
        content: String content or list of strings/ImageInputs
        **metadata: Additional metadata

    Returns:
        UserMessage instance
    """
    import time

    if isinstance(content, str):
        return UserMessage(
            role="user",
            content=content,
            timestamp=int(time.time() * 1000)
        )

    # List of content parts
    content_parts = []
    for part in content:
        if isinstance(part, str):
            content_parts.append(TextContent(type="text", text=part))
        elif isinstance(part, ImageInput):
            content_parts.append(ImageContent(
                type="image",
                data=part.data,
                mime_type=part.mime_type
            ))

    return UserMessage(
        role="user",
        content=content_parts,
        timestamp=int(time.time() * 1000)
    )


# Type alias for API key resolver callback
ApiKeyResolver = Callable[[], Optional[str]]

# Type alias for session cache
SessionCache = Dict[str, Any]
