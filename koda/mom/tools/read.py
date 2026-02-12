"""
Read Tool - File reading for Mom agent

Pi Mono compatible implementation:
- Read file contents with offset/limit
- Image support (PNG, JPEG, GIF, WebP)
- Encoding detection
- Pagination support
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import base64

from koda.mom.tools.truncate import truncate_head, format_truncation_notice


# Image magic numbers for detection
IMAGE_MAGIC_NUMBERS = [
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
    (b'RIFF', 'image/webp'),  # WebP starts with RIFF....WEBP
]


@dataclass
class ReadResult:
    """Result from reading a file"""
    success: bool
    content: str
    path: str
    start_line: int
    end_line: int
    total_lines: int
    truncated: bool
    next_offset: int
    is_image: bool = False
    image_data: Optional[str] = None  # Base64 encoded
    mime_type: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def detect_image_mime_type(file_path: Path) -> Optional[str]:
    """
    Detect image MIME type from file magic numbers.

    This is more reliable than extension-based detection.

    Args:
        file_path: Path to file

    Returns:
        MIME type string or None
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)  # Read first 32 bytes

        for magic, mime_type in IMAGE_MAGIC_NUMBERS:
            if header.startswith(magic):
                # Special handling for WebP
                if mime_type == 'image/webp':
                    if b'WEBP' in header[:12]:
                        return mime_type
                else:
                    return mime_type

        return None
    except Exception:
        return None


def detect_encoding(file_path: Path) -> str:
    """
    Detect file encoding.

    Simple detection - defaults to UTF-8.

    Args:
        file_path: Path to file

    Returns:
        Encoding string
    """
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(4)

        # Check for BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        elif raw.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        elif raw.startswith(b'\xfe\xff'):
            return 'utf-16-be'

        return 'utf-8'
    except Exception:
        return 'utf-8'


def read_file(
    file_path: str,
    offset: int = 1,
    limit: Optional[int] = None,
    base_path: Optional[Path] = None,
    auto_detect_image: bool = True,
) -> ReadResult:
    """
    Read file contents (Pi Mono compatible).

    Args:
        file_path: Path to file (relative or absolute)
        offset: Starting line number (1-indexed)
        limit: Maximum number of lines to read
        base_path: Base directory for relative paths
        auto_detect_image: Whether to auto-detect and handle images

    Returns:
        ReadResult with file contents or error
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

    # Check if file exists
    if not path.exists():
        return ReadResult(
            success=False,
            content="",
            path=str(path),
            start_line=0,
            end_line=0,
            total_lines=0,
            truncated=False,
            next_offset=0,
            error=f"File not found: {file_path}",
        )

    # Check if it's a file
    if not path.is_file():
        return ReadResult(
            success=False,
            content="",
            path=str(path),
            start_line=0,
            end_line=0,
            total_lines=0,
            truncated=False,
            next_offset=0,
            error=f"Not a file: {file_path}",
        )

    try:
        # Check if it's an image
        if auto_detect_image:
            mime_type = detect_image_mime_type(path)
            if mime_type:
                return _read_image(path, mime_type)

        # Detect encoding
        encoding = detect_encoding(path)

        # Read text file
        with open(path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()

        # Process lines
        lines = content.split('\n')
        total_lines = len(lines)

        # Calculate start and end indices
        start_idx = max(0, offset - 1)  # Convert to 0-indexed

        # Check if offset is beyond file
        if start_idx >= total_lines:
            return ReadResult(
                success=False,
                content="",
                path=str(path),
                start_line=0,
                end_line=0,
                total_lines=total_lines,
                truncated=False,
                next_offset=0,
                error=f"Offset {offset} is beyond end of file ({total_lines} lines total)",
            )

        # Calculate end index
        if limit is not None:
            end_idx = min(start_idx + limit, total_lines)
        else:
            end_idx = total_lines

        # Extract lines
        selected_lines = lines[start_idx:end_idx]
        selected_content = '\n'.join(selected_lines)

        # Apply head truncation
        truncation = truncate_head(selected_content)

        # Calculate actual line numbers
        actual_start = start_idx + 1  # 1-indexed
        actual_end = start_idx + truncation.output_lines

        # Build output with line numbers
        output_lines = []
        for i, line in enumerate(truncation.content.split('\n')):
            line_num = actual_start + i
            output_lines.append(f"{line_num:6d}\t{line}")

        output_text = '\n'.join(output_lines)

        # Add truncation notice
        if truncation.truncated:
            notice = format_truncation_notice(truncation, "head")
            if notice:
                output_text += f"\n\n{notice}"

        # Calculate next offset
        next_offset = actual_end + 1 if truncation.truncated or (limit and end_idx < total_lines) else 0

        return ReadResult(
            success=True,
            content=output_text,
            path=str(path),
            start_line=actual_start,
            end_line=actual_end,
            total_lines=total_lines,
            truncated=truncation.truncated,
            next_offset=next_offset,
            metadata={
                "encoding": encoding,
                "bytes_read": len(selected_content.encode('utf-8')),
            },
        )

    except Exception as e:
        return ReadResult(
            success=False,
            content="",
            path=str(path),
            start_line=0,
            end_line=0,
            total_lines=0,
            truncated=False,
            next_offset=0,
            error=str(e),
        )


def _read_image(path: Path, mime_type: str) -> ReadResult:
    """Read an image file and return base64 encoded data."""
    try:
        with open(path, 'rb') as f:
            image_bytes = f.read()

        base64_data = base64.b64encode(image_bytes).decode('utf-8')

        return ReadResult(
            success=True,
            content=f"[Image: {mime_type}, {len(image_bytes)} bytes]",
            path=str(path),
            start_line=0,
            end_line=0,
            total_lines=0,
            truncated=False,
            next_offset=0,
            is_image=True,
            image_data=base64_data,
            mime_type=mime_type,
            metadata={
                "size_bytes": len(image_bytes),
            },
        )
    except Exception as e:
        return ReadResult(
            success=False,
            content="",
            path=str(path),
            start_line=0,
            end_line=0,
            total_lines=0,
            truncated=False,
            next_offset=0,
            error=str(e),
        )


class ReadTool:
    """
    Read Tool class for Mom agent.

    Provides file reading capabilities with:
    - Pagination support
    - Image handling
    - Encoding detection
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()

    def read(
        self,
        file_path: str,
        offset: int = 1,
        limit: Optional[int] = None,
    ) -> ReadResult:
        """Read a file."""
        return read_file(file_path, offset, limit, self.base_path)

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for LLM."""
        return {
            "name": "read",
            "description": "Read file contents. Supports text files and images. Use offset/limit for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (relative or absolute)",
                    },
                    "offset": {
                        "type": "integer",
                        "default": 1,
                        "description": "Starting line number (1-indexed)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read",
                    },
                },
                "required": ["file_path"],
            },
        }
