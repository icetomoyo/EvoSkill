"""
Google Gemini CLI Provider
Equivalent to Pi Mono's packages/ai/src/providers/gemini-cli.ts

Provider for Google Gemini CLI (google-generativeai SDK).
"""
import asyncio
import json
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass

from ..types import (
    AssistantMessage,
    Context,
    ModelInfo,
    StopReason,
    StreamOptions,
    TextContent,
    ToolCall,
    ToolResultMessage,
)
from ..event_stream import AssistantMessageEventStream


@dataclass
class GeminiConfig:
    """Gemini CLI configuration"""
    api_key: Optional[str] = None
    base_url: str = "https://generativelanguage.googleapis.com"
    api_version: str = "v1beta"


class GeminiCLIProvider:
    """
    Google Gemini CLI Provider.
    
    Uses the google-generativeai SDK or REST API directly.
    
    Example:
        >>> provider = GeminiCLIProvider(api_key="your-key")
        >>> stream = await provider.stream(model, context, options)
        >>> async for event in stream:
        ...     print(event)
    """
    
    api_type = "google-gemini-cli"
    
    def __init__(self, config: Optional[GeminiConfig] = None):
        self.config = config or GeminiConfig()
        self._client = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if google-generativeai is available"""
        try:
            import google.generativeai as genai
            self._genai = genai
            self._has_sdk = True
        except ImportError:
            self._has_sdk = False
            self._genai = None
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Stream response from Gemini.
        
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
                api_key = self.config.api_key
            
            if not api_key:
                raise ValueError("Gemini API key required")
            
            if self._has_sdk:
                await self._stream_with_sdk(model, context, options, api_key, stream)
            else:
                await self._stream_with_rest(model, context, options, api_key, stream)
                
        except Exception as e:
            stream.push({
                "type": "error",
                "error": str(e)
            })
            stream.end()
    
    async def _stream_with_sdk(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        api_key: str,
        stream: AssistantMessageEventStream
    ):
        """Stream using google-generativeai SDK"""
        # Configure SDK
        self._genai.configure(api_key=api_key)
        
        # Create model
        gemini_model = self._genai.GenerativeModel(model.id)
        
        # Build contents
        contents = self._build_contents(context)
        
        # Generation config
        generation_config = self._build_generation_config(options)
        
        # Start streaming
        stream.push({"type": "start"})
        
        response_stream = gemini_model.generate_content(
            contents,
            generation_config=generation_config,
            stream=True
        )
        
        full_text = ""
        for chunk in response_stream:
            if chunk.text:
                full_text += chunk.text
                stream.push({
                    "type": "text_delta",
                    "delta": chunk.text
                })
        
        # Build final message
        message = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text=full_text)],
            model=model.id,
            provider="google-gemini-cli",
            stop_reason=StopReason.STOP,
            timestamp=0
        )
        
        stream.push({
            "type": "done",
            "message": message
        })
        stream.end()
    
    async def _stream_with_rest(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        api_key: str,
        stream: AssistantMessageEventStream
    ):
        """Stream using REST API directly"""
        import aiohttp
        
        url = f"{self.config.base_url}/{self.config.api_version}/models/{model.id}:streamGenerateContent"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
        
        payload = self._build_rest_payload(context, options)
        
        stream.push({"type": "start"})
        
        full_text = ""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error {response.status}: {error_text}")
                
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        candidates = data.get("candidates", [])
                        
                        for candidate in candidates:
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])
                            
                            for part in parts:
                                if "text" in part:
                                    text = part["text"]
                                    full_text += text
                                    stream.push({
                                        "type": "text_delta",
                                        "delta": text
                                    })
                    except json.JSONDecodeError:
                        continue
        
        # Build final message
        message = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text=full_text)],
            model=model.id,
            provider="google-gemini-cli",
            stop_reason=StopReason.STOP,
            timestamp=0
        )
        
        stream.push({
            "type": "done",
            "message": message
        })
        stream.end()
    
    def _build_contents(self, context: Context) -> List[Dict[str, Any]]:
        """Build contents for Gemini API"""
        contents = []
        
        # System prompt
        if context.system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {context.system_prompt}"}]
            })
        
        # Messages
        for msg in context.messages:
            role = "user" if msg.get("role") in ("user", "system") else "model"
            content = msg.get("content", "")
            
            if isinstance(content, str):
                contents.append({
                    "role": role,
                    "parts": [{"text": content}]
                })
            elif isinstance(content, list):
                # Handle content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                
                if text_parts:
                    contents.append({
                        "role": role,
                        "parts": [{"text": "\n".join(text_parts)}]
                    })
        
        return contents
    
    def _build_generation_config(self, options: Optional[StreamOptions]) -> Dict[str, Any]:
        """Build generation config"""
        config = {}
        
        if options:
            if options.get("temperature") is not None:
                config["temperature"] = options["temperature"]
            if options.get("max_tokens"):
                config["max_output_tokens"] = options["max_tokens"]
        
        return config
    
    def _build_rest_payload(
        self,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build REST API payload"""
        contents = self._build_contents(context)
        
        payload = {
            "contents": contents,
            "generationConfig": {}
        }
        
        if options:
            if options.get("temperature") is not None:
                payload["generationConfig"]["temperature"] = options["temperature"]
            if options.get("max_tokens"):
                payload["generationConfig"]["maxOutputTokens"] = options["max_tokens"]
        
        return payload
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available Gemini models"""
        return [
            {
                "id": "gemini-2.0-flash-exp",
                "name": "Gemini 2.0 Flash",
                "context_window": 1048576,
                "max_tokens": 8192,
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "context_window": 2097152,
                "max_tokens": 8192,
            },
            {
                "id": "gemini-1.5-flash",
                "name": "Gemini 1.5 Flash",
                "context_window": 1048576,
                "max_tokens": 8192,
            },
        ]


__all__ = ["GeminiCLIProvider", "GeminiConfig"]
