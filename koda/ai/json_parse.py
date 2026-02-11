"""
JSON Parsing Utilities
Equivalent to Pi Mono's packages/ai/src/utils/json-parse.ts

Streaming JSON parser for incomplete JSON data.
"""
import json
from typing import Any, Optional


def parse_streaming_json(json_str: str) -> Optional[Any]:
    """
    Parse potentially incomplete JSON string.
    
    Attempts to parse the JSON string. If it fails due to being incomplete
    (e.g., from a streaming response), it tries to extract valid JSON objects.
    
    Args:
        json_str: JSON string that may be incomplete
        
    Returns:
        Parsed JSON object, or None if parsing fails
        
    Examples:
        >>> parse_streaming_json('{"key": "value"}')
        {'key': 'value'}
        >>> parse_streaming_json('{"key": "val')  # incomplete
        None
    """
    if not json_str or not json_str.strip():
        return None
    
    try:
        # Try normal parsing first
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # Try to find complete JSON objects
    # For object parsing, try adding closing braces
    try:
        # Try with closing brace
        if json_str.strip().startswith('{'):
            result = json.loads(json_str + '}')
            return result
    except json.JSONDecodeError:
        pass
    
    try:
        # Try with closing braces for nested objects
        if json_str.strip().startswith('{'):
            result = json.loads(json_str + '}}')
            return result
    except json.JSONDecodeError:
        pass
    
    try:
        # Try parsing as array
        if json_str.strip().startswith('['):
            result = json.loads(json_str + ']')
            return result
    except json.JSONDecodeError:
        pass
    
    return None


def try_parse_partial_json(json_str: str) -> tuple[Optional[Any], str]:
    """
    Try to parse partial JSON, returning parsed content and remaining string.
    
    Args:
        json_str: JSON string that may contain partial data
        
    Returns:
        Tuple of (parsed object or None, remaining unparsed string)
    """
    if not json_str:
        return None, ""
    
    # Try to parse the whole thing first
    try:
        result = json.loads(json_str)
        return result, ""
    except json.JSONDecodeError:
        pass
    
    # Try incremental parsing
    for i in range(len(json_str), 0, -1):
        try:
            result = json.loads(json_str[:i])
            return result, json_str[i:]
        except json.JSONDecodeError:
            continue
    
    return None, json_str
