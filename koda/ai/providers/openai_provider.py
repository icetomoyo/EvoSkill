"""
OpenAI Provider

Supports OpenAI API and compatible APIs (Kimi, OpenRouter, etc.)
"""
import json
from typing import Any, AsyncIterator, Dict, List, Optional

from koda.ai.provider import LLMProvider, Message, Model, StreamEvent, ToolCall, Usage


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider
    
    Supports:
    - OpenAI official API (gpt-4, gpt-4o, gpt-3.5-turbo)
    - Compatible APIs (Kimi, OpenRouter, Azure, etc.)
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("openai package required. Install: pip install openai")
            
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
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
        """Chat with OpenAI API"""
        client = self._get_client()
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages)
        
        # Build request
        request = {
            "model": model or self.get_default_model(),
            "messages": openai_messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            request["max_tokens"] = max_tokens
        
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        
        # Add extra kwargs
        request.update(kwargs)
        
        # Make request
        if stream:
            async for event in self._stream_chat(client, request):
                yield event
        else:
            response = await client.chat.completions.create(**request)
            for event in self._parse_response(response):
                yield event
    
    async def _stream_chat(self, client, request: Dict) -> AsyncIterator[StreamEvent]:
        """Stream chat responses"""
        request["stream"] = True
        
        stream = await client.chat.completions.create(**request)
        
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            
            if not delta:
                continue
            
            # Text content
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
            
            # Usage (final chunk)
            if chunk.usage:
                yield StreamEvent.usage(Usage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                ))
            
            # Finish reason
            if chunk.choices[0].finish_reason:
                yield StreamEvent.stop(chunk.choices[0].finish_reason)
    
    def _parse_response(self, response) -> List[StreamEvent]:
        """Parse non-streaming response"""
        events = []
        
        message = response.choices[0].message
        
        # Text content
        if message.content:
            events.append(StreamEvent.text(message.content))
        
        # Tool calls
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_call = ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                )
                events.append(StreamEvent.tool_call(tool_call))
        
        # Usage
        if response.usage:
            events.append(StreamEvent.usage(Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )))
        
        events.append(StreamEvent.stop())
        return events
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert unified messages to OpenAI format"""
        result = []
        
        for msg in messages:
            openai_msg: Dict[str, Any] = {"role": msg.role}
            
            if msg.role == "tool":
                openai_msg["tool_call_id"] = msg.tool_call_id
                openai_msg["content"] = msg.content
                if msg.name:
                    openai_msg["name"] = msg.name
            elif msg.tool_calls:
                openai_msg["content"] = msg.content
                openai_msg["tool_calls"] = [
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
                openai_msg["content"] = msg.content
            
            result.append(openai_msg)
        
        return result
    
    async def get_models(self) -> List[Model]:
        """Get available models"""
        client = self._get_client()
        
        try:
            models_response = await client.models.list()
            
            models = []
            for m in models_response.data:
                # Filter for chat models
                if "gpt" in m.id or "chat" in m.id:
                    models.append(Model(
                        id=m.id,
                        provider="openai",
                        name=m.id,
                        context_window=self._get_context_window(m.id),
                        supports_tools=True,
                        supports_streaming=True,
                    ))
            
            return models
        except Exception:
            # Return default models if API fails
            return self._get_default_models()
    
    def get_default_model(self) -> str:
        """Get default model"""
        return "gpt-4o-mini"
    
    def _get_context_window(self, model_id: str) -> int:
        """Get context window for model"""
        windows = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
        }
        for prefix, window in windows.items():
            if model_id.startswith(prefix):
                return window
        return 8192  # Default
    
    def _get_default_models(self) -> List[Model]:
        """Default models when API unavailable"""
        return [
            Model(id="gpt-4o", provider="openai", name="GPT-4o", 
                  context_window=128000, supports_vision=True),
            Model(id="gpt-4o-mini", provider="openai", name="GPT-4o Mini", 
                  context_window=128000),
            Model(id="gpt-4-turbo", provider="openai", name="GPT-4 Turbo", 
                  context_window=128000),
        ]
