"""
Git Utilities
Equivalent to Pi Mono's packages/coding-agent/src/utils/git.ts

Git operation helpers.
"""
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .shell import ShellUtils, ShellResult


@dataclass
class GitInfo:
    """Git repository information"""
    is_git_repo: bool
    root: Optional[str] = None
    branch: Optional[str] = None
    remote_url: Optional[str] = None
    last_commit: Optional[str] = None
    last_commit_msg: Optional[str] = None


class GitUtils:
    """
    Git operation utilities.
    
    Example:
        >>> git = GitUtils()
        >>> info = git.get_info()
        >>> if info.is_git_repo:
        ...     print(f"On branch: {info.branch}")
    """
    
    def __init__(self, cwd: Optional[str] = None):
        self.shell = ShellUtils(cwd=cwd)
        self.cwd = cwd or os.getcwd()
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        result = self.shell.run("git rev-parse --git-dir", timeout=5)
        return result.returncode == 0
    
    def get_info(self) -> GitInfo:
        """Get git repository information"""
        if not self.is_git_repo():
            return GitInfo(is_git_repo=False)
        
        # Get root
        root_result = self.shell.run("git rev-parse --show-toplevel")
        root = root_result.stdout.strip() if root_result.returncode == 0 else None
        
        # Get branch
        branch_result = self.shell.run("git branch --show-current")
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
        
        # Get remote URL
        remote_result = self.shell.run("git remote get-url origin")
        remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else None
        
        # Get last commit
        commit_result = self.shell.run("git rev-parse --short HEAD")
        last_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None
        
        # Get last commit message
        msg_result = self.shell.run("git log -1 --pretty=%B")
        last_commit_msg = msg_result.stdout.strip() if msg_result.returncode == 0 else None
        
        return GitInfo(
            is_git_repo=True,
            root=root,
            branch=branch,
            remote_url=remote_url,
            last_commit=last_commit,
            last_commit_msg=last_commit_msg
        )
    
    def get_status(self) -> Dict[str, List[str]]:
        """
        Get git status.
        
        Returns:
            Dict with 'staged', 'modified', 'untracked' file lists
        """
        result = self.shell.run("git status --porcelain")
        
        if result.returncode != 0:
            return {"staged": [], "modified": [], "untracked": []}
        
        staged = []
        modified = []
        untracked = []
        
        for line in result.stdout.split('\n'):
            if not line:
                continue
            
            status = line[:2]
            file = line[3:].strip()
            
            if status[0] in 'AMDR':
                staged.append(file)
            if status[1] in 'MD':
                modified.append(file)
            if status == '??':
                untracked.append(file)
        
        return {
            "staged": staged,
            "modified": modified,
            "untracked": untracked
        }
    
    def get_diff(self, staged: bool = False) -> str:
        """
        Get git diff.
        
        Args:
            staged: Show staged changes
            
        Returns:
            Diff output
        """
        cmd = "git diff --cached" if staged else "git diff"
        result = self.shell.run(cmd)
        return result.stdout if result.returncode == 0 else ""
    
    def get_log(
        self,
        n: int = 10,
        format: str = "%h - %s (%an, %ar)"
    ) -> List[Dict[str, str]]:
        """
        Get git log.
        
        Args:
            n: Number of commits
            format: Log format string
            
        Returns:
            List of commit info dicts
        """
        cmd = f'git log -n {n} --pretty=format:"{format}%n---COMMIT---"'
        result = self.shell.run(cmd)
        
        if result.returncode != 0:
            return []
        
        commits = []
        for entry in result.stdout.split('---COMMIT---'):
            entry = entry.strip()
            if entry:
                commits.append({"message": entry})
        
        return commits
    
    def get_tracked_files(self) -> List[str]:
        """Get list of tracked files"""
        result = self.shell.run("git ls-files")
        if result.returncode == 0:
            return [f for f in result.stdout.split('\n') if f]
        return []
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        result = self.shell.run("git status --porcelain")
        return result.returncode == 0 and bool(result.stdout.strip())
    
    def get_current_commit_hash(self, short: bool = True) -> Optional[str]:
        """Get current commit hash"""
        cmd = "git rev-parse --short HEAD" if short else "git rev-parse HEAD"
        result = self.shell.run(cmd)
        return result.stdout.strip() if result.returncode == 0 else None


# Convenience functions
def is_git_repo(cwd: Optional[str] = None) -> bool:
    """Check if directory is a git repo"""
    git = GitUtils(cwd=cwd)
    return git.is_git_repo()


def get_git_info(cwd: Optional[str] = None) -> GitInfo:
    """Get git repository info"""
    git = GitUtils(cwd=cwd)
    return git.get_info()


def get_git_diff(staged: bool = False, cwd: Optional[str] = None) -> str:
    """Get git diff"""
    git = GitUtils(cwd=cwd)
    return git.get_diff(staged=staged)


__all__ = [
    "GitUtils",
    "GitInfo",
    "is_git_repo",
    "get_git_info",
    "get_git_diff",
]
