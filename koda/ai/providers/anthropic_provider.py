"""
Anthropic Provider

Supports Claude models with thinking/reasoning capabilities.
"""
import json
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from koda.ai.provider import LLMProvider, Message, Model, StreamEvent, ToolCall, Usage


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider

    Features:
    - Claude 3.5 Sonnet/Opus/Haiku
    - Extended thinking mode
    - 200K context window
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        proxy: Optional[Union[str, Dict[str, str]]] = None,
        **kwargs
    ):
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL, **kwargs)
        self._client = None
        self.thinking_level = kwargs.get("thinking_level")  # low/medium/high
        self._proxy = proxy

    def _get_proxy_config(self) -> Optional[str]:
        """Get proxy configuration for httpx client"""
        if self._proxy is None:
            # Try to load from environment
            from koda.ai.http_proxy import load_proxy_from_env
            proxy_config = load_proxy_from_env()
            if proxy_config:
                return proxy_config.url
            return None

        if isinstance(self._proxy, str):
            return self._proxy

        if isinstance(self._proxy, dict):
            return self._proxy.get("https://") or self._proxy.get("http://")

        return None

    def _get_client(self):
        """Lazy initialization of Anthropic client"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError("anthropic package required. Install: pip install anthropic")

            client_kwargs = {
                "api_key": self.api_key,
                "base_url": self.base_url,
            }

            # Configure proxy if available
            proxy_url = self._get_proxy_config()
            if proxy_url:
                try:
                    import httpx
                    client_kwargs["http_client"] = httpx.AsyncClient(
                        proxy=proxy_url,
                        timeout=httpx.Timeout(60.0, connect=30.0)
                    )
                except ImportError:
                    pass

            self._client = AsyncAnthropic(**client_kwargs)
        return self._client
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[StreamEvent]:
        """Chat with Claude API"""
        client = self._get_client()
        
        # Convert messages
        system, anthropic_messages = self._convert_messages(messages)
        
        # Build request
        request = {
            "model": model or self.get_default_model(),
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": stream,
        }
        
        if system:
            request["system"] = system
        
        if tools:
            request["tools"] = tools
        
        # Add thinking if specified
        if self.thinking_level:
            request["thinking"] = {
                "type": "enabled",
                "budget_tokens": self._get_thinking_budget()
            }
        
        # Make request
        if stream:
            async for event in self._stream_chat(client, request):
                yield event
        else:
            response = await client.messages.create(**request)
            for event in self._parse_response(response):
                yield event
    
    async def _stream_chat(self, client, request: Dict) -> AsyncIterator[StreamEvent]:
        """Stream chat responses"""
        request["stream"] = True
        
        stream = await client.messages.create(**request)
        
        async for event in stream:
            if event.type == "content_block_delta":
                delta = event.delta
                
                # Text
                if hasattr(delta, 'text') and delta.text:
                    yield StreamEvent.text(delta.text)
                
                # Thinking
                if hasattr(delta, 'thinking') and delta.thinking:
                    yield StreamEvent.thinking(delta.thinking)
            
            elif event.type == "message_stop":
                # Usage info
                if hasattr(event, 'message') and event.message.usage:
                    usage = event.message.usage
                    yield StreamEvent.usage(Usage(
                        prompt_tokens=usage.input_tokens,
                        completion_tokens=usage.output_tokens,
                        total_tokens=usage.input_tokens + usage.output_tokens,
                    ))
                yield StreamEvent.stop()
    
    def _parse_response(self, response) -> List[StreamEvent]:
        """Parse non-streaming response"""
        events = []
        
        for block in response.content:
            if block.type == "text":
                events.append(StreamEvent.text(block.text))
            elif block.type == "thinking":
                events.append(StreamEvent.thinking(block.thinking))
            elif block.type == "tool_use":
                tool_call = ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input
                )
                events.append(StreamEvent.tool_call(tool_call))
        
        # Usage
        if response.usage:
            events.append(StreamEvent.usage(Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )))
        
        events.append(StreamEvent.stop())
        return events
    
    def _convert_messages(self, messages: List[Message]) -> tuple:
        """
        Convert to Anthropic format
        
        Returns: (system_prompt, messages)
        """
        system_prompt = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content if isinstance(msg.content, str) else ""
            elif msg.role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    }]
                })
            elif msg.role == "assistant" and msg.tool_calls:
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments
                    })
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                anthropic_messages.append({"role": msg.role, "content": content})
        
        return system_prompt, anthropic_messages
    
    async def get_models(self) -> List[Model]:
        """Get available Claude models"""
        return [
            Model(
                id="claude-3-5-sonnet-20241022",
                provider="anthropic",
                name="Claude 3.5 Sonnet",
                context_window=200000,
                max_output_tokens=8192,
                supports_vision=True,
            ),
            Model(
                id="claude-3-5-haiku-20241022",
                provider="anthropic",
                name="Claude 3.5 Haiku",
                context_window=200000,
                max_output_tokens=8192,
            ),
            Model(
                id="claude-3-opus-20240229",
                provider="anthropic",
                name="Claude 3 Opus",
                context_window=200000,
                max_output_tokens=4096,
                supports_vision=True,
            ),
        ]
    
    def get_default_model(self) -> str:
        """Get default model"""
        return "claude-3-5-sonnet-20241022"
    
    def _get_thinking_budget(self) -> int:
        """Get thinking token budget"""
        budgets = {
            "low": 1024,
            "medium": 4096,
            "high": 16384,
        }
        return budgets.get(self.thinking_level, 4096)
    
    def supports_feature(self, feature: str) -> bool:
        """Check feature support"""
        features = {
            "streaming": True,
            "tools": True,
            "vision": True,
            "thinking": True,  # Claude specific
        }
        return features.get(feature, False)
