"""
MIME Type Utilities - MIME 类型处理工具

检测和处理文件的 MIME 类型。
"""
import os
import struct
from pathlib import Path
from typing import Optional, Dict, Union, Tuple


# MIME 类型常量字典
MIME_TYPES: Dict[str, str] = {
    # 文本类型
    "text/plain": ".txt",
    "text/html": ".html",
    "text/css": ".css",
    "text/javascript": ".js",
    "text/csv": ".csv",
    "text/xml": ".xml",
    "text/markdown": ".md",
    "text/rtf": ".rtf",

    # 应用类型
    "application/json": ".json",
    "application/xml": ".xml",
    "application/javascript": ".js",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "application/x-7z-compressed": ".7z",
    "application/x-rar-compressed": ".rar",
    "application/octet-stream": ".bin",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",

    # 图片类型
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",
    "image/avif": ".avif",
    "image/heic": ".heic",
    "image/heif": ".heif",

    # 音频类型
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/aac": ".aac",
    "audio/midi": ".mid",

    # 视频类型
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "video/x-msvideo": ".avi",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/mpeg": ".mpeg",

    # 字体类型
    "font/ttf": ".ttf",
    "font/otf": ".otf",
    "font/woff": ".woff",
    "font/woff2": ".woff2",

    # 代码类型
    "application/x-python-code": ".py",
    "application/x-ruby": ".rb",
    "application/x-perl": ".pl",
    "application/x-php": ".php",
    "application/x-sh": ".sh",
    "application/x-csh": ".csh",
    "application/x-java-archive": ".jar",
    "application/x-python-pycode": ".pyc",
}

# 反向映射：扩展名 -> MIME 类型
EXTENSION_TO_MIME: Dict[str, str] = {v: k for k, v in MIME_TYPES.items()}

# 补充扩展名映射
EXTENSION_TO_MIME.update({
    # 编程语言
    ".py": "text/x-python",
    ".rb": "text/x-ruby",
    ".pl": "text/x-perl",
    ".php": "text/x-php",
    ".sh": "text/x-shellscript",
    ".bash": "text/x-shellscript",
    ".zsh": "text/x-shellscript",
    ".c": "text/x-c",
    ".cpp": "text/x-c++",
    ".h": "text/x-c",
    ".hpp": "text/x-c++",
    ".java": "text/x-java",
    ".kt": "text/x-kotlin",
    ".rs": "text/x-rust",
    ".go": "text/x-go",
    ".ts": "text/x-typescript",
    ".tsx": "text/x-typescript",
    ".jsx": "text/x-jsx",
    ".vue": "text/x-vue",
    ".svelte": "text/x-svelte",
    ".swift": "text/x-swift",
    ".scala": "text/x-scala",
    ".lua": "text/x-lua",
    ".r": "text/x-r",
    ".sql": "text/x-sql",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".toml": "text/x-toml",
    ".ini": "text/x-ini",
    ".conf": "text/plain",
    ".log": "text/plain",
    ".dockerfile": "text/x-dockerfile",
    ".makefile": "text/x-makefile",
    ".cmake": "text/x-cmake",

    # 数据格式
    ".proto": "text/x-protobuf",
    ".graphql": "text/x-graphql",
    ".gql": "text/x-graphql",

    # 标记语言
    ".rst": "text/x-rst",
    ".org": "text/x-org",
    ".tex": "text/x-tex",

    # 其他
    ".lock": "text/plain",
    ".gitignore": "text/plain",
    ".env": "text/plain",
})

# 文件魔数 (Magic Numbers)
MAGIC_NUMBERS: list = [
    # 图片
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # 需要额外检查 WEBP
    (b"BM", "image/bmp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"\x00\x00\x01\x00", "image/x-icon"),

    # 压缩文件
    (b"\x1f\x8b", "application/gzip"),
    (b"PK\x03\x04", "application/zip"),
    (b"PK\x05\x06", "application/zip"),
    (b"Rar!\x1a\x07", "application/x-rar-compressed"),
    (b"7z\xbc\xaf\x27\x1c", "application/x-7z-compressed"),
    (b"BZh", "application/x-bzip2"),
    (b"\xfd7zXZ\x00", "application/x-xz"),

    # 文档
    (b"%PDF", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),  # Office 文档也是 zip

    # 音频
    (b"ID3", "audio/mpeg"),
    (b"\xff\xfb", "audio/mpeg"),
    (b"\xff\xfa", "audio/mpeg"),
    (b"fLaC", "audio/flac"),
    (b"OggS", "audio/ogg"),

    # 视频
    (b"\x00\x00\x00\x1cftyp", "video/mp4"),
    (b"\x00\x00\x00\x20ftyp", "video/mp4"),
    (b"\x1aE\xdf\xa3", "video/webm"),
    (b"RIFF", "video/avi"),  # 需要额外检查 AVI

    # 可执行文件
    (b"MZ", "application/x-dosexec"),
    (b"\x7fELF", "application/x-elf"),
    (b"\xca\xfe\xba\xbe", "application/x-java-archive"),
    (b"dex\n", "application/x-android-dex"),

    # 字体
    (b"\x00\x01\x00\x00", "font/ttf"),
    (b"OTTO", "font/otf"),
    (b"wOFF", "font/woff"),
    (b"wOF2", "font/woff2"),
]


def detect_mime_type(
    file_path: Union[str, Path],
    use_magic: bool = True,
    fallback: str = "application/octet-stream"
) -> str:
    """
    检测文件的 MIME 类型

    优先使用文件魔数检测，然后回退到扩展名检测。

    Args:
        file_path: 文件路径
        use_magic: 是否使用文件魔数检测
        fallback: 无法检测时的回退类型

    Returns:
        MIME 类型字符串

    Example:
        >>> detect_mime_type("image.png")
        'image/png'
        >>> detect_mime_type("document.pdf")
        'application/pdf'
    """
    path = Path(file_path)

    # 尝试通过魔数检测
    if use_magic and path.exists() and path.is_file():
        mime = _detect_by_magic(path)
        if mime:
            return mime

    # 通过扩展名检测
    mime = _detect_by_extension(path)
    if mime:
        return mime

    return fallback


def _detect_by_magic(file_path: Path) -> Optional[str]:
    """通过文件魔数检测 MIME 类型"""
    try:
        with open(file_path, "rb") as f:
            header = f.read(64)

        if len(header) == 0:
            return None

        for magic, mime_type in MAGIC_NUMBERS:
            if header.startswith(magic):
                # 特殊处理 RIFF 格式
                if magic == b"RIFF" and len(header) >= 12:
                    format_id = header[8:12]
                    if format_id == b"WEBP":
                        return "image/webp"
                    elif format_id == b"AVI ":
                        return "video/x-msvideo"
                    elif format_id == b"WAVE":
                        return "audio/wav"
                return mime_type

        # 检查是否是文本文件
        if _is_text_content(header):
            return "text/plain"

        return None

    except (IOError, OSError):
        return None


def _detect_by_extension(file_path: Path) -> Optional[str]:
    """通过扩展名检测 MIME 类型"""
    ext = file_path.suffix.lower()
    return EXTENSION_TO_MIME.get(ext)


def _is_text_content(data: bytes) -> bool:
    """检查内容是否是文本"""
    if not data:
        return True

    # 检查是否有 NULL 字节（通常是二进制）
    if b"\x00" in data:
        return False

    # 检查是否大部分是可打印字符
    try:
        text = data.decode("utf-8")
        # 简单启发式：大部分是可打印字符
        printable_count = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
        return printable_count / len(text) > 0.85
    except UnicodeDecodeError:
        return False


def get_extension(mime_type: str) -> Optional[str]:
    """
    根据 MIME 类型获取文件扩展名

    Args:
        mime_type: MIME 类型

    Returns:
        文件扩展名（包含点），未知类型返回 None

    Example:
        >>> get_extension("image/png")
        '.png'
        >>> get_extension("application/json")
        '.json'
    """
    # 标准化 MIME 类型
    mime_type = mime_type.lower().split(";")[0].strip()

    return MIME_TYPES.get(mime_type)


def is_binary(
    file_path: Union[str, Path],
    sample_size: int = 8192
) -> bool:
    """
    判断文件是否是二进制文件

    Args:
        file_path: 文件路径
        sample_size: 检测的样本大小（字节）

    Returns:
        True 如果是二进制文件

    Example:
        >>> is_binary("image.png")
        True
        >>> is_binary("README.md")
        False
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        return False

    # 首先通过 MIME 类型判断
    mime = detect_mime_type(path)
    if mime.startswith("text/"):
        return False
    if mime.startswith("image/"):
        return True
    if mime.startswith("audio/"):
        return True
    if mime.startswith("video/"):
        return True
    if mime in ("application/pdf", "application/zip", "application/gzip"):
        return True

    # 通过内容判断
    try:
        with open(path, "rb") as f:
            sample = f.read(sample_size)

        if not sample:
            return False

        # 检查 NULL 字节
        if b"\x00" in sample:
            return True

        # 检查是否包含非文本字符
        # 使用类似的启发式方法
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
        non_text = sum(1 for byte in sample if byte not in text_chars)

        # 如果超过 30% 是非文本字符，认为是二进制
        return non_text / len(sample) > 0.30

    except (IOError, OSError):
        return False


def is_text_file(file_path: Union[str, Path]) -> bool:
    """
    判断是否是文本文件

    Args:
        file_path: 文件路径

    Returns:
        True 如果是文本文件
    """
    return not is_binary(file_path)


def is_image_file(file_path: Union[str, Path]) -> bool:
    """
    判断是否是图片文件

    Args:
        file_path: 文件路径

    Returns:
        True 如果是图片文件
    """
    mime = detect_mime_type(file_path)
    return mime.startswith("image/")


def is_audio_file(file_path: Union[str, Path]) -> bool:
    """
    判断是否是音频文件

    Args:
        file_path: 文件路径

    Returns:
        True 如果是音频文件
    """
    mime = detect_mime_type(file_path)
    return mime.startswith("audio/")


def is_video_file(file_path: Union[str, Path]) -> bool:
    """
    判断是否是视频文件

    Args:
        file_path: 文件路径

    Returns:
        True 如果是视频文件
    """
    mime = detect_mime_type(file_path)
    return mime.startswith("video/")


def get_mime_category(mime_type: str) -> str:
    """
    获取 MIME 类型的分类

    Args:
        mime_type: MIME 类型

    Returns:
        分类名称 (text, image, audio, video, application, etc.)
    """
    mime_type = mime_type.lower().split(";")[0].strip()
    return mime_type.split("/")[0] if "/" in mime_type else "application"


class MimeTypeDetector:
    """
    MIME 类型检测器类

    提供面向对象的 MIME 类型检测接口。

    Example:
        >>> detector = MimeTypeDetector()
        >>> mime = detector.detect("file.py")
        >>> print(mime)
        'text/x-python'
    """

    def __init__(self, custom_mappings: Optional[Dict[str, str]] = None):
        """
        初始化检测器

        Args:
            custom_mappings: 自定义 MIME 类型映射 {extension: mime_type}
        """
        self._mappings = dict(EXTENSION_TO_MIME)
        if custom_mappings:
            self._mappings.update(custom_mappings)

    def detect(
        self,
        file_path: Union[str, Path],
        use_magic: bool = True
    ) -> str:
        """检测 MIME 类型"""
        path = Path(file_path)

        # 魔数检测
        if use_magic and path.exists() and path.is_file():
            mime = _detect_by_magic(path)
            if mime:
                return mime

        # 扩展名检测
        ext = path.suffix.lower()
        return self._mappings.get(ext, "application/octet-stream")

    def get_extension(self, mime_type: str) -> Optional[str]:
        """获取扩展名"""
        return get_extension(mime_type)

    def is_binary(self, file_path: Union[str, Path]) -> bool:
        """判断是否二进制"""
        return is_binary(file_path)

    def register(self, extension: str, mime_type: str) -> None:
        """
        注册自定义 MIME 类型映射

        Args:
            extension: 扩展名（带点）
            mime_type: MIME 类型
        """
        self._mappings[extension.lower()] = mime_type.lower()


__all__ = [
    "MIME_TYPES",
    "EXTENSION_TO_MIME",
    "detect_mime_type",
    "get_extension",
    "is_binary",
    "is_text_file",
    "is_image_file",
    "is_audio_file",
    "is_video_file",
    "get_mime_category",
    "MimeTypeDetector",
]
