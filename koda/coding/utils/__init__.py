"""
Coding Utilities
Equivalent to Pi Mono's packages/coding-agent/src/utils/
"""
from .shell import ShellUtils, ShellResult, run_command, escape_shell_arg, which
from .git import GitUtils, GitInfo, is_git_repo, get_git_info, get_git_diff
from .clipboard import ClipboardUtils, copy_to_clipboard, paste_from_clipboard, is_clipboard_available
from .image_convert import ImageConverter, ImageInfo, image_to_base64, convert_image

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
]
