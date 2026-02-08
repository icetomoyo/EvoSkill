"""
File Tool - 文件操作工具

Pi-compatible 文件操作：
- read: 读取文件内容，支持 offset/limit
- write: 写入文件，自动创建目录
- edit: 精确文本替换编辑
"""
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import asyncio

from koda.core.truncation import truncate_for_read


@dataclass
class ReadResult:
    """读取结果"""
    content: str
    path: str
    start_line: int
    end_line: int
    truncated: bool
    next_offset: int
    error: Optional[str] = None


@dataclass
class EditResult:
    """编辑结果"""
    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class WriteResult:
    """写入结果"""
    success: bool
    path: str
    error: Optional[str] = None


class FileTool:
    """
    Pi-compatible 文件工具
    
    支持：
    - 读取（带 offset/limit）
    - 写入（自动创建目录）
    - 编辑（精确文本替换）
    """
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        target = Path(path)
        if not target.is_absolute():
            target = self.base_path / target
        return target.resolve()
    
    async def read(
        self,
        path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> ReadResult:
        """
        读取文件内容
        
        Args:
            path: 文件路径
            offset: 起始行号（1-indexed）
            limit: 最大读取行数
            
        Returns:
            ReadResult
        """
        try:
            target = self._resolve_path(path)
            
            if not target.exists():
                return ReadResult(
                    content="",
                    path=str(target),
                    start_line=0,
                    end_line=0,
                    truncated=False,
                    next_offset=0,
                    error=f"File not found: {path}"
                )
            
            if not target.is_file():
                return ReadResult(
                    content="",
                    path=str(target),
                    start_line=0,
                    end_line=0,
                    truncated=False,
                    next_offset=0,
                    error=f"Not a file: {path}"
                )
            
            # 读取内容
            content = target.read_text(encoding='utf-8', errors='replace')
            
            # 处理 offset 和 limit
            lines = content.split('\n')
            total_lines = len(lines)
            
            # 计算起始和结束
            start_idx = max(0, (offset or 1) - 1)  # offset 是 1-indexed
            end_idx = total_lines
            
            if limit is not None:
                end_idx = min(start_idx + limit, total_lines)
            
            # 提取内容
            selected_lines = lines[start_idx:end_idx]
            selected_content = '\n'.join(selected_lines)
            
            # 应用截断
            truncated_result = truncate_for_read(selected_content, offset=1, limit=None)
            
            # 计算实际行号
            actual_start = start_idx + 1  # 1-indexed
            actual_end = start_idx + truncated_result.output_lines
            
            return ReadResult(
                content=truncated_result.content,
                path=str(target),
                start_line=actual_start,
                end_line=actual_end,
                truncated=truncated_result.truncated,
                next_offset=actual_end + 1 if truncated_result.truncated else 0,
            )
            
        except Exception as e:
            return ReadResult(
                content="",
                path=path,
                start_line=0,
                end_line=0,
                truncated=False,
                next_offset=0,
                error=str(e)
            )
    
    async def write(self, path: str, content: str) -> WriteResult:
        """
        写入文件
        
        Args:
            path: 文件路径
            content: 文件内容
            
        Returns:
            WriteResult
        """
        try:
            target = self._resolve_path(path)
            
            # 创建父目录
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            target.write_text(content, encoding='utf-8')
            
            return WriteResult(
                success=True,
                path=str(target),
            )
            
        except Exception as e:
            return WriteResult(
                success=False,
                path=path,
                error=str(e)
            )
    
    async def edit(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> EditResult:
        """
        编辑文件 - 精确文本替换
        
        old_text 必须精确匹配（包括空白字符和缩进）
        
        Args:
            path: 文件路径
            old_text: 要替换的文本（精确匹配）
            new_text: 新文本
            
        Returns:
            EditResult
        """
        try:
            target = self._resolve_path(path)
            
            if not target.exists():
                return EditResult(
                    success=False,
                    path=str(target),
                    error=f"File not found: {path}"
                )
            
            # 读取内容
            content = target.read_text(encoding='utf-8', errors='replace')
            
            # 精确匹配替换
            if old_text not in content:
                return EditResult(
                    success=False,
                    path=str(target),
                    error=f"old_text not found in file (must match exactly, including whitespace)"
                )
            
            # 替换（只替换第一次出现）
            new_content = content.replace(old_text, new_text, 1)
            
            # 写回文件
            target.write_text(new_content, encoding='utf-8')
            
            return EditResult(
                success=True,
                path=str(target),
            )
            
        except Exception as e:
            return EditResult(
                success=False,
                path=path,
                error=str(e)
            )
    
    async def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        try:
            target = self._resolve_path(path)
            return target.exists()
        except:
            return False
    
    async def is_directory(self, path: str) -> bool:
        """检查是否是目录"""
        try:
            target = self._resolve_path(path)
            return target.is_dir()
        except:
            return False
