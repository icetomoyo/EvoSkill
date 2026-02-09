"""
Truncation utilities for tools

Extends core truncation with tool-specific functions
"""
from dataclasses import dataclass


# Grep max line length (matching Pi)
GREP_MAX_LINE_LENGTH = 500


@dataclass
class LineTruncationResult:
    """Result of truncating a single line"""
    text: str
    was_truncated: bool


def truncate_line(line: str, max_chars: int = GREP_MAX_LINE_LENGTH) -> LineTruncationResult:
    """
    Truncate a single line to max characters, adding [truncated] suffix
    
    Used for grep match lines.
    """
    if len(line) <= max_chars:
        return LineTruncationResult(text=line, was_truncated=False)
    
    return LineTruncationResult(
        text=f"{line[:max_chars]}... [truncated]",
        was_truncated=True
    )
