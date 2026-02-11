"""
Stream Proxy
Equivalent to Pi Mono's packages/agent/src/proxy.ts

Proxy stream function for apps that route LLM calls through a server.
The server manages auth and proxies requests to LLM providers.

This is NOT multi-agent coordination - it's HTTP proxy for LLM calls.
"""
import asyncio
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..ai.types import (
    AssistantMessage,
    AssistantMessageEvent,
    ModelInfo,
    Context,
    SimpleStreamOptions,
    StopReason,
    ToolCall,
    TextContent,
    ThinkingContent,
)
from ..ai.event_stream import AssistantMessageEventStream, create_event_stream
from ..ai.json_parse import parse_streaming_json


# Proxy event types - server sends these with partial field stripped to reduce bandwidth
ProxyAssistantMessageEvent = Dict[str, Any]


@dataclass
class ProxyStreamOptions(SimpleStreamOptions):
    """Options for proxy stream"""
    auth_token: str = ""
    proxy_url: str = ""  # e.g., "https://genai.example.com"


class ProxyMessageEventStream(AssistantMessageEventStream):
    """
    Stream class for proxy messages.
    
    Reconstructs partial message client-side from proxy events.
    """
    pass


def create_proxy_stream() -> ProxyMessageEventStream:
    """Factory function for ProxyMessageEventStream"""
    return create_event_stream()


async def stream_proxy(
    model: ModelInfo,
    context: Context,
    options: ProxyStreamOptions
) -> ProxyMessageEventStream:
    """
    Stream function that proxies through a server instead of calling LLM providers directly.
    
    The server strips the partial field from delta events to reduce bandwidth.
    We reconstruct the partial message client-side.

    Use this as the `stream_fn` option when creating an Agent that needs to go through a proxy.

    Example:
        ```python
        agent = Agent({
            'stream_fn': lambda model, context, options: stream_proxy(
                model, context,
                ProxyStreamOptions(
                    **options,
                    auth_token=await get_auth_token(),
                    proxy_url="https://genai.example.com"
                )
            )
        })
        ```

    Args:
        model: Model configuration
        context: Conversation context
        options: Proxy stream options including auth_token and proxy_url

    Returns:
        ProxyMessageEventStream that yields events as they arrive
    """
    stream = create_proxy_stream()

    # Run the streaming in a background task
    asyncio.create_task(_run_proxy_stream(model, context, options, stream))

    return stream


async def _run_proxy_stream(
    model: ModelInfo,
    context: Context,
    options: ProxyStreamOptions,
    stream: ProxyMessageEventStream
) -> None:
    """
    Internal function to run the proxy stream.
    
    This runs in a background task and pushes events to the stream.
    """
    # Initialize the partial message that we'll build up from events
    partial = AssistantMessage(
        role="assistant",
        stop_reason="stop",
        content=[],
        api=model.api,
        provider=model.provider,
        model=model.id,
        usage={
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
            "total_tokens": 0,
            "cost": {
                "input": 0.0,
                "output": 0.0,
                "cache_read": 0.0,
                "cache_write": 0.0,
                "total": 0.0,
            },
        },
        timestamp=asyncio.get_event_loop().time() * 1000,
    )

    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{options.proxy_url}/api/stream",
                headers={
                    "Authorization": f"Bearer {options.auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model.to_dict() if hasattr(model, 'to_dict') else {
                        "id": model.id,
                        "api": model.api,
                        "provider": model.provider,
                    },
                    "context": {
                        "system_prompt": context.system_prompt,
                        "messages": [
                            m.to_dict() if hasattr(m, 'to_dict') else m
                            for m in context.messages
                        ],
                        "tools": [
                            t.to_dict() if hasattr(t, 'to_dict') else t
                            for t in (context.tools or [])
                        ],
                    },
                    "options": {
                        "temperature": options.temperature,
                        "max_tokens": options.max_tokens,
                        "reasoning": options.reasoning,
                    },
                },
                timeout=aiohttp.ClientTimeout(total=300),
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    try:
                        error_data = json.loads(error_text)
                        error_message = f"Proxy error: {error_data.get('error', error_text)}"
                    except json.JSONDecodeError:
                        error_message = f"Proxy error: {response.status} {response.reason}"
                    
                    raise Exception(error_message)

                # Process SSE stream
                buffer = ""
                async for chunk in response.content:
                    if options.signal and options.signal.is_set():
                        raise Exception("Request aborted by user")

                    buffer += chunk.decode('utf-8')
                    lines = buffer.split("\n")
                    buffer = lines.pop()  # Keep incomplete line

                    for line in lines:
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data:
                                try:
                                    proxy_event = json.loads(data)
                                    event = _process_proxy_event(proxy_event, partial)
                                    if event:
                                        stream.push(event)
                                except json.JSONDecodeError:
                                    continue

    except Exception as e:
        error_message = str(e)
        reason = "aborted" if (options.signal and options.signal.is_set()) else "error"
        partial.stop_reason = reason
        partial.error_message = error_message
        
        stream.push({
            "type": "error",
            "reason": reason,
            "error": partial,
        })
    finally:
        stream.end()


def _process_proxy_event(
    proxy_event: ProxyAssistantMessageEvent,
    partial: AssistantMessage
) -> Optional[AssistantMessageEvent]:
    """
    Process a proxy event and update the partial message.
    
    Args:
        proxy_event: Event from proxy server
        partial: Partial message being built
        
    Returns:
        AssistantMessageEvent or None
    """
    event_type = proxy_event.get("type")

    if event_type == "start":
        return {"type": "start", "partial": partial}

    elif event_type == "text_start":
        content_index = proxy_event["contentIndex"]
        partial.content.insert(content_index, TextContent(type="text", text=""))
        return {"type": "text_start", "content_index": content_index, "partial": partial}

    elif event_type == "text_delta":
        content_index = proxy_event["contentIndex"]
        delta = proxy_event["delta"]
        
        if content_index < len(partial.content):
            content = partial.content[content_index]
            if content.type == "text":
                content.text += delta
                return {
                    "type": "text_delta",
                    "content_index": content_index,
                    "delta": delta,
                    "partial": partial,
                }
        raise ValueError("Received text_delta for non-text content")

    elif event_type == "text_end":
        content_index = proxy_event["contentIndex"]
        content_signature = proxy_event.get("contentSignature")
        
        if content_index < len(partial.content):
            content = partial.content[content_index]
            if content.type == "text":
                content.text_signature = content_signature
                return {
                    "type": "text_end",
                    "content_index": content_index,
                    "content": content.text,
                    "partial": partial,
                }
        raise ValueError("Received text_end for non-text content")

    elif event_type == "thinking_start":
        content_index = proxy_event["contentIndex"]
        partial.content.insert(content_index, ThinkingContent(type="thinking", thinking=""))
        return {"type": "thinking_start", "content_index": content_index, "partial": partial}

    elif event_type == "thinking_delta":
        content_index = proxy_event["contentIndex"]
        delta = proxy_event["delta"]
        
        if content_index < len(partial.content):
            content = partial.content[content_index]
            if content.type == "thinking":
                content.thinking += delta
                return {
                    "type": "thinking_delta",
                    "content_index": content_index,
                    "delta": delta,
                    "partial": partial,
                }
        raise ValueError("Received thinking_delta for non-thinking content")

    elif event_type == "thinking_end":
        content_index = proxy_event["contentIndex"]
        content_signature = proxy_event.get("contentSignature")
        
        if content_index < len(partial.content):
            content = partial.content[content_index]
            if content.type == "thinking":
                content.thinking_signature = content_signature
                return {
                    "type": "thinking_end",
                    "content_index": content_index,
                    "content": content.thinking,
                    "partial": partial,
                }
        raise ValueError("Received thinking_end for non-thinking content")

    elif event_type == "toolcall_start":
        content_index = proxy_event["contentIndex"]
        tool_id = proxy_event["id"]
        tool_name = proxy_event["toolName"]
        
        partial.content.insert(content_index, ToolCall(
            type="tool_call",
            id=tool_id,
            name=tool_name,
            arguments={},
        ))
        return {"type": "toolcall_start", "content_index": content_index, "partial": partial}

    elif event_type == "toolcall_delta":
        content_index = proxy_event["contentIndex"]
        delta = proxy_event["delta"]
        
        if content_index < len(partial.content):
            content = partial.content[content_index]
            if content.type == "tool_call":
                # Store partial JSON in a temporary attribute
                if not hasattr(content, '_partial_json'):
                    content._partial_json = ""
                content._partial_json += delta
                content.arguments = parse_streaming_json(content._partial_json) or {}
                return {
                    "type": "toolcall_delta",
                    "content_index": content_index,
                    "delta": delta,
                    "partial": partial,
                }
        raise ValueError("Received toolcall_delta for non-toolCall content")

    elif event_type == "toolcall_end":
        content_index = proxy_event["contentIndex"]
        
        if content_index < len(partial.content):
            content = partial.content[content_index]
            if content.type == "tool_call":
                # Clean up temporary attribute
                if hasattr(content, '_partial_json'):
                    delattr(content, '_partial_json')
                return {
                    "type": "toolcall_end",
                    "content_index": content_index,
                    "tool_call": content,
                    "partial": partial,
                }
        return None

    elif event_type == "done":
        partial.stop_reason = proxy_event["reason"]
        partial.usage = proxy_event["usage"]
        return {"type": "done", "reason": proxy_event["reason"], "message": partial}

    elif event_type == "error":
        partial.stop_reason = proxy_event["reason"]
        partial.error_message = proxy_event.get("errorMessage")
        partial.usage = proxy_event["usage"]
        return {"type": "error", "reason": proxy_event["reason"], "error": partial}

    else:
        print(f"Unhandled proxy event type: {event_type}")
        return None
