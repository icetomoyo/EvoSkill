"""
Google Provider - Gemini API, Vertex AI, and Gemini CLI
Supports: text, vision, tools, streaming
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
    ToolCall,
    ImageContent,
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


class GoogleProvider(BaseProvider):
    """
    Google Generative AI Provider
    
    Supports:
    - Gemini API (google-generative-ai)
    - Vertex AI (google-vertex)
    - Gemini CLI (google-gemini-cli)
    
    Equivalent to Pi Mono's google*.ts files
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None, api_type: str = "google-generative-ai"):
        super().__init__(config)
        self._api_type = api_type
        
        if config and config.base_url:
            self.base_url = config.base_url
        elif api_type == "google-generative-ai":
            self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        elif api_type == "google-vertex":
            # Vertex AI uses regional endpoints
            region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            self.base_url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}"
        else:
            self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        self.api_key = config.api_key if config and config.api_key else os.getenv("GOOGLE_API_KEY")
    
    @property
    def api_type(self) -> str:
        return self._api_type
    
    @property
    def provider_id(self) -> str:
        return "google"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost for Google models"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """Gemini 2.0+ supports thinking"""
        return True  # Gemini models support thinking
    
    def supports_cache_retention(self) -> bool:
        return False  # Google doesn't have explicit cache retention
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """Stream completion from Google API"""
        stream = AssistantMessageEventStream()
        asyncio.create_task(self._stream_generate(model, context, options, stream))
        return stream
    
    async def _stream_generate(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming for Google Generative AI"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Build request
            payload = self._build_payload(model, context, options)
            
            # Determine endpoint
            if self._api_type == "google-generative-ai":
                endpoint = f"{self.base_url}/models/{model.id}:streamGenerateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
            else:
                # Vertex AI
                endpoint = f"{self.base_url}/publishers/google/models/{model.id}:streamGenerateContent"
                headers = self._get_vertex_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Google API error: {response.status} - {error_text}")
                    
                    # Parse streaming response
                    content_buffer = ""
                    has_started = False
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        
                        try:
                            data = json.loads(line)
                            
                            if "candidates" in data and len(data["candidates"]) > 0:
                                candidate = data["candidates"][0]
                                
                                if "content" in candidate:
                                    content = candidate["content"]
                                    
                                    if "parts" in content:
                                        for part in content["parts"]:
                                            # Handle text
                                            if "text" in part:
                                                if not has_started:
                                                    text_content = TextContent(type="text", text="")
                                                    message.content.append(text_content)
                                                    self._emit_text_start(stream, message, len(message.content) - 1)
                                                    has_started = True
                                                
                                                delta = part["text"]
                                                content_buffer += delta
                                                self._emit_text_delta(
                                                    stream, message, len(message.content) - 1, delta
                                                )
                                            
                                            # Handle function call (tool)
                                            if "functionCall" in part:
                                                func = part["functionCall"]
                                                tool_call = ToolCall(
                                                    type="toolCall",
                                                    id=func.get("name", "call_0"),
                                                    name=func.get("name", ""),
                                                    arguments=func.get("args", {})
                                                )
                                                idx = len(message.content)
                                                message.content.append(tool_call)
                                                self._emit_toolcall_start(stream, message, idx, tool_call)
                                                self._emit_toolcall_end(stream, message, idx, tool_call)
                                    
                                    # Check finish reason
                                    if candidate.get("finishReason"):
                                        if has_started:
                                            self._emit_text_end(stream, message, len(message.content) - 1, content_buffer)
                                        
                                        # Map finish reason
                                        reason_map = {
                                            "STOP": StopReason.STOP,
                                            "MAX_TOKENS": StopReason.LENGTH,
                                            "SAFETY": StopReason.ERROR,
                                            "RECITATION": StopReason.ERROR,
                                            "OTHER": StopReason.ERROR,
                                        }
                                        stop_reason = reason_map.get(
                                            candidate["finishReason"],
                                            StopReason.STOP
                                        )
                                        
                                        # Get usage if available
                                        if "usageMetadata" in data:
                                            usage_meta = data["usageMetadata"]
                                            message.usage.input = usage_meta.get("promptTokenCount", 0)
                                            message.usage.output = usage_meta.get("candidatesTokenCount", 0)
                                            message.usage.total_tokens = usage_meta.get("totalTokenCount", 0)
                                        
                                        self._emit_done(stream, message, stop_reason)
                                        return
                        
                        except json.JSONDecodeError:
                            continue
                    
                    # End of stream
                    if has_started:
                        self._emit_text_end(stream, message, len(message.content) - 1, content_buffer)
                    self._emit_done(stream, message, StopReason.STOP)
        
        except Exception as e:
            self._emit_error(stream, message if 'message' in locals() else AssistantMessage(), e)
    
    def _build_payload(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build Google API request payload"""
        # Convert messages to Google format
        contents = self._convert_messages(context.messages)
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {},
        }
        
        # Add system instruction
        if context.system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": context.system_prompt}]
            }
        
        # Add generation config
        if options:
            if options.temperature is not None:
                payload["generationConfig"]["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["generationConfig"]["maxOutputTokens"] = options.max_tokens
        
        # Add tools
        if context.tools:
            payload["tools"] = [{
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                    for tool in context.tools
                ]
            }]
        
        return payload
    
    def _convert_messages(self, messages: list) -> list:
        """Convert messages to Google format"""
        contents = []
        
        for msg in messages:
            if msg.role == "user":
                parts = []
                if isinstance(msg.content, str):
                    parts.append({"text": msg.content})
                else:
                    for item in msg.content:
                        if item.type == "text":
                            parts.append({"text": item.text})
                        elif item.type == "image":
                            parts.append({
                                "inlineData": {
                                    "mimeType": item.mime_type,
                                    "data": item.data
                                }
                            })
                
                contents.append({
                    "role": "user",
                    "parts": parts
                })
            
            elif msg.role == "assistant":
                parts = []
                for item in msg.content:
                    if item.type == "text":
                        parts.append({"text": item.text})
                    elif item.type == "toolCall":
                        parts.append({
                            "functionCall": {
                                "name": item.name,
                                "args": item.arguments
                            }
                        })
                
                if parts:
                    contents.append({
                        "role": "model",
                        "parts": parts
                    })
            
            elif msg.role == "toolResult":
                # Tool results go as function responses
                parts = []
                for item in msg.content:
                    if item.type == "text":
                        parts.append({
                            "functionResponse": {
                                "name": msg.tool_name,
                                "response": {"result": item.text}
                            }
                        })
                
                if parts:
                    contents.append({
                        "role": "user",  # Google uses 'user' for function responses
                        "parts": parts
                    })
        
        return contents
    
    def _get_vertex_headers(self) -> Dict[str, str]:
        """Get headers for Vertex AI authentication"""
        headers = {"Content-Type": "application/json"}
        
        # Try to get token from gcloud or environment
        token = os.getenv("GOOGLE_ACCESS_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        return headers


import asyncio
