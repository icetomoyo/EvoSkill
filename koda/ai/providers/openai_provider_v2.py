"""
OpenAI Provider V2 - Refactored to use new BaseProvider
Supports: openai-completions, openai-responses, reasoning, tools, vision, compat detection
"""
import json
import os
import asyncio
from typing import Optional, Dict, Any, AsyncIterator, List, Union
from dataclasses import dataclass
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
    KnownApi,
    OpenAICompletionsCompat,
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


@dataclass
class CompatConfig:
    """Compatibility configuration for OpenAI-compatible APIs"""
    # Mistral-specific
    requires_mistral_tool_ids: bool = False

    # DeepSeek-specific
    requires_thinking_as_text: bool = False

    # General compat
    requires_assistant_after_tool_result: bool = False
    requires_tool_result_name: bool = False
    supports_usage_in_streaming: bool = True
    max_tokens_field: str = "max_tokens"  # or "max_completion_tokens"


# Provider-specific compatibility configurations
COMPAT_CONFIGS: Dict[str, CompatConfig] = {
    "mistral": CompatConfig(
        requires_mistral_tool_ids=True,
        supports_usage_in_streaming=False,
    ),
    "deepseek": CompatConfig(
        requires_thinking_as_text=True,
    ),
    "groq": CompatConfig(
        supports_usage_in_streaming=False,
    ),
    "cerebras": CompatConfig(
        supports_usage_in_streaming=False,
    ),
    "openai": CompatConfig(),  # Default OpenAI
}


def detect_compat_from_url(base_url: str) -> str:
    """Detect provider type from base URL"""
    if "mistral" in base_url:
        return "mistral"
    elif "deepseek" in base_url:
        return "deepseek"
    elif "groq" in base_url:
        return "groq"
    elif "cerebras" in base_url:
        return "cerebras"
    elif "x.ai" in base_url:
        return "xai"
    elif "openrouter" in base_url:
        return "openrouter"
    return "openai"


class OpenAIProviderV2(BaseProvider):
    """
    OpenAI Provider - Supports Completions and Responses API

    Features:
    - Standard OpenAI chat completions
    - OpenAI-compatible APIs (Mistral, DeepSeek, Groq, etc.)
    - Tool calling with provider-specific normalization
    - Vision support
    - Reasoning (o-series models, DeepSeek R1)
    - Reasoning details extraction
    - Compat detection for different providers

    Equivalent to Pi Mono's openai-completions.ts + openai-responses.ts
    """

    def __init__(
        self,
        config: Optional[ProviderConfig] = None,
        compat_type: Optional[str] = None
    ):
        super().__init__(config)
        self.base_url = config.base_url if config and config.base_url else "https://api.openai.com/v1"
        self.api_key = config.api_key if config and config.api_key else os.getenv("OPENAI_API_KEY")

        # Detect compatibility type
        if compat_type:
            self.compat_type = compat_type
        else:
            self.compat_type = detect_compat_from_url(self.base_url)

        # Get compat config
        self.compat = COMPAT_CONFIGS.get(self.compat_type, CompatConfig())
    
    @property
    def api_type(self) -> str:
        return KnownApi.OPENAI_COMPLETIONS.value
    
    @property
    def provider_id(self) -> str:
        return "openai"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost based on model pricing"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """Check if model supports reasoning effort"""
        # o-series models support reasoning
        return model.id.startswith("o") and "gpt" not in model.id.lower()
    
    def supports_cache_retention(self) -> bool:
        return False  # OpenAI doesn't support cache retention
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        Stream chat completion
        
        Supports:
        - Standard chat completions
        - Tool calling
        - Vision (via image_url in messages)
        - Reasoning (o-series models)
        """
        stream = AssistantMessageEventStream()
        
        # Start streaming in background
        asyncio.create_task(self._stream_completion(model, context, options, stream))
        
        return stream
    
    async def _stream_completion(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming implementation"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)

            # Build request payload
            payload = self._build_payload(model, context, options, stream=True)

            # Make request
            headers = self.get_default_headers()
            auth_header = self.get_auth_header()
            if auth_header:
                headers.update(auth_header)

            if options and options.headers:
                headers.update(options.headers)

            endpoint = f"{self.base_url}/chat/completions"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")

                    # Parse SSE stream
                    content_buffer = ""
                    reasoning_buffer = ""  # For reasoning_details
                    tool_calls_buffer: Dict[int, Dict] = {}
                    thinking_index: Optional[int] = None

                    async for line in response.content:
                        line = line.decode('utf-8').strip()

                        if not line or line == "data: [DONE]":
                            continue

                        if line.startswith("data: "):
                            data = json.loads(line[6:])

                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                delta = choice.get("delta", {})

                                # Handle reasoning_details (for o-series, DeepSeek R1)
                                if "reasoning_content" in delta:
                                    reasoning = delta["reasoning_content"]
                                    if reasoning:
                                        if thinking_index is None:
                                            # First reasoning - emit thinking_start
                                            thinking_content = ThinkingContent(type="thinking", thinking="")
                                            message.content.append(thinking_content)
                                            thinking_index = len(message.content) - 1
                                            self._emit_thinking_start(stream, message, thinking_index)

                                        reasoning_buffer += reasoning
                                        self._emit_thinking_delta(stream, message, thinking_index, reasoning)

                                # Handle regular content
                                if "content" in delta and delta["content"]:
                                    # Close thinking block if we had one
                                    if thinking_index is not None:
                                        self._emit_thinking_end(stream, message, thinking_index)
                                        thinking_index = None

                                    if not content_buffer:
                                        # First content - emit text_start
                                        text_content = TextContent(type="text", text="")
                                        message.content.append(text_content)
                                        self._emit_text_start(stream, message, len(message.content) - 1)

                                    content_buffer += delta["content"]
                                    self._emit_text_delta(
                                        stream, message, len(message.content) - 1, delta["content"]
                                    )

                                # Handle tool calls with provider-specific normalization
                                if "tool_calls" in delta:
                                    for tc_delta in delta["tool_calls"]:
                                        idx = tc_delta.get("index", 0)

                                        if idx not in tool_calls_buffer:
                                            # Mistral requires specific tool ID format
                                            tool_id = tc_delta.get("id", f"call_{idx}")
                                            if self.compat.requires_mistral_tool_ids:
                                                # Normalize tool ID for Mistral
                                                if not tool_id.startswith("call_"):
                                                    tool_id = f"call_{tool_id}"

                                            tool_calls_buffer[idx] = {
                                                "id": tool_id,
                                                "name": "",
                                                "arguments": ""
                                            }
                                            # Emit toolcall_start
                                            tool_call = ToolCall(
                                                type="toolCall",
                                                id=tool_calls_buffer[idx]["id"],
                                                name="",
                                                arguments={}
                                            )
                                            self._emit_toolcall_start(stream, message, idx, tool_call)

                                        # Accumulate function data
                                        if "function" in tc_delta:
                                            func = tc_delta["function"]
                                            if "name" in func:
                                                tool_calls_buffer[idx]["name"] += func["name"]
                                            if "arguments" in func:
                                                tool_calls_buffer[idx]["arguments"] += func["arguments"]

                                                # Emit delta for arguments
                                                self._emit_toolcall_delta(
                                                    stream, message, idx, func["arguments"]
                                                )

                                # Check for finish reason
                                finish_reason = choice.get("finish_reason")
                                if finish_reason:
                                    # Close thinking block if we had one
                                    if thinking_index is not None:
                                        self._emit_thinking_end(stream, message, thinking_index)

                                    # Emit text_end if we had content
                                    if content_buffer:
                                        self._emit_text_end(stream, message, len(message.content) - 1, content_buffer)

                                    # Emit toolcall_end for any tool calls
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

                                    # Update usage if available (some providers don't include in stream)
                                    if "usage" in data and self.compat.supports_usage_in_streaming:
                                        usage_data = data["usage"]
                                        message.usage.input = usage_data.get("prompt_tokens", 0)
                                        message.usage.output = usage_data.get("completion_tokens", 0)
                                        message.usage.total_tokens = usage_data.get("total_tokens", 0)
                                        self.calculate_cost(self._get_model_info(model.id), message.usage)

                                    # Map finish reason
                                    stop_reason = self._map_finish_reason(finish_reason)
                                    self._emit_done(stream, message, stop_reason)
                                    return

            # If we get here without finish_reason, emit done
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
        """Build API request payload"""
        payload: Dict[str, Any] = {
            "model": model.id,
            "stream": stream,
        }

        # Use appropriate max_tokens field based on compat
        max_tokens_field = self.compat.max_tokens_field

        # Add messages with provider-specific handling
        messages = self._convert_messages(context.messages)
        payload["messages"] = messages

        # Add system prompt if present
        if context.system_prompt:
            # Insert at beginning
            payload["messages"].insert(0, {
                "role": "system",
                "content": context.system_prompt
            })

        # Add options
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload[max_tokens_field] = options.max_tokens

            # Handle reasoning for o-series models and DeepSeek R1
            reasoning_level = None
            if hasattr(options, 'reasoning') and options.reasoning:
                reasoning_level = options.reasoning

            if reasoning_level:
                # For OpenAI o-series, use reasoning_effort
                if model.id.startswith("o") and "gpt" not in model.id.lower():
                    reasoning_map = {
                        "minimal": "low",
                        "low": "low",
                        "medium": "medium",
                        "high": "high",
                        "xhigh": "high",
                    }
                    payload["reasoning_effort"] = reasoning_map.get(reasoning_level, "medium")

                # For DeepSeek R1, the model handles reasoning automatically
                # No special parameters needed

        # Add tools if present
        if context.tools:
            tools_payload = []
            for tool in context.tools:
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                }
                tools_payload.append(tool_def)

            payload["tools"] = tools_payload

            # Enable tool_choice for supported providers
            if not self.compat.requires_mistral_tool_ids:
                payload["tool_choice"] = "auto"

        # Provider-specific modifications

        # DeepSeek R1 requires stream_options for reasoning content
        if "deepseek-reasoner" in model.id and stream:
            payload["stream_options"] = {
                "include_usage": True
            }

        return payload
    
    def _convert_messages(self, messages: list) -> list:
        """Convert internal messages to OpenAI format with provider-specific handling"""
        result = []

        for msg in messages:
            if msg.role == "user":
                if isinstance(msg.content, str):
                    result.append({"role": "user", "content": msg.content})
                else:
                    # Handle multimodal content
                    content = []
                    for item in msg.content:
                        if item.type == "text":
                            content.append({"type": "text", "text": item.text})
                        elif item.type == "image":
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{item.mime_type};base64,{item.data}"
                                }
                            })
                    result.append({"role": "user", "content": content})

            elif msg.role == "assistant":
                content = ""
                tool_calls = []

                for item in msg.content:
                    if item.type == "text":
                        content += item.text
                    elif item.type == "thinking":
                        # For providers that require thinking as text (e.g., DeepSeek R1)
                        if self.compat.requires_thinking_as_text:
                            content += f"\n<thinking>\n{item.thinking}\n</thinking>\n"
                    elif item.type == "toolCall":
                        tool_call_def = {
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.name,
                                "arguments": json.dumps(item.arguments)
                            }
                        }
                        tool_calls.append(tool_call_def)

                assistant_msg: Dict[str, Any] = {"role": "assistant"}
                if content:
                    assistant_msg["content"] = content
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls

                result.append(assistant_msg)

            elif msg.role == "toolResult":
                tool_msg: Dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content[0].text if msg.content else ""
                }

                # Some providers require tool result name
                if self.compat.requires_tool_result_name:
                    tool_msg["name"] = msg.tool_name

                result.append(tool_msg)

        # Some providers require assistant message after tool results
        if self.compat.requires_assistant_after_tool_result:
            # Insert empty assistant message after each tool result
            new_result = []
            for msg in result:
                new_result.append(msg)
                if msg.get("role") == "tool":
                    new_result.append({"role": "assistant", "content": ""})
            result = new_result

        return result
    
    def _map_finish_reason(self, reason: str) -> StopReason:
        """Map OpenAI finish reason to StopReason"""
        mapping = {
            "stop": StopReason.STOP,
            "length": StopReason.LENGTH,
            "tool_calls": StopReason.TOOL_USE,
            "content_filter": StopReason.ERROR,
        }
        return mapping.get(reason, StopReason.STOP)
    
    def _get_model_info(self, model_id: str) -> ModelInfo:
        """Get model info for cost calculation"""
        # Default model info
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
