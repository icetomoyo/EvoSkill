"""
Resolve Config Value
Equivalent to Pi Mono's packages/coding-agent/src/core/resolve-config-value.ts

Resolves configuration values that may be shell commands, environment variables, or literals.
Used by auth-storage.ts and model-registry.ts.

SYNTAX:
- If starts with "!", executes the rest as a shell command and uses stdout (cached)
- Otherwise checks environment variable first, then treats as literal (not cached)
"""
import os
import subprocess
from typing import Optional, Dict
from pathlib import Path


# Cache for shell command results (persists for process lifetime)
_command_result_cache: Dict[str, Optional[str]] = {}


def resolve_config_value(config: str) -> Optional[str]:
    """
    Resolve a config value (API key, header value, etc.) to an actual value.

    Syntax:
    - If starts with "!", executes the rest as a shell command and uses stdout (cached)
    - Otherwise checks environment variable first, then treats as literal (not cached)

    Examples:
        >>> resolve_config_value("!echo $API_KEY")  # Execute command
        'my-api-key'
        >>> resolve_config_value("OPENAI_API_KEY")  # Check env var
        'sk-...'
        >>> resolve_config_value("literal-value")  # Return as-is
        'literal-value'

    Args:
        config: Configuration value that may be a command (!command), 
                environment variable name, or literal string

    Returns:
        Resolved value, or None if command/env var not found
    """
    if not config:
        return None

    # If starts with "!", execute as shell command
    if config.startswith("!"):
        return _execute_command(config)

    # Otherwise, check environment variable first
    env_value = os.getenv(config)
    if env_value is not None:
        return env_value

    # Treat as literal
    return config


def _execute_command(command_config: str) -> Optional[str]:
    """
    Execute a shell command and return stdout.

    Results are cached for the process lifetime to avoid repeated execution.

    Args:
        command_config: Command string starting with "!"

    Returns:
        Command stdout (stripped), or None if command fails
    """
    # Check cache first
    if command_config in _command_result_cache:
        return _command_result_cache[command_config]

    # Remove the leading "!"
    command = command_config[1:]

    result: Optional[str] = None
    try:
        output = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            # stdin is implicitly DEVNULL when capture_output is True
        )
        if output.returncode == 0:
            result = output.stdout.strip() if output.stdout else None
        else:
            result = None
    except subprocess.TimeoutExpired:
        result = None
    except Exception:
        result = None

    # Cache the result
    _command_result_cache[command_config] = result
    return result


def resolve_headers(headers: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Resolve all header values using the same resolution logic as API keys.

    Supports embedded commands within values (e.g., "Bearer !echo token").

    Args:
        headers: Dictionary of header names to values (which may be commands/env vars)

    Returns:
        Dictionary with resolved values, or None if no valid headers
    """
    if not headers:
        return None

    resolved: Dict[str, str] = {}
    for key, value in headers.items():
        resolved_value = _resolve_embedded_commands(value)
        if resolved_value is not None:
            resolved[key] = resolved_value

    return resolved if resolved else None


def _resolve_embedded_commands(value: str) -> Optional[str]:
    """
    Resolve embedded commands within a value.

    Supports patterns like:
    - "Bearer !echo token" -> "Bearer token"
    - "${API_KEY}" -> (env var value)
    - "literal" -> "literal"
    - "!command" -> (command output)

    Args:
        value: Value that may contain embedded commands

    Returns:
        Resolved value
    """
    if not value:
        return value

    import re

    # Pattern to match !command within text
    # Matches !command or !command args (up to end of string or space if followed by non-command)
    command_pattern = r'!([^\s]+(?:\s+[^\s]+)*)'

    def replace_command(match):
        full_match = match.group(0)
        command = match.group(1)
        result = _execute_command("!" + command)
        return result if result else full_match

    # Replace all embedded commands
    result = re.sub(command_pattern, replace_command, value)

    # Check if result is an env var reference (for backward compatibility)
    if result and not result.startswith("!"):
        env_value = os.getenv(result)
        if env_value is not None:
            return env_value

    return result


def resolve_model_config(config: Dict[str, any]) -> Dict[str, any]:
    """
    Resolve all values in a model configuration dict.

    Recursively resolves strings that may be commands or env vars.

    Args:
        config: Model configuration dictionary

    Returns:
        Configuration with resolved values
    """
    resolved = {}
    for key, value in config.items():
        if isinstance(value, str):
            resolved[key] = resolve_config_value(value)
        elif isinstance(value, dict):
            resolved[key] = resolve_model_config(value)
        elif isinstance(value, list):
            resolved[key] = [
                resolve_config_value(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            resolved[key] = value
    return resolved


def clear_config_value_cache() -> None:
    """
    Clear the config value command cache.

    Exported for testing purposes.
    """
    _command_result_cache.clear()


def get_cache_size() -> int:
    """
    Get the number of cached command results.

    Returns:
        Cache size
    """
    return len(_command_result_cache)


def is_cached(config: str) -> bool:
    """
    Check if a config value is in the cache.

    Args:
        config: Config value to check

    Returns:
        True if in cache
    """
    return config in _command_result_cache
