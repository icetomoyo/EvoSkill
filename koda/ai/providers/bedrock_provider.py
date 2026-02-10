"""
AWS Bedrock Provider - Converse Stream API
Supports: Claude, Llama, Mistral, etc. via AWS Bedrock
"""
import json
import os
from typing import Optional, Dict, Any

from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    StreamOptions,
    ThinkingLevel,
    StopReason,
    TextContent,
    ToolCall,
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


class BedrockProvider(BaseProvider):
    """
    AWS Bedrock Converse Stream Provider
    
    Supports:
    - Amazon Bedrock Converse API
    - Multiple models (Claude, Llama, Mistral, etc.)
    - Cross-region inference
    - Streaming
    - Tool use
    
    Equivalent to Pi Mono's amazon-bedrock.ts
    
    Requires AWS credentials configured (via env vars or ~/.aws/credentials)
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.base_url = f"https://bedrock-runtime.{self.region}.amazonaws.com"
        
        # Try to import boto3
        try:
            import boto3
            self.boto3 = boto3
            self.session = boto3.Session()
            self.client = self.session.client(
                service_name="bedrock-runtime",
                region_name=self.region
            )
        except ImportError:
            raise ImportError("boto3 is required for BedrockProvider. Install with: pip install boto3")
    
    @property
    def api_type(self) -> str:
        return "bedrock-converse-stream"
    
    @property
    def provider_id(self) -> str:
        return "amazon-bedrock"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost for Bedrock models"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """Depends on underlying model"""
        return True
    
    def supports_cache_retention(self) -> bool:
        return False
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """Stream completion from Bedrock API"""
        stream = AssistantMessageEventStream()
        
        # Bedrock uses boto3 which is sync, run in thread
        import asyncio
        asyncio.create_task(self._stream_converse(model, context, options, stream))
        
        return stream
    
    async def _stream_converse(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming for Bedrock Converse API"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Build request
            request = self._build_request(model, context, options)
            
            # Run sync boto3 call in thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.converse_stream(**request)
            )
            
            # Process streaming response
            content_buffer = ""
            has_started = False
            
            for event in response["stream"]:
                # Handle metadata
                if "metadata" in event:
                    metadata = event["metadata"]
                    if "usage" in metadata:
                        usage_data = metadata["usage"]
                        message.usage.input = usage_data.get("inputTokens", 0)
                        message.usage.output = usage_data.get("outputTokens", 0)
                        message.usage.total_tokens = message.usage.input + message.usage.output
                
                # Handle content block start
                if "contentBlockStart" in event:
                    start = event["contentBlockStart"]
                    if "start" in start and "toolUse" in start["start"]:
                        # Tool use starting
                        tool_use = start["start"]["toolUse"]
                        tool_call = ToolCall(
                            type="toolCall",
                            id=tool_use.get("toolUseId", ""),
                            name=tool_use.get("name", ""),
                            arguments={}
                        )
                        idx = len(message.content)
                        message.content.append(tool_call)
                        self._emit_toolcall_start(stream, message, idx, tool_call)
                
                # Handle content block delta
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"]["delta"]
                    
                    if "text" in delta:
                        if not has_started:
                            text_content = TextContent(type="text", text="")
                            message.content.append(text_content)
                            self._emit_text_start(stream, message, len(message.content) - 1)
                            has_started = True
                        
                        text = delta["text"]
                        content_buffer += text
                        self._emit_text_delta(stream, message, len(message.content) - 1, text)
                    
                    if "toolUse" in delta:
                        # Tool input JSON
                        tool_input = delta["toolUse"].get("input", "")
                        if tool_input:
                            # Find the last tool call
                            for i in range(len(message.content) - 1, -1, -1):
                                if message.content[i].type == "toolCall":
                                    self._emit_toolcall_delta(stream, message, i, tool_input)
                                    break
                
                # Handle content block stop
                if "contentBlockStop" in event:
                    if has_started and content_buffer:
                        self._emit_text_end(stream, message, len(message.content) - 1, content_buffer)
                        content_buffer = ""
                        has_started = False
                
                # Handle message stop
                if "messageStop" in event:
                    stop_reason = event["messageStop"].get("stopReason", "end_turn")
                    reason_map = {
                        "end_turn": StopReason.STOP,
                        "max_tokens": StopReason.LENGTH,
                        "stop_sequence": StopReason.STOP,
                        "tool_use": StopReason.TOOL_USE,
                    }
                    mapped_reason = reason_map.get(stop_reason, StopReason.STOP)
                    
                    self.calculate_cost(model, message.usage)
                    self._emit_done(stream, message, mapped_reason)
                    return
            
            self._emit_done(stream, message, StopReason.STOP)
        
        except Exception as e:
            self._emit_error(stream, message if 'message' in locals() else AssistantMessage(), e)
    
    def _build_request(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build Bedrock Converse API request"""
        request: Dict[str, Any] = {
            "modelId": model.id,
            "messages": self._convert_messages(context.messages),
        }
        
        # Add system prompt
        if context.system_prompt:
            request["system"] = [{"text": context.system_prompt}]
        
        # Add inference config
        inference_config = {}
        if options:
            if options.temperature is not None:
                inference_config["temperature"] = options.temperature
            if options.max_tokens is not None:
                inference_config["maxTokens"] = options.max_tokens
        
        if inference_config:
            request["inferenceConfig"] = inference_config
        
        # Add tools
        if context.tools:
            request["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": {"json": tool.parameters}
                        }
                    }
                    for tool in context.tools
                ]
            }
        
        return request
    
    def _convert_messages(self, messages: list) -> list:
        """Convert messages to Bedrock format"""
        result = []
        
        for msg in messages:
            if msg.role == "user":
                content = self._convert_content(msg.content)
                result.append({"role": "user", "content": content})
            
            elif msg.role == "assistant":
                content = []
                for item in msg.content:
                    if item.type == "text":
                        content.append({"text": item.text})
                    elif item.type == "toolCall":
                        content.append({
                            "toolUse": {
                                "toolUseId": item.id,
                                "name": item.name,
                                "input": item.arguments
                            }
                        })
                
                if content:
                    result.append({"role": "assistant", "content": content})
            
            elif msg.role == "toolResult":
                content = []
                for item in msg.content:
                    if item.type == "text":
                        content.append({
                            "toolResult": {
                                "toolUseId": msg.tool_call_id,
                                "content": [{"text": item.text}],
                                "status": "error" if msg.is_error else "success"
                            }
                        })
                    elif item.type == "image":
                        content.append({
                            "toolResult": {
                                "toolUseId": msg.tool_call_id,
                                "content": [{
                                    "image": {
                                        "format": item.mime_type.split("/")[-1],
                                        "source": {"bytes": item.data}
                                    }
                                }]
                            }
                        })
                
                if content:
                    result.append({"role": "user", "content": content})
        
        return result
    
    def _convert_content(self, content) -> list:
        """Convert content to Bedrock format"""
        if isinstance(content, str):
            return [{"text": content}]
        
        result = []
        for item in content:
            if item.type == "text":
                result.append({"text": item.text})
            elif item.type == "image":
                # Bedrock uses different image format
                format_map = {
                    "image/jpeg": "jpeg",
                    "image/png": "png",
                    "image/gif": "gif",
                    "image/webp": "webp",
                }
                image_format = format_map.get(item.mime_type, "jpeg")
                result.append({
                    "image": {
                        "format": image_format,
                        "source": {"bytes": item.data}
                    }
                })
        
        return result


import asyncio
