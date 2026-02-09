"""
Shell Tool - Shell command execution tool

Pi-compatible command execution:
- Async execution
- Timeout support
- AbortSignal support
- Automatic truncation
- Temp file for large output
- Process tree termination
"""
from dataclasses import dataclass
from typing import Optional, Callable
from pathlib import Path
import asyncio
import subprocess
import tempfile
import os
import sys

from koda.coding._support.truncation import truncate_tail, format_size, DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES


@dataclass
class ShellResult:
    """Shell execution result"""
    success: bool
    output: str
    error: str
    exit_code: int
    truncated: bool = False
    total_lines: int = 0
    output_lines: int = 0
    full_output_path: Optional[str] = None


class AbortSignal:
    """Abort signal - Pi compatible"""
    
    def __init__(self):
        self._cancelled = False
        self._callbacks = []
    
    @property
    def aborted(self) -> bool:
        return self._cancelled
    
    def abort(self):
        """Trigger abort"""
        self._cancelled = True
        for callback in self._callbacks:
            callback()
    
    def on_abort(self, callback):
        """Register abort callback"""
        self._callbacks.append(callback)


def _kill_process_tree(pid: int):
    """
    Kill process tree
    
    Cross-platform implementation.
    """
    if sys.platform == 'win32':
        # Windows: use taskkill /T to kill process tree
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                         capture_output=True, check=False)
        except Exception:
            pass
    else:
        # Unix: use psutil if available, otherwise just kill the process
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                child.terminate()
            parent.terminate()
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            for p in alive:
                p.kill()
        except ImportError:
            # Fallback: just kill the main process
            try:
                os.kill(pid, 9)
            except Exception:
                pass
        except Exception:
            pass


class ShellTool:
    """
    Pi-compatible Shell tool
    
    Features:
    - Async command execution
    - Timeout handling
    - AbortSignal support
    - Output truncation (50KB/2000 lines)
    - Temp file for large output
    - Process tree kill
    """
    
    def __init__(self, base_path: Path = None, default_timeout: int = 60):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.default_timeout = default_timeout
    
    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        signal: Optional[AbortSignal] = None,
        on_update: Optional[Callable[[str], None]] = None,
    ) -> ShellResult:
        """
        Execute shell command (Pi-compatible)
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            signal: Abort signal
            on_update: Output update callback
            
        Returns:
            ShellResult
        """
        timeout = timeout or self.default_timeout
        temp_file_path = None
        temp_file = None
        
        try:
            # Check working directory exists
            if not self.base_path.exists():
                return ShellResult(
                    success=False,
                    output="",
                    error=f"Working directory does not exist: {self.base_path}",
                    exit_code=-1,
                )
            
            # Create subprocess
            if sys.platform == 'win32':
                # Windows: use cmd.exe
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.base_path),
                )
            else:
                # Unix: use bash
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.base_path),
                )
            
            # Rolling buffer for recent output
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
                        line = await asyncio.wait_for(
                            stream.read(8192),  # Read in chunks
                            timeout=0.1
                        )
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
                return ShellResult(
                    success=False,
                    output=full_output,
                    error="Command aborted",
                    exit_code=-1,
                )
            
            # Check timeout
            if timed_out:
                full_output = b''.join(chunks).decode('utf-8', errors='replace')
                return ShellResult(
                    success=False,
                    output=full_output,
                    error=f"Command timed out after {timeout} seconds",
                    exit_code=-1,
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
            
            return ShellResult(
                success=exit_code == 0,
                output=output_text,
                error="" if exit_code == 0 else output_text,
                exit_code=exit_code or 0,
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
            
            return ShellResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
            )
    
    async def run_simple(self, command: str) -> str:
        """Simple execution, returns output only"""
        result = await self.execute(command)
        return result.output if result.success else f"Error: {result.error}"
