"""
Kimi Provider

Supports Moonshot Kimi API (including Kimi For Coding).
"""
import json
from typing import Any, AsyncIterator, Dict, List, Optional

from koda.ai.provider import LLMProvider, Message, Model, StreamEvent, ToolCall, Usage


class KimiProvider(LLMProvider):
    """
    Moonshot Kimi provider
    
    Supports:
    - Kimi K2.5 (256K context)
    - Kimi For Coding (special API)
    - Standard Kimi models
    """
    
    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
    CODING_BASE_URL = "https://api.kimi.com/coding/v1"
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        # Auto-detect Kimi For Coding
        self.is_coding = kwargs.get("for_coding", False) or "kimi.com/coding" in (base_url or "")
        
        if self.is_coding and not base_url:
            base_url = self.CODING_BASE_URL
        elif not base_url:
            base_url = self.DEFAULT_BASE_URL
        
        super().__init__(api_key, base_url, **kwargs)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("openai package required. Install: pip install openai")
            
            # Kimi For Coding needs special headers
            headers = {}
            if self.is_coding:
                headers["User-Agent"] = "Kimi-CLI/1.0"
            
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers=headers,
            )
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
        """Chat with Kimi API"""
        client = self._get_client()
        
        # Convert messages
        kimi_messages = self._convert_messages(messages)
        
        # Build request
        request = {
            "model": model or self.get_default_model(),
            "messages": kimi_messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            request["max_tokens"] = max_tokens
        
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        
        # Kimi specific: enable search if available
        if kwargs.get("enable_search"):
            request["extra_body"] = {"enable_search": True}
        
        if stream:
            async for event in self._stream_chat(client, request):
                yield event
        else:
            response = await client.chat.completions.create(**request)
            for event in self._parse_response(response):
                yield event
    
    async def _stream_chat(self, client, request: Dict) -> AsyncIterator[StreamEvent]:
        """Stream responses"""
        request["stream"] = True
        
        stream = await client.chat.completions.create(**request)
        
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            
            if not delta:
                continue
            
            # Text
            if delta.content:
                yield StreamEvent.text(delta.content)
            
            # Tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.function:
                        tool_call = ToolCall(
                            id=tc.id or "",
                            name=tc.function.name or "",
                            arguments=json.loads(tc.function.arguments) if tc.function.arguments else {}
                        )
                        yield StreamEvent.tool_call(tool_call)
            
            # Usage
            if chunk.usage:
                yield StreamEvent.usage(Usage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                ))
            
            # Finish
            if chunk.choices[0].finish_reason:
                yield StreamEvent.stop(chunk.choices[0].finish_reason)
    
    def _parse_response(self, response) -> List[StreamEvent]:
        """Parse non-streaming response"""
        events = []
        message = response.choices[0].message
        
        if message.content:
            events.append(StreamEvent.text(message.content))
        
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_call = ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                )
                events.append(StreamEvent.tool_call(tool_call))
        
        if response.usage:
            events.append(StreamEvent.usage(Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )))
        
        events.append(StreamEvent.stop())
        return events
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert to Kimi format (OpenAI compatible)"""
        result = []
        
        for msg in messages:
            kimi_msg: Dict[str, Any] = {"role": msg.role}
            
            if msg.role == "tool":
                kimi_msg["tool_call_id"] = msg.tool_call_id
                kimi_msg["content"] = msg.content
                if msg.name:
                    kimi_msg["name"] = msg.name
            elif msg.tool_calls:
                kimi_msg["content"] = msg.content
                kimi_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in msg.tool_calls
                ]
            else:
                kimi_msg["content"] = msg.content
            
            result.append(kimi_msg)
        
        return result
    
    async def get_models(self) -> List[Model]:
        """Get available Kimi models"""
        if self.is_coding:
            # Kimi For Coding models
            return [
                Model(
                    id="k2.5",
                    provider="kimi-coding",
                    name="Kimi K2.5 (Coding)",
                    context_window=256000,
                    supports_tools=True,
                    supports_vision=True,
                ),
            ]
        
        # Standard Kimi models
        return [
            Model(
                id="moonshot-v1-8k",
                provider="kimi",
                name="Kimi V1 (8K)",
                context_window=8192,
            ),
            Model(
                id="moonshot-v1-32k",
                provider="kimi",
                name="Kimi V1 (32K)",
                context_window=32768,
            ),
            Model(
                id="moonshot-v1-128k",
                provider="kimi",
                name="Kimi V1 (128K)",
                context_window=128000,
            ),
            Model(
                id="kimi-k2.5",
                provider="kimi",
                name="Kimi K2.5",
                context_window=256000,
                supports_vision=True,
            ),
        ]
    
    def get_default_model(self) -> str:
        """Get default model"""
        if self.is_coding:
            return "k2.5"
        return "kimi-k2.5"
