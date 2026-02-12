"""
JSON Streaming Parser
Equivalent to Pi Mono's packages/ai/src/json-streaming-parser.ts

Streaming JSON parser for partial content handling.
Supports partial JSON parsing for streaming scenarios.
"""
import json
import re
from enum import Enum
from typing import Optional, Dict, Any, Callable, List, Tuple, Union
from dataclasses import dataclass


class JSONParseEventType(Enum):
    """JSON parse event types"""
    VALUE = "value"
    ERROR = "error"
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"


@dataclass
class JSONParseEvent:
    """JSON parse event"""
    type: JSONParseEventType
    value: Any = None
    path: str = ""
    error: Optional[str] = None


@dataclass
class PartialJSONResult:
    """Result of partial JSON parsing"""
    parsed: Any  # The successfully parsed portion
    remaining: str  # The remaining unparsed text
    is_complete: bool  # Whether the JSON was fully parsed
    error: Optional[str] = None  # Error message if any


class PartialJSONParser:
    """
    Parser for incomplete/partial JSON content.

    Handles:
    - Truncated strings: "hello wo -> "hello wo"
    - Truncated arrays: [1, 2, 3 -> [1, 2, 3]
    - Truncated objects: {"a": 1, "b" -> {"a": 1}
    - Nested structures: {"arr": [1, 2, {"x -> {"arr": [1, 2, {}]}

    Example:
        >>> parser = PartialJSONParser()
        >>> result = parser.parse('{"name": "test", "age": 2')
        >>> print(result.parsed)
        {'name': 'test'}
        >>> print(result.remaining)
        ', "age": 2'
    """

    # Patterns for detecting incomplete structures
    INCOMPLETE_STRING_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*$')
    NUMBER_PATTERN = re.compile(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d*)?$')

    def __init__(self, strict: bool = False):
        """
        Initialize partial JSON parser.

        Args:
            strict: If True, raise errors on invalid JSON. If False, try to recover.
        """
        self.strict = strict

    def parse(self, text: str) -> PartialJSONResult:
        """
        Parse potentially incomplete JSON text.

        Args:
            text: JSON text that may be incomplete

        Returns:
            PartialJSONResult with parsed value and remaining text
        """
        text = text.strip()

        if not text:
            return PartialJSONResult(
                parsed=None,
                remaining="",
                is_complete=True
            )

        try:
            # First, try to parse as complete JSON
            return self._try_complete_parse(text)
        except json.JSONDecodeError:
            # Try to parse as partial JSON
            return self._parse_partial(text)

    def _try_complete_parse(self, text: str) -> PartialJSONResult:
        """Try to parse text as complete JSON."""
        decoder = json.JSONDecoder()
        try:
            value, idx = decoder.raw_decode(text)
            remaining = text[idx:].strip()
            return PartialJSONResult(
                parsed=value,
                remaining=remaining,
                is_complete=not remaining
            )
        except json.JSONDecodeError:
            raise

    def _parse_partial(self, text: str) -> PartialJSONResult:
        """Parse incomplete JSON text."""
        if not text:
            return PartialJSONResult(
                parsed=None,
                remaining="",
                is_complete=True
            )

        first_char = text[0]

        try:
            if first_char == '{':
                return self._parse_partial_object(text)
            elif first_char == '[':
                return self._parse_partial_array(text)
            elif first_char == '"':
                return self._parse_partial_string(text)
            elif first_char.isdigit() or first_char == '-':
                return self._parse_partial_number(text)
            elif text.lower().startswith('true'):
                return PartialJSONResult(parsed=True, remaining=text[4:], is_complete=False)
            elif text.lower().startswith('false'):
                return PartialJSONResult(parsed=False, remaining=text[5:], is_complete=False)
            elif text.lower().startswith('null'):
                return PartialJSONResult(parsed=None, remaining=text[4:], is_complete=False)
            else:
                return PartialJSONResult(
                    parsed=None,
                    remaining=text,
                    is_complete=False,
                    error=f"Unexpected character: {first_char}"
                )
        except Exception as e:
            return PartialJSONResult(
                parsed=None,
                remaining=text,
                is_complete=False,
                error=str(e)
            )

    def _parse_partial_object(self, text: str) -> PartialJSONResult:
        """Parse incomplete JSON object."""
        if not text.startswith('{'):
            return PartialJSONResult(
                parsed=None,
                remaining=text,
                is_complete=False,
                error="Expected '{'"
            )

        result = {}
        pos = 1  # Skip opening brace
        text = text[pos:]

        while text:
            text = text.lstrip()

            if not text:
                # Ran out of text while parsing object
                return PartialJSONResult(
                    parsed=result,
                    remaining="",
                    is_complete=False
                )

            if text[0] == '}':
                # Object is complete
                return PartialJSONResult(
                    parsed=result,
                    remaining=text[1:],
                    is_complete=True
                )

            if text[0] == ',':
                text = text[1:].lstrip()
                if not text:
                    return PartialJSONResult(
                        parsed=result,
                        remaining="",
                        is_complete=False
                    )

            # Parse key
            if text[0] != '"':
                # Key must be a string
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False,
                    error="Expected string key"
                )

            key_result = self._parse_partial_string(text)
            if key_result.error and self.strict:
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False,
                    error=key_result.error
                )

            key = key_result.parsed
            if key is None:
                # Incomplete key
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False
                )

            text = key_result.remaining.lstrip()

            # Expect colon
            if not text:
                return PartialJSONResult(
                    parsed=result,
                    remaining="",
                    is_complete=False
                )

            if text[0] != ':':
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False,
                    error="Expected ':'"
                )

            text = text[1:].lstrip()

            if not text:
                return PartialJSONResult(
                    parsed=result,
                    remaining="",
                    is_complete=False
                )

            # Parse value
            value_result = self._parse_partial(text)
            if value_result.error and self.strict:
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False,
                    error=value_result.error
                )

            result[key] = value_result.parsed
            text = value_result.remaining.lstrip()

            if value_result.error or not text:
                # Incomplete value
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False
                )

        return PartialJSONResult(
            parsed=result,
            remaining="",
            is_complete=False
        )

    def _parse_partial_array(self, text: str) -> PartialJSONResult:
        """Parse incomplete JSON array."""
        if not text.startswith('['):
            return PartialJSONResult(
                parsed=None,
                remaining=text,
                is_complete=False,
                error="Expected '['"
            )

        result = []
        text = text[1:]  # Skip opening bracket

        while text:
            text = text.lstrip()

            if not text:
                # Ran out of text while parsing array
                return PartialJSONResult(
                    parsed=result,
                    remaining="",
                    is_complete=False
                )

            if text[0] == ']':
                # Array is complete
                return PartialJSONResult(
                    parsed=result,
                    remaining=text[1:],
                    is_complete=True
                )

            if text[0] == ',':
                text = text[1:].lstrip()
                if not text:
                    return PartialJSONResult(
                        parsed=result,
                        remaining="",
                        is_complete=False
                    )

            # Parse value
            value_result = self._parse_partial(text)
            if value_result.error and self.strict:
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False,
                    error=value_result.error
                )

            result.append(value_result.parsed)
            text = value_result.remaining.lstrip()

            if value_result.error or not text:
                # Incomplete value
                return PartialJSONResult(
                    parsed=result,
                    remaining=text,
                    is_complete=False
                )

        return PartialJSONResult(
            parsed=result,
            remaining="",
            is_complete=False
        )

    def _parse_partial_string(self, text: str) -> PartialJSONResult:
        """Parse incomplete JSON string."""
        if not text.startswith('"'):
            return PartialJSONResult(
                parsed=None,
                remaining=text,
                is_complete=False,
                error="Expected '\"'"
            )

        # Try to find the closing quote
        i = 1
        result_chars = []

        while i < len(text):
            char = text[i]

            if char == '\\':
                # Escape sequence
                if i + 1 >= len(text):
                    # Incomplete escape sequence
                    return PartialJSONResult(
                        parsed=''.join(result_chars),
                        remaining="",
                        is_complete=False
                    )

                next_char = text[i + 1]
                escape_map = {
                    '"': '"', '\\': '\\', '/': '/', 'b': '\b',
                    'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'
                }

                if next_char in escape_map:
                    result_chars.append(escape_map[next_char])
                    i += 2
                elif next_char == 'u':
                    # Unicode escape
                    if i + 5 >= len(text):
                        # Incomplete unicode escape
                        return PartialJSONResult(
                            parsed=''.join(result_chars),
                            remaining="",
                            is_complete=False
                        )
                    hex_chars = text[i + 2:i + 6]
                    try:
                        code_point = int(hex_chars, 16)
                        result_chars.append(chr(code_point))
                        i += 6
                    except ValueError:
                        return PartialJSONResult(
                            parsed=''.join(result_chars),
                            remaining=text[i:],
                            is_complete=False,
                            error=f"Invalid unicode escape: \\u{hex_chars}"
                        )
                else:
                    result_chars.append(next_char)
                    i += 2
            elif char == '"':
                # End of string
                return PartialJSONResult(
                    parsed=''.join(result_chars),
                    remaining=text[i + 1:],
                    is_complete=True
                )
            else:
                result_chars.append(char)
                i += 1

        # String was never closed
        return PartialJSONResult(
            parsed=''.join(result_chars),
            remaining="",
            is_complete=False
        )

    def _parse_partial_number(self, text: str) -> PartialJSONResult:
        """Parse incomplete JSON number."""
        match = self.NUMBER_PATTERN.match(text)

        if match:
            number_str = match.group()
            try:
                if '.' in number_str or 'e' in number_str.lower():
                    value = float(number_str)
                else:
                    value = int(number_str)
                return PartialJSONResult(
                    parsed=value,
                    remaining=text[len(number_str):],
                    is_complete=True
                )
            except ValueError:
                pass

        # Try to find where number parsing stopped
        number_chars = []
        for i, char in enumerate(text):
            if char.isdigit() or char in '-+.eE':
                number_chars.append(char)
            else:
                break

        if number_chars:
            number_str = ''.join(number_chars)
            try:
                if '.' in number_str or 'e' in number_str.lower():
                    value = float(number_str)
                else:
                    value = int(number_str)
                return PartialJSONResult(
                    parsed=value,
                    remaining=text[len(number_chars):],
                    is_complete=False
                )
            except ValueError:
                pass

        return PartialJSONResult(
            parsed=None,
            remaining=text,
            is_complete=False,
            error="Invalid number"
        )


def parse_partial_json(text: str, strict: bool = False) -> PartialJSONResult:
    """
    Parse potentially incomplete JSON text.

    This is a convenience function that creates a PartialJSONParser
    and parses the text.

    Args:
        text: JSON text that may be incomplete
        strict: If True, raise errors on invalid JSON. If False, try to recover.

    Returns:
        PartialJSONResult with parsed value and remaining text

    Example:
        >>> result = parse_partial_json('{"name": "test", "items": [1, 2')
        >>> print(result.parsed)
        {'name': 'test', 'items': [1, 2]}
        >>> print(result.is_complete)
        False
    """
    parser = PartialJSONParser(strict=strict)
    return parser.parse(text)


class StreamingJSONCollector:
    """
    Collects streaming JSON chunks and provides incremental parsing.

    Useful for LLM streaming responses where you want to access
    partially parsed JSON as it arrives.

    Example:
        >>> collector = StreamingJSONCollector()
        >>> collector.add_chunk('{"name": "')
        >>> collector.add_chunk('test", "count": ')
        >>> collector.add_chunk('42}')
        >>> result = collector.get_partial()
        >>> print(result.parsed)
        {'name': 'test', 'count': 42}
    """

    def __init__(self, strict: bool = False):
        """
        Initialize streaming collector.

        Args:
            strict: If True, raise errors on invalid JSON
        """
        self.buffer = ""
        self.parser = PartialJSONParser(strict=strict)
        self._last_result: Optional[PartialJSONResult] = None

    def add_chunk(self, chunk: str) -> PartialJSONResult:
        """
        Add a chunk of JSON data.

        Args:
            chunk: JSON string chunk

        Returns:
            Current partial parse result
        """
        self.buffer += chunk
        self._last_result = self.parser.parse(self.buffer)
        return self._last_result

    def get_partial(self) -> PartialJSONResult:
        """
        Get current partial parse result.

        Returns:
            PartialJSONResult with current parsed state
        """
        if self._last_result is None:
            self._last_result = self.parser.parse(self.buffer)
        return self._last_result

    def is_complete(self) -> bool:
        """Check if JSON parsing is complete."""
        result = self.get_partial()
        return result.is_complete and not result.remaining

    def get_value(self) -> Any:
        """
        Get the current parsed value.

        Returns:
            Parsed JSON value or None if nothing parsed yet
        """
        result = self.get_partial()
        return result.parsed

    def reset(self):
        """Reset collector state."""
        self.buffer = ""
        self._last_result = None


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
    "PartialJSONParser",
    "PartialJSONResult",
    "StreamingJSONCollector",
    "parse_partial_json",
]
