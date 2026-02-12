"""
Unified Streaming API - 统一流式入口
Equivalent to Pi Mono's unified.ts

Provides simple, high-level API for common LLM operations.
"""
import asyncio
from typing import AsyncIterator, List, Optional, Union

from koda.ai.types import (
    Context,
    AssistantMessage,
    StreamOptions,
    SimpleStreamOptions,
    ThinkingLevel,
    ModelInfo,
    UserMessage,
    TextContent,
    CacheRetention,
)
from koda.ai.event_stream import AssistantMessageEventStream
from koda.ai.provider_base import BaseProvider
from koda.ai.registry import get_model_registry


async def stream(
    model: str,
    messages: List,
    options: Optional[StreamOptions] = None
) -> AssistantMessageEventStream:
    """
    Stream response from model.

    Args:
        model: Model ID (e.g., "claude-3-opus", "gpt-4")
        messages: List of messages
        options: Stream options

    Returns:
        AssistantMessageEventStream event stream
    """
    registry = get_model_registry()
    model_info = registry.get(model)

    if not model_info:
        raise ValueError(f"Unknown model: {model}")

    provider = registry.get_provider_for_model(model)
    context = Context(messages=messages)

    return await provider.stream(model_info, context, options)


async def complete(
    model: str,
    messages: List,
    options: Optional[StreamOptions] = None
) -> AssistantMessage:
    """
    Complete and return full response.

    Args:
        model: Model ID
        messages: List of messages
        options: Stream options

    Returns:
        Complete AssistantMessage
    """
    event_stream = await stream(model, messages, options)
    return await event_stream.collect()


async def stream_simple(
    prompt: str,
    model: str = "auto",
    options: Optional[SimpleStreamOptions] = None
) -> AsyncIterator[str]:
    """
    Simple streaming interface - yields text chunks.

    Args:
        prompt: User prompt
        model: Model ID or "auto" for automatic selection
        options: Simple stream options

    Yields:
        Text chunks
    """
    registry = get_model_registry()

    # Resolve model
    if model == "auto":
        model_info = registry.get_default()
    else:
        model_info = registry.get(model)

    if not model_info:
        raise ValueError(f"Unknown model: {model}")

    provider = registry.get_provider_for_model(model_info.id)

    # Build context
    messages = [UserMessage(
        role="user",
        content=prompt,
        timestamp=int(asyncio.get_event_loop().time() * 1000)
    )]
    context = Context(messages=messages)

    # Apply options
    stream_options = options or SimpleStreamOptions()
    if stream_options.reasoning and not provider.supports_thinking_level(stream_options.reasoning):
        # Fall back to no reasoning if not supported
        stream_options.reasoning = None

    # Stream response
    event_stream = await provider.stream(model_info, context, stream_options)

    async for event in event_stream:
        if event.type == "text_delta":
            if event.delta:
                yield event.delta
        elif event.type == "done":
            break
        elif event.type == "error":
            raise event.error or Exception("Stream error")


async def complete_simple(
    prompt: str,
    model: str = "auto",
    options: Optional[SimpleStreamOptions] = None
) -> str:
    """
    Simple completion interface - returns full text.

    Args:
        prompt: User prompt
        model: Model ID or "auto"
        options: Simple stream options

    Returns:
        Complete response text
    """
    chunks = []
    async for chunk in stream_simple(prompt, model, options):
        chunks.append(chunk)
    return "".join(chunks)


class UnifiedClient:
    """
    Unified client for LLM operations.

    Provides a convenient interface for common operations.

    Usage:
        client = UnifiedClient()

        # Simple completion
        response = await client.ask("What is Python?")

        # Streaming
        async for chunk in client.ask_stream("Write a poem"):
            print(chunk, end="")

        # With specific model
        response = await client.ask("Hello", model="claude-3-opus")

        # With context
        response = await client.chat([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"}
        ])
    """

    def __init__(
        self,
        default_model: str = "auto",
        default_options: Optional[SimpleStreamOptions] = None
    ):
        self.default_model = default_model
        self.default_options = default_options or SimpleStreamOptions()

    async def ask(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[SimpleStreamOptions] = None
    ) -> str:
        """
        Ask a question and get complete response.

        Args:
            prompt: User prompt
            model: Model ID (uses default if not specified)
            options: Stream options

        Returns:
            Response text
        """
        return await complete_simple(
            prompt,
            model=model or self.default_model,
            options=options or self.default_options
        )

    async def ask_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[SimpleStreamOptions] = None
    ) -> AsyncIterator[str]:
        """
        Ask a question and stream response.

        Args:
            prompt: User prompt
            model: Model ID
            options: Stream options

        Yields:
            Text chunks
        """
        async for chunk in stream_simple(
            prompt,
            model=model or self.default_model,
            options=options or self.default_options
        ):
            yield chunk

    async def chat(
        self,
        messages: List[Union[dict, UserMessage]],
        model: Optional[str] = None,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessage:
        """
        Chat with message history.

        Args:
            messages: List of messages (dict or UserMessage)
            model: Model ID
            options: Stream options

        Returns:
            Complete assistant message
        """
        # Normalize messages
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                normalized.append(UserMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=int(asyncio.get_event_loop().time() * 1000)
                ))
            else:
                normalized.append(msg)

        return await complete(
            model or self.default_model,
            normalized,
            options
        )

    async def chat_stream(
        self,
        messages: List[Union[dict, UserMessage]],
        model: Optional[str] = None,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Chat with streaming response.

        Args:
            messages: List of messages
            model: Model ID
            options: Stream options

        Returns:
            Event stream
        """
        # Normalize messages
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                normalized.append(UserMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=int(asyncio.get_event_loop().time() * 1000)
                ))
            else:
                normalized.append(msg)

        return await stream(
            model or self.default_model,
            normalized,
            options
        )


# Convenience function to create client
def create_client(
    default_model: str = "auto",
    default_options: Optional[SimpleStreamOptions] = None
) -> UnifiedClient:
    """Create unified client."""
    return UnifiedClient(default_model, default_options)
