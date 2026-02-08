"""
Shell Tool - Shell 命令执行工具

Pi-compatible 命令执行：
- 异步执行命令
- 支持超时
- 支持取消信号
- 自动截断大输出
"""
from dataclasses import dataclass
from typing import Optional, Callable
from pathlib import Path
import asyncio
import subprocess
import signal

from koda.core.truncation import truncate_for_bash


@dataclass
class ShellResult:
    """Shell 执行结果"""
    success: bool
    output: str
    error: str
    exit_code: int
    truncated: bool = False
    total_lines: int = 0
    output_lines: int = 0


class AbortSignal:
    """
    取消信号
    
    兼容 Pi 的 AbortController 模式
    """
    
    def __init__(self):
        self._cancelled = False
        self._callbacks = []
    
    @property
    def aborted(self) -> bool:
        return self._cancelled
    
    def abort(self):
        """触发取消"""
        self._cancelled = True
        for callback in self._callbacks:
            callback()
    
    def on_abort(self, callback):
        """注册取消回调"""
        self._callbacks.append(callback)


class ShellTool:
    """
    Pi-compatible Shell 工具
    
    支持：
    - 异步命令执行
    - 超时处理
    - 取消信号
    - 输出截断（50KB/2000行）
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
        执行 Shell 命令
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒），默认 60
            signal: 取消信号
            on_update: 输出更新回调
            
        Returns:
            ShellResult
        """
        timeout = timeout or self.default_timeout
        
        try:
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_path),
            )
            
            # 收集输出
            stdout_parts = []
            stderr_parts = []
            
            # 读取输出
            async def read_stream(stream, parts, prefix=""):
                while True:
                    if signal and signal.aborted:
                        process.kill()
                        break
                    
                    try:
                        line = await asyncio.wait_for(
                            stream.readline(),
                            timeout=0.1
                        )
                        if not line:
                            break
                        
                        decoded = line.decode('utf-8', errors='replace')
                        parts.append(decoded)
                        
                        if on_update:
                            on_update(prefix + decoded)
                            
                    except asyncio.TimeoutError:
                        continue
            
            # 并发读取 stdout 和 stderr
            await asyncio.gather(
                read_stream(process.stdout, stdout_parts),
                read_stream(process.stderr, stderr_parts, "[stderr] "),
            )
            
            # 等待进程完成（带超时）
            try:
                exit_code = await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ShellResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds",
                    exit_code=-1,
                )
            
            # 处理输出
            stdout = ''.join(stdout_parts)
            stderr = ''.join(stderr_parts)
            
            # 合并输出（Pi 风格）
            full_output = stdout
            if stderr:
                full_output += "\n[stderr]\n" + stderr
            
            # 截断处理（保留末尾）
            truncated_result = truncate_for_bash(full_output)
            
            return ShellResult(
                success=exit_code == 0,
                output=truncated_result.content,
                error=stderr if exit_code != 0 else "",
                exit_code=exit_code,
                truncated=truncated_result.truncated,
                total_lines=truncated_result.total_lines,
                output_lines=truncated_result.output_lines,
            )
            
        except Exception as e:
            return ShellResult(
                success=False,
                output="",
                error=str(e),
                exit_code=-1,
            )
    
    async def run_simple(self, command: str) -> str:
        """
        简单执行，只返回输出
        
        Args:
            command: 命令
            
        Returns:
            命令输出
        """
        result = await self.execute(command)
        return result.output if result.success else f"Error: {result.error}"
