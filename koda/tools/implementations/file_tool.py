"""
FileTool - 文件操作工具

安全的文件读写、目录操作等。
"""
import os
import shutil
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
from pathlib import Path


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    size: int
    is_dir: bool
    modified: float


class FileTool:
    """
    文件操作工具
    
    Example:
        tool = FileTool("/workspace")
        content = await tool.read("main.py")
        await tool.write("test.py", "print('hello')")
    """
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).resolve()
        self.allowed_extensions = [
            '.py', '.js', '.ts', '.json', '.yaml', '.yml',
            '.md', '.txt', '.html', '.css', '.xml', '.toml',
            '.ini', '.cfg', '.sh', '.bat',
        ]
    
    def _resolve_path(self, path: str) -> Path:
        """解析并验证路径"""
        target = (self.base_path / path).resolve()
        
        # 安全检查：确保在 base_path 内
        if not str(target).startswith(str(self.base_path)):
            raise ValueError(f"Path outside workspace: {path}")
        
        return target
    
    async def read(self, path: str, encoding: str = 'utf-8') -> str:
        """
        读取文件
        
        Args:
            path: 文件路径
            encoding: 编码
            
        Returns:
            文件内容
        """
        target = self._resolve_path(path)
        
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not target.is_file():
            raise IsADirectoryError(f"Is a directory: {path}")
        
        with open(target, 'r', encoding=encoding, errors='ignore') as f:
            return f.read()
    
    async def write(
        self,
        path: str,
        content: str,
        encoding: str = 'utf-8',
    ) -> None:
        """
        写入文件
        
        Args:
            path: 文件路径
            content: 内容
            encoding: 编码
        """
        target = self._resolve_path(path)
        
        # 确保目录存在
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, 'w', encoding=encoding) as f:
            f.write(content)
    
    async def append(
        self,
        path: str,
        content: str,
        encoding: str = 'utf-8',
    ) -> None:
        """追加内容到文件"""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, 'a', encoding=encoding) as f:
            f.write(content)
    
    async def delete(self, path: str) -> None:
        """
        删除文件或目录
        
        Args:
            path: 路径
        """
        target = self._resolve_path(path)
        
        if not target.exists():
            return
        
        if target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    
    async def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        target = self._resolve_path(path)
        return target.exists()
    
    async def list(
        self,
        path: str = ".",
        pattern: str = "*",
    ) -> List[FileInfo]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            pattern: 匹配模式
            
        Returns:
            文件信息列表
        """
        target = self._resolve_path(path)
        
        if not target.exists():
            return []
        
        results = []
        for item in target.glob(pattern):
            stat = item.stat()
            results.append(FileInfo(
                path=str(item.relative_to(self.base_path)),
                name=item.name,
                size=stat.st_size,
                is_dir=item.is_dir(),
                modified=stat.st_mtime,
            ))
        
        return results
    
    async def mkdir(self, path: str, parents: bool = True) -> None:
        """创建目录"""
        target = self._resolve_path(path)
        target.mkdir(parents=parents, exist_ok=True)
    
    async def copy(self, src: str, dst: str) -> None:
        """复制文件"""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        
        if src_path.is_file():
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
        else:
            shutil.copytree(src_path, dst_path)
    
    async def move(self, src: str, dst: str) -> None:
        """移动文件"""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        shutil.move(str(src_path), str(dst_path))
    
    async def get_info(self, path: str) -> FileInfo:
        """获取文件信息"""
        target = self._resolve_path(path)
        stat = target.stat()
        
        return FileInfo(
            path=str(target.relative_to(self.base_path)),
            name=target.name,
            size=stat.st_size,
            is_dir=target.is_dir(),
            modified=stat.st_mtime,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "file",
            "base_path": str(self.base_path),
        }
