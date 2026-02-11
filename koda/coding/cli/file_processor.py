"""
File Processor
等效于 Pi-Mono 的 packages/coding-agent/src/cli/file-processor.ts

文件处理和验证。
"""

import os
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    size: int
    mime_type: str
    is_binary: bool = False
    is_text: bool = True
    encoding: Optional[str] = None
    content_preview: Optional[str] = None


@dataclass
class ProcessedFiles:
    """处理结果"""
    files: List[FileInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_size: int = 0
    skipped: List[str] = field(default_factory=list)


class FileProcessor:
    """
    文件处理器
    
    处理用户输入的文件路径，验证和准备文件。
    
    Example:
        >>> processor = FileProcessor(max_size=10*1024*1024)
        >>> result = await processor.process(["file1.py", "file2.txt"])
    """
    
    # 二进制文件类型
    BINARY_EXTENSIONS: Set[str] = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
        '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.exe', '.dll', '.so', '.dylib',
    }
    
    # 文本编码尝试顺序
    TEXT_ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'gbk']
    
    def __init__(
        self,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        max_total_size: int = 50 * 1024 * 1024,  # 50MB
        allowed_extensions: Optional[Set[str]] = None,
        blocked_extensions: Optional[Set[str]] = None,
    ):
        self.max_size = max_size
        self.max_total_size = max_total_size
        self.allowed_extensions = allowed_extensions
        self.blocked_extensions = blocked_extensions or set()
    
    async def process(
        self,
        paths: List[str],
        base_dir: Optional[str] = None,
    ) -> ProcessedFiles:
        """
        处理文件路径列表
        
        Args:
            paths: 文件路径列表
            base_dir: 基础目录（用于相对路径）
        
        Returns:
            处理结果
        """
        result = ProcessedFiles()
        
        for path in paths:
            try:
                file_info = await self._process_path(path, base_dir)
                
                if file_info:
                    # Check total size
                    if result.total_size + file_info.size > self.max_total_size:
                        result.errors.append(f"Total size limit exceeded: {path}")
                        continue
                    
                    result.files.append(file_info)
                    result.total_size += file_info.size
                    
            except Exception as e:
                result.errors.append(f"Error processing {path}: {e}")
        
        return result
    
    async def _process_path(
        self,
        path: str,
        base_dir: Optional[str] = None,
    ) -> Optional[FileInfo]:
        """处理单个路径"""
        # Resolve path
        if base_dir and not os.path.isabs(path):
            full_path = os.path.join(base_dir, path)
        else:
            full_path = path
        
        path_obj = Path(full_path)
        
        # Check exists
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Check if directory
        if path_obj.is_dir():
            raise IsADirectoryError(f"Path is a directory: {path}")
        
        # Check extension
        ext = path_obj.suffix.lower()
        
        if self.blocked_extensions and ext in self.blocked_extensions:
            raise ValueError(f"File type not allowed: {ext}")
        
        if self.allowed_extensions and ext not in self.allowed_extensions:
            raise ValueError(f"File type not in allowed list: {ext}")
        
        # Check size
        size = path_obj.stat().st_size
        if size > self.max_size:
            raise ValueError(f"File too large: {size} bytes (max {self.max_size})")
        
        # Determine file type
        is_binary = ext in self.BINARY_EXTENSIONS
        mime_type, _ = mimetypes.guess_type(str(path_obj))
        mime_type = mime_type or "application/octet-stream"
        
        # Try to read text content
        encoding = None
        content_preview = None
        is_text = not is_binary
        
        if is_text and mime_type.startswith('text/'):
            encoding, content_preview = self._try_read_text(path_obj)
            is_text = encoding is not None
        
        return FileInfo(
            path=str(path_obj.absolute()),
            size=size,
            mime_type=mime_type,
            is_binary=is_binary or not is_text,
            is_text=is_text,
            encoding=encoding,
            content_preview=content_preview,
        )
    
    def _try_read_text(
        self,
        path: Path,
        preview_lines: int = 10,
    ) -> tuple[Optional[str], Optional[str]]:
        """尝试读取文本内容"""
        for encoding in self.TEXT_ENCODINGS:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()
                    lines = content.split('\n')[:preview_lines]
                    preview = '\n'.join(lines)
                    if len(lines) == preview_lines:
                        preview += '\n...'
                    return encoding, preview
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        
        return None, None
    
    def validate_paths(self, paths: List[str]) -> List[str]:
        """
        验证路径列表
        
        Returns:
            错误信息列表
        """
        errors = []
        
        for path in paths:
            if not os.path.exists(path):
                errors.append(f"Not found: {path}")
            elif os.path.isdir(path):
                errors.append(f"Is directory: {path}")
            else:
                size = os.path.getsize(path)
                if size > self.max_size:
                    errors.append(f"Too large ({size} bytes): {path}")
        
        return errors
    
    def get_stats(self, result: ProcessedFiles) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_files": len(result.files),
            "total_size": result.total_size,
            "total_size_mb": result.total_size / (1024 * 1024),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "text_files": sum(1 for f in result.files if f.is_text),
            "binary_files": sum(1 for f in result.files if f.is_binary),
        }


class FileBatchProcessor:
    """
    批量文件处理器
    
    处理大量文件，支持分批和进度报告。
    """
    
    def __init__(
        self,
        processor: FileProcessor,
        batch_size: int = 10,
    ):
        self.processor = processor
        self.batch_size = batch_size
    
    async def process_batch(
        self,
        paths: List[str],
        progress_callback: Optional[callable] = None,
    ) -> ProcessedFiles:
        """
        分批处理文件
        
        Args:
            paths: 文件路径列表
            progress_callback: 进度回调(current, total)
        
        Returns:
            处理结果
        """
        result = ProcessedFiles()
        total = len(paths)
        
        for i in range(0, total, self.batch_size):
            batch = paths[i:i + self.batch_size]
            batch_result = await self.processor.process(batch)
            
            result.files.extend(batch_result.files)
            result.errors.extend(batch_result.errors)
            result.skipped.extend(batch_result.skipped)
            result.total_size += batch_result.total_size
            
            if progress_callback:
                progress_callback(min(i + self.batch_size, total), total)
        
        return result


__all__ = [
    "FileInfo",
    "ProcessedFiles",
    "FileProcessor",
    "FileBatchProcessor",
]
