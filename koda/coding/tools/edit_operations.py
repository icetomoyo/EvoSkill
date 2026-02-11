"""
Edit Operations - File operations abstraction
Equivalent to Pi Mono's packages/coding-agent/src/core/tools/edit-operations.ts

Supports local filesystem and virtual (in-memory) operations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, Dict


@dataclass
class FileStat:
    """File statistics"""
    size: int = 0
    mtime: float = 0.0
    mode: int = 0
    exists: bool = False


class EditOperations(Protocol):
    """
    Protocol for pluggable edit operations.
    
    Implement this to provide custom file operations,
    such as SSH-based editing or remote filesystem access.
    """
    
    def read_file(self, path: str) -> str:
        """Read file contents as string"""
        ...
    
    def write_file(self, path: str, content: str) -> None:
        """Write string content to file"""
        ...


class LocalFileOperations:
    """Default local filesystem operations"""
    
    def read_file(self, path) -> str:
        """Read file contents"""
        return Path(path).read_text(encoding="utf-8")
    
    def read_file_bytes(self, path) -> bytes:
        """Read file as bytes"""
        return Path(path).read_bytes()
    
    def write_file(self, path, content: str) -> None:
        """Write file contents"""
        Path(path).write_text(content, encoding="utf-8")
    
    def write_file_bytes(self, path, data: bytes) -> None:
        """Write bytes to file"""
        Path(path).write_bytes(data)
    
    def file_exists(self, path) -> bool:
        """Check if file exists"""
        return Path(path).exists()
    
    def access(self, path) -> bool:
        """Check if path is accessible"""
        return Path(path).exists()
    
    def stat(self, path) -> FileStat:
        """Get file stats"""
        p = Path(path)
        if not p.exists():
            return FileStat(exists=False)
        
        s = p.stat()
        return FileStat(
            size=s.st_size,
            mtime=s.st_mtime,
            mode=s.st_mode,
            exists=True
        )
    
    def mkdir(self, path, parents=False) -> None:
        """Create directory"""
        Path(path).mkdir(parents=parents, exist_ok=True)


class VirtualFileOperations:
    """Virtual in-memory file operations for testing"""
    
    def __init__(self):
        self._files: Dict[str, bytes] = {}
    
    def read_file(self, path: str) -> str:
        """Read file contents"""
        path = str(path)
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[path].decode("utf-8")
    
    def read_file_bytes(self, path: str) -> bytes:
        """Read file as bytes"""
        path = str(path)
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        return self._files[path]
    
    def write_file(self, path: str, content: str) -> None:
        """Write file contents"""
        self._files[str(path)] = content.encode("utf-8")
    
    def write_file_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file"""
        self._files[str(path)] = data
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists"""
        return str(path) in self._files
    
    def access(self, path: str) -> bool:
        """Check if path is accessible"""
        return str(path) in self._files
    
    def stat(self, path: str) -> FileStat:
        """Get file stats"""
        path = str(path)
        if path not in self._files:
            return FileStat(exists=False)
        
        data = self._files[path]
        return FileStat(
            size=len(data),
            mtime=0,
            mode=0o644,
            exists=True
        )
    
    def mkdir(self, path, parents=False) -> None:
        """Create directory (no-op for virtual fs)"""
        pass
    
    def add_file(self, path: str, content: str) -> None:
        """Helper to add a file"""
        self.write_file(path, content)
    
    def get_file(self, path: str) -> Optional[str]:
        """Helper to get file content or None"""
        try:
            return self.read_file(path)
        except FileNotFoundError:
            return None
    
    def list_files(self) -> list:
        """List all files"""
        return list(self._files.keys())


# Backward compatibility
LocalEditOperations = LocalFileOperations


class EditOperationsFactory:
    """Factory for creating edit operations"""
    
    _default: Optional[LocalFileOperations] = None
    
    @classmethod
    def create_local(cls) -> LocalFileOperations:
        """Create local file operations"""
        return LocalFileOperations()
    
    @classmethod
    def create_virtual(cls, initial_files: Optional[Dict[str, str]] = None) -> VirtualFileOperations:
        """Create virtual file operations"""
        vfs = VirtualFileOperations()
        if initial_files:
            for path, content in initial_files.items():
                vfs.write_file(path, content)
        return vfs
    
    @classmethod
    def get_default(cls) -> LocalFileOperations:
        """Get default operations (singleton)"""
        if cls._default is None:
            cls._default = cls.create_local()
        return cls._default
    
    @classmethod
    def set_default(cls, ops) -> None:
        """Set default operations"""
        cls._default = ops


class EditOperationsRegistry:
    """Registry for pluggable edit operations"""
    
    def __init__(self):
        self._operations = LocalFileOperations()
    
    def register(self, operations) -> None:
        """Register custom operations"""
        self._operations = operations
    
    def get(self):
        """Get current operations"""
        return self._operations
    
    def reset(self) -> None:
        """Reset to default local operations"""
        self._operations = LocalFileOperations()


# Global registry instance
_registry = EditOperationsRegistry()


def get_edit_operations():
    """Get current edit operations"""
    return _registry.get()


def set_edit_operations(operations) -> None:
    """Set custom edit operations"""
    _registry.register(operations)


def reset_edit_operations() -> None:
    """Reset to default local operations"""
    _registry.reset()


# Convenience functions that use the registry
async def read_file(path: str) -> bytes:
    """Read file using current operations"""
    return await get_edit_operations().read_file(path)


async def write_file(path: str, content: str) -> None:
    """Write file using current operations"""
    return await get_edit_operations().write_file(path, content)


async def access(path: str) -> None:
    """Check access using current operations"""
    return await get_edit_operations().access(path)


__all__ = [
    "FileStat",
    "EditOperations",
    "LocalFileOperations",
    "LocalEditOperations",
    "VirtualFileOperations",
    "EditOperationsFactory",
    "EditOperationsRegistry",
    "get_edit_operations",
    "set_edit_operations",
    "reset_edit_operations",
    "read_file",
    "write_file",
    "access",
]
