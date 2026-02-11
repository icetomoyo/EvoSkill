"""
Google Vertex AI Provider
Equivalent to Pi Mono's packages/ai/src/providers/vertex.ts

Provider for Google Cloud Vertex AI.
"""
import asyncio
import json
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

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


@dataclass
class VertexConfig:
    """Vertex AI configuration"""
    project_id: str
    location: str = "us-central1"
    credentials_path: Optional[str] = None
    credentials_json: Optional[str] = None


class VertexProvider:
    """
    Google Cloud Vertex AI Provider.
    
    Uses Vertex AI SDK or REST API for model inference.
    
    Example:
        >>> config = VertexConfig(project_id="my-project")
        >>> provider = VertexProvider(config)
        >>> stream = await provider.stream(model, context, options)
    """
    
    api_type = "google-vertex"
    
    def __init__(self, config: Optional[VertexConfig] = None):
        self.config = config
        self._client = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if vertexai SDK is available"""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            self._vertexai = vertexai
            self._GenerativeModel = GenerativeModel
            self._has_sdk = True
        except ImportError:
            self._has_sdk = False
            self._vertexai = None
            self._GenerativeModel = None
    
    def _initialize(self):
        """Initialize Vertex AI SDK"""
        if not self._has_sdk or not self.config:
            return
        
        init_kwargs = {
            "project": self.config.project_id,
            "location": self.config.location,
        }
        
        if self.config.credentials_path:
            init_kwargs["credentials"] = self.config.credentials_path
        
        self._vertexai.init(**init_kwargs)
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Stream response from Vertex AI.
        
        Args:
            model: Model configuration
            context: Conversation context
            options: Stream options
            
        Returns:
            Event stream
        """
        stream = AssistantMessageEventStream()
        
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
            if self._has_sdk:
                await self._stream_with_sdk(model, context, options, stream)
            else:
                await self._stream_with_rest(model, context, options, stream)
                
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
        stream: AssistantMessageEventStream
    ):
        """Stream using Vertex AI SDK"""
        self._initialize()
        
        # Create model
        vertex_model = self._GenerativeModel(model.id)
        
        # Build contents
        contents = self._build_contents(context)
        
        # Generation config
        generation_config = self._build_generation_config(options)
        
        # Start streaming
        stream.push({"type": "start"})
        
        # Run in thread pool since SDK is synchronous
        loop = asyncio.get_event_loop()
        
        def generate():
            responses = vertex_model.generate_content(
                contents,
                generation_config=generation_config,
                stream=True
            )
            return list(responses)
        
        responses = await loop.run_in_executor(None, generate)
        
        full_text = ""
        for response in responses:
            if response.text:
                full_text += response.text
                stream.push({
                    "type": "text_delta",
                    "delta": response.text
                })
        
        # Build final message
        message = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text=full_text)],
            model=model.id,
            provider="google-vertex",
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
        stream: AssistantMessageEventStream
    ):
        """Stream using REST API directly"""
        try:
            import aiohttp
            from google.auth import default as google_auth_default
            from google.auth.transport.requests import Request
        except ImportError:
            raise ImportError(
                "Google auth libraries required for Vertex REST API. "
                "Install with: pip install google-auth google-auth-oauthlib"
            )
        
        # Get credentials
        if self.config and self.config.credentials_json:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                self.config.credentials_json
            )
        else:
            credentials, _ = google_auth_default(
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
        
        # Refresh token
        credentials.refresh(Request())
        
        # Build URL
        base_url = f"https://{self.config.location}-aiplatform.googleapis.com"
        url = f"{base_url}/v1/projects/{self.config.project_id}/locations/{self.config.location}/publishers/google/models/{model.id}:streamGenerateContent"
        
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }
        
        payload = self._build_rest_payload(context, options)
        
        stream.push({"type": "start"})
        
        full_text = ""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Vertex API error {response.status}: {error_text}")
                
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
            provider="google-vertex",
            stop_reason=StopReason.STOP,
            timestamp=0
        )
        
        stream.push({
            "type": "done",
            "message": message
        })
        stream.end()
    
    def _build_contents(self, context: Context) -> List[Any]:
        """Build contents for Vertex API"""
        contents = []
        
        for msg in context.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if isinstance(content, str):
                if role == "user":
                    contents.append({"role": "user", "parts": [{"text": content}]})
                else:
                    contents.append({"role": "model", "parts": [{"text": content}]})
        
        return contents
    
    def _build_generation_config(self, options: Optional[StreamOptions]) -> Dict[str, Any]:
        """Build generation config"""
        config = {}
        
        if options:
            if options.get("temperature") is not None:
                config["temperature"] = options["temperature"]
            if options.get("max_tokens"):
                config["max_output_tokens"] = options["max_tokens"]
            if options.get("top_p") is not None:
                config["top_p"] = options["top_p"]
        
        return config
    
    def _build_rest_payload(
        self,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build REST API payload"""
        contents = []
        
        for msg in context.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if isinstance(content, str):
                vertex_role = "user" if role in ("user", "system") else "model"
                contents.append({
                    "role": vertex_role,
                    "parts": [{"text": content}]
                })
        
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
        """List available Vertex AI models"""
        return [
            {
                "id": "gemini-1.5-pro-001",
                "name": "Gemini 1.5 Pro",
                "context_window": 2097152,
                "max_tokens": 8192,
            },
            {
                "id": "gemini-1.5-flash-001",
                "name": "Gemini 1.5 Flash",
                "context_window": 1048576,
                "max_tokens": 8192,
            },
            {
                "id": "gemini-1.0-pro-001",
                "name": "Gemini 1.0 Pro",
                "context_window": 32768,
                "max_tokens": 2048,
            },
        ]


__all__ = ["VertexProvider", "VertexConfig"]
