"""
Shell Utilities
Equivalent to Pi Mono's packages/coding-agent/src/utils/shell.ts

Shell command helpers and utilities.
"""
import os
import re
import shlex
import subprocess
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ShellResult:
    """Shell command result"""
    stdout: str
    stderr: str
    returncode: int
    command: str


class ShellUtils:
    """
    Shell command utilities.
    
    Provides safe shell execution, escaping, and helpers.
    
    Example:
        >>> utils = ShellUtils()
        >>> result = utils.run("echo hello")
        >>> result.stdout.strip()
        'hello'
    """
    
    def __init__(self, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        """
        Initialize shell utils.
        
        Args:
            cwd: Working directory for commands
            env: Environment variables
        """
        self.cwd = cwd or os.getcwd()
        self.env = {**os.environ, **(env or {})}
    
    def run(
        self,
        command: str,
        timeout: int = 60,
        capture: bool = True
    ) -> ShellResult:
        """
        Run a shell command.
        
        Args:
            command: Command to run
            timeout: Timeout in seconds
            capture: Capture output
            
        Returns:
            ShellResult with output and exit code
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                env=self.env,
                capture_output=capture,
                text=True,
                timeout=timeout
            )
            
            return ShellResult(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                returncode=result.returncode,
                command=command
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                returncode=-1,
                command=command
            )
        except Exception as e:
            return ShellResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                command=command
            )
    
    def run_safe(
        self,
        command: List[str],
        timeout: int = 60
    ) -> ShellResult:
        """
        Run a command without shell (safer).
        
        Args:
            command: Command as list of args
            timeout: Timeout in seconds
            
        Returns:
            ShellResult
        """
        try:
            result = subprocess.run(
                command,
                cwd=self.cwd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return ShellResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                command=" ".join(shlex.quote(c) for c in command)
            )
        except Exception as e:
            return ShellResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                command=" ".join(command)
            )
    
    def which(self, program: str) -> Optional[str]:
        """
        Find program in PATH.
        
        Args:
            program: Program name
            
        Returns:
            Full path or None
        """
        # Use 'where' on Windows, 'which' on Unix
        if os.name == 'nt':
            result = self.run(f"where {program}")
        else:
            result = self.run(f"which {program}")
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
        return None
    
    def escape(self, arg: str) -> str:
        """
        Escape a shell argument.
        
        Args:
            arg: Argument to escape
            
        Returns:
            Escaped argument
        """
        return shlex.quote(arg)
    
    def is_safe_command(self, command: str) -> Tuple[bool, str]:
        """
        Check if a command is safe to run.
        
        Returns:
            (is_safe, reason)
        """
        dangerous = [
            r'rm\s+-rf\s+/',
            r':\(\)\{\s*:\|\:&\s*\};\s*:',
            r'>\s*/dev/sda',
            r'dd\s+if=.*\s+of=/dev/sda',
            r'mkfs\.',
            r'curl.*\|\s*sh',
            r'wget.*\|\s*sh',
        ]
        
        for pattern in dangerous:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Potentially dangerous command detected"
        
        return True, ""
    
    def expand_path(self, path: str) -> str:
        """
        Expand ~ and environment variables in path.
        
        Args:
            path: Path with possible ~ or $VAR
            
        Returns:
            Expanded path
        """
        return os.path.expandvars(os.path.expanduser(path))
    
    def find_files(
        self,
        pattern: str,
        directory: str = ".",
        recursive: bool = True
    ) -> List[str]:
        """
        Find files matching pattern.
        
        Args:
            pattern: Glob pattern
            directory: Search directory
            recursive: Search recursively
            
        Returns:
            List of matching files
        """
        from pathlib import Path
        
        base_path = Path(self.expand_path(directory))
        
        if recursive:
            matches = list(base_path.rglob(pattern))
        else:
            matches = list(base_path.glob(pattern))
        
        return [str(m) for m in matches if m.is_file()]


# Convenience functions
def run_command(command: str, cwd: Optional[str] = None, timeout: int = 60) -> ShellResult:
    """Run a shell command"""
    utils = ShellUtils(cwd=cwd)
    return utils.run(command, timeout=timeout)


def escape_shell_arg(arg: str) -> str:
    """Escape a shell argument"""
    return shlex.quote(arg)


def which(program: str) -> Optional[str]:
    """Find program in PATH"""
    utils = ShellUtils()
    return utils.which(program)


__all__ = [
    "ShellUtils",
    "ShellResult",
    "run_command",
    "escape_shell_arg",
    "which",
]
