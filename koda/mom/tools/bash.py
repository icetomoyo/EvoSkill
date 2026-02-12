"""
Bash Tool - Shell command execution for Mom agent

Pi Mono compatible implementation:
- Execute shell commands
- Output truncation
- Timeout handling
- Security sandbox options
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import subprocess
import asyncio
import os
import sys
import tempfile

from koda.mom.tools.truncate import truncate_tail, format_size, DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES


@dataclass
class BashResult:
    """Result from executing a bash command"""
    success: bool
    output: str
    exit_code: int
    truncated: bool = False
    total_lines: int = 0
    output_lines: int = 0
    full_output_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AbortSignal:
    """Abort signal for cancelling execution."""

    def __init__(self):
        self._cancelled = False
        self._callbacks = []

    @property
    def aborted(self) -> bool:
        return self._cancelled

    def abort(self):
        """Trigger abort."""
        self._cancelled = True
        for callback in self._callbacks:
            try:
                callback()
            except:
                pass

    def on_abort(self, callback: Callable):
        """Register abort callback."""
        self._callbacks.append(callback)


def _kill_process_tree(pid: int):
    """Kill process tree (cross-platform)."""
    if sys.platform == 'win32':
        # Windows: use taskkill /T
        try:
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(pid)],
                capture_output=True,
                check=False
            )
        except:
            pass
    else:
        # Unix: try psutil, fallback to os.kill
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except:
                    pass
            parent.terminate()
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            for p in alive:
                try:
                    p.kill()
                except:
                    pass
        except ImportError:
            # Fallback: just kill the main process
            try:
                os.kill(pid, 9)
            except:
                pass
        except:
            pass


def execute_bash(
    command: str,
    base_path: Optional[Path] = None,
    timeout: int = 60,
    signal: Optional[AbortSignal] = None,
    on_update: Optional[Callable[[str], None]] = None,
    env: Optional[Dict[str, str]] = None,
) -> BashResult:
    """
    Execute a shell command (synchronous version).

    Args:
        command: Command to execute
        base_path: Working directory
        timeout: Timeout in seconds
        signal: Abort signal
        on_update: Output update callback
        env: Environment variables

    Returns:
        BashResult with output and status
    """
    base_path = base_path or Path.cwd()
    temp_file_path = None
    temp_file = None

    try:
        # Check working directory
        if not base_path.exists():
            return BashResult(
                success=False,
                output="",
                exit_code=-1,
                error=f"Working directory does not exist: {base_path}",
            )

        # Build environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Create subprocess
        if sys.platform == 'win32':
            # Windows: use cmd.exe
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(base_path),
                env=process_env,
            )
        else:
            # Unix: use bash
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(base_path),
                env=process_env,
            )

        # Collect output
        chunks = []
        chunks_bytes = 0
        max_chunks_bytes = DEFAULT_MAX_BYTES * 2
        total_bytes = 0

        try:
            # Read with timeout
            import time
            start_time = time.time()

            while True:
                # Check abort
                if signal and signal.aborted:
                    _kill_process_tree(process.pid)
                    break

                # Check timeout
                if time.time() - start_time > timeout:
                    _kill_process_tree(process.pid)
                    break

                # Try to read
                try:
                    # Use select for non-blocking read (Unix only)
                    if sys.platform != 'win32':
                        import select
                        readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
                    else:
                        readable = [process.stdout, process.stderr]

                    for stream in readable:
                        line = stream.read(8192)
                        if not line:
                            continue

                        total_bytes += len(line)

                        # Start writing to temp file once we exceed threshold
                        if total_bytes > DEFAULT_MAX_BYTES and not temp_file:
                            temp_file = tempfile.NamedTemporaryFile(
                                mode='w+b',
                                delete=False,
                                suffix='.log',
                                prefix='koda-bash-'
                            )
                            temp_file_path = temp_file.name
                            # Write buffered chunks
                            for chunk in chunks:
                                temp_file.write(chunk)

                        # Write to temp file if we have one
                        if temp_file:
                            temp_file.write(line)

                        # Keep rolling buffer
                        chunks.append(line)
                        chunks_bytes += len(line)

                        # Trim old chunks
                        while chunks_bytes > max_chunks_bytes and len(chunks) > 1:
                            removed = chunks.pop(0)
                            chunks_bytes -= len(removed)

                        # Stream to callback
                        if on_update:
                            text = line.decode('utf-8', errors='replace')
                            on_update(text)

                except Exception:
                    pass

                # Check if process finished
                if process.poll() is not None:
                    # Read any remaining output
                    remaining_stdout = process.stdout.read()
                    remaining_stderr = process.stderr.read()
                    if remaining_stdout:
                        chunks.append(remaining_stdout)
                    if remaining_stderr:
                        chunks.append(remaining_stderr)
                    break

        except Exception:
            pass

        # Get exit code
        exit_code = process.returncode if process.returncode is not None else -1

        # Close temp file
        if temp_file:
            temp_file.close()

        # Check abort signal
        if signal and signal.aborted:
            full_output = b''.join(chunks).decode('utf-8', errors='replace')
            return BashResult(
                success=False,
                output=full_output,
                exit_code=-1,
                error="Command aborted",
            )

        # Combine output
        full_buffer = b''.join(chunks)
        full_output = full_buffer.decode('utf-8', errors='replace')

        # Apply tail truncation
        truncation = truncate_tail(full_output)
        output_text = truncation.content or "(no output)"

        # Build result with truncation notice
        full_output_path = None
        if truncation.truncated:
            full_output_path = temp_file_path
            start_line = truncation.total_lines - truncation.output_lines + 1
            end_line = truncation.total_lines

            if truncation.last_line_partial:
                last_line_size = format_size(len(full_output.split('\n')[-1].encode('utf-8')))
                output_text += f"\n\n[Showing last {format_size(truncation.output_bytes)} of line {end_line} (line is {last_line_size}). Full output: {temp_file_path}]"
            elif truncation.truncated_by == "lines":
                output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines}. Full output: {temp_file_path}]"
            else:
                output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). Full output: {temp_file_path}]"

        # Add exit code notice if non-zero
        if exit_code != 0 and exit_code is not None:
            output_text += f"\n\nCommand exited with code {exit_code}"

        return BashResult(
            success=exit_code == 0,
            output=output_text,
            exit_code=exit_code or 0,
            error="" if exit_code == 0 else output_text,
            truncated=truncation.truncated,
            total_lines=truncation.total_lines,
            output_lines=truncation.output_lines,
            full_output_path=full_output_path,
        )

    except subprocess.TimeoutExpired:
        _kill_process_tree(process.pid)
        return BashResult(
            success=False,
            output="",
            exit_code=-1,
            error=f"Command timed out after {timeout} seconds",
        )
    except Exception as e:
        # Cleanup temp file on error
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

        return BashResult(
            success=False,
            output="",
            exit_code=-1,
            error=str(e),
        )


async def execute_bash_async(
    command: str,
    base_path: Optional[Path] = None,
    timeout: int = 60,
    signal: Optional[AbortSignal] = None,
    on_update: Optional[Callable[[str], None]] = None,
    env: Optional[Dict[str, str]] = None,
) -> BashResult:
    """
    Execute a shell command (async version).

    Args:
        command: Command to execute
        base_path: Working directory
        timeout: Timeout in seconds
        signal: Abort signal
        on_update: Output update callback
        env: Environment variables

    Returns:
        BashResult with output and status
    """
    base_path = base_path or Path.cwd()
    temp_file_path = None
    temp_file = None

    try:
        # Check working directory
        if not base_path.exists():
            return BashResult(
                success=False,
                output="",
                exit_code=-1,
                error=f"Working directory does not exist: {base_path}",
            )

        # Build environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Create subprocess
        if sys.platform == 'win32':
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(base_path),
                env=process_env,
            )
        else:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(base_path),
                env=process_env,
            )

        # Rolling buffer
        chunks = []
        chunks_bytes = 0
        max_chunks_bytes = DEFAULT_MAX_BYTES * 2
        total_bytes = 0

        async def read_stream(stream, is_stderr=False):
            nonlocal temp_file, temp_file_path, chunks, chunks_bytes, total_bytes

            while True:
                # Check abort signal
                if signal and signal.aborted:
                    _kill_process_tree(process.pid)
                    break

                try:
                    line = await asyncio.wait_for(stream.read(8192), timeout=0.1)
                    if not line:
                        break

                    total_bytes += len(line)

                    # Start writing to temp file once we exceed threshold
                    if total_bytes > DEFAULT_MAX_BYTES and not temp_file:
                        temp_file = tempfile.NamedTemporaryFile(
                            mode='w+b',
                            delete=False,
                            suffix='.log',
                            prefix='koda-bash-'
                        )
                        temp_file_path = temp_file.name
                        for chunk in chunks:
                            temp_file.write(chunk)

                    # Write to temp file if we have one
                    if temp_file:
                        temp_file.write(line)

                    # Keep rolling buffer
                    chunks.append(line)
                    chunks_bytes += len(line)

                    # Trim old chunks
                    while chunks_bytes > max_chunks_bytes and len(chunks) > 1:
                        removed = chunks.pop(0)
                        chunks_bytes -= len(removed)

                    # Stream to callback
                    if on_update:
                        text = line.decode('utf-8', errors='replace')
                        on_update(text)

                except asyncio.TimeoutError:
                    continue

        # Read stdout and stderr concurrently
        await asyncio.gather(
            read_stream(process.stdout, False),
            read_stream(process.stderr, True),
        )

        # Wait for process with timeout
        timed_out = False
        try:
            exit_code = await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            _kill_process_tree(process.pid)
            await process.wait()
            exit_code = -1

        # Close temp file
        if temp_file:
            temp_file.close()

        # Check abort signal
        if signal and signal.aborted:
            full_output = b''.join(chunks).decode('utf-8', errors='replace')
            return BashResult(
                success=False,
                output=full_output,
                exit_code=-1,
                error="Command aborted",
            )

        # Check timeout
        if timed_out:
            full_output = b''.join(chunks).decode('utf-8', errors='replace')
            return BashResult(
                success=False,
                output=full_output,
                exit_code=-1,
                error=f"Command timed out after {timeout} seconds",
            )

        # Combine output
        full_buffer = b''.join(chunks)
        full_output = full_buffer.decode('utf-8', errors='replace')

        # Apply tail truncation
        truncation = truncate_tail(full_output)
        output_text = truncation.content or "(no output)"

        # Build result with truncation notice
        full_output_path = None
        if truncation.truncated:
            full_output_path = temp_file_path
            start_line = truncation.total_lines - truncation.output_lines + 1
            end_line = truncation.total_lines

            if truncation.last_line_partial:
                last_line_size = format_size(len(full_output.split('\n')[-1].encode('utf-8')))
                output_text += f"\n\n[Showing last {format_size(truncation.output_bytes)} of line {end_line} (line is {last_line_size}). Full output: {temp_file_path}]"
            elif truncation.truncated_by == "lines":
                output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines}. Full output: {temp_file_path}]"
            else:
                output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). Full output: {temp_file_path}]"

        # Add exit code notice if non-zero
        if exit_code != 0 and exit_code is not None:
            output_text += f"\n\nCommand exited with code {exit_code}"

        return BashResult(
            success=exit_code == 0,
            output=output_text,
            exit_code=exit_code or 0,
            error="" if exit_code == 0 else output_text,
            truncated=truncation.truncated,
            total_lines=truncation.total_lines,
            output_lines=truncation.output_lines,
            full_output_path=full_output_path,
        )

    except Exception as e:
        # Cleanup temp file on error
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

        return BashResult(
            success=False,
            output="",
            exit_code=-1,
            error=str(e),
        )


class BashTool:
    """
    Bash Tool class for Mom agent.

    Provides shell command execution with:
    - Timeout handling
    - Output truncation
    - Abort signal support
    """

    def __init__(
        self,
        base_path: Optional[Path] = None,
        default_timeout: int = 60,
    ):
        self.base_path = base_path or Path.cwd()
        self.default_timeout = default_timeout

    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        signal: Optional[AbortSignal] = None,
    ) -> BashResult:
        """Execute a command (synchronous)."""
        return execute_bash(
            command,
            self.base_path,
            timeout or self.default_timeout,
            signal,
        )

    async def execute_async(
        self,
        command: str,
        timeout: Optional[int] = None,
        signal: Optional[AbortSignal] = None,
    ) -> BashResult:
        """Execute a command (async)."""
        return await execute_bash_async(
            command,
            self.base_path,
            timeout or self.default_timeout,
            signal,
        )

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for LLM."""
        return {
            "name": "bash",
            "description": "Execute a shell command. Output is automatically truncated if too large.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 60,
                        "description": "Timeout in seconds",
                    },
                },
                "required": ["command"],
            },
        }
