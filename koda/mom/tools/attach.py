"""
Attach Tool - File attachment handling for Mom agent

Pi Mono compatible implementation:
- Attach files to conversation
- MIME type detection
- Base64 encoding for binary files
- Size limits
- Image handling
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import base64
import mimetypes

from koda.mom.tools.truncate import format_size


# Attachment size limits
DEFAULT_MAX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_SIZE = 4.5 * 1024 * 1024   # 4.5MB (matching Pi Mono)

# Supported MIME types
SUPPORTED_IMAGE_TYPES = {
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/gif',
    'image/webp',
}

SUPPORTED_TEXT_TYPES = {
    'text/plain',
    'text/markdown',
    'text/html',
    'text/css',
    'text/javascript',
    'text/csv',
    'text/xml',
    'application/json',
    'application/xml',
    'application/javascript',
}

# File extension to MIME type mapping
EXTENSION_MIME_MAP = {
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.markdown': 'text/markdown',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.xml': 'application/xml',
    '.csv': 'text/csv',
    '.py': 'text/x-python',
    '.java': 'text/x-java',
    '.c': 'text/x-c',
    '.cpp': 'text/x-c++',
    '.h': 'text/x-c',
    '.hpp': 'text/x-c++',
    '.rs': 'text/x-rust',
    '.go': 'text/x-go',
    '.ts': 'text/x-typescript',
    '.tsx': 'text/x-typescript',
    '.jsx': 'text/x-javascript',
    '.sh': 'text/x-sh',
    '.bash': 'text/x-sh',
    '.yml': 'text/x-yaml',
    '.yaml': 'text/x-yaml',
    '.toml': 'text/x-toml',
    '.ini': 'text/x-ini',
    '.cfg': 'text/x-ini',
}


@dataclass
class AttachResult:
    """Result from attaching a file"""
    success: bool
    path: str
    output: str
    attachment_type: str  # "image", "text", "binary"
    mime_type: Optional[str] = None
    data: Optional[str] = None  # Base64 encoded for binary/image
    content: Optional[str] = None  # Text content for text files
    size: int = 0
    description: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def detect_mime_type(file_path: Path) -> Optional[str]:
    """
    Detect MIME type from file.

    Uses multiple strategies:
    1. Extension-based (from mapping)
    2. mimetypes library
    3. None if unknown

    Args:
        file_path: Path to file

    Returns:
        MIME type string or None
    """
    # Try extension-based detection first
    ext = file_path.suffix.lower()
    if ext in EXTENSION_MIME_MAP:
        return EXTENSION_MIME_MAP[ext]

    # Try mimetypes library
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type


def is_image_mime_type(mime_type: Optional[str]) -> bool:
    """Check if MIME type is an image."""
    return mime_type in SUPPORTED_IMAGE_TYPES


def is_text_mime_type(mime_type: Optional[str]) -> bool:
    """Check if MIME type is text."""
    if mime_type is None:
        return False
    if mime_type in SUPPORTED_TEXT_TYPES:
        return True
    if mime_type.startswith('text/'):
        return True
    if mime_type.startswith('application/') and any(
        mime_type.endswith(x) for x in ['json', 'xml', 'javascript']
    ):
        return True
    return False


def encode_file(file_path: Path) -> str:
    """
    Encode file to Base64.

    Args:
        file_path: Path to file

    Returns:
        Base64 encoded string
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode('utf-8')


def attach_file(
    file_path: str,
    base_path: Optional[Path] = None,
    description: Optional[str] = None,
    max_size: int = DEFAULT_MAX_SIZE,
    encoding: str = 'utf-8',
) -> AttachResult:
    """
    Attach a file to conversation (Pi Mono compatible).

    Args:
        file_path: Path to file (relative or absolute)
        base_path: Base directory for relative paths
        description: Optional description
        max_size: Maximum file size in bytes
        encoding: Encoding for text files

    Returns:
        AttachResult with file data or error
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
        return AttachResult(
            success=False,
            path=str(path),
            output="",
            attachment_type="",
            error=f"File not found: {file_path}",
        )

    # Check if it's a file
    if not path.is_file():
        return AttachResult(
            success=False,
            path=str(path),
            output="",
            attachment_type="",
            error=f"Not a file: {file_path}",
        )

    try:
        # Get file size
        file_size = path.stat().st_size

        # Check size limit
        if file_size > max_size:
            return AttachResult(
                success=False,
                path=str(path),
                output="",
                attachment_type="",
                error=f"File too large: {format_size(file_size)} (max: {format_size(max_size)})",
            )

        # Detect MIME type
        mime_type = detect_mime_type(path)

        # Handle images
        if is_image_mime_type(mime_type):
            return _attach_image(path, mime_type, file_size, description)

        # Handle text files
        if is_text_mime_type(mime_type):
            return _attach_text(path, mime_type, file_size, description, encoding)

        # Handle other binary files
        return _attach_binary(path, mime_type, file_size, description)

    except Exception as e:
        return AttachResult(
            success=False,
            path=str(path),
            output="",
            attachment_type="",
            error=str(e),
        )


def _attach_image(
    path: Path,
    mime_type: str,
    file_size: int,
    description: Optional[str],
) -> AttachResult:
    """Attach an image file."""
    try:
        # Check image size limit
        if file_size > MAX_IMAGE_SIZE:
            # Could resize here in the future
            return AttachResult(
                success=False,
                path=str(path),
                output="",
                attachment_type="image",
                error=f"Image too large: {format_size(file_size)} (max: {format_size(MAX_IMAGE_SIZE)})",
            )

        # Encode to base64
        b64_data = encode_file(path)

        output = f"Attached image: {path.name}"
        if description:
            output += f" - {description}"
        output += f" ({format_size(file_size)})"

        return AttachResult(
            success=True,
            path=str(path),
            output=output,
            attachment_type="image",
            mime_type=mime_type,
            data=b64_data,
            size=file_size,
            description=description,
            metadata={
                "width": None,  # Could extract with PIL
                "height": None,
            },
        )
    except Exception as e:
        return AttachResult(
            success=False,
            path=str(path),
            output="",
            attachment_type="image",
            error=str(e),
        )


def _attach_text(
    path: Path,
    mime_type: str,
    file_size: int,
    description: Optional[str],
    encoding: str,
) -> AttachResult:
    """Attach a text file."""
    try:
        with open(path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()

        output = f"Attached text file: {path.name}"
        if description:
            output += f" - {description}"
        output += f" ({format_size(file_size)})"

        return AttachResult(
            success=True,
            path=str(path),
            output=output,
            attachment_type="text",
            mime_type=mime_type,
            content=content,
            size=file_size,
            description=description,
            metadata={
                "lines": len(content.split('\n')),
                "encoding": encoding,
            },
        )
    except Exception as e:
        return AttachResult(
            success=False,
            path=str(path),
            output="",
            attachment_type="text",
            error=str(e),
        )


def _attach_binary(
    path: Path,
    mime_type: Optional[str],
    file_size: int,
    description: Optional[str],
) -> AttachResult:
    """Attach a binary file."""
    try:
        b64_data = encode_file(path)

        output = f"Attached file: {path.name}"
        if description:
            output += f" - {description}"
        output += f" ({format_size(file_size)})"

        return AttachResult(
            success=True,
            path=str(path),
            output=output,
            attachment_type="binary",
            mime_type=mime_type or "application/octet-stream",
            data=b64_data,
            size=file_size,
            description=description,
        )
    except Exception as e:
        return AttachResult(
            success=False,
            path=str(path),
            output="",
            attachment_type="binary",
            error=str(e),
        )


class AttachTool:
    """
    Attach Tool class for Mom agent.

    Provides file attachment capabilities with:
    - MIME type detection
    - Base64 encoding
    - Size limits
    """

    def __init__(
        self,
        base_path: Optional[Path] = None,
        max_size: int = DEFAULT_MAX_SIZE,
    ):
        self.base_path = base_path or Path.cwd()
        self.max_size = max_size

    def attach(
        self,
        file_path: str,
        description: Optional[str] = None,
    ) -> AttachResult:
        """Attach a file."""
        return attach_file(
            file_path,
            self.base_path,
            description,
            self.max_size,
        )

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for LLM."""
        return {
            "name": "attach",
            "description": "Attach a file or image to the conversation. Supports images, text files, and binary files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (relative or absolute)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the attachment",
                    },
                },
                "required": ["file_path"],
            },
        }
