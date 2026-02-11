"""
Message Transformation
Equivalent to Pi Mono's packages/ai/src/providers/transform-messages.ts

Transforms messages for cross-provider compatibility.
Handles:
- Tool call ID normalization
- Thinking block conversion
- Message format adaptation
"""
from typing import List, Callable, Optional, Dict
from .types import (
    Message, UserMessage, AssistantMessage, ToolResultMessage,
    ToolCall, TextContent, ThinkingContent,
    ModelInfo
)


def normalize_tool_call_id(id: str, provider: str) -> str:
    """
    Normalize tool call ID for cross-provider compatibility.
    
    OpenAI Responses API generates IDs that are 450+ chars with special characters like `|`.
    Anthropic APIs require IDs matching ^[a-zA-Z0-9_-]+$ (max 64 chars).
    
    Args:
        id: Original tool call ID
        provider: Target provider
        
    Returns:
        Normalized ID safe for the provider
    """
    if not id:
        return id
    
    # For Anthropic, normalize to safe characters
    if provider in ("anthropic", "bedrock"):
        # Replace unsafe characters with underscore
        safe_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in id)
        # Truncate to 64 chars
        return safe_id[:64]
    
    # For other providers, return as-is
    return id


def transform_messages(
    messages: List[Message],
    model: ModelInfo,
    normalize_tool_call_id_fn: Optional[Callable[[str, ModelInfo, AssistantMessage], str]] = None
) -> List[Message]:
    """
    Transform messages for provider compatibility.
    
    This function:
    1. Normalizes tool call IDs for cross-provider compatibility
    2. Converts thinking blocks between providers
    3. Removes provider-specific signatures when switching providers
    
    Args:
        messages: Original messages
        model: Target model info
        normalize_tool_call_id_fn: Optional custom ID normalization function
        
    Returns:
        Transformed messages ready for the target provider
    """
    # Map of original tool call IDs to normalized IDs
    tool_call_id_map: Dict[str, str] = {}
    
    # First pass: transform content and build ID map
    transformed = []
    for msg in messages:
        if isinstance(msg, UserMessage):
            # User messages pass through unchanged
            transformed.append(msg)
            
        elif isinstance(msg, ToolResultMessage):
            # Normalize tool call ID if we have a mapping
            normalized_id = tool_call_id_map.get(msg.tool_call_id, msg.tool_call_id)
            if normalized_id != msg.tool_call_id:
                # Create new message with normalized ID
                new_msg = ToolResultMessage(
                    role="tool",
                    tool_call_id=normalized_id,
                    tool_name=msg.tool_name,
                    content=msg.content,
                    is_error=msg.is_error,
                    timestamp=msg.timestamp
                )
                transformed.append(new_msg)
            else:
                transformed.append(msg)
                
        elif isinstance(msg, AssistantMessage):
            # Check if same model (no transformation needed for content)
            is_same_model = (
                msg.provider == model.provider and
                msg.model == model.id
            )
            
            transformed_content = []
            for block in msg.content:
                if isinstance(block, ThinkingContent):
                    # Handle thinking blocks
                    if is_same_model and block.thinking_signature:
                        # Same model with signature - keep as-is (needed for replay)
                        transformed_content.append(block)
                    elif block.thinking and block.thinking.strip():
                        # Has thinking content - convert to text if different model
                        if is_same_model:
                            transformed_content.append(block)
                        else:
                            transformed_content.append(TextContent(
                                type="text",
                                text=block.thinking
                            ))
                    # Empty thinking blocks are filtered out
                    
                elif isinstance(block, TextContent):
                    # Text blocks pass through
                    transformed_content.append(block)
                    
                elif isinstance(block, ToolCall):
                    # Handle tool calls
                    tool_call = block
                    
                    # Remove provider-specific signatures when switching models
                    if not is_same_model and hasattr(tool_call, 'thought_signature'):
                        # Create new tool call without signature
                        tool_call = ToolCall(
                            type="tool_call",
                            id=tool_call.id,
                            name=tool_call.name,
                            arguments=tool_call.arguments
                        )
                    
                    # Normalize tool call ID if needed
                    if not is_same_model or normalize_tool_call_id_fn:
                        if normalize_tool_call_id_fn:
                            normalized_id = normalize_tool_call_id_fn(
                                tool_call.id, model, msg
                            )
                        else:
                            normalized_id = normalize_tool_call_id(
                                tool_call.id, model.provider
                            )
                        
                        if normalized_id != tool_call.id:
                            # Store mapping for tool results
                            tool_call_id_map[tool_call.id] = normalized_id
                            # Create new tool call with normalized ID
                            tool_call = ToolCall(
                                type="tool_call",
                                id=normalized_id,
                                name=tool_call.name,
                                arguments=tool_call.arguments
                            )
                    
                    transformed_content.append(tool_call)
            
            # Create transformed assistant message
            new_msg = AssistantMessage(
                role="assistant",
                content=transformed_content,
                model=model.id,
                provider=model.provider,
                stop_reason=msg.stop_reason,
                usage=msg.usage,
                timestamp=msg.timestamp
            )
            transformed.append(new_msg)
        else:
            # Unknown message type - pass through
            transformed.append(msg)
    
    # Second pass: handle orphaned tool calls
    # Insert synthetic empty tool results for tool calls that don't have results
    result = []
    pending_tool_calls: List[ToolCall] = []
    existing_tool_result_ids = set()
    
    for msg in transformed:
        if isinstance(msg, ToolResultMessage):
            existing_tool_result_ids.add(msg.tool_call_id)
        
        if isinstance(msg, AssistantMessage):
            # Check for tool calls in this message
            for block in msg.content:
                if isinstance(block, ToolCall):
                    pending_tool_calls.append(block)
        
        result.append(msg)
    
    # Add synthetic tool results for orphaned tool calls
    for tool_call in pending_tool_calls:
        if tool_call.id not in existing_tool_result_ids:
            # Create synthetic empty tool result
            synthetic_result = ToolResultMessage(
                role="tool",
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                content=[TextContent(type="text", text="")],
                is_error=False,
                timestamp=0
            )
            result.append(synthetic_result)
    
    return result


def clamp_reasoning(effort: Optional[str]) -> Optional[str]:
    """
    Clamp reasoning effort to valid range.
    
    Maps 'xhigh' to 'high' since not all providers support it.
    
    Args:
        effort: Reasoning effort level
        
    Returns:
        Clamped effort level
    """
    if effort == "xhigh":
        return "high"
    return effort


__all__ = [
    "normalize_tool_call_id",
    "transform_messages",
    "clamp_reasoning",
]
