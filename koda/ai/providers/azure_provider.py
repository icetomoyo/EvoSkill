"""
Azure OpenAI Provider - Azure OpenAI Service
Supports: chat completions with Azure-specific authentication
Equivalent to Pi Mono's azure-openai-responses.ts
"""
import json
import os
from typing import Optional, Dict, Any
import aiohttp

from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    StreamOptions,
    StopReason,
    TextContent,
    ToolCall,
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


class AzureOpenAIProvider(BaseProvider):
    """
    Azure OpenAI Service Provider
    
    Features:
    - Azure AD authentication (preferred)
    - API Key authentication
    - Regional endpoints
    - Deployments (mapped to models)
    
    Environment variables:
    - AZURE_OPENAI_ENDPOINT: https://{resource}.openai.azure.com
    - AZURE_OPENAI_API_KEY: API key (if not using Azure AD)
    - AZURE_OPENAI_AD_TOKEN: Azure AD token
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        
        # Azure endpoint format: https://{resource}.openai.azure.com/openai/deployments/{deployment}
        self.endpoint = config.base_url if config and config.base_url else os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = config.api_key if config and config.api_key else os.getenv("AZURE_OPENAI_API_KEY")
        self.ad_token = os.getenv("AZURE_OPENAI_AD_TOKEN")
        self.api_version = "2024-10-21"  # Latest stable
        
        if not self.endpoint:
            raise ValueError("Azure OpenAI endpoint required. Set AZURE_OPENAI_ENDPOINT or config.base_url")
    
    @property
    def api_type(self) -> str:
        return "azure-openai-responses"
    
    @property
    def provider_id(self) -> str:
        return "azure-openai"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost - Azure has same pricing as OpenAI"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level) -> bool:
        """Depends on deployed model"""
        return False  # Azure doesn't expose o-series yet
    
    def supports_cache_retention(self) -> bool:
        return False
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """Stream completion from Azure OpenAI"""
        stream = AssistantMessageEventStream()
        asyncio.create_task(self._stream_azure(model, context, options, stream))
        return stream
    
    async def _stream_azure(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming for Azure"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Build request
            payload = self._build_payload(model, context, options)
            
            # Build URL with deployment
            # model.id is the deployment name in Azure
            url = f"{self.endpoint}/openai/deployments/{model.id}/chat/completions"
            url += f"?api-version={self.api_version}"
            
            # Headers
            headers = {
                "Content-Type": "application/json",
            }
            
            # Authentication priority: AD Token > API Key
            if self.ad_token:
                headers["Authorization"] = f"Bearer {self.ad_token}"
            elif self.api_key:
                headers["api-key"] = self.api_key
            else:
                raise ValueError("Azure OpenAI requires api-key or Azure AD token")
            
            if options and options.headers:
                headers.update(options.headers)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Azure OpenAI error: {response.status} - {error_text}")
                    
                    # Parse SSE stream (same format as OpenAI)
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
                                            tool_call = ToolCall(
                                                type="toolCall",
                                                id=tool_calls_buffer[idx]["id"],
                                                name="",
                                                arguments={}
                                            )
                                            self._emit_toolcall_start(stream, message, idx, tool_call)
                                        
                                        if "function" in tc_delta:
                                            func = tc_delta["function"]
                                            if "name" in func:
                                                tool_calls_buffer[idx]["name"] += func["name"]
                                            if "arguments" in func:
                                                tool_calls_buffer[idx]["arguments"] += func["arguments"]
                                                self._emit_toolcall_delta(
                                                    stream, message, idx, func["arguments"]
                                                )
                                
                                # Check finish reason
                                finish_reason = choice.get("finish_reason")
                                if finish_reason:
                                    if content_buffer:
                                        self._emit_text_end(stream, message, len(message.content) - 1, content_buffer)
                                    
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
                                    
                                    if "usage" in data:
                                        usage_data = data["usage"]
                                        message.usage.input = usage_data.get("prompt_tokens", 0)
                                        message.usage.output = usage_data.get("completion_tokens", 0)
                                        message.usage.total_tokens = usage_data.get("total_tokens", 0)
                                        self.calculate_cost(self._get_model_info(model.id), message.usage)
                                    
                                    stop_reason = self._map_finish_reason(finish_reason)
                                    self._emit_done(stream, message, stop_reason)
                                    return
            
            self._emit_done(stream, message, StopReason.STOP)
            
        except Exception as e:
            self._emit_error(stream, message if 'message' in locals() else AssistantMessage(), e)
    
    def _build_payload(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build Azure OpenAI request payload"""
        payload: Dict[str, Any] = {
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        
        # Add messages
        messages = self._convert_messages(context.messages)
        if context.system_prompt:
            messages.insert(0, {"role": "system", "content": context.system_prompt})
        payload["messages"] = messages
        
        # Add options
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens
        
        # Add tools
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
        """Convert to Azure format (same as OpenAI)"""
        result = []
        
        for msg in messages:
            if msg.role == "user":
                if isinstance(msg.content, str):
                    result.append({"role": "user", "content": msg.content})
                else:
                    content = []
                    for item in msg.content:
                        if item.type == "text":
                            content.append({"type": "text", "text": item.text})
                        elif item.type == "image":
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{item.mime_type};base64,{item.data}"}
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
                
                assistant_msg = {"role": "assistant"}
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
        """Map finish reason"""
        mapping = {
            "stop": StopReason.STOP,
            "length": StopReason.LENGTH,
            "tool_calls": StopReason.TOOL_USE,
            "content_filter": StopReason.ERROR,
        }
        return mapping.get(reason, StopReason.STOP)
    
    def _get_model_info(self, model_id: str) -> ModelInfo:
        """Get model info"""
        return ModelInfo(
            id=model_id,
            name=model_id,
            api=self.api_type,
            provider=self.provider_id,
            base_url=self.endpoint,
            cost={"input": 2.5, "output": 10.0, "cache_read": 0, "cache_write": 0},
            context_window=128000,
            max_tokens=16384,
        )


import asyncio
