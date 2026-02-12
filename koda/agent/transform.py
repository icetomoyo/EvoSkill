"""
Message Transform - Context transformation and optimization
Equivalent to Pi Mono's transform.ts

Provides message filtering, context pruning, and optimization before LLM calls.
"""
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from koda.ai.types import (
    Context,
    Message,
    AssistantMessage,
    UserMessage,
    ToolResultMessage,
    TextContent,
    ToolCall,
)


class TransformStrategy(Enum):
    """Context transformation strategy"""
    SMART = "smart"          # Intelligent pruning based on importance
    TRUNCATE = "truncate"    # Simple truncation from beginning
    SUMMARIZE = "summarize"  # Summarize older messages
    COMPACT = "compact"      # Compact by removing verbose content


@dataclass
class TransformConfig:
    """Transform configuration"""
    strategy: TransformStrategy = TransformStrategy.SMART
    max_tokens: int = 128000
    target_utilization: float = 0.75  # Target 75% of max tokens
    preserve_system: bool = True
    preserve_recent: int = 4  # Always preserve last N messages
    min_messages: int = 2     # Minimum messages to keep


@dataclass
class TransformResult:
    """Result of context transformation"""
    context: Context
    original_tokens: int
    new_tokens: int
    tokens_saved: int
    messages_removed: int
    strategy_used: TransformStrategy


def convert_to_llm(
    context: Context,
    provider: str,
    model_id: str,
    max_tokens: Optional[int] = None
) -> Context:
    """
    Convert context for LLM call.

    This function transforms/filters messages before sending to the LLM.
    It handles provider-specific requirements and context window limits.

    Args:
        context: Original context
        provider: Provider ID (e.g., "anthropic", "openai")
        model_id: Model ID for context window detection
        max_tokens: Maximum context tokens (auto-detected if None)

    Returns:
        Transformed context ready for LLM
    """
    # Estimate current token count
    current_tokens = estimate_tokens(context)

    # Get model context window
    target_tokens = max_tokens or get_model_context_window(model_id)
    target_tokens = int(target_tokens * 0.75)  # Leave room for response

    if current_tokens <= target_tokens:
        # No transformation needed
        return context

    # Apply transformation
    config = TransformConfig(
        max_tokens=target_tokens,
        strategy=TransformStrategy.SMART
    )
    result = transform_context(context, config)

    # Provider-specific adjustments
    if provider == "anthropic":
        return _adjust_for_anthropic(result.context)
    elif provider in ("openai", "mistral", "groq"):
        return _adjust_for_openai_compat(result.context, provider)

    return result.context


def transform_context(
    context: Context,
    config: Optional[TransformConfig] = None
) -> TransformResult:
    """
    Transform context using specified strategy.

    Args:
        context: Original context
        config: Transform configuration

    Returns:
        TransformResult with transformed context and metadata
    """
    config = config or TransformConfig()

    original_tokens = estimate_tokens(context)
    target_tokens = int(config.max_tokens * config.target_utilization)

    if original_tokens <= target_tokens:
        return TransformResult(
            context=context,
            original_tokens=original_tokens,
            new_tokens=original_tokens,
            tokens_saved=0,
            messages_removed=0,
            strategy_used=config.strategy
        )

    # Apply strategy
    if config.strategy == TransformStrategy.SMART:
        transformed = _smart_prune(context, target_tokens, config)
    elif config.strategy == TransformStrategy.TRUNCATE:
        transformed = _truncate_prune(context, target_tokens, config)
    elif config.strategy == TransformStrategy.COMPACT:
        transformed = _compact_prune(context, target_tokens, config)
    else:
        transformed = _smart_prune(context, target_tokens, config)

    new_tokens = estimate_tokens(transformed)

    return TransformResult(
        context=transformed,
        original_tokens=original_tokens,
        new_tokens=new_tokens,
        tokens_saved=original_tokens - new_tokens,
        messages_removed=len(context.messages) - len(transformed.messages),
        strategy_used=config.strategy
    )


def estimate_tokens(context: Context) -> int:
    """
    Estimate token count for context.

    Uses a simple heuristic: ~4 characters per token.
    """
    total = 0

    # System prompt
    if context.system_prompt:
        total += len(context.system_prompt) // 4

    # Messages
    for msg in context.messages:
        total += estimate_message_tokens(msg)

    # Tools
    if context.tools:
        for tool in context.tools:
            total += len(tool.name) // 4
            total += len(tool.description) // 4
            total += len(str(tool.parameters)) // 4

    return total


def estimate_message_tokens(msg: Message) -> int:
    """Estimate tokens for a single message"""
    total = 4  # Role overhead

    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, str):
            total += len(content) // 4
        else:
            for item in content:
                if hasattr(item, 'text'):
                    total += len(item.text) // 4
                elif hasattr(item, 'data'):
                    total += len(item.data) // 20  # Images are more compact

    elif isinstance(msg, AssistantMessage):
        for item in msg.content:
            if item.type == "text":
                total += len(item.text) // 4
            elif item.type == "thinking":
                total += len(item.thinking) // 4
            elif item.type == "toolCall":
                total += len(item.name) // 4
                total += len(str(item.arguments)) // 4

    elif isinstance(msg, ToolResultMessage):
        for item in msg.content:
            if hasattr(item, 'text'):
                total += len(item.text) // 4

    return total


def get_model_context_window(model_id: str) -> int:
    """Get context window for a model"""
    # Default context windows
    context_windows = {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "claude-3-5-sonnet": 200000,
        "claude-3-5-haiku": 200000,
        "claude-3-7-sonnet": 200000,
        "claude-4": 200000,
        "claude-opus-4": 200000,
        "claude-sonnet-4": 200000,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "o1": 200000,
        "o1-mini": 128000,
        "gemini-1.5-pro": 2097152,
        "gemini-1.5-flash": 1048576,
        "gemini-2": 1048576,
    }

    for prefix, window in context_windows.items():
        if model_id.startswith(prefix):
            return window

    return 128000  # Default


def _smart_prune(
    context: Context,
    target_tokens: int,
    config: TransformConfig
) -> Context:
    """
    Smart pruning based on message importance.

    Prioritizes:
    1. Recent messages
    2. Messages with tool calls
    3. User messages
    """
    messages = list(context.messages)

    if len(messages) <= config.min_messages:
        return context

    # Calculate importance scores
    scored_messages = []
    for i, msg in enumerate(messages):
        score = _calculate_importance(msg, i, len(messages))
        scored_messages.append((score, i, msg))

    # Sort by importance (descending)
    scored_messages.sort(key=lambda x: (-x[0], x[1]))

    # Select messages to keep
    kept_indices = set()

    # Always keep recent messages
    for i in range(min(config.preserve_recent, len(messages))):
        kept_indices.add(len(messages) - 1 - i)

    # Add messages by importance until we hit target
    current_tokens = 0
    for score, idx, msg in scored_messages:
        if idx in kept_indices:
            current_tokens += estimate_message_tokens(msg)
            continue

        msg_tokens = estimate_message_tokens(msg)
        if current_tokens + msg_tokens <= target_tokens:
            kept_indices.add(idx)
            current_tokens += msg_tokens

    # Build new message list in order
    new_messages = [messages[i] for i in sorted(kept_indices)]

    return Context(
        system_prompt=context.system_prompt,
        messages=new_messages,
        tools=context.tools
    )


def _calculate_importance(msg: Message, index: int, total: int) -> float:
    """Calculate importance score for a message"""
    score = 0.0

    # Recency bonus (newer = more important)
    recency = (index + 1) / total
    score += recency * 10

    # Type bonuses
    if isinstance(msg, UserMessage):
        score += 5.0  # User messages are important

    elif isinstance(msg, AssistantMessage):
        # Check for tool calls
        has_tools = any(c.type == "toolCall" for c in msg.content)
        if has_tools:
            score += 3.0

    elif isinstance(msg, ToolResultMessage):
        score += 2.0  # Tool results are somewhat important
        if msg.is_error:
            score += 1.0  # Errors are important for context

    return score


def _truncate_prune(
    context: Context,
    target_tokens: int,
    config: TransformConfig
) -> Context:
    """Simple truncation from beginning"""
    messages = list(context.messages)

    # Start from the end and work backwards
    kept_messages = []
    current_tokens = 0

    for msg in reversed(messages):
        msg_tokens = estimate_message_tokens(msg)
        if current_tokens + msg_tokens <= target_tokens:
            kept_messages.insert(0, msg)
            current_tokens += msg_tokens
        else:
            break

    # Ensure minimum messages
    if len(kept_messages) < config.min_messages:
        kept_messages = messages[-config.min_messages:]

    return Context(
        system_prompt=context.system_prompt,
        messages=kept_messages,
        tools=context.tools
    )


def _compact_prune(
    context: Context,
    target_tokens: int,
    config: TransformConfig
) -> Context:
    """
    Compact by shortening verbose content.

    This strategy keeps all messages but shortens long ones.
    """
    messages = []

    for msg in context.messages:
        compacted = _compact_message(msg, max_length=2000)
        messages.append(compacted)

    return Context(
        system_prompt=context.system_prompt,
        messages=messages,
        tools=context.tools
    )


def _compact_message(msg: Message, max_length: int = 2000) -> Message:
    """Compact a single message by truncating long content"""
    if isinstance(msg, UserMessage):
        if isinstance(msg.content, str) and len(msg.content) > max_length:
            # Truncate with ellipsis
            truncated = msg.content[:max_length] + "\n...[truncated]"
            return UserMessage(
                role="user",
                content=truncated,
                timestamp=msg.timestamp
            )

    elif isinstance(msg, AssistantMessage):
        new_content = []
        for item in msg.content:
            if item.type == "text" and len(item.text) > max_length:
                # Truncate text
                truncated_text = item.text[:max_length] + "\n...[truncated]"
                new_content.append(TextContent(type="text", text=truncated_text))
            else:
                new_content.append(item)

        return AssistantMessage(
            role="assistant",
            content=new_content,
            api=msg.api,
            provider=msg.provider,
            model=msg.model,
            usage=msg.usage,
            stop_reason=msg.stop_reason,
            error_message=msg.error_message,
            timestamp=msg.timestamp
        )

    elif isinstance(msg, ToolResultMessage):
        new_content = []
        for item in msg.content:
            if hasattr(item, 'text') and len(item.text) > max_length:
                truncated_text = item.text[:max_length] + "\n...[truncated]"
                new_content.append(TextContent(type="text", text=truncated_text))
            else:
                new_content.append(item)

        return ToolResultMessage(
            role="toolResult",
            tool_call_id=msg.tool_call_id,
            tool_name=msg.tool_name,
            content=new_content,
            details=msg.details,
            is_error=msg.is_error,
            timestamp=msg.timestamp
        )

    return msg


def _adjust_for_anthropic(context: Context) -> Context:
    """
    Adjust context for Anthropic-specific requirements.

    - Ensure user/tool-result alternation
    - Cache control placement
    """
    messages = list(context.messages)
    adjusted = []
    last_role = None

    for msg in messages:
        current_role = msg.role

        # Anthropic requires user messages after tool results
        if last_role == "toolResult" and current_role != "user":
            # Insert a placeholder user message
            adjusted.append(UserMessage(
                role="user",
                content="Continue.",
                timestamp=0
            ))

        adjusted.append(msg)
        last_role = current_role

    return Context(
        system_prompt=context.system_prompt,
        messages=adjusted,
        tools=context.tools
    )


def _adjust_for_openai_compat(context: Context, provider: str) -> Context:
    """
    Adjust context for OpenAI-compatible providers.

    - Handle provider-specific quirks
    - Ensure message format compatibility
    """
    messages = []

    for msg in context.messages:
        # Most OpenAI-compatible APIs handle standard formats
        # But some have specific requirements
        if provider == "mistral":
            # Mistral requires specific tool call IDs
            if isinstance(msg, AssistantMessage):
                for item in msg.content:
                    if item.type == "toolCall" and not item.id.startswith("call_"):
                        item.id = f"call_{item.id}"

        messages.append(msg)

    return Context(
        system_prompt=context.system_prompt,
        messages=messages,
        tools=context.tools
    )


def filter_tool_results(
    context: Context,
    keep_errors: bool = True,
    max_results: Optional[int] = None
) -> Context:
    """
    Filter tool result messages.

    Args:
        context: Original context
        keep_errors: Whether to keep error results
        max_results: Maximum number of tool results to keep

    Returns:
        Context with filtered tool results
    """
    messages = []

    for msg in context.messages:
        if isinstance(msg, ToolResultMessage):
            if keep_errors and msg.is_error:
                messages.append(msg)
            elif max_results is None or len([m for m in messages if isinstance(m, ToolResultMessage)]) < max_results:
                messages.append(msg)
        else:
            messages.append(msg)

    return Context(
        system_prompt=context.system_prompt,
        messages=messages,
        tools=context.tools
    )


def extract_text_content(context: Context) -> str:
    """
    Extract all text content from context.

    Useful for logging or debugging.
    """
    parts = []

    if context.system_prompt:
        parts.append(f"[System]\n{context.system_prompt}")

    for msg in context.messages:
        if isinstance(msg, UserMessage):
            content = msg.content
            if isinstance(content, str):
                parts.append(f"[User]\n{content}")
            else:
                text_parts = [item.text for item in content if hasattr(item, 'text')]
                if text_parts:
                    parts.append(f"[User]\n{' '.join(text_parts)}")

        elif isinstance(msg, AssistantMessage):
            text_parts = []
            for item in msg.content:
                if item.type == "text":
                    text_parts.append(item.text)
                elif item.type == "thinking":
                    text_parts.append(f"[thinking: {len(item.thinking)} chars]")
                elif item.type == "toolCall":
                    text_parts.append(f"[tool: {item.name}]")
            parts.append(f"[Assistant]\n{' '.join(text_parts)}")

        elif isinstance(msg, ToolResultMessage):
            text = msg.content[0].text if msg.content else ""
            parts.append(f"[Tool: {msg.tool_name}]\n{text[:500]}")

    return "\n\n".join(parts)
