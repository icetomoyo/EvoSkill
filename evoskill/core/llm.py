"""
LLM 提供商抽象

支持 OpenAI、Anthropic 等主流 API
"""

import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from evoskill.core.types import (
    LLMConfig,
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    ToolDefinition,
    ContentBlock,
    TextContent,
    ThinkingContent,
    ToolCallContent,
    ToolCall,
    EventType,
    TokenUsage,
)


class LLMProvider(ABC):
    """LLM 提供商抽象基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        与 LLM 对话
        
        Args:
            messages: 消息列表
            tools: 可用工具定义
            stream: 是否流式响应
            **kwargs: 额外参数
            
        Yields:
            事件字典，包含类型和数据
        """
        pass
    
    def _messages_to_provider_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """将内部消息格式转换为提供商格式"""
        result = []
        for msg in messages:
            if isinstance(msg, UserMessage):
                content = msg.content
                # 如果有图片附件，使用多模态格式
                if msg.attachments:
                    content = [{"type": "text", "text": msg.content}]
                    for img in msg.attachments:
                        if isinstance(img.source, str):
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": img.source}
                            })
                        else:
                            content.append({
                                "type": "image",
                                "source": img.source
                            })
                result.append({"role": "user", "content": content})
            
            elif isinstance(msg, AssistantMessage):
                content = []
                tool_calls = []
                for block in msg.content:
                    if isinstance(block, TextContent):
                        content.append({"type": "text", "text": block.text})
                    elif isinstance(block, ToolCallContent):
                        tool_calls.append({
                            "id": block.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.arguments)
                            }
                        })
                
                msg_dict: Dict[str, Any] = {"role": "assistant"}
                if content:
                    msg_dict["content"] = content
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                result.append(msg_dict)
            
            elif isinstance(msg, ToolResultMessage):
                # 工具结果需要特殊处理
                content = ""
                for block in msg.content:
                    if isinstance(block, TextContent):
                        content += block.text
                
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": content
                })
        
        return result


class OpenAIProvider(LLMProvider):
    """OpenAI / 兼容 OpenAI API 的提供商"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        
        # 设置自定义 HTTP 头
        # Kimi For Coding 需要特定的 User-Agent
        default_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        
        # 检测是否是 Kimi For Coding API
        is_kimi_coding = (
            config.base_url and 
            "api.kimi.com/coding" in config.base_url
        ) or config.provider == "kimi-coding"
        
        if is_kimi_coding:
            # Kimi For Coding 需要特定的 User-Agent
            default_headers["User-Agent"] = "KimiCLI/0.77"
        
        # 合并用户自定义 headers
        if config.headers:
            default_headers.update(config.headers)
        
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            default_headers=default_headers,
        )
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """OpenAI 对话实现"""
        provider_messages = self._messages_to_provider_format(messages)
        
        # 转换工具定义
        provider_tools = None
        if tools:
            provider_tools = [tool.to_dict() for tool in tools]
        
        request_params = {
            "model": self.config.model,
            "messages": provider_messages,
            "temperature": self.config.temperature,
            "stream": stream,
        }
        
        if provider_tools:
            request_params["tools"] = provider_tools
            request_params["tool_choice"] = "auto"
        
        if self.config.max_tokens:
            request_params["max_tokens"] = self.config.max_tokens
        
        request_params.update(kwargs)
        
        if stream:
            async for chunk in await self.client.chat.completions.create(**request_params):
                # 跳过没有 choices 的 chunk（如心跳包）
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # 文本增量
                if delta.content:
                    yield {
                        "type": "text_delta",
                        "content": delta.content
                    }
                
                # 工具调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        yield {
                            "type": "tool_call_delta",
                            "tool_call_id": tc.id,
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
        else:
            # 非流式响应
            response = await self.client.chat.completions.create(**request_params)
            if not response.choices:
                yield {
                    "type": "error",
                    "error": "Empty response from API"
                }
                return
            choice = response.choices[0]
            message = choice.message
            
            # 构建完整响应
            content = message.content or ""
            if content:
                yield {
                    "type": "text_delta",
                    "content": content
                }
            
            if message.tool_calls:
                for tc in message.tool_calls:
                    yield {
                        "type": "tool_call_delta",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
            
            yield {
                "type": "finish",
                "finish_reason": choice.finish_reason,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                }
            }


class AnthropicProvider(LLMProvider):
    """Anthropic Claude 提供商"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
        )
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Anthropic 对话实现"""
        # Anthropic 使用不同的消息格式
        provider_messages = []
        system_message = None
        
        for msg in messages:
            if isinstance(msg, UserMessage):
                content = msg.content
                if msg.attachments:
                    content = [{"type": "text", "text": msg.content}]
                    for img in msg.attachments:
                        content.append({
                            "type": "image",
                            "source": img.source if isinstance(img.source, dict) else {
                                "type": "url",
                                "url": img.source
                            }
                        })
                provider_messages.append({"role": "user", "content": content})
            
            elif isinstance(msg, AssistantMessage):
                content_blocks = []
                for block in msg.content:
                    if isinstance(block, TextContent):
                        content_blocks.append({"type": "text", "text": block.text})
                    elif isinstance(block, ToolCallContent):
                        content_blocks.append({
                            "type": "tool_use",
                            "id": block.tool_call_id,
                            "name": block.name,
                            "input": block.arguments
                        })
                provider_messages.append({"role": "assistant", "content": content_blocks})
            
            elif isinstance(msg, ToolResultMessage):
                provider_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": block.text if isinstance(block := msg.content[0], TextContent) else "",
                        "is_error": msg.is_error
                    }]
                })
        
        # 转换工具定义 (Anthropic 格式)
        provider_tools = None
        if tools:
            provider_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.to_dict()["function"]["parameters"]
                }
                for tool in tools
            ]
        
        request_params = {
            "model": self.config.model,
            "messages": provider_messages,
            "max_tokens": self.config.max_tokens or 4096,
        }
        
        if system_message:
            request_params["system"] = system_message
        
        if provider_tools:
            request_params["tools"] = provider_tools
        
        # 添加 thinking 级别
        if self.config.thinking_level:
            request_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": 16000 if self.config.thinking_level == "high" else 4000
            }
        
        request_params.update(kwargs)
        
        if stream:
            async with self.client.messages.stream(**request_params) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, 'text'):
                            yield {"type": "text_delta", "content": delta.text}
                        elif hasattr(delta, 'thinking'):
                            yield {"type": "thinking_delta", "content": delta.thinking}
                    
                    elif event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            yield {
                                "type": "tool_call_start",
                                "tool_call_id": event.content_block.id,
                                "name": event.content_block.name
                            }
                    
                    elif event.type == "message_stop":
                        yield {"type": "finish", "finish_reason": "stop"}
        else:
            response = await self.client.messages.create(**request_params)
            for block in response.content:
                if block.type == "text":
                    yield {"type": "text_delta", "content": block.text}
                elif block.type == "thinking":
                    yield {"type": "thinking_delta", "content": block.thinking}
                elif block.type == "tool_use":
                    yield {
                        "type": "tool_call_delta",
                        "tool_call_id": block.id,
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
            
            yield {
                "type": "finish",
                "finish_reason": "stop",
                "usage": {
                    "input_tokens": response.usage.input_tokens if response.usage else 0,
                    "output_tokens": response.usage.output_tokens if response.usage else 0,
                }
            }


def create_llm_provider(config: LLMConfig) -> LLMProvider:
    """
    创建 LLM 提供商实例
    
    Args:
        config: LLM 配置
        
    Returns:
        LLMProvider 实例
    """
    if config.provider == "openai":
        return OpenAIProvider(config)
    elif config.provider == "anthropic":
        return AnthropicProvider(config)
    elif config.provider == "kimi-coding":
        # Kimi For Coding 使用 OpenAI 格式，但需要特殊 User-Agent
        return OpenAIProvider(config)
    else:
        # 默认使用 OpenAI 格式（兼容大多数 API）
        return OpenAIProvider(config)
