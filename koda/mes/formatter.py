"""
Message Formatter

Formats messages for different LLM providers.
Handles provider-specific message format conversion.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import json

from koda.ai.provider import Message, ToolCall


@dataclass
class FormattedMessage:
    """Provider-specific formatted message"""
    provider: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return self.data


class MessageFormatter:
    """
    Formats messages for different providers
    
    Supports:
    - OpenAI format
    - Anthropic format
    - Google Gemini format
    - Generic format
    """
    
    def __init__(self, provider: str):
        """
        Args:
            provider: Provider name (openai, anthropic, google)
        """
        self.provider = provider.lower()
    
    def format_messages(self, messages: List[Message]) -> List[FormattedMessage]:
        """
        Format messages for the provider
        
        Args:
            messages: Unified messages
            
        Returns:
            List of formatted messages
        """
        if self.provider == "openai":
            return self._format_openai(messages)
        elif self.provider == "anthropic":
            return self._format_anthropic(messages)
        elif self.provider == "google":
            return self._format_google(messages)
        else:
            # Generic OpenAI-compatible
            return self._format_openai(messages)
    
    def _format_openai(self, messages: List[Message]) -> List[FormattedMessage]:
        """Format for OpenAI API"""
        result = []
        
        for msg in messages:
            formatted: Dict[str, Any] = {"role": msg.role}
            
            if msg.role == "tool":
                formatted["tool_call_id"] = msg.tool_call_id
                formatted["content"] = self._stringify_content(msg.content)
                if msg.name:
                    formatted["name"] = msg.name
            
            elif msg.role == "assistant" and msg.tool_calls:
                formatted["content"] = msg.content or ""
                formatted["tool_calls"] = [
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
                formatted["content"] = msg.content
            
            result.append(FormattedMessage(provider="openai", data=formatted))
        
        return result
    
    def _format_anthropic(self, messages: List[Message]) -> List[FormattedMessage]:
        """Format for Anthropic Claude API"""
        result = []
        system_content = ""
        
        for msg in messages:
            if msg.role == "system":
                system_content = self._stringify_content(msg.content)
                continue
            
            formatted: Dict[str, Any] = {"role": msg.role if msg.role != "assistant" else "assistant"}
            
            if msg.role == "tool":
                formatted["role"] = "user"
                formatted["content"] = [{
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": self._stringify_content(msg.content)
                }]
            
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
                formatted["content"] = content
            
            else:
                content = self._stringify_content(msg.content)
                formatted["content"] = content
            
            result.append(FormattedMessage(provider="anthropic", data=formatted))
        
        # Prepend system as special field if present
        if system_content:
            result.insert(0, FormattedMessage(
                provider="anthropic",
                data={"role": "system", "content": system_content}
            ))
        
        return result
    
    def _format_google(self, messages: List[Message]) -> List[FormattedMessage]:
        """Format for Google Gemini API"""
        result = []
        
        for msg in messages:
            formatted: Dict[str, Any] = {}
            
            # Map roles
            role_map = {
                "system": "user",  # Gemini doesn't have system role
                "user": "user",
                "assistant": "model",
                "tool": "user",
            }
            
            formatted["role"] = role_map.get(msg.role, "user")
            
            # Format content
            if isinstance(msg.content, list):
                parts = []
                for part in msg.content:
                    if isinstance(part, dict):
                        if part.get("type") == "image_url":
                            parts.append({
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": part["image_url"]["url"]
                                }
                            })
                        else:
                            parts.append({"text": str(part.get("text", ""))})
                    else:
                        parts.append({"text": str(part)})
                formatted["parts"] = parts
            else:
                formatted["parts"] = [{"text": self._stringify_content(msg.content)}]
            
            result.append(FormattedMessage(provider="google", data=formatted))
        
        return result
    
    def _stringify_content(self, content: Any) -> str:
        """Convert content to string"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Extract text from content parts
            texts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    texts.append(part["text"])
                else:
                    texts.append(str(part))
            return " ".join(texts)
        else:
            return str(content)
    
    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format tool definitions for provider
        
        Args:
            tools: Tool definitions
            
        Returns:
            Formatted tools
        """
        if self.provider == "anthropic":
            # Anthropic uses different format
            return [self._convert_tool_anthropic(t) for t in tools]
        
        # OpenAI format is default
        return tools
    
    def _convert_tool_anthropic(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAI tool format to Anthropic"""
        if "function" in tool:
            func = tool["function"]
            return {
                "name": func["name"],
                "description": func["description"],
                "input_schema": func.get("parameters", {"type": "object", "properties": {}})
            }
        return tool


def create_formatter(provider: str) -> MessageFormatter:
    """Factory function to create formatter"""
    return MessageFormatter(provider)
