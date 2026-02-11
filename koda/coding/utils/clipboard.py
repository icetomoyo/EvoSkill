"""
Clipboard Utilities
Equivalent to Pi Mono's packages/coding-agent/src/utils/clipboard.ts

Clipboard read/write operations.
"""
import subprocess
from typing import Optional


class ClipboardUtils:
    """
    Clipboard operations.
    
    Cross-platform clipboard access.
    
    Example:
        >>> clipboard = ClipboardUtils()
        >>> clipboard.copy("Hello, World!")
        >>> content = clipboard.paste()
        >>> print(content)
        'Hello, World!'
    """
    
    def __init__(self):
        self._platform = self._detect_platform()
    
    def _detect_platform(self) -> str:
        """Detect operating system"""
        import sys
        if sys.platform == 'win32':
            return 'windows'
        elif sys.platform == 'darwin':
            return 'macos'
        else:
            return 'linux'
    
    def copy(self, text: str) -> bool:
        """
        Copy text to clipboard.
        
        Args:
            text: Text to copy
            
        Returns:
            True if successful
        """
        try:
            if self._platform == 'windows':
                return self._copy_windows(text)
            elif self._platform == 'macos':
                return self._copy_macos(text)
            else:
                return self._copy_linux(text)
        except Exception:
            return False
    
    def paste(self) -> Optional[str]:
        """
        Paste text from clipboard.
        
        Returns:
            Clipboard content or None
        """
        try:
            if self._platform == 'windows':
                return self._paste_windows()
            elif self._platform == 'macos':
                return self._paste_macos()
            else:
                return self._paste_linux()
        except Exception:
            return None
    
    def _copy_windows(self, text: str) -> bool:
        """Copy on Windows"""
        # Try using clip command
        result = subprocess.run(
            ['clip'],
            input=text,
            capture_output=True,
            text=True,
            shell=True
        )
        return result.returncode == 0
    
    def _paste_windows(self) -> Optional[str]:
        """Paste on Windows"""
        # Try using PowerShell
        result = subprocess.run(
            ['powershell', '-command', 'Get-Clipboard'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout
        return None
    
    def _copy_macos(self, text: str) -> bool:
        """Copy on macOS"""
        result = subprocess.run(
            ['pbcopy'],
            input=text,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    
    def _paste_macos(self) -> Optional[str]:
        """Paste on macOS"""
        result = subprocess.run(
            ['pbpaste'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout
        return None
    
    def _copy_linux(self, text: str) -> bool:
        """Copy on Linux"""
        # Try wl-copy (Wayland) first, then xclip (X11)
        for cmd in [['wl-copy'], ['xclip', '-selection', 'clipboard', '-in']]:
            try:
                result = subprocess.run(
                    cmd,
                    input=text,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return True
            except FileNotFoundError:
                continue
        return False
    
    def _paste_linux(self) -> Optional[str]:
        """Paste on Linux"""
        # Try wl-paste (Wayland) first, then xclip (X11)
        for cmd in [['wl-paste'], ['xclip', '-selection', 'clipboard', '-out']]:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout
            except FileNotFoundError:
                continue
        return None
    
    def is_available(self) -> bool:
        """Check if clipboard is available"""
        # Try to copy and paste a test string
        test = "__clipboard_test__"
        if self.copy(test):
            # Note: paste might fail if clipboard is empty
            return True
        return False


# Convenience functions
def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard"""
    clipboard = ClipboardUtils()
    return clipboard.copy(text)


def paste_from_clipboard() -> Optional[str]:
    """Paste text from clipboard"""
    clipboard = ClipboardUtils()
    return clipboard.paste()


def is_clipboard_available() -> bool:
    """Check if clipboard operations are available"""
    clipboard = ClipboardUtils()
    return clipboard.is_available()


__all__ = [
    "ClipboardUtils",
    "copy_to_clipboard",
    "paste_from_clipboard",
    "is_clipboard_available",
]
