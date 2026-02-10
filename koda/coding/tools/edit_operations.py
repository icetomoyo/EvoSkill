"""
Edit Operations - Pluggable file operations for Edit tool

Equivalent to Pi Mono's EditOperations interface
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional, Callable
import os


@dataclass
class FileStat:
    """File statistics"""
    size: int
    mtime: float
    mode: int
    exists: bool


class EditOperations(ABC):
    """
    Abstract interface for file operations
    
    Allows pluggable implementations for:
    - Regular filesystem
    - Virtual filesystem (testing)
    - Remote filesystem
    - Git-based versioning
    """
    
    @abstractmethod
    def read_file(self, path: Union[str, Path]) -> str:
        """Read file content as string"""
        pass
    
    @abstractmethod
    def read_file_bytes(self, path: Union[str, Path]) -> bytes:
        """Read file content as bytes"""
        pass
    
    @abstractmethod
    def write_file(self, path: Union[str, Path], content: str) -> None:
        """Write string content to file"""
        pass
    
    @abstractmethod
    def write_file_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes content to file"""
        pass
    
    @abstractmethod
    def file_exists(self, path: Union[str, Path]) -> bool:
        """Check if file exists"""
        pass
    
    @abstractmethod
    def access(self, path: Union[str, Path]) -> bool:
        """Check if file is accessible (readable/writable)"""
        pass
    
    @abstractmethod
    def stat(self, path: Union[str, Path]) -> FileStat:
        """Get file statistics"""
        pass
    
    @abstractmethod
    def mkdir(self, path: Union[str, Path], parents: bool = True) -> None:
        """Create directory"""
        pass


class LocalFileOperations(EditOperations):
    """
    Local filesystem operations
    Default implementation for real file editing
    """
    
    def read_file(self, path: Union[str, Path]) -> str:
        """Read file as UTF-8 text"""
        return Path(path).read_text(encoding='utf-8')
    
    def read_file_bytes(self, path: Union[str, Path]) -> bytes:
        """Read file as bytes"""
        return Path(path).read_bytes()
    
    def write_file(self, path: Union[str, Path], content: str) -> None:
        """Write UTF-8 text to file"""
        Path(path).write_text(content, encoding='utf-8')
    
    def write_file_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes to file"""
        Path(path).write_bytes(content)
    
    def file_exists(self, path: Union[str, Path]) -> bool:
        """Check if file exists"""
        return Path(path).exists()
    
    def access(self, path: Union[str, Path]) -> bool:
        """Check file accessibility"""
        p = Path(path)
        return p.exists() and os.access(p, os.R_OK | os.W_OK)
    
    def stat(self, path: Union[str, Path]) -> FileStat:
        """Get file stats"""
        p = Path(path)
        if not p.exists():
            return FileStat(size=0, mtime=0, mode=0, exists=False)
        
        s = p.stat()
        return FileStat(
            size=s.st_size,
            mtime=s.st_mtime,
            mode=s.st_mode,
            exists=True
        )
    
    def mkdir(self, path: Union[str, Path], parents: bool = True) -> None:
        """Create directory"""
        Path(path).mkdir(parents=parents, exist_ok=True)


class VirtualFileOperations(EditOperations):
    """
    In-memory virtual filesystem for testing
    """
    
    def __init__(self, files: Optional[dict] = None):
        self._files: dict = files or {}
        self._stats: dict = {}
    
    def read_file(self, path: Union[str, Path]) -> str:
        """Read from virtual filesystem"""
        key = str(path)
        if key not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        content = self._files[key]
        return content if isinstance(content, str) else content.decode('utf-8')
    
    def read_file_bytes(self, path: Union[str, Path]) -> bytes:
        """Read bytes from virtual filesystem"""
        key = str(path)
        if key not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        content = self._files[key]
        return content.encode('utf-8') if isinstance(content, str) else content
    
    def write_file(self, path: Union[str, Path], content: str) -> None:
        """Write to virtual filesystem"""
        self._files[str(path)] = content
        self._stats[str(path)] = FileStat(
            size=len(content.encode('utf-8')),
            mtime=__import__('time').time(),
            mode=0o644,
            exists=True
        )
    
    def write_file_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write bytes to virtual filesystem"""
        self._files[str(path)] = content
        self._stats[str(path)] = FileStat(
            size=len(content),
            mtime=__import__('time').time(),
            mode=0o644,
            exists=True
        )
    
    def file_exists(self, path: Union[str, Path]) -> bool:
        """Check virtual file existence"""
        return str(path) in self._files
    
    def access(self, path: Union[str, Path]) -> bool:
        """Virtual files are always accessible"""
        return self.file_exists(path)
    
    def stat(self, path: Union[str, Path]) -> FileStat:
        """Get virtual file stats"""
        key = str(path)
        if key in self._stats:
            return self._stats[key]
        return FileStat(size=0, mtime=0, mode=0, exists=False)
    
    def mkdir(self, path: Union[str, Path], parents: bool = True) -> None:
        """No-op for virtual filesystem"""
        pass
    
    def add_file(self, path: Union[str, Path], content: Union[str, bytes]) -> None:
        """Helper to add files for testing"""
        if isinstance(content, str):
            self.write_file(path, content)
        else:
            self.write_file_bytes(path, content)
    
    def get_file(self, path: Union[str, Path]) -> Optional[str]:
        """Helper to get file content"""
        key = str(path)
        if key in self._files:
            content = self._files[key]
            return content if isinstance(content, str) else content.decode('utf-8')
        return None
    
    def list_files(self) -> list:
        """List all files in virtual filesystem"""
        return list(self._files.keys())


class EditOperationsFactory:
    """Factory for creating EditOperations instances"""
    
    _default: Optional[EditOperations] = None
    
    @classmethod
    def get_default(cls) -> EditOperations:
        """Get default (local filesystem) operations"""
        if cls._default is None:
            cls._default = LocalFileOperations()
        return cls._default
    
    @classmethod
    def set_default(cls, operations: EditOperations) -> None:
        """Set default operations"""
        cls._default = operations
    
    @classmethod
    def create_local(cls) -> LocalFileOperations:
        """Create local filesystem operations"""
        return LocalFileOperations()
    
    @classmethod
    def create_virtual(cls, files: Optional[dict] = None) -> VirtualFileOperations:
        """Create virtual filesystem for testing"""
        return VirtualFileOperations(files)
