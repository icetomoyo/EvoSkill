"""
Git 操作 Skill

提供常用的 Git 命令封装：status, diff, commit, log, branch
"""
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path


async def _run_git_command(args: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    运行 Git 命令
    
    Args:
        args: Git 命令参数
        cwd: 工作目录
        
    Returns:
        命令执行结果
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return {
                "success": True,
                "output": stdout.decode("utf-8", errors="replace").strip(),
            }
        else:
            return {
                "success": False,
                "error": stderr.decode("utf-8", errors="replace").strip(),
            }
            
    except FileNotFoundError:
        return {
            "success": False,
            "error": "Git 命令未找到，请确保 Git 已安装并添加到 PATH",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def git_status(
    path: Optional[str] = None,
    short: bool = True,
) -> Dict[str, Any]:
    """
    查看 Git 状态
    
    Args:
        path: 要查看的路径，默认为当前目录
        short: 是否使用简洁格式
        
    Returns:
        Git 状态信息
    """
    try:
        args = ["status"]
        if short:
            args.append("-s")
        else:
            args.append("--porcelain")
        
        result = await _run_git_command(args, cwd=path)
        
        if not result["success"]:
            return result
        
        output = result["output"]
        
        if not output:
            return {
                "success": True,
                "status": "clean",
                "message": "工作区干净，没有更改",
                "changes": [],
            }
        
        # 解析状态输出
        changes = []
        for line in output.split("\n"):
            if line.strip():
                changes.append(line.strip())
        
        return {
            "success": True,
            "status": "modified",
            "changes": changes,
            "raw_output": output,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def git_diff(
    path: Optional[str] = None,
    cached: bool = False,
) -> Dict[str, Any]:
    """
    查看修改差异
    
    Args:
        path: 要比较的文件路径，默认为所有文件
        cached: 是否查看已暂存的更改
        
    Returns:
        差异内容
    """
    try:
        args = ["diff"]
        if cached:
            args.append("--cached")
        if path:
            args.append(path)
        
        result = await _run_git_command(args)
        
        if not result["success"]:
            return result
        
        output = result["output"]
        
        if not output:
            return {
                "success": True,
                "has_changes": False,
                "message": "没有可显示的更改",
            }
        
        return {
            "success": True,
            "has_changes": True,
            "diff": output,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def git_commit(
    message: str,
    add_all: bool = False,
) -> Dict[str, Any]:
    """
    提交更改
    
    Args:
        message: 提交信息
        add_all: 是否自动暂存所有更改
        
    Returns:
        提交结果
    """
    try:
        if not message or not message.strip():
            return {
                "success": False,
                "error": "提交信息不能为空",
            }
        
        # 如果需要，先暂存所有更改
        if add_all:
            add_result = await _run_git_command(["add", "."])
            if not add_result["success"]:
                return add_result
        
        # 提交
        result = await _run_git_command(["commit", "-m", message])
        
        if not result["success"]:
            # 检查是否是 "nothing to commit"
            if "nothing to commit" in result.get("error", "").lower():
                return {
                    "success": True,
                    "message": "没有要提交的更改",
                    "nothing_to_commit": True,
                }
            return result
        
        # 解析提交结果
        output = result["output"]
        commit_hash = ""
        
        # 提取提交哈希
        if "[" in output and "]" in output:
            # 格式: [branch hash] message
            parts = output.split("]")[0].split(" ")
            if len(parts) >= 2:
                commit_hash = parts[-1]
        
        return {
            "success": True,
            "message": "提交成功",
            "commit_hash": commit_hash,
            "output": output,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def git_log(
    limit: int = 10,
    oneline: bool = True,
) -> Dict[str, Any]:
    """
    查看提交历史
    
    Args:
        limit: 显示的提交数量
        oneline: 是否使用单行格式
        
    Returns:
        提交历史列表
    """
    try:
        args = ["log"]
        
        if oneline:
            args.append("--oneline")
        
        args.extend(["-n", str(limit)])
        
        result = await _run_git_command(args)
        
        if not result["success"]:
            return result
        
        output = result["output"]
        
        if not output:
            return {
                "success": True,
                "commits": [],
                "message": "没有提交历史",
            }
        
        # 解析提交列表
        commits = []
        for line in output.split("\n"):
            if line.strip():
                if oneline:
                    # 格式: hash message
                    parts = line.split(" ", 1)
                    if len(parts) >= 2:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1],
                        })
                    else:
                        commits.append({
                            "hash": parts[0],
                            "message": "",
                        })
                else:
                    commits.append({"raw": line})
        
        return {
            "success": True,
            "commits": commits,
            "count": len(commits),
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


async def git_branch(
    list_branches: bool = True,
) -> Dict[str, Any]:
    """
    查看分支列表
    
    Args:
        list_branches: 是否列出所有分支
        
    Returns:
        分支信息
    """
    try:
        if not list_branches:
            return {
                "success": True,
                "message": "请设置 list_branches=True 查看分支",
            }
        
        # 获取当前分支
        current_result = await _run_git_command(["branch", "--show-current"])
        current_branch = ""
        if current_result["success"]:
            current_branch = current_result["output"].strip()
        
        # 获取所有分支
        result = await _run_git_command(["branch", "-a"])
        
        if not result["success"]:
            return result
        
        output = result["output"]
        
        branches = []
        for line in output.split("\n"):
            line = line.strip()
            if line:
                # 移除开头的 * 和空格
                is_current = line.startswith("*")
                branch_name = line.lstrip("* ").strip()
                
                branches.append({
                    "name": branch_name,
                    "current": is_current,
                })
        
        return {
            "success": True,
            "current_branch": current_branch,
            "branches": branches,
            "count": len(branches),
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# Skill metadata for registration
SKILL_NAME = "git"
SKILL_VERSION = "0.1.0"
SKILL_DESCRIPTION = "Git 操作 Skill，提供常用的 Git 命令封装"
SKILL_TOOLS = [
    {
        "name": "git_status",
        "description": "查看 Git 工作区状态",
        "handler": git_status,
    },
    {
        "name": "git_diff",
        "description": "查看文件修改差异",
        "handler": git_diff,
    },
    {
        "name": "git_commit",
        "description": "提交代码更改",
        "handler": git_commit,
    },
    {
        "name": "git_log",
        "description": "查看提交历史",
        "handler": git_log,
    },
    {
        "name": "git_branch",
        "description": "查看分支列表",
        "handler": git_branch,
    },
]


async def main():
    """Test the skill"""
    print(f"{SKILL_NAME} v{SKILL_VERSION} loaded")
    print(f"Available tools: {', '.join([t['name'] for t in SKILL_TOOLS])}")
    
    # Test git_status
    result = await git_status()
    print(f"\nGit status test:")
    print(f"  Success: {result.get('success')}")
    if result.get('success'):
        print(f"  Status: {result.get('status')}")


if __name__ == "__main__":
    asyncio.run(main())
