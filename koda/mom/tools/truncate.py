"""
Truncate Tool - Output truncation for Mom agent

Pi Mono compatible implementation:
- 50KB / 2000 lines limits
- Head truncation (for file reads)
- Tail truncation (for bash output)
- Smart truncation strategies
- Preserve critical information
"""
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict

# Default limits (matching Pi Mono)
DEFAULT_MAX_BYTES = 50 * 1024  # 50KB
DEFAULT_MAX_LINES = 2000


def format_size(bytes_val: int) -> str:
    """Format bytes as human-readable size."""
    if bytes_val < 1024:
        return f"{bytes_val}B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f}KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f}MB"


@dataclass
class TruncationResult:
    """Truncation result"""
    content: str
    truncated: bool
    truncated_by: Optional[str]  # "lines", "bytes", or None
    total_lines: int
    total_bytes: int
    output_lines: int
    output_bytes: int
    last_line_partial: bool = False
    first_line_exceeds_limit: bool = False
    max_lines: int = DEFAULT_MAX_LINES
    max_bytes: int = DEFAULT_MAX_BYTES
    next_offset: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


def truncate_head(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """
    Head truncation - keep beginning of content

    Used for file reads.
    Never returns partial lines.

    Args:
        content: Content to truncate
        max_lines: Maximum number of lines
        max_bytes: Maximum bytes

    Returns:
        TruncationResult
    """
    total_bytes = len(content.encode('utf-8'))
    lines = content.split('\n')
    total_lines = len(lines)

    # No truncation needed
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=total_lines,
            output_bytes=total_bytes,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )

    # Check if first line alone exceeds byte limit
    first_line_bytes = len(lines[0].encode('utf-8'))
    if first_line_bytes > max_bytes:
        return TruncationResult(
            content="",
            truncated=True,
            truncated_by="bytes",
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=0,
            output_bytes=0,
            first_line_exceeds_limit=True,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )

    # Collect complete lines that fit
    output_lines_arr = []
    output_bytes_count = 0
    truncated_by = "lines"

    for i, line in enumerate(lines):
        if i >= max_lines:
            truncated_by = "lines"
            break

        line_bytes = len(line.encode('utf-8')) + (1 if i > 0 else 0)  # +1 for newline

        if output_bytes_count + line_bytes > max_bytes:
            truncated_by = "bytes"
            break

        output_lines_arr.append(line)
        output_bytes_count += line_bytes

    output_content = '\n'.join(output_lines_arr)
    final_output_bytes = len(output_content.encode('utf-8'))

    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines_arr),
        output_bytes=final_output_bytes,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def truncate_tail(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """
    Tail truncation - keep end of content

    Used for bash output.
    May return partial first line if last line exceeds byte limit.

    Args:
        content: Content to truncate
        max_lines: Maximum number of lines
        max_bytes: Maximum bytes

    Returns:
        TruncationResult
    """
    total_bytes = len(content.encode('utf-8'))
    lines = content.split('\n')
    total_lines = len(lines)

    # No truncation needed
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=total_lines,
            output_bytes=total_bytes,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )

    # Work backwards from the end
    output_lines_arr = []
    output_bytes_count = 0
    truncated_by = "lines"
    last_line_partial = False

    for i in range(len(lines) - 1, -1, -1):
        if len(output_lines_arr) >= max_lines:
            truncated_by = "lines"
            break

        line = lines[i]
        line_bytes = len(line.encode('utf-8')) + (1 if output_lines_arr else 0)

        if output_bytes_count + line_bytes > max_bytes:
            truncated_by = "bytes"
            # Edge case: if we haven't added ANY lines yet and this line exceeds maxBytes,
            # take the end of the line (partial)
            if not output_lines_arr:
                truncated_line = _truncate_string_to_bytes_from_end(line, max_bytes)
                output_lines_arr.insert(0, truncated_line)
                output_bytes_count = len(truncated_line.encode('utf-8'))
                last_line_partial = True
            break

        output_lines_arr.insert(0, line)
        output_bytes_count += line_bytes

    output_content = '\n'.join(output_lines_arr)
    final_output_bytes = len(output_content.encode('utf-8'))

    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines_arr),
        output_bytes=final_output_bytes,
        last_line_partial=last_line_partial,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def _truncate_string_to_bytes_from_end(s: str, max_bytes: int) -> str:
    """
    Truncate a string from the end to fit within byte limit.
    Handles multi-byte UTF-8 characters correctly.
    """
    encoded = s.encode('utf-8')
    if len(encoded) <= max_bytes:
        return s

    # Start from the end, skip max_bytes back
    start = len(encoded) - max_bytes

    # Find a valid UTF-8 boundary (start of a character)
    # UTF-8 continuation bytes start with 10xxxxxx (0x80-0xBF)
    while start < len(encoded) and (encoded[start] & 0xC0) == 0x80:
        start += 1

    return encoded[start:].decode('utf-8')


def truncate_output(
    content: str,
    mode: str = "head",
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
    preserve_patterns: Optional[List[str]] = None,
) -> TruncationResult:
    """
    Smart truncation with pattern preservation.

    This is the main truncation function for Mom tools.

    Args:
        content: Content to truncate
        mode: "head" or "tail" truncation
        max_lines: Maximum number of lines
        max_bytes: Maximum bytes
        preserve_patterns: List of regex patterns to preserve

    Returns:
        TruncationResult with truncated content and metadata
    """
    import re

    # Apply base truncation
    if mode == "head":
        result = truncate_head(content, max_lines, max_bytes)
    else:
        result = truncate_tail(content, max_lines, max_bytes)

    # If no patterns to preserve, return result
    if not preserve_patterns or not result.truncated:
        return result

    # Extract lines matching preserve patterns
    preserved_lines = []
    lines = content.split('\n')

    for pattern in preserve_patterns:
        try:
            regex = re.compile(pattern)
            for i, line in enumerate(lines):
                if regex.search(line):
                    # Add line with context
                    preserved_lines.append({
                        "line": line,
                        "line_number": i + 1,
                        "pattern": pattern,
                    })
        except re.error:
            continue

    # Add preserved lines to metadata
    if preserved_lines:
        result.metadata["preserved_lines"] = preserved_lines[:10]  # Limit to 10

    return result


def format_truncation_notice(result: TruncationResult, mode: str = "head") -> str:
    """
    Format a human-readable truncation notice.

    Args:
        result: TruncationResult
        mode: "head" or "tail"

    Returns:
        Formatted notice string
    """
    if not result.truncated:
        return ""

    if mode == "head":
        if result.first_line_exceeds_limit:
            return f"[First line exceeds {format_size(result.max_bytes)} limit. Cannot display.]"
        elif result.truncated_by == "lines":
            return f"[Showing lines 1-{result.output_lines} of {result.total_lines}. Use offset={result.output_lines + 1} to continue.]"
        else:
            return f"[Showing {format_size(result.output_bytes)} of {format_size(result.total_bytes)}. Use offset={result.output_lines + 1} to continue.]"
    else:
        start_line = result.total_lines - result.output_lines + 1
        if result.last_line_partial:
            return f"[Showing last {format_size(result.output_bytes)} of line {result.total_lines}.]"
        elif result.truncated_by == "lines":
            return f"[Showing lines {start_line}-{result.total_lines} of {result.total_lines}.]"
        else:
            return f"[Showing lines {start_line}-{result.total_lines} ({format_size(result.max_bytes)} limit).]"

    return ""
