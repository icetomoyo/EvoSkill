"""
Truncation - Content truncation handling

Pi Coding Agent compatible implementation:
- 50KB / 2000 lines limits
- Head truncation (for file reads)
- Tail truncation (for bash output)
- Multi-byte UTF-8 handling
"""
from dataclasses import dataclass
from typing import Optional


# Default limits (matching Pi)
DEFAULT_MAX_BYTES = 50 * 1024  # 50KB
DEFAULT_MAX_LINES = 2000

# Grep max line length
GREP_MAX_LINE_LENGTH = 500


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
    """Truncation result - Pi compatible"""
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


def truncate_head(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """
    Head truncation - keep beginning of content
    
    Used for file reads.
    Never returns partial lines.
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


def format_truncation_message(result: TruncationResult, mode: str = "head") -> str:
    """Format truncation notice message"""
    if not result.truncated:
        return ""
    
    if mode == "head":
        if result.truncated_by == "lines":
            return f"[Showing lines 1-{result.output_lines} of {result.total_lines}. Use offset={result.output_lines + 1} to continue.]"
        elif result.truncated_by == "bytes":
            return f"[Showing {format_size(result.output_bytes)} of {format_size(result.total_bytes)}. Use offset={result.output_lines + 1} to continue.]"
    else:
        start_line = result.total_lines - result.output_lines + 1
        if result.last_line_partial:
            return f"[Showing last {format_size(result.output_bytes)} of line {result.total_lines}. Full output in temporary file.]"
        elif result.truncated_by == "lines":
            return f"[Showing lines {start_line}-{result.total_lines} of {result.total_lines}. Full output in temporary file.]"
        else:
            return f"[Showing lines {start_line}-{result.total_lines} of {result.total_lines} ({format_size(result.max_bytes)} limit). Full output in temporary file.]"
    
    return ""


def truncate_for_read(content: str, offset: int = 1, limit: Optional[int] = None) -> TruncationResult:
    """Truncate for file reading - applies offset and limit first, then head truncation"""
    lines = content.split('\n')
    
    # Apply offset (convert to 0-indexed)
    start_idx = max(0, offset - 1)
    
    # Apply limit
    if limit is not None:
        end_idx = min(start_idx + limit, len(lines))
        selected = lines[start_idx:end_idx]
    else:
        selected = lines[start_idx:]
    
    content = '\n'.join(selected)
    
    # Apply head truncation
    result = truncate_head(content)
    
    # Adjust line numbers
    if result.truncated:
        result.next_offset = start_idx + result.output_lines + 1
    
    return result


def truncate_for_bash(content: str) -> TruncationResult:
    """Truncate for bash output - uses tail truncation"""
    return truncate_tail(content)
