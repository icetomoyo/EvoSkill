"""
Message Converter - Convert agent messages to LLM-compatible format

Based on: packages/coding-agent/src/core/messages.ts
"""
from typing import List, Optional, Union

from koda.core.multimodal_types import (
    Message, UserMessage, AssistantMessage, ToolResultMessage,
    BashExecutionMessage, CustomMessage, BranchSummaryMessage, CompactionSummaryMessage,
    TextContent, ImageContent,
    COMPACTION_SUMMARY_PREFIX, COMPACTION_SUMMARY_SUFFIX,
    BRANCH_SUMMARY_PREFIX, BRANCH_SUMMARY_SUFFIX,
    ExtendedMessage
)


def bash_execution_to_text(msg: BashExecutionMessage) -> str:
    """
    Convert BashExecutionMessage to text for LLM context
    
    Based on Pi's bashExecutionToText function
    """
    text = f"Ran `{msg.command}`\n"
    
    if msg.output:
        text += f"```\n{msg.output}\n```"
    else:
        text += "(no output)"
    
    if msg.cancelled:
        text += "\n\n(command cancelled)"
    elif msg.exitCode is not None and msg.exitCode != 0:
        text += f"\n\nCommand exited with code {msg.exitCode}"
    
    if msg.truncated and msg.fullOutputPath:
        text += f"\n\n[Output truncated. Full output: {msg.fullOutputPath}]"
    
    return text


def create_branch_summary_message(summary: str, from_id: str, timestamp: str) -> BranchSummaryMessage:
    """Create a branch summary message"""
    from datetime import datetime
    return BranchSummaryMessage(
        role="branchSummary",
        summary=summary,
        fromId=from_id,
        timestamp=int(datetime.fromisoformat(timestamp).timestamp() * 1000)
    )


def create_compaction_summary_message(summary: str, tokens_before: int, timestamp: str) -> CompactionSummaryMessage:
    """Create a compaction summary message"""
    from datetime import datetime
    return CompactionSummaryMessage(
        role="compactionSummary",
        summary=summary,
        tokensBefore=tokens_before,
        timestamp=int(datetime.fromisoformat(timestamp).timestamp() * 1000)
    )


def create_custom_message(
    custom_type: str,
    content: Union[str, List[Union[TextContent, ImageContent]]],
    display: bool,
    details: Optional[Any],
    timestamp: str
) -> CustomMessage:
    """Create a custom message"""
    from datetime import datetime
    return CustomMessage(
        role="custom",
        customType=custom_type,
        content=content,
        display=display,
        details=details,
        timestamp=int(datetime.fromisoformat(timestamp).timestamp() * 1000)
    )


def convert_to_llm(messages: List[ExtendedMessage]) -> List[Message]:
    """
    Transform AgentMessages (including custom types) to LLM-compatible Messages
    
    This is the core function used by:
    - Agent's transformToLlm option (for prompt calls and queued messages)
    - Compaction's generateSummary (for summarization)
    - Custom extensions and tools
    
    Based on Pi's convertToLlm function
    """
    result: List[Message] = []
    
    for m in messages:
        converted: Optional[Message] = None
        
        # Handle custom message types
        if isinstance(m, BashExecutionMessage):
            # Skip messages excluded from context (!! prefix)
            if m.excludeFromContext:
                continue
            converted = UserMessage(
                role="user",
                content=[TextContent(type="text", text=bash_execution_to_text(m))],
                timestamp=m.timestamp
            )
        
        elif isinstance(m, CustomMessage):
            content = m.content if isinstance(m.content, list) else [TextContent(type="text", text=m.content)]
            converted = UserMessage(
                role="user",
                content=content,
                timestamp=m.timestamp
            )
        
        elif isinstance(m, BranchSummaryMessage):
            converted = UserMessage(
                role="user",
                content=[TextContent(
                    type="text",
                    text=BRANCH_SUMMARY_PREFIX + m.summary + BRANCH_SUMMARY_SUFFIX
                )],
                timestamp=m.timestamp
            )
        
        elif isinstance(m, CompactionSummaryMessage):
            converted = UserMessage(
                role="user",
                content=[TextContent(
                    type="text",
                    text=COMPACTION_SUMMARY_PREFIX + m.summary + COMPACTION_SUMMARY_SUFFIX
                )],
                timestamp=m.timestamp
            )
        
        elif isinstance(m, (UserMessage, AssistantMessage, ToolResultMessage)):
            # Already LLM-compatible
            converted = m
        
        if converted:
            result.append(converted)
    
    return result


def is_multimodal_content(content: Union[str, List[Union[TextContent, ImageContent]]]) -> bool:
    """Check if content contains images"""
    if isinstance(content, str):
        return False
    return any(isinstance(item, ImageContent) for item in content)


def extract_text_from_content(content: Union[str, List[Union[TextContent, ImageContent]]]) -> str:
    """Extract text from content, ignoring images"""
    if isinstance(content, str):
        return content
    
    texts = []
    for item in content:
        if isinstance(item, TextContent):
            texts.append(item.text)
    return "\n".join(texts)


def extract_images_from_content(content: Union[str, List[Union[TextContent, ImageContent]]]) -> List[ImageContent]:
    """Extract images from content"""
    if isinstance(content, str):
        return []
    
    return [item for item in content if isinstance(item, ImageContent)]


# Import Any for type hints
from typing import Any
