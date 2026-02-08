"""
GitTool - Git 版本控制工具

执行 Git 操作。
"""
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class GitResult:
    """Git 操作结果"""
    success: bool
    output: str
    error: str
    command: str


class GitTool:
    """
    Git 版本控制工具
    
    Example:
        git = GitTool("/path/to/repo")
        result = await git.status()
        result = await git.commit("Update code")
    """
    
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
    
    async def _run(self, command: str) -> GitResult:
        """执行 git 命令"""
        full_command = f"git {command}"
        
        try:
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.repo_path,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30,
            )
            
            return GitResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8', errors='replace'),
                error=stderr.decode('utf-8', errors='replace'),
                command=full_command,
            )
        except Exception as e:
            return GitResult(
                success=False,
                output="",
                error=str(e),
                command=full_command,
            )
    
    async def status(self) -> GitResult:
        """查看状态"""
        return await self._run("status")
    
    async def add(self, files: str = ".") -> GitResult:
        """添加文件"""
        return await self._run(f"add {files}")
    
    async def commit(self, message: str) -> GitResult:
        """提交更改"""
        return await self._run(f'commit -m "{message}"')
    
    async def push(self, remote: str = "origin", branch: str = "") -> GitResult:
        """推送代码"""
        cmd = f"push {remote}"
        if branch:
            cmd += f" {branch}"
        return await self._run(cmd)
    
    async def pull(self, remote: str = "origin", branch: str = "") -> GitResult:
        """拉取代码"""
        cmd = f"pull {remote}"
        if branch:
            cmd += f" {branch}"
        return await self._run(cmd)
    
    async def branch(self, branch_name: Optional[str] = None) -> GitResult:
        """分支操作"""
        if branch_name:
            return await self._run(f"checkout -b {branch_name}")
        return await self._run("branch -a")
    
    async def checkout(self, branch_or_commit: str) -> GitResult:
        """切换分支"""
        return await self._run(f"checkout {branch_or_commit}")
    
    async def log(self, n: int = 10) -> GitResult:
        """查看提交历史"""
        return await self._run(f'log --oneline -{n}')
    
    async def diff(self, staged: bool = False) -> GitResult:
        """查看差异"""
        cmd = "diff"
        if staged:
            cmd += " --staged"
        return await self._run(cmd)
    
    async def clone(self, url: str, dest: Optional[str] = None) -> GitResult:
        """克隆仓库"""
        cmd = f"clone {url}"
        if dest:
            cmd += f" {dest}"
        return await self._run(cmd)
    
    async def init(self) -> GitResult:
        """初始化仓库"""
        return await self._run("init")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "git",
            "repo_path": str(self.repo_path),
        }
