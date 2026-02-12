"""
Anthropic Provider V2 - Refactored with full Pi Mono parity
Supports: messages API, thinking, caching, tools, vision, adaptive thinking, effort levels
"""
import json
import os
import asyncio
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
import aiohttp

from koda.ai.types import (
    ModelInfo,
    Context,
    Usage,
    AssistantMessage,
    StreamOptions,
    SimpleStreamOptions,
    ThinkingLevel,
    StopReason,
    TextContent,
    ThinkingContent,
    ToolCall,
    ImageContent,
)
from koda.ai.provider_base import BaseProvider, ProviderConfig
from koda.ai.event_stream import AssistantMessageEventStream, EventType


@dataclass
class ThinkingBudget:
    """Thinking budget configuration"""
    minimal: int = 1024
    low: int = 2048
    medium: int = 8192
    high: int = 16384
    xhigh: int = 32768
    adaptive: int = -1  # -1 means adaptive


# Model-specific thinking budgets
MODEL_THINKING_BUDGETS: Dict[str, ThinkingBudget] = {
    "claude-opus-4-5": ThinkingBudget(minimal=2048, low=4096, medium=16384, high=32768, xhigh=65536),
    "claude-opus-4": ThinkingBudget(minimal=2048, low=4096, medium=16384, high=32768, xhigh=65536),
    "claude-sonnet-4": ThinkingBudget(minimal=1024, low=2048, medium=8192, high=16384, xhigh=32768),
    "claude-3-7-sonnet": ThinkingBudget(minimal=1024, low=2048, medium=8192, high=16384, xhigh=32768),
    "default": ThinkingBudget(),
}


@dataclass
class ClaudeCodeConfig:
    """Claude Code specific configuration"""
    stealth_mode: bool = False  # When True, minimize identifiable patterns
    adaptive_thinking: bool = True  # Enable adaptive thinking budget
    max_thinking_tokens: int = 65536  # Maximum thinking tokens


class AnthropicProviderV2(BaseProvider):
    """
    Anthropic Messages API Provider

    Supports:
    - Claude 3/3.5/4/4.5 models
    - Extended thinking (reasoning) with adaptive budgets
    - Prompt caching
    - Vision
    - Tool use
    - Streaming
    - Claude Code stealth mode
    - Effort level mapping for thinking

    Equivalent to Pi Mono's anthropic.ts
    """

    def __init__(
        self,
        config: Optional[ProviderConfig] = None,
        claude_code_config: Optional[ClaudeCodeConfig] = None
    ):
        super().__init__(config)
        self.base_url = config.base_url if config and config.base_url else "https://api.anthropic.com/v1"
        self.api_key = config.api_key if config and config.api_key else os.getenv("ANTHROPIC_API_KEY")
        self.claude_code = claude_code_config or ClaudeCodeConfig()
    
    @property
    def api_type(self) -> str:
        return "anthropic-messages"
    
    @property
    def provider_id(self) -> str:
        return "anthropic"
    
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """Calculate cost for Anthropic models"""
        usage.calculate_cost(model.cost)
        return usage.cost["total"]
    
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """Claude 3.7+ supports thinking levels"""
        return True
    
    def supports_cache_retention(self) -> bool:
        """Anthropic supports prompt caching"""
        return True
    
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """Stream completion from Anthropic API"""
        stream = AssistantMessageEventStream()
        asyncio.create_task(self._stream_messages(model, context, options, stream))
        return stream
    
    async def _stream_messages(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions],
        stream: AssistantMessageEventStream
    ) -> None:
        """Internal streaming for Anthropic Messages API"""
        try:
            message = self._create_initial_message(model)
            self._emit_start(stream, message)
            
            # Build request
            payload = self._build_payload(model, context, options)
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
            
            if options and options.headers:
                headers.update(options.headers)
            
            endpoint = f"{self.base_url}/messages"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Anthropic API error: {response.status} - {error_text}")
                    
                    # Parse SSE stream
                    content_blocks: Dict[int, Dict] = {}
                    current_block_type: Optional[str] = None
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]  # Remove "data: "
                        if data_str == "[DONE]":
                            continue
                        
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type")
                            
                            if event_type == "message_start":
                                # Capture initial usage
                                if "message" in event and "usage" in event["message"]:
                                    usage_data = event["message"]["usage"]
                                    message.usage.input = usage_data.get("input_tokens", 0)
                                    message.usage.output = usage_data.get("output_tokens", 0)
                                    message.usage.cache_read = usage_data.get("cache_read_input_tokens", 0)
                                    message.usage.cache_write = usage_data.get("cache_creation_input_tokens", 0)
                            
                            elif event_type == "content_block_start":
                                index = event.get("index", 0)
                                block = event.get("content_block", {})
                                block_type = block.get("type")
                                content_blocks[index] = {"type": block_type, "content": ""}
                                current_block_type = block_type
                                
                                if block_type == "text":
                                    text_content = TextContent(type="text", text="")
                                    message.content.append(text_content)
                                    self._emit_text_start(stream, message, len(message.content) - 1)
                                
                                elif block_type == "thinking":
                                    thinking_content = ThinkingContent(type="thinking", thinking="")
                                    message.content.append(thinking_content)
                                    self._emit_thinking_start(stream, message, len(message.content) - 1)
                                
                                elif block_type == "tool_use":
                                    tool_call = ToolCall(
                                        type="toolCall",
                                        id=block.get("id", ""),
                                        name=block.get("name", ""),
                                        arguments={}
                                    )
                                    idx = len(message.content)
                                    message.content.append(tool_call)
                                    content_blocks[index]["tool_call_idx"] = idx
                                    self._emit_toolcall_start(stream, message, idx, tool_call)
                            
                            elif event_type == "content_block_delta":
                                index = event.get("index", 0)
                                delta = event.get("delta", {})
                                
                                if "text" in delta:
                                    text = delta["text"]
                                    content_blocks[index]["content"] += text
                                    self._emit_text_delta(stream, message, len(message.content) - 1, text)
                                
                                elif "thinking" in delta:
                                    thinking = delta["thinking"]
                                    content_blocks[index]["content"] += thinking
                                    self._emit_thinking_delta(stream, message, len(message.content) - 1, thinking)
                                
                                elif "partial_json" in delta:
                                    partial = delta["partial_json"]
                                    content_blocks[index]["content"] += partial
                                    tool_idx = content_blocks[index].get("tool_call_idx", 0)
                                    self._emit_toolcall_delta(stream, message, tool_idx, partial)
                            
                            elif event_type == "content_block_stop":
                                index = event.get("index", 0)
                                block_info = content_blocks.get(index, {})
                                block_type = block_info.get("type")
                                
                                if block_type == "text":
                                    self._emit_text_end(stream, message, len(message.content) - 1, block_info["content"])
                                
                                elif block_type == "thinking":
                                    self._emit_thinking_end(stream, message, len(message.content) - 1)
                                
                                elif block_type == "tool_use":
                                    tool_idx = block_info.get("tool_call_idx", 0)
                                    try:
                                        args = json.loads(block_info["content"]) if block_info["content"] else {}
                                    except json.JSONDecodeError:
                                        args = {}
                                    
                                    if tool_idx < len(message.content):
                                        message.content[tool_idx].arguments = args
                                        self._emit_toolcall_end(stream, message, tool_idx, message.content[tool_idx])
                            
                            elif event_type == "message_delta":
                                if "usage" in event:
                                    usage_data = event["usage"]
                                    if "output_tokens" in usage_data:
                                        message.usage.output = usage_data["output_tokens"]
                                
                                if "delta" in event and "stop_reason" in event["delta"]:
                                    reason_map = {
                                        "end_turn": StopReason.STOP,
                                        "max_tokens": StopReason.LENGTH,
                                        "tool_use": StopReason.TOOL_USE,
                                    }
                                    stop_reason = reason_map.get(
                                        event["delta"]["stop_reason"],
                                        StopReason.STOP
                                    )
                                    self._emit_done(stream, message, stop_reason)
                                    return
                            
                            elif event_type == "message_stop":
                                self.calculate_cost(model, message.usage)
                                self._emit_done(stream, message, StopReason.STOP)
                                return
                        
                        except json.JSONDecodeError:
                            continue
            
            self._emit_done(stream, message, StopReason.STOP)
        
        except Exception as e:
            self._emit_error(stream, message if 'message' in locals() else AssistantMessage(), e)
    
    def _build_payload(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions]
    ) -> Dict[str, Any]:
        """Build Anthropic API request payload"""
        payload: Dict[str, Any] = {
            "model": model.id,
            "max_tokens": options.max_tokens if options and options.max_tokens else 4096,
            "stream": True,
            "messages": self._convert_messages(context.messages),
        }

        # Add system prompt
        if context.system_prompt:
            payload["system"] = context.system_prompt

        # Add options
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature

            # Handle thinking/reasoning with adaptive budgets
            thinking_level = None
            if hasattr(options, 'reasoning') and options.reasoning:
                thinking_level = options.reasoning
            elif isinstance(options, SimpleStreamOptions) and options.reasoning:
                thinking_level = options.reasoning

            if thinking_level and self._supports_extended_thinking(model.id):
                # Get thinking budget for this model
                budget = self._get_thinking_budget(model.id, thinking_level)

                # Effort level mapping (for Claude 4.5+ adaptive thinking)
                effort_map = {
                    ThinkingLevel.MINIMAL: "minimal",
                    ThinkingLevel.LOW: "low",
                    ThinkingLevel.MEDIUM: "medium",
                    ThinkingLevel.HIGH: "high",
                    ThinkingLevel.XHIGH: "max",
                }

                if isinstance(thinking_level, str):
                    thinking_level = ThinkingLevel(thinking_level)

                effort = effort_map.get(thinking_level, "medium")

                # Thinking config
                thinking_config: Dict[str, Any] = {
                    "type": "enabled",
                }

                # For Claude 4.5+ with adaptive thinking, use effort instead of budget_tokens
                if self._supports_adaptive_thinking(model.id) and self.claude_code.adaptive_thinking:
                    thinking_config["effort"] = effort
                else:
                    # Use fixed budget tokens for older models
                    thinking_config["budget_tokens"] = min(budget, self.claude_code.max_thinking_tokens)

                payload["thinking"] = thinking_config

            # Handle cache retention
            if options.cache_retention and options.cache_retention != "none":
                # Add cache control to last user message
                if payload["messages"] and payload["messages"][-1]["role"] == "user":
                    content = payload["messages"][-1]["content"]
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                item["cache_control"] = {"type": "ephemeral"}
                                break
                    elif isinstance(content, str):
                        payload["messages"][-1]["content"] = [
                            {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
                        ]

        # Add tools
        if context.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters
                }
                for tool in context.tools
            ]

        # Claude Code stealth mode modifications
        if self.claude_code.stealth_mode:
            # Add extra headers for stealth mode
            if "extra_headers" not in payload:
                payload["extra_headers"] = {}
            payload["extra_headers"]["anthropic-beta"] = "claude-code-stealth-1"

        return payload

    def _supports_extended_thinking(self, model_id: str) -> bool:
        """Check if model supports extended thinking"""
        thinking_models = [
            "claude-opus-4-5",
            "claude-opus-4",
            "claude-sonnet-4",
            "claude-3-7-sonnet",
        ]
        return any(m in model_id for m in thinking_models)

    def _supports_adaptive_thinking(self, model_id: str) -> bool:
        """Check if model supports adaptive thinking (Claude 4.5+)"""
        adaptive_models = [
            "claude-opus-4-5",
            "claude-4-5",
        ]
        return any(m in model_id for m in adaptive_models)

    def _get_thinking_budget(self, model_id: str, level: ThinkingLevel) -> int:
        """Get thinking budget for model and level"""
        # Find model-specific budget or use default
        for model_prefix, budget in MODEL_THINKING_BUDGETS.items():
            if model_prefix in model_id:
                break
        else:
            budget = MODEL_THINKING_BUDGETS["default"]

        # Map level to budget value
        level_map = {
            ThinkingLevel.MINIMAL: budget.minimal,
            ThinkingLevel.LOW: budget.low,
            ThinkingLevel.MEDIUM: budget.medium,
            ThinkingLevel.HIGH: budget.high,
            ThinkingLevel.XHIGH: budget.xhigh,
        }
        return level_map.get(level, budget.medium)
    
    def _convert_messages(self, messages: list) -> list:
        """Convert messages to Anthropic format"""
        result = []
        
        for msg in messages:
            if msg.role == "user":
                content = self._convert_content(msg.content)
                result.append({"role": "user", "content": content})
            
            elif msg.role == "assistant":
                content = []
                for item in msg.content:
                    if item.type == "text":
                        content.append({"type": "text", "text": item.text})
                    elif item.type == "thinking":
                        content.append({"type": "thinking", "thinking": item.thinking})
                    elif item.type == "toolCall":
                        content.append({
                            "type": "tool_use",
                            "id": item.id,
                            "name": item.name,
                            "input": item.arguments
                        })
                
                if content:
                    result.append({"role": "assistant", "content": content})
            
            elif msg.role == "toolResult":
                content = []
                for item in msg.content:
                    if item.type == "text":
                        content.append({
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": item.text,
                            "is_error": msg.is_error
                        })
                    elif item.type == "image":
                        content.append({
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": item.mime_type,
                                        "data": item.data
                                    }
                                }
                            ]
                        })
                
                if content:
                    result.append({"role": "user", "content": content})
        
        return result
    
    def _convert_content(self, content) -> Any:
        """Convert content to Anthropic format"""
        if isinstance(content, str):
            return content
        
        result = []
        for item in content:
            if item.type == "text":
                result.append({"type": "text", "text": item.text})
            elif item.type == "image":
                result.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": item.mime_type,
                        "data": item.data
                    }
                })
        
        return result if len(result) > 1 else result[0] if result else ""
