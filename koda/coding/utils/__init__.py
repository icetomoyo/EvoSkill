"""
Coding Utilities
Equivalent to Pi Mono's packages/coding-agent/src/utils/
"""
from .shell import ShellUtils, ShellResult, run_command, escape_shell_arg, which
from .git import GitUtils, GitInfo, is_git_repo, get_git_info, get_git_diff
from .clipboard import ClipboardUtils, copy_to_clipboard, paste_from_clipboard, is_clipboard_available
from .image_convert import ImageConverter, ImageInfo, image_to_base64, convert_image
from .changelog import (
    Version, VersionBump, ChangelogEntry, Changelog, ChangelogParser,
    parse_changelog, compare_versions, detect_version_bump
)
from .mime import (
    MIME_TYPES, EXTENSION_TO_MIME, detect_mime_type, get_extension,
    is_binary, is_text_file, is_image_file, is_audio_file, is_video_file,
    get_mime_category, MimeTypeDetector
)
from .photon import (
    PIL_AVAILABLE, check_pillow_available, ImageSize, ImageMetadata,
    ResizeResult, ConvertResult, get_image_size, get_image_metadata,
    resize_image, convert_format, create_thumbnail, apply_filter,
    auto_orient, PhotonProcessor
)
from .sleep import (
    SleepState, SleepResult, SleepHandle, async_sleep, sleep_with_timeout,
    SleepManager, periodic_sleep
)
from .tools_manager import (
    ToolStatus, ToolCategory, ToolParameter, ToolResult, ToolSchema,
    ToolInfo, ToolValidator, ToolManager, tool, parameter,
    get_tool_manager, register_tool, execute_tool
)

__all__ = [
    # Shell
    "ShellUtils",
    "ShellResult",
    "run_command",
    "escape_shell_arg",
    "which",
    # Git
    "GitUtils",
    "GitInfo",
    "is_git_repo",
    "get_git_info",
    "get_git_diff",
    # Clipboard
    "ClipboardUtils",
    "copy_to_clipboard",
    "paste_from_clipboard",
    "is_clipboard_available",
    # Image
    "ImageConverter",
    "ImageInfo",
    "image_to_base64",
    "convert_image",
    # Changelog
    "Version",
    "VersionBump",
    "ChangelogEntry",
    "Changelog",
    "ChangelogParser",
    "parse_changelog",
    "compare_versions",
    "detect_version_bump",
    # MIME
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
    # Photon
    "PIL_AVAILABLE",
    "check_pillow_available",
    "ImageSize",
    "ImageMetadata",
    "ResizeResult",
    "ConvertResult",
    "get_image_size",
    "get_image_metadata",
    "resize_image",
    "convert_format",
    "create_thumbnail",
    "apply_filter",
    "auto_orient",
    "PhotonProcessor",
    # Sleep
    "SleepState",
    "SleepResult",
    "SleepHandle",
    "async_sleep",
    "sleep_with_timeout",
    "SleepManager",
    "periodic_sleep",
    # Tools Manager
    "ToolStatus",
    "ToolCategory",
    "ToolParameter",
    "ToolResult",
    "ToolSchema",
    "ToolInfo",
    "ToolValidator",
    "ToolManager",
    "tool",
    "parameter",
    "get_tool_manager",
    "register_tool",
    "execute_tool",
]
