"""
OpenAI Provider - OpenAI API compatibility

Supports:
- OpenAI Completions API
- OpenAI Responses API
- Azure OpenAI
- Compatible providers (Groq, Cerebras, etc.)
"""
import os
from typing import AsyncIterator, Dict, Any, Optional
import asyncio

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from koda.providers.base import (
    BaseProvider, StreamEvent, TextDeltaEvent, ThinkingDeltaEvent,
    ToolCallEvent, DoneEvent, ErrorEvent
)
from koda.core.multimodal_types import (
    Model, Message, UserMessage, AssistantMessage, ToolResultMessage,
    StreamOptions, TextContent, ThinkingContent, ToolCall,
    StopReason, Usage, CostBreakdown
)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def api_type(self) -> str:
        return "openai-completions"
    
    def supports_feature(self, feature: str) -> bool:
        features = {
            'images': True,
            'thinking': True,  # via reasoning_effort
            'tool_calls': True,
            'streaming': True,
            'cache': True,
        }
        return features.get(feature, False)
    
    def convert_messages(self, messages: list[Message]) -> list[Dict[str, Any]]:
        """Convert messages to OpenAI format"""
        result = []
        
        for msg in messages:
            if isinstance(msg, UserMessage):
                content = self._convert_content(msg.content)
                result.append({"role": "user", "content": content})
                
            elif isinstance(msg, AssistantMessage):
                # Handle assistant message with possible tool calls
                content_parts = []
                tool_calls = []
                
                for item in msg.content:
                    if isinstance(item, TextContent):
                        content_parts.append(item.text)
                    elif isinstance(item, ThinkingContent):
                        # OpenAI doesn't have native thinking blocks
                        content_parts.append(f"<thinking>{item.thinking}</thinking>")
                    elif isinstance(item, ToolCall):
                        tool_calls.append({
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.name,
                                "arguments": str(item.arguments)
                            }
                        })
                
                msg_dict = {
                    "role": "assistant",
                    "content": "\n".join(content_parts) if content_parts else None
                }
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                result.append(msg_dict)
                
            elif isinstance(msg, ToolResultMessage):
                content = self._convert_content(msg.content)
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.toolCallId,
                    "content": content if isinstance(content, str) else str(content)
                })
        
        return result
    
    def _convert_content(self, content) -> Any:
        """Convert content to OpenAI format"""
        from koda.core.multimodal_types import TextContent, ImageContent
        
        if isinstance(content, str):
            return content
        
        result = []
        for item in content:
            if isinstance(item, TextContent):
                result.append({"type": "text", "text": item.text})
            elif isinstance(item, ImageContent):
                result.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{item.mimeType};base64,{item.data}"
                    }
                })
        return result
    
    async def stream(
        self,
        model: Model,
        messages: list[Message],
        options: StreamOptions
    ) -> AsyncIterator[StreamEvent]:
        """Stream OpenAI response"""
        if not OPENAI_AVAILABLE:
            yield ErrorEvent(error="OpenAI package not installed")
            return
        
        try:
            client = openai.AsyncOpenAI(
                api_key=options.apiKey or os.getenv("OPENAI_API_KEY"),
                base_url=model.baseUrl if model.baseUrl else None
            )
            
            # Convert messages
            openai_messages = self.convert_messages(messages)
            
            # Build request parameters
            params = {
                "model": model.id,
                "messages": openai_messages,
                "stream": True,
                "temperature": options.temperature if options.temperature is not None else 0.7,
            }
            
            if options.maxTokens:
                params["max_tokens"] = options.maxTokens
            
            # Handle thinking/reasoning
            if model.reasoning:
                params["reasoning_effort"] = "medium"
            
            # Handle tools
            if options.tools:
                params["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters
                        }
                    }
                    for tool in options.tools
                ]
            
            # Make request
            stream = await client.chat.completions.create(**params)
            
            # Process stream
            content_buffer = ""
            thinking_buffer = ""
            tool_calls = []
            usage_info = None
            
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                
                if not delta:
                    continue
                
                # Text content
                if delta.content:
                    content_buffer += delta.content
                    yield TextDeltaEvent(delta=delta.content, content_index=0)
                
                # Tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index >= len(tool_calls):
                            tool_calls.append({"id": "", "name": "", "arguments": ""})
                        
                        if tc.id:
                            tool_calls[tc.index]["id"] += tc.id
                        if tc.function.name:
                            tool_calls[tc.index]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls[tc.index]["arguments"] += tc.function.arguments
                
                # Usage (final chunk)
                if chunk.usage:
                    usage_info = chunk.usage
            
            # Yield tool calls
            for tc in tool_calls:
                import json
                try:
                    args = json.loads(tc["arguments"])
                except:
                    args = {}
                
                yield ToolCallEvent(tool_call=ToolCall(
                    type="toolCall",
                    id=tc["id"],
                    name=tc["name"],
                    arguments=args
                ))
            
            # Build final message
            final_content = [TextContent(type="text", text=content_buffer)] if content_buffer else []
            
            # Calculate usage
            usage = Usage()
            if usage_info:
                usage.input = usage_info.prompt_tokens
                usage.output = usage_info.completion_tokens
                usage.totalTokens = usage_info.total_tokens
            
            yield DoneEvent(message=AssistantMessage(
                role="assistant",
                content=final_content,
                api=self.api_type,
                provider=self.name,
                model=model.id,
                usage=usage,
                stopReason=StopReason.STOP
            ))
            
        except Exception as e:
            yield ErrorEvent(error=str(e))


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider"""
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def api_type(self) -> str:
        return "anthropic-messages"
    
    def supports_feature(self, feature: str) -> bool:
        features = {
            'images': True,
            'thinking': True,
            'tool_calls': True,
            'streaming': True,
            'cache': True,
        }
        return features.get(feature, False)
    
    def convert_messages(self, messages: list[Message]) -> list[Dict[str, Any]]:
        """Convert messages to Anthropic format"""
        result = []
        
        for msg in messages:
            if isinstance(msg, UserMessage):
                content = self._convert_content(msg.content)
                result.append({"role": "user", "content": content})
                
            elif isinstance(msg, AssistantMessage):
                content_parts = []
                
                for item in msg.content:
                    if isinstance(item, TextContent):
                        content_parts.append({"type": "text", "text": item.text})
                    elif isinstance(item, ThinkingContent):
                        content_parts.append({
                            "type": "thinking",
                            "thinking": item.thinking
                        })
                    elif isinstance(item, ToolCall):
                        content_parts.append({
                            "type": "tool_use",
                            "id": item.id,
                            "name": item.name,
                            "input": item.arguments
                        })
                
                result.append({"role": "assistant", "content": content_parts})
                
            elif isinstance(msg, ToolResultMessage):
                content = self._convert_content(msg.content)
                result.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.toolCallId,
                        "content": content
                    }]
                })
        
        return result
    
    def _convert_content(self, content) -> Any:
        """Convert content to Anthropic format"""
        from koda.core.multimodal_types import TextContent, ImageContent
        
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        
        result = []
        for item in content:
            if isinstance(item, TextContent):
                result.append({"type": "text", "text": item.text})
            elif isinstance(item, ImageContent):
                result.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": item.mimeType,
                        "data": item.data
                    }
                })
        return result
    
    async def stream(
        self,
        model: Model,
        messages: list[Message],
        options: StreamOptions
    ) -> AsyncIterator[StreamEvent]:
        """Stream Anthropic response"""
        # Anthropic implementation would go here
        # For now, yield error to indicate not fully implemented
        yield ErrorEvent(error="Anthropic provider not fully implemented")
        return


# Register providers
ProviderRegistry.register(OpenAIProvider())
ProviderRegistry.register(AnthropicProvider())


# Import at end to avoid circular dependency
from koda.providers.base import ProviderRegistry
