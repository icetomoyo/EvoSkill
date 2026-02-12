"""
Write Tool - File writing for Mom agent

Pi Mono compatible implementation:
- Write content to file
- Automatic directory creation
- Atomic write support
- Backup options
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil
import os


@dataclass
class WriteResult:
    """Result from writing a file"""
    success: bool
    path: str
    bytes_written: int = 0
    backup_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def write_file(
    file_path: str,
    content: str,
    base_path: Optional[Path] = None,
    create_dirs: bool = True,
    atomic: bool = True,
    backup: bool = False,
    encoding: str = 'utf-8',
) -> WriteResult:
    """
    Write content to a file (Pi Mono compatible).

    Args:
        file_path: Path to file (relative or absolute)
        content: Content to write
        base_path: Base directory for relative paths
        create_dirs: Whether to create parent directories
        atomic: Whether to use atomic write (write to temp, then rename)
        backup: Whether to create backup of existing file
        encoding: File encoding

    Returns:
        WriteResult with status and metadata
    """
    # Resolve path
    path = Path(file_path)
    if not path.is_absolute():
        if base_path:
            path = base_path / path
        else:
            path = Path.cwd() / path

    # Resolve to absolute path
    try:
        path = path.resolve()
    except Exception:
        pass

    try:
        # Create parent directories if needed
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if requested and file exists
        backup_path = None
        if backup and path.exists():
            backup_path = str(path) + '.bak'
            counter = 1
            while Path(backup_path).exists():
                backup_path = f"{path}.bak.{counter}"
                counter += 1
            shutil.copy2(str(path), backup_path)

        # Calculate bytes to write
        content_bytes = content.encode(encoding)
        bytes_written = len(content_bytes)

        if atomic:
            # Atomic write: write to temp file, then rename
            # This prevents corruption if write is interrupted
            temp_fd = None
            temp_path = None

            try:
                # Create temp file in same directory (ensures same filesystem)
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=str(path.parent),
                    prefix='.tmp_',
                    suffix=path.suffix,
                )

                # Write content to temp file
                with os.fdopen(temp_fd, 'w', encoding=encoding) as f:
                    f.write(content)
                temp_fd = None  # Already closed by fdopen

                # Atomic rename
                shutil.move(temp_path, str(path))
                temp_path = None

            finally:
                # Cleanup temp file if something went wrong
                if temp_fd is not None:
                    try:
                        os.close(temp_fd)
                    except:
                        pass
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
        else:
            # Direct write
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)

        return WriteResult(
            success=True,
            path=str(path),
            bytes_written=bytes_written,
            backup_path=backup_path,
            metadata={
                "encoding": encoding,
                "atomic": atomic,
            },
        )

    except PermissionError:
        return WriteResult(
            success=False,
            path=str(path),
            error=f"Permission denied: {file_path}",
        )
    except Exception as e:
        return WriteResult(
            success=False,
            path=str(path),
            error=str(e),
        )


class WriteTool:
    """
    Write Tool class for Mom agent.

    Provides file writing capabilities with:
    - Atomic writes
    - Backup support
    - Automatic directory creation
    """

    def __init__(
        self,
        base_path: Optional[Path] = None,
        atomic: bool = True,
        backup: bool = False,
    ):
        self.base_path = base_path or Path.cwd()
        self.atomic = atomic
        self.backup = backup

    def write(
        self,
        file_path: str,
        content: str,
    ) -> WriteResult:
        """Write content to a file."""
        return write_file(
            file_path,
            content,
            self.base_path,
            atomic=self.atomic,
            backup=self.backup,
        )

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for LLM."""
        return {
            "name": "write",
            "description": "Write content to a file. Creates directories automatically. Overwrites existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (relative or absolute)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                },
                "required": ["file_path", "content"],
            },
        }
