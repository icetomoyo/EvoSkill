"""
Config Value Resolver
Equivalent to Pi Mono's packages/ai/src/config-value-resolver.ts

Resolves config values with shell command substitution (!command syntax).
"""
import re
import subprocess
from typing import Optional, Union, Dict, Any


class ConfigValueResolver:
    """
    Resolves configuration values with special syntax.
    
    Supports:
    - Shell command substitution: !command
    - Environment variable substitution: $VAR or ${VAR}
    """
    
    # Pattern for shell command: !command
    COMMAND_PATTERN = re.compile(r'^!(.+)$')
    # Pattern for env var: $VAR or ${VAR}
    ENV_PATTERN = re.compile(r'\$\{?(\w+)\}?')
    
    def __init__(self, timeout: int = 30):
        """
        Initialize resolver.
        
        Args:
            timeout: Command execution timeout in seconds
        """
        self.timeout = timeout
    
    def resolve(self, value: Any) -> Any:
        """
        Resolve a config value.
        
        If value is a string starting with !, executes it as a shell command
        and returns the output. Otherwise returns the value unchanged.
        
        Args:
            value: Config value to resolve
            
        Returns:
            Resolved value
            
        Example:
            >>> resolver = ConfigValueResolver()
            >>> resolver.resolve("!echo hello")
            'hello'
            >>> resolver.resolve("normal value")
            'normal value'
        """
        if not isinstance(value, str):
            return value
        
        # Check for shell command
        match = self.COMMAND_PATTERN.match(value)
        if match:
            command = match.group(1)
            return self._execute_command(command)
        
        # Substitute environment variables
        value = self._substitute_env_vars(value)
        
        return value
    
    def _execute_command(self, command: str) -> str:
        """
        Execute a shell command and return output.
        
        Args:
            command: Shell command to execute
            
        Returns:
            Command output (stdout), stripped of whitespace
            
        Raises:
            RuntimeError: If command fails or times out
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out after {self.timeout}s: {command}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed with exit code {e.returncode}: {command}\n{e.stderr}")
    
    def _substitute_env_vars(self, value: str) -> str:
        """
        Substitute environment variables in a string.
        
        Args:
            value: String containing $VAR or ${VAR}
            
        Returns:
            String with variables substituted
        """
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        import os
        return self.ENV_PATTERN.sub(replace_var, value)
    
    def resolve_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all values in a config dictionary.
        
        Args:
            config: Dictionary with config values
            
        Returns:
            New dictionary with resolved values
        """
        return {k: self.resolve(v) for k, v in config.items()}


# Global resolver instance
_resolver: Optional[ConfigValueResolver] = None


def resolve_value(value: Any, timeout: int = 30) -> Any:
    """
    Resolve a config value using default resolver.
    
    Args:
        value: Value to resolve
        timeout: Command timeout in seconds
        
    Returns:
        Resolved value
    """
    global _resolver
    if _resolver is None:
        _resolver = ConfigValueResolver(timeout=timeout)
    return _resolver.resolve(value)


def resolve_dict(config: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """
    Resolve all values in a config dictionary.
    
    Args:
        config: Dictionary to resolve
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary with resolved values
    """
    resolver = ConfigValueResolver(timeout=timeout)
    return resolver.resolve_dict(config)


__all__ = [
    "ConfigValueResolver",
    "resolve_value",
    "resolve_dict",
]
