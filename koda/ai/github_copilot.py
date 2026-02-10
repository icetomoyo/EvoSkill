"""
GitHub Copilot Provider

GitHub Copilot API provider with OAuth authentication.
Based on Pi Mono's GitHub Copilot integration.

Note: GitHub Copilot API is not officially public and may change.
This implementation uses the available endpoints.
"""
import asyncio
import json
import ssl
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from urllib.error import HTTPError

from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    StreamOptions,
    StopReason,
    TextContent,
    ThinkingContent,
    ToolCall,
    KnownApi,
)
from koda.ai.event_stream import AssistantMessageEventStream, EventType, AssistantMessageEvent
from koda.ai.oauth import GitHubCopilotOAuth, OAuthError


@dataclass
class GitHubCopilotConfig(ProviderConfig):
    """GitHub Copilot Provider Configuration"""
    oauth: Optional[GitHubCopilotOAuth] = None
    # Copilot API endpoints
    api_base: str = "https://api.githubcopilot.com"
    chat_endpoint: str = "/chat/completions"
    models_endpoint: str = "/models"


class GitHubCopilotProvider(BaseProvider):
    """
    GitHub Copilot Provider
    
    Provides access to GitHub Copilot models through OAuth authentication.
    
    Features:
    - OAuth-based authentication
    - Streaming responses
    - Code completion and chat
    - Tool calling (limited support)
    
    Usage:
        ```python
        from koda.ai.github_copilot import GitHubCopilotProvider, GitHubCopilotConfig
        from koda.ai.oauth import GitHubCopilotOAuth
        
        # Authenticate
        oauth = GitHubCopilotOAuth()
        tokens = await oauth.authenticate()
        
        # Create provider
        config = GitHubCopilotConfig(oauth=oauth)
        provider = GitHubCopilotProvider(config)
        
        # Use provider
        stream = await provider.stream(model, context)
        ```
    """
    
    # Available Copilot models (as of early 2025)
    DEFAULT_MODELS = {
        "gpt-4o-copilot": {
            "id": "gpt-4o-copilot",
            "name": "GPT-4o Copilot",
            "context_window": 128000,
            "max_tokens": 4096,
            "supports_tools": True,
            "supports_vision": True,
        },
        "gpt-4-copilot": {
            "id": "gpt-4-copilot", 
            "name": "GPT-4 Copilot",
            "context_window": 8192,
            "max_tokens": 4096,
            "supports_tools": True,
            "supports_vision": False,
        },
    }
    
    def __init__(self, config: Optional[GitHubCopilotConfig] = None):
        super().__init__(config)
        self.config: GitHubCopilotConfig = config or GitHubCopilotConfig()
        self._oauth = self.config.oauth or GitHubCopilotOAuth()
        self._ssl_context = ssl.create_default_context()
    
    @property
    def api_type(self) -> str:
        return "github-copilot"
    
    @property
    def provider_id(self) -> str:
        return "github-copilot"
    
    @property
    def is_authenticated(self) -> bool:
        """Check if provider is authenticated"""
        return self._oauth.is_authenticated
    
    async def authenticate(self, timeout: float = 300.0) -> None:
        """
        Authenticate with GitHub Copilot
        
        Args:
            timeout: Authentication timeout in seconds
        """
        await self._oauth.authenticate(timeout)
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Stream response from GitHub Copilot
        
        Args:
            model: Model information
            context: Conversation context
            options: Stream options
            
        Returns:
            AssistantMessageEventStream
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
    ) -> None:
        """Handle streaming response"""
        try:
            # Check authentication
            if not self.is_authenticated:
                raise OAuthError("Not authenticated. Call authenticate() first.")
            
            # Build request
            url = f"{self.config.api_base}{self.config.chat_endpoint}"
            headers = self._build_headers()
            payload = self._build_payload(model, context, options, stream=True)
            
            # Create message
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Make request
            loop = asyncio.get_event_loop()
            response_data = await loop.run_in_executor(
                None,
                lambda: self._make_request(url, headers, payload, stream_response=True)
            )
            
            # Parse SSE stream
            await self._parse_stream(response_data, stream, message)
            
        except Exception as e:
            self._emit_error(stream, message if 'message' in locals() else None, e)
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        token = self._oauth.get_access_token()
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Copilot-Integration-Id": "vscode-chat",  # Required header
            "User-Agent": "Koda/1.0",
        }
    
    def _build_payload(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: bool = True
    ) -> Dict[str, Any]:
        """Build request payload"""
        # Convert messages to OpenAI format
        messages = []
        if context.system_prompt:
            messages.append({
                "role": "system",
                "content": context.system_prompt
            })
        
        for msg in context.messages:
            if hasattr(msg, 'to_dict'):
                messages.append(msg.to_dict())
            else:
                # Fallback conversion
                messages.append({
                    "role": getattr(msg, 'role', 'user'),
                    "content": getattr(msg, 'content', str(msg))
                })
        
        payload: Dict[str, Any] = {
            "model": model.id,
            "messages": messages,
            "stream": stream,
        }
        
        # Add options
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens
        
        # Tools
        if context.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters
                    }
                }
                for t in context.tools
            ]
        
        return payload
    
    def _make_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        stream_response: bool = False
    ) -> Any:
        """
        Make HTTP request (blocking)
        
        Returns response data or generator for streaming
        """
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(
                req,
                context=self._ssl_context,
                timeout=self.config.timeout
            ) as response:
                # Apply rate limits
                self._apply_rate_limits(dict(response.headers))
                
                if stream_response:
                    return response
                else:
                    return json.loads(response.read().decode('utf-8'))
                    
        except HTTPError as e:
            error_body = e.read().decode()
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get("error", {}).get("message", error_body)
            except:
                error_msg = error_body or str(e)
            
            if e.code == 401:
                raise OAuthError(f"Authentication failed: {error_msg}")
            elif e.code == 429:
                raise Exception(f"Rate limited: {error_msg}")
            else:
                raise Exception(f"HTTP {e.code}: {error_msg}")
    
    async def _parse_stream(
        self,
        response: Any,
        stream: AssistantMessageEventStream,
        message: AssistantMessage
    ) -> None:
        """Parse SSE stream"""
        text_index = 0
        current_text = ""
        
        loop = asyncio.get_event_loop()
        
        def read_stream():
            """Read from response (blocking)"""
            for line in response:
                yield line.decode('utf-8')
        
        # Run blocking read in executor
        iterator = await loop.run_in_executor(None, read_stream)
        
        for line in iterator:
            line = line.strip()
            
            if not line or line.startswith(":"):
                continue
            
            if line.startswith("data: "):
                data = line[6:]
                
                if data == "[DONE]":
                    break
                
                try:
                    chunk = json.loads(data)
                    
                    # Handle choices
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta", {})
                        
                        # Text content
                        if "content" in delta and delta["content"]:
                            if text_index >= len(message.content):
                                # Start new text block
                                content = TextContent(type="text", text="")
                                message.content.append(content)
                                self._emit_text_start(stream, message, text_index)
                            
                            text_delta = delta["content"]
                            current_text += text_delta
                            self._emit_text_delta(stream, message, text_index, text_delta)
                        
                        # Tool calls
                        if "tool_calls" in delta:
                            # TODO: Implement tool call streaming
                            pass
                        
                        # Finish reason
                        finish_reason = choice.get("finish_reason")
                        if finish_reason:
                            if finish_reason == "stop":
                                self._emit_done(stream, message, StopReason.STOP)
                            elif finish_reason == "length":
                                self._emit_done(stream, message, StopReason.LENGTH)
                            elif finish_reason == "tool_calls":
                                self._emit_done(stream, message, StopReason.TOOL_USE)
                            else:
                                self._emit_done(stream, message, StopReason.STOP)
                            return
                        
                        # Usage (final chunk sometimes has usage)
                        if "usage" in chunk:
                            usage_data = chunk["usage"]
                            message.usage.input = usage_data.get("prompt_tokens", 0)
                            message.usage.output = usage_data.get("completion_tokens", 0)
                            message.usage.total = usage_data.get("total_tokens", 0)
                
                except json.JSONDecodeError:
                    continue
        
        # Ensure we emit done if not already
        if message.stop_reason is None:
            self._emit_done(stream, message, StopReason.STOP)
    
    async def complete(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessage:
        """Non-streaming completion"""
        try:
            # Check authentication
            if not self.is_authenticated:
                raise OAuthError("Not authenticated. Call authenticate() first.")
            
            # Build request
            url = f"{self.config.api_base}{self.config.chat_endpoint}"
            headers = self._build_headers()
            payload = self._build_payload(model, context, options, stream=False)
            
            # Make request
            loop = asyncio.get_event_loop()
            response_data = await loop.run_in_executor(
                None,
                lambda: self._make_request(url, headers, payload, stream_response=False)
            )
            
            # Parse response
            return self._parse_response(model, response_data)
            
        except Exception as e:
            return AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                api=self.api_type,
                provider=self.provider_id,
                model=model.id,
                stop_reason=StopReason.ERROR,
                error_message=str(e),
                timestamp=int(time.time() * 1000)
            )
    
    def _parse_response(
        self,
        model: ModelInfo,
        data: Dict[str, Any]
    ) -> AssistantMessage:
        """Parse non-streaming response"""
        message_data = data.get("choices", [{}])[0].get("message", {})
        
        content = []
        
        # Text content
        text = message_data.get("content", "")
        if text:
            content.append(TextContent(type="text", text=text))
        
        # Tool calls
        tool_calls_data = message_data.get("tool_calls", [])
        for tc in tool_calls_data:
            if tc.get("type") == "function":
                func = tc.get("function", {})
                content.append(ToolCall(
                    type="toolCall",
                    id=tc.get("id", ""),
                    name=func.get("name", ""),
                    arguments=json.loads(func.get("arguments", "{}"))
                ))
        
        # Usage
        usage_data = data.get("usage", {})
        usage = Usage(
            input=usage_data.get("prompt_tokens", 0),
            output=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )
        
        # Stop reason
        finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
        stop_reason = StopReason.STOP
        if finish_reason == "length":
            stop_reason = StopReason.LENGTH
        elif finish_reason == "tool_calls":
            stop_reason = StopReason.TOOL_USE
        
        return AssistantMessage(
            role="assistant",
            content=content,
            api=self.api_type,
            provider=self.provider_id,
            model=model.id,
            usage=usage,
            stop_reason=stop_reason,
            timestamp=int(time.time() * 1000)
        )
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """
        Calculate request cost
        
        Note: GitHub Copilot pricing is subscription-based,
        so we return 0.0 for direct cost calculation.
        """
        # Copilot is subscription-based, no per-token cost
        return 0.0
    
    def supports_tools(self) -> bool:
        """Whether tool calling is supported"""
        return True
    
    def supports_vision(self) -> bool:
        """Whether vision is supported"""
        return True
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Copilot models"""
        return list(self.DEFAULT_MODELS.values())


# Model definitions for GitHub Copilot
GITHUB_COPILOT_MODELS = [
    ModelInfo(
        id="gpt-4o-copilot",
        name="GPT-4o Copilot",
        provider="github-copilot",
        api=KnownApi.OPENAI_COMPLETIONS.value,  # Uses OpenAI-compatible API
        base_url="https://api.githubcopilot.com",
        context_window=128000,
        max_tokens=4096,
        cost={"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
        input=["text", "image"],
    ),
    ModelInfo(
        id="gpt-4-copilot",
        name="GPT-4 Copilot",
        provider="github-copilot",
        api=KnownApi.OPENAI_COMPLETIONS.value,
        base_url="https://api.githubcopilot.com",
        context_window=8192,
        max_tokens=4096,
        cost={"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
        input=["text"],
    ),
]


def register_copilot_models(registry: Any) -> None:
    """Register GitHub Copilot models with registry"""
    for model in GITHUB_COPILOT_MODELS:
        registry.register(model)


def create_copilot_provider(
    oauth: Optional[GitHubCopilotOAuth] = None
) -> GitHubCopilotProvider:
    """
    Factory function to create GitHub Copilot provider
    
    Args:
        oauth: Optional pre-authenticated OAuth instance
        
    Returns:
        GitHubCopilotProvider instance
    """
    config = GitHubCopilotConfig(oauth=oauth)
    return GitHubCopilotProvider(config)
