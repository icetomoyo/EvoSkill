"""
OpenAI Responses API Provider
Distinct from Completions API - supports reasoning, store parameter, etc.
Equivalent to Pi Mono's openai-responses.ts
"""
import json
import os
from typing import Optional, Dict, Any, List
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
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


class OpenAIResponsesProvider(BaseProvider):
    """
    OpenAI Responses API Provider
    
    Distinct from Completions API. Features:
    - Built-in reasoning (o-series models)
    - Store parameter for training data opt-out
    - Developer messages instead of system
    - Output item structure different from completions
    
    Endpoint: POST https://api.openai.com/v1/responses
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.base_url = config.base_url if config and config.base_url else "https://api.openai.com/v1"
        self.api_key = config.api_key if config and config.api_key else os.getenv("OPENAI_API_KEY")
    
    @property
    def api_type(self) -> str:
        return "openai-responses"
    
    @property
    def provider_id(self) -> str:
        return "openai"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost based on model pricing"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """o-series models support reasoning"""
        return model.id.startswith("o") and "gpt" not in model.id.lower()
    
    def supports_cache_retention(self) -> bool:
        return False
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """Stream responses from Responses API"""
        stream = AssistantMessageEventStream()
        asyncio.create_task(self._stream_responses(model, context, options, stream))
        return stream
    
    async def _stream_responses(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming for Responses API"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Build request payload
            payload = self._build_payload(model, context, options, stream=True)
            
            headers = self.get_default_headers()
            auth_header = self.get_auth_header()
            if auth_header:
                headers.update(auth_header)
            
            if options and options.headers:
                headers.update(options.headers)
            
            endpoint = f"{self.base_url}/responses"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI Responses API error: {response.status} - {error_text}")
                    
                    # Parse SSE stream - different format from completions
                    output_items: List[Dict] = []
                    current_item_index: Optional[int] = None
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if not line or line == "data: [DONE]":
                            continue
                        
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            
                            # Handle different event types in Responses API
                            event_type = data.get("type")
                            
                            if event_type == "response.created":
                                # Initial response metadata
                                response_data = data.get("response", {})
                                if "usage" in response_data:
                                    usage_data = response_data["usage"]
                                    message.usage.input = usage_data.get("input_tokens", 0)
                                    message.usage.output = usage_data.get("output_tokens", 0)
                                    message.usage.total_tokens = usage_data.get("total_tokens", 0)
                            
                            elif event_type == "response.output_item.added":
                                # New output item (message, reasoning, function_call)
                                item = data.get("item", {})
                                item_type = item.get("type")
                                
                                if item_type == "message":
                                    # Standard message
                                    text_content = TextContent(type="text", text="")
                                    message.content.append(text_content)
                                    current_item_index = len(message.content) - 1
                                    self._emit_text_start(stream, message, current_item_index)
                                
                                elif item_type == "reasoning":
                                    # Reasoning content (o-series)
                                    thinking_content = ThinkingContent(type="thinking", thinking="")
                                    message.content.append(thinking_content)
                                    current_item_index = len(message.content) - 1
                                    self._emit_thinking_start(stream, message, current_item_index)
                                
                                elif item_type == "function_call":
                                    # Tool call
                                    tool_call = ToolCall(
                                        type="toolCall",
                                        id=item.get("call_id", ""),
                                        name=item.get("name", ""),
                                        arguments={}
                                    )
                                    idx = len(message.content)
                                    message.content.append(tool_call)
                                    self._emit_toolcall_start(stream, message, idx, tool_call)
                                    current_item_index = idx
                                
                                output_items.append(item)
                            
                            elif event_type == "response.output_text.delta":
                                # Text content delta
                                delta = data.get("delta", "")
                                item_index = data.get("output_index", 0)
                                
                                if current_item_index is not None:
                                    self._emit_text_delta(stream, message, current_item_index, delta)
                            
                            elif event_type == "response.reasoning_summary_part.added":
                                # Reasoning summary part
                                part = data.get("part", {})
                                text = part.get("text", "")
                                
                                if current_item_index is not None:
                                    self._emit_thinking_delta(stream, message, current_item_index, text)
                            
                            elif event_type == "response.function_call_arguments.delta":
                                # Function arguments delta
                                delta = data.get("delta", "")
                                
                                if current_item_index is not None:
                                    self._emit_toolcall_delta(stream, message, current_item_index, delta)
                            
                            elif event_type == "response.output_item.done":
                                # Output item completed
                                item_index = data.get("output_index", 0)
                                item = data.get("item", {})
                                
                                if item.get("type") == "message" and current_item_index is not None:
                                    content = message.content[current_item_index]
                                    if content.type == "text":
                                        self._emit_text_end(stream, message, current_item_index, content.text)
                                
                                elif item.get("type") == "reasoning" and current_item_index is not None:
                                    self._emit_thinking_end(stream, message, current_item_index)
                                
                                elif item.get("type") == "function_call":
                                    # Parse final arguments
                                    args_text = item.get("arguments", "{}")
                                    try:
                                        args = json.loads(args_text)
                                    except json.JSONDecodeError:
                                        args = {}
                                    
                                    if current_item_index is not None:
                                        message.content[current_item_index].arguments = args
                                        self._emit_toolcall_end(
                                            stream, message, current_item_index, message.content[current_item_index]
                                        )
                            
                            elif event_type == "response.completed":
                                # Response completed
                                response_data = data.get("response", {})
                                
                                # Update final usage
                                if "usage" in response_data:
                                    usage_data = response_data["usage"]
                                    message.usage.input = usage_data.get("input_tokens", 0)
                                    message.usage.output = usage_data.get("output_tokens", 0)
                                    message.usage.total_tokens = usage_data.get("total_tokens", 0)
                                    self.calculate_cost(self._get_model_info(model.id), message.usage)
                                
                                # Determine stop reason
                                status = response_data.get("status", "completed")
                                incomplete_details = response_data.get("incomplete_details", {})
                                
                                if incomplete_details.get("reason") == "max_output_tokens":
                                    stop_reason = StopReason.LENGTH
                                elif status == "completed":
                                    stop_reason = StopReason.STOP
                                else:
                                    stop_reason = StopReason.STOP
                                
                                self._emit_done(stream, message, stop_reason)
                                return
            
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
        """Build Responses API request payload"""
        payload: Dict[str, Any] = {
            "model": model.id,
            "stream": stream,
        }
        
        # Convert messages to Responses API format
        inputs = self._convert_inputs(context)
        if inputs:
            payload["input"] = inputs
        
        # Add options
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_output_tokens"] = options.max_tokens
            
            # Handle reasoning for o-series models
            if self.supports_thinking_level(ThinkingLevel.MEDIUM) and model.id.startswith("o"):
                payload["reasoning"] = {"effort": "medium"}
            
            # Store parameter (opt-out of training data storage)
            # Default to False for privacy
            payload["store"] = False
        
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
        
        # Include usage in streaming
        if stream:
            payload["stream_options"] = {"include_usage": True}
        
        return payload
    
    def _convert_inputs(self, context: Context) -> List[Dict]:
        """Convert to Responses API input format"""
        inputs = []
        
        # Handle system/developer message
        if context.system_prompt:
            # Responses API uses "developer" role for o-series, "system" for others
            # We'll use "system" for compatibility
            inputs.append({
                "role": "system",
                "content": context.system_prompt
            })
        
        # Convert messages
        for msg in context.messages:
            if msg.role == "user":
                if isinstance(msg.content, str):
                    inputs.append({
                        "role": "user",
                        "content": msg.content
                    })
                else:
                    # Multimodal
                    content = []
                    for item in msg.content:
                        if item.type == "text":
                            content.append({
                                "type": "input_text",
                                "text": item.text
                            })
                        elif item.type == "image":
                            content.append({
                                "type": "input_image",
                                "image_url": f"data:{item.mime_type};base64,{item.data}"
                            })
                    inputs.append({"role": "user", "content": content})
            
            elif msg.role == "assistant":
                # Assistant messages in input are for context
                content = ""
                for item in msg.content:
                    if item.type == "text":
                        content += item.text
                
                if content:
                    inputs.append({
                        "role": "assistant",
                        "content": content
                    })
            
            elif msg.role == "toolResult":
                # Function call output
                output_text = ""
                for item in msg.content:
                    if item.type == "text":
                        output_text = item.text
                
                inputs.append({
                    "type": "function_call_output",
                    "call_id": msg.tool_call_id,
                    "output": output_text
                })
        
        return inputs
    
    def _get_model_info(self, model_id: str) -> ModelInfo:
        """Get model info for cost calculation"""
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


import asyncio
