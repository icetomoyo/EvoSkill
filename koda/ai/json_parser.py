"""
JSON Streaming Parser
Equivalent to Pi Mono's packages/ai/src/json-streaming-parser.ts

Streaming JSON parser for partial content handling.
"""
import json
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass


class JSONParseEventType(Enum):
    """JSON parse event types"""
    VALUE = "value"
    ERROR = "error"
    INCOMPLETE = "incomplete"


@dataclass
class JSONParseEvent:
    """JSON parse event"""
    type: JSONParseEventType
    value: Any = None
    path: str = ""
    error: Optional[str] = None


class JSONStreamingParser:
    """
    Streaming JSON parser that handles partial/incomplete JSON.
    
    Useful for parsing JSON from streaming LLM responses where
    the content may be incomplete.
    
    Example:
        >>> parser = JSONStreamingParser()
        >>> for event in parser.feed('{"name": "test'):
        ...     print(event.type)
        incomplete
        >>> for event in parser.feed('"}'):
        ...     print(event.type, event.value)
        value {'name': 'test'}
    """
    
    def __init__(self):
        self.buffer = ""
        self.decoder = json.JSONDecoder()
    
    def feed(self, chunk: str) -> list:
        """
        Feed a chunk of JSON data.
        
        Args:
            chunk: JSON string chunk
            
        Returns:
            List of parse events
        """
        self.buffer += chunk
        events = []
        
        while self.buffer:
            self.buffer = self.buffer.strip()
            if not self.buffer:
                break
            
            try:
                value, idx = self.decoder.raw_decode(self.buffer)
                events.append(JSONParseEvent(
                    type=JSONParseEventType.VALUE,
                    value=value
                ))
                self.buffer = self.buffer[idx:]
            except json.JSONDecodeError as e:
                # Check if it's just incomplete or actually invalid
                if self._is_incomplete():
                    events.append(JSONParseEvent(
                        type=JSONParseEventType.INCOMPLETE,
                        error="Incomplete JSON"
                    ))
                else:
                    events.append(JSONParseEvent(
                        type=JSONParseEventType.ERROR,
                        error=str(e)
                    ))
                break
        
        return events
    
    def _is_incomplete(self) -> bool:
        """Check if buffer contains incomplete but valid JSON"""
        # Simple heuristic: if it looks like it could be complete
        # with more data, consider it incomplete
        text = self.buffer.strip()
        
        if not text:
            return False
        
        # Check for unclosed structures
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        open_quotes = text.count('"') % 2
        
        return open_braces > 0 or open_brackets > 0 or open_quotes > 0
    
    def parse_complete(self, text: str) -> Any:
        """
        Parse complete JSON text.
        
        Args:
            text: Complete JSON string
            
        Returns:
            Parsed JSON value
            
        Raises:
            json.JSONDecodeError: If invalid JSON
        """
        return json.loads(text)
    
    def reset(self):
        """Reset parser state"""
        self.buffer = ""


__all__ = [
    "JSONStreamingParser",
    "JSONParseEvent",
    "JSONParseEventType",
]
