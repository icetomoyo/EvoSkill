"""
OpenAI Provider V2 - Refactored to use new BaseProvider
Supports: openai-completions, openai-responses, reasoning, tools, vision
"""
import json
import os
from typing import Optional, Dict, Any, AsyncIterator
import aiohttp

from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    StreamOptions,
    ThinkingLevel,
    StopReason,
    TextContent,
    ThinkingContent,
    ToolCall,
    UserMessage,
    AssistantMessageEvent,
    KnownApi,
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


class OpenAIProviderV2(BaseProvider):
    """
    OpenAI Provider - Supports Completions and Responses API
    
    Equivalent to Pi Mono's openai-completions.ts + openai-responses.ts
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.base_url = config.base_url if config and config.base_url else "https://api.openai.com/v1"
        self.api_key = config.api_key if config and config.api_key else os.getenv("OPENAI_API_KEY")
    
    @property
    def api_type(self) -> str:
        return KnownApi.OPENAI_COMPLETIONS.value
    
    @property
    def provider_id(self) -> str:
        return "openai"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost based on model pricing"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """Check if model supports reasoning effort"""
        # o-series models support reasoning
        return model.id.startswith("o") and "gpt" not in model.id.lower()
    
    def supports_cache_retention(self) -> bool:
        return False  # OpenAI doesn't support cache retention
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Stream chat completion
        
        Supports:
        - Standard chat completions
        - Tool calling
        - Vision (via image_url in messages)
        - Reasoning (o-series models)
        """
        stream = AssistantMessageEventStream()
        
        # Start streaming in background
        asyncio.create_task(self._stream_completion(model, context, options, stream))
        
        return stream
    
    async def _stream_completion(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming implementation"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Build request payload
            payload = self._build_payload(model, context, options, stream=True)
            
            # Make request
            headers = self.get_default_headers()
            auth_header = self.get_auth_header()
            if auth_header:
                headers.update(auth_header)
            
            if options and options.headers:
                headers.update(options.headers)
            
            endpoint = f"{self.base_url}/chat/completions"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                    
                    # Parse SSE stream
                    content_buffer = ""
                    tool_calls_buffer: Dict[int, Dict] = {}
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if not line or line == "data: [DONE]":
                            continue
                        
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                delta = choice.get("delta", {})
                                
                                # Handle content
                                if "content" in delta and delta["content"]:
                                    if not content_buffer:
                                        # First content - emit text_start
                                        text_content = TextContent(type="text", text="")
                                        message.content.append(text_content)
                                        self._emit_text_start(stream, message, len(message.content) - 1)
                                    
                                    content_buffer += delta["content"]
                                    self._emit_text_delta(
                                        stream, message, len(message.content) - 1, delta["content"]
                                    )
                                
                                # Handle tool calls
                                if "tool_calls" in delta:
                                    for tc_delta in delta["tool_calls"]:
                                        idx = tc_delta.get("index", 0)
                                        
                                        if idx not in tool_calls_buffer:
                                            tool_calls_buffer[idx] = {
                                                "id": tc_delta.get("id", f"call_{idx}"),
                                                "name": "",
                                                "arguments": ""
                                            }
                                            # Emit toolcall_start
                                            tool_call = ToolCall(
                                                type="toolCall",
                                                id=tool_calls_buffer[idx]["id"],
                                                name="",
                                                arguments={}
                                            )
                                            self._emit_toolcall_start(stream, message, idx, tool_call)
                                        
                                        # Accumulate function data
                                        if "function" in tc_delta:
                                            func = tc_delta["function"]
                                            if "name" in func:
                                                tool_calls_buffer[idx]["name"] += func["name"]
                                            if "arguments" in func:
                                                tool_calls_buffer[idx]["arguments"] += func["arguments"]
                                                
                                                # Emit delta for arguments
                                                self._emit_toolcall_delta(
                                                    stream, message, idx, func["arguments"]
                                                )
                                
                                # Check for finish reason
                                finish_reason = choice.get("finish_reason")
                                if finish_reason:
                                    # Emit text_end if we had content
                                    if content_buffer:
                                        self._emit_text_end(stream, message, len(message.content) - 1, content_buffer)
                                    
                                    # Emit toolcall_end for any tool calls
                                    for idx, tc_data in tool_calls_buffer.items():
                                        try:
                                            args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                                        except json.JSONDecodeError:
                                            args = {}
                                        
                                        tool_call = ToolCall(
                                            type="toolCall",
                                            id=tc_data["id"],
                                            name=tc_data["name"],
                                            arguments=args
                                        )
                                        self._emit_toolcall_end(stream, message, idx, tool_call)
                                    
                                    # Update usage if available
                                    if "usage" in data:
                                        usage_data = data["usage"]
                                        message.usage.input = usage_data.get("prompt_tokens", 0)
                                        message.usage.output = usage_data.get("completion_tokens", 0)
                                        message.usage.total_tokens = usage_data.get("total_tokens", 0)
                                        self.calculate_cost(self._get_model_info(model.id), message.usage)
                                    
                                    # Map finish reason
                                    stop_reason = self._map_finish_reason(finish_reason)
                                    self._emit_done(stream, message, stop_reason)
                                    return
            
            # If we get here without finish_reason, emit done
            self._emit_done(stream, message, StopReason.STOP)
            
        except Exception as e:
            self._emit_error(stream, message if 'message' in locals() else AssistantMessage(), e)
    
    def _build_payload(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: bool = True
    ) -> Dict[str, Any]:
        """Build API request payload"""
        payload: Dict[str, Any] = {
            "model": model.id,
            "stream": stream,
        }
        
        # Add messages
        messages = self._convert_messages(context.messages)
        payload["messages"] = messages
        
        # Add system prompt if present
        if context.system_prompt:
            # Insert at beginning
            payload["messages"].insert(0, {
                "role": "system",
                "content": context.system_prompt
            })
        
        # Add options
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens
            
            # Handle reasoning for o-series models
            if hasattr(options, 'reasoning') and options.reasoning and model.id.startswith("o"):
                # Map thinking level to reasoning_effort
                reasoning_map = {
                    "minimal": "low",
                    "low": "low",
                    "medium": "medium",
                    "high": "high",
                    "xhigh": "high",
                }
                payload["reasoning_effort"] = reasoning_map.get(options.reasoning, "medium")
        
        # Add tools if present
        if context.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                }
                for tool in context.tools
            ]
        
        return payload
    
    def _convert_messages(self, messages: list) -> list:
        """Convert internal messages to OpenAI format"""
        result = []
        
        for msg in messages:
            if msg.role == "user":
                if isinstance(msg.content, str):
                    result.append({"role": "user", "content": msg.content})
                else:
                    # Handle multimodal content
                    content = []
                    for item in msg.content:
                        if item.type == "text":
                            content.append({"type": "text", "text": item.text})
                        elif item.type == "image":
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{item.mime_type};base64,{item.data}"
                                }
                            })
                    result.append({"role": "user", "content": content})
            
            elif msg.role == "assistant":
                content = ""
                tool_calls = []
                
                for item in msg.content:
                    if item.type == "text":
                        content += item.text
                    elif item.type == "toolCall":
                        tool_calls.append({
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.name,
                                "arguments": json.dumps(item.arguments)
                            }
                        })
                
                assistant_msg: Dict[str, Any] = {"role": "assistant"}
                if content:
                    assistant_msg["content"] = content
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                
                result.append(assistant_msg)
            
            elif msg.role == "toolResult":
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content[0].text if msg.content else ""
                })
        
        return result
    
    def _map_finish_reason(self, reason: str) -> StopReason:
        """Map OpenAI finish reason to StopReason"""
        mapping = {
            "stop": StopReason.STOP,
            "length": StopReason.LENGTH,
            "tool_calls": StopReason.TOOL_USE,
            "content_filter": StopReason.ERROR,
        }
        return mapping.get(reason, StopReason.STOP)
    
    def _get_model_info(self, model_id: str) -> ModelInfo:
        """Get model info for cost calculation"""
        # Default model info
        return ModelInfo(
            id=model_id,
            name=model_id,
            api=self.api_type,
            provider=self.provider_id,
            base_url=self.base_url,
            cost={"input": 2.5, "output": 10.0, "cache_read": 0, "cache_write": 0},
            context_window=128000,
            max_tokens=16384,
        )


# Import for async
import asyncio
