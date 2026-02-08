"""
ShellTool - 终端命令执行工具

安全地执行 shell 命令。
"""
import asyncio
import shlex
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class ShellResult:
    """命令执行结果"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: int


class ShellTool:
    """
    终端命令执行工具
    
    Example:
        tool = ShellTool()
        result = await tool.execute("ls -la")
        print(result.stdout)
    """
    
    # 危险命令黑名单
    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "> /dev/sda",
        "dd if=/dev/zero",
        "mkfs",
        ":(){:|:&};:",  # fork bomb
    ]
    
    def __init__(
        self,
        working_dir: Optional[Path] = None,
        timeout: int = 60,
        allowed_commands: Optional[List[str]] = None,
        blocked_commands: Optional[List[str]] = None,
    ):
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout
        self.allowed_commands = allowed_commands
        self.blocked_commands = blocked_commands or []
    
    async def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ShellResult:
        """
        执行 shell 命令
        
        Args:
            command: 要执行的命令
            cwd: 工作目录
            env: 环境变量
            
        Returns:
            ShellResult: 执行结果
        """
        # 安全检查
        if not self._is_safe_command(command):
            return ShellResult(
                success=False,
                stdout="",
                stderr=f"Command blocked for security: {command}",
                exit_code=-1,
                command=command,
                duration_ms=0,
            )
        
        working_dir = cwd or self.working_dir
        
        try:
            import time
            start = time.time()
            
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env,
            )
            
            # 等待执行完成
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            duration = int((time.time() - start) * 1000)
            
            return ShellResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                exit_code=process.returncode,
                command=command,
                duration_ms=duration,
            )
            
        except asyncio.TimeoutError:
            process.kill()
            return ShellResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                exit_code=-1,
                command=command,
                duration_ms=self.timeout * 1000,
            )
        except Exception as e:
            return ShellResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                command=command,
                duration_ms=0,
            )
    
    async def execute_many(
        self,
        commands: List[str],
        stop_on_error: bool = True,
    ) -> List[ShellResult]:
        """
        执行多个命令
        
        Args:
            commands: 命令列表
            stop_on_error: 出错时停止
            
        Returns:
            结果列表
        """
        results = []
        for cmd in commands:
            result = await self.execute(cmd)
            results.append(result)
            
            if stop_on_error and not result.success:
                break
        
        return results
    
    def _is_safe_command(self, command: str) -> bool:
        """检查命令是否安全"""
        cmd_lower = command.lower()
        
        # 检查黑名单
        for blocked in self.DANGEROUS_COMMANDS:
            if blocked in cmd_lower:
                return False
        
        # 检查自定义黑名单
        for blocked in self.blocked_commands:
            if blocked.lower() in cmd_lower:
                return False
        
        # 检查白名单（如果配置了）
        if self.allowed_commands:
            cmd_name = shlex.split(command)[0]
            if cmd_name not in self.allowed_commands:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "type": "shell",
            "working_dir": str(self.working_dir),
            "timeout": self.timeout,
        }
