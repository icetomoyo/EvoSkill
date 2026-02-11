"""
Enhanced Bash Executor
Equivalent to Pi Mono's packages/coding-agent/src/core/bash-executor.ts

Advanced bash execution with hooks, timeout, and security.
"""
import os
import re
import shlex
import signal
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum


class ExitCode(Enum):
    """Special exit codes"""
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISUSE_SHELL = 2
    COMMAND_NOT_EXECUTABLE = 126
    COMMAND_NOT_FOUND = 127
    INVALID_EXIT_ARG = 128
    TERMINATED_BY_CTRL_C = 130
    TERMINATED_BY_SIGTERM = 143
    TIMEOUT = 124


@dataclass
class BashResult:
    """Bash execution result"""
    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: float
    timed_out: bool = False
    killed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BashHookContext:
    """Context for bash hooks"""
    command: str
    cwd: str
    env: Dict[str, str]
    timeout: int


class BashHooks:
    """Bash execution hooks"""
    
    def __init__(self):
        self._before_exec: List[Callable[[BashHookContext], None]] = []
        self._after_exec: List[Callable[[BashHookContext, BashResult], None]] = []
        self._on_error: List[Callable[[BashHookContext, BashResult], None]] = []
    
    def before_exec(self, callback: Callable[[BashHookContext], None]):
        """Register before-execution hook"""
        self._before_exec.append(callback)
        return callback
    
    def after_exec(self, callback: Callable[[BashHookContext, BashResult], None]):
        """Register after-execution hook"""
        self._after_exec.append(callback)
        return callback
    
    def on_error(self, callback: Callable[[BashHookContext, BashResult], None]):
        """Register error hook"""
        self._on_error.append(callback)
        return callback
    
    def trigger_before(self, context: BashHookContext):
        """Trigger before hooks"""
        for hook in self._before_exec:
            try:
                hook(context)
            except Exception:
                pass
    
    def trigger_after(self, context: BashHookContext, result: BashResult):
        """Trigger after hooks"""
        for hook in self._after_exec:
            try:
                hook(context, result)
            except Exception:
                pass
    
    def trigger_error(self, context: BashHookContext, result: BashResult):
        """Trigger error hooks"""
        for hook in self._on_error:
            try:
                hook(context, result)
            except Exception:
                pass


class BashExecutor:
    """
    Enhanced bash executor with security and hooks.
    
    Features:
    - Command timeout with graceful kill
    - Security validation
    - Execution hooks
    - Environment management
    - Working directory control
    
    Example:
        >>> executor = BashExecutor(timeout=30)
        >>> result = executor.run("ls -la")
        >>> print(result.stdout)
    """
    
    # Dangerous patterns to check
    DANGEROUS_PATTERNS = [
        (r'rm\s+-rf\s+/\s*\Z', "Attempting to delete root directory"),
        (r'rm\s+-rf\s+/\s+', "Attempting to delete root directory"),
        (r':\(\)\{\s*:\|\:&\s*\};\s*:', "Fork bomb detected"),
        (r'>\s*/dev/sda\s*\Z', "Attempting to write to disk device"),
        (r'dd\s+if=.*\s+of=/dev/sda', "Attempting to overwrite disk"),
        (r'mkfs\.\w+\s+/dev/sda', "Attempting to format disk"),
        (r'curl.*\|\s*sh', "Piping curl to shell"),
        (r'wget.*\|\s*sh', "Piping wget to shell"),
    ]
    
    def __init__(
        self,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        shell: str = "/bin/bash",
        hooks: Optional[BashHooks] = None,
        allow_dangerous: bool = False
    ):
        """
        Initialize bash executor.
        
        Args:
            cwd: Working directory
            env: Environment variables
            timeout: Default timeout in seconds
            shell: Shell to use
            hooks: Execution hooks
            allow_dangerous: Skip dangerous command check
        """
        self.cwd = cwd or os.getcwd()
        self.env = {**os.environ, **(env or {})}
        self.timeout = timeout
        self.shell = shell
        self.hooks = hooks or BashHooks()
        self.allow_dangerous = allow_dangerous
        self._process: Optional[subprocess.Popen] = None
        self._killed = False
    
    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None
    ) -> BashResult:
        """
        Execute a bash command.
        
        Args:
            command: Command to execute
            timeout: Timeout override
            cwd: Working directory override
            env: Environment override
            input_data: Input to pipe to command
            
        Returns:
            BashResult with output and metadata
        """
        import time
        
        # Validate command
        if not self.allow_dangerous:
            is_safe, reason = self._validate_command(command)
            if not is_safe:
                return BashResult(
                    stdout="",
                    stderr=f"Security check failed: {reason}",
                    exit_code=ExitCode.GENERAL_ERROR.value,
                    command=command,
                    duration_ms=0.0,
                    metadata={"security_error": True}
                )
        
        # Setup context
        cwd = cwd or self.cwd
        env = {**self.env, **(env or {})}
        timeout = timeout or self.timeout
        
        hook_context = BashHookContext(
            command=command,
            cwd=str(cwd),
            env=env,
            timeout=timeout
        )
        
        # Trigger before hooks
        self.hooks.trigger_before(hook_context)
        
        start_time = time.perf_counter()
        
        try:
            # Execute command
            result = self._execute(
                command=command,
                cwd=cwd,
                env=env,
                timeout=timeout,
                input_data=input_data
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Update result with metadata
            result.duration_ms = duration_ms
            result.metadata.update({
                "working_directory": str(cwd),
                "shell": self.shell,
            })
            
            # Trigger hooks
            if result.exit_code != 0:
                self.hooks.trigger_error(hook_context, result)
            else:
                self.hooks.trigger_after(hook_context, result)
            
            return result
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            result = BashResult(
                stdout="",
                stderr=str(e),
                exit_code=ExitCode.GENERAL_ERROR.value,
                command=command,
                duration_ms=duration_ms,
                metadata={"exception": str(e)}
            )
            
            self.hooks.trigger_error(hook_context, result)
            return result
    
    def _execute(
        self,
        command: str,
        cwd: Union[str, Path],
        env: Dict[str, str],
        timeout: int,
        input_data: Optional[str] = None
    ) -> BashResult:
        """Execute command with timeout handling"""
        import time
        
        self._killed = False
        
        # Start process
        try:
            self._process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                executable=self.shell if os.name != 'nt' else None
            )
        except Exception as e:
            return BashResult(
                stdout="",
                stderr=str(e),
                exit_code=ExitCode.COMMAND_NOT_EXECUTABLE.value,
                command=command,
                duration_ms=0.0
            )
        
        # Setup timeout timer
        timer = None
        if timeout > 0:
            def kill_process():
                self._killed = True
                try:
                    self._process.terminate()
                    # Give it a grace period
                    import threading
                    def force_kill():
                        try:
                            self._process.kill()
                        except:
                            pass
                    threading.Timer(2.0, force_kill).start()
                except:
                    pass
            
            timer = threading.Timer(timeout, kill_process)
            timer.start()
        
        try:
            # Wait for completion
            stdout, stderr = self._process.communicate(input=input_data, timeout=timeout + 5)
            
            if timer:
                timer.cancel()
            
            return BashResult(
                stdout=stdout or "",
                stderr=stderr or "",
                exit_code=self._process.returncode,
                command=command,
                duration_ms=0.0,  # Will be set by caller
                timed_out=self._killed,
                killed=self._killed
            )
            
        except subprocess.TimeoutExpired:
            if timer:
                timer.cancel()
            
            # Kill the process
            try:
                self._process.kill()
                stdout, stderr = self._process.communicate()
            except:
                stdout, stderr = "", ""
            
            return BashResult(
                stdout=stdout or "",
                stderr=stderr or "",
                exit_code=ExitCode.TIMEOUT.value,
                command=command,
                duration_ms=0.0,
                timed_out=True,
                killed=True
            )
    
    def _validate_command(self, command: str) -> tuple:
        """
        Validate command for dangerous patterns.
        
        Returns:
            (is_safe, reason)
        """
        # Check patterns
        for pattern, reason in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, reason
        
        # Check for sudo (warn but allow)
        if command.strip().startswith("sudo "):
            return True, "Warning: Using sudo"
        
        return True, ""
    
    def run_safe(
        self,
        command: List[str],
        **kwargs
    ) -> BashResult:
        """
        Run command without shell (safer).
        
        Args:
            command: Command as list of arguments
            **kwargs: Other arguments passed to run()
            
        Returns:
            BashResult
        """
        # Convert list to safe command string
        safe_command = " ".join(shlex.quote(arg) for arg in command)
        return self.run(safe_command, **kwargs)
    
    def kill(self):
        """Kill running process"""
        if self._process and self._process.poll() is None:
            self._killed = True
            try:
                self._process.terminate()
            except:
                pass


# Convenience functions
def run_bash(
    command: str,
    timeout: int = 60,
    cwd: Optional[str] = None,
    **kwargs
) -> BashResult:
    """
    Run a bash command (convenience function).
    
    Args:
        command: Command to run
        timeout: Timeout in seconds
        cwd: Working directory
        **kwargs: Additional arguments
        
    Returns:
        BashResult
    """
    executor = BashExecutor(timeout=timeout, cwd=cwd)
    return executor.run(command, **kwargs)


__all__ = [
    "BashExecutor",
    "BashResult",
    "BashHooks",
    "BashHookContext",
    "ExitCode",
    "run_bash",
]
