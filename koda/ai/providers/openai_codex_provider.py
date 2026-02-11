"""
OpenAI Codex Provider
Equivalent to Pi Mono's packages/ai/src/providers/openai-codex-responses.ts

Supports OpenAI Codex Responses API for coding tasks.
"""
import asyncio
import json
from typing import AsyncIterator, Optional, Dict, Any
import aiohttp

from ..types import (
    AssistantMessage,
    Context,
    ModelInfo,
    StopReason,
    StreamOptions,
    TextContent,
    ToolCall,
)
from ..event_stream import AssistantMessageEventStream


class OpenAICodexProvider:
    """
    OpenAI Codex Responses API Provider.
    
    Codex is OpenAI's code-specialized model with built-in tool use.
    """
    
    api_type = "openai-codex-responses"
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.openai.com"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Stream response from Codex API.
        
        Args:
            model: Model configuration
            context: Conversation context
            options: Stream options
            
        Returns:
            Event stream
        """
        stream = AssistantMessageEventStream()
        
        # Start streaming in background
        asyncio.create_task(
            self._stream_response(model, context, options, stream)
        )
        
        return stream
    
    async def _stream_response(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ):
        """Internal streaming implementation"""
        try:
            api_key = options.get("api_key") if options else None
            if not api_key:
                api_key = self.api_key
            
            if not api_key:
                raise ValueError("OpenAI API key required")
            
            # Build request payload
            payload = self._build_payload(model, context, options)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/responses",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error {response.status}: {error_text}")
                    
                    # Process SSE stream
                    buffer = ""
                    async for chunk in response.content:
                        buffer += chunk.decode("utf-8")
                        lines = buffer.split("\n")
                        buffer = lines.pop()
                        
                        for line in lines:
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    event = json.loads(data)
                                    self._process_event(event, stream)
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            stream.push({
                "type": "error",
                "error": str(e)
            })
            stream.end()
    
    def _build_payload(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build API request payload"""
        payload = {
            "model": model.id,
            "input": self._convert_messages(context),
            "stream": True,
        }
        
        if options:
            if options.get("temperature") is not None:
                payload["temperature"] = options["temperature"]
            if options.get("max_tokens"):
                payload["max_output_tokens"] = options["max_tokens"]
        
        # Add tools if present
        if context.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                }
                for tool in context.tools
            ]
        
        return payload
    
    def _convert_messages(self, context: Context) -> list:
        """Convert context to Codex format"""
        messages = []
        
        # Add system prompt
        if context.system_prompt:
            messages.append({
                "role": "system",
                "content": context.system_prompt
            })
        
        # Add conversation messages
        for msg in context.messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append({"role": role, "content": content})
            else:
                # Handle typed messages
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "")
                if isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                        elif hasattr(block, "text"):
                            text_parts.append(block.text)
                    content = "\n".join(text_parts)
                messages.append({"role": role, "content": content})
        
        return messages
    
    def _process_event(self, event: Dict, stream: AssistantMessageEventStream):
        """Process streaming event"""
        event_type = event.get("type")
        
        if event_type == "response.created":
            stream.push({"type": "start"})
        
        elif event_type == "response.output_text.delta":
            delta = event.get("delta", "")
            stream.push({
                "type": "text_delta",
                "delta": delta
            })
        
        elif event_type == "response.completed":
            # Build final message
            message = AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text="")],
                model=event.get("model", ""),
                provider="openai-codex",
                stop_reason="stop",
                usage=event.get("usage", {}),
                timestamp=0
            )
            stream.push({
                "type": "done",
                "message": message
            })
            stream.end()


__all__ = ["OpenAICodexProvider"]
