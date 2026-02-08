"""
Truncation - 内容截断处理

实现 Pi Coding Agent 的截断策略：
- 50KB / 2000行 限制
- 头部截断（保留开头）- 用于文件读取
- 尾部截断（保留末尾）- 用于命令输出
"""
from dataclasses import dataclass
from typing import Optional


# 默认限制
DEFAULT_MAX_BYTES = 50 * 1024  # 50KB
DEFAULT_MAX_LINES = 2000


@dataclass
class TruncationResult:
    """截断结果"""
    content: str
    truncated: bool
    truncated_by: Optional[str]  # "lines", "bytes", or None
    total_lines: int
    output_lines: int
    total_bytes: int
    output_bytes: int
    first_line_exceeds_limit: bool = False
    last_line_partial: bool = False
    next_offset: int = 0  # 用于继续读取


def truncate_head(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """
    头部截断 - 保留开头
    
    用于文件读取、搜索结果等场景。
    保留内容的开头部分，超出部分截断。
    
    Args:
        content: 原始内容
        max_lines: 最大行数
        max_bytes: 最大字节数
        
    Returns:
        TruncationResult
    """
    lines = content.split('\n')
    total_lines = len(lines)
    total_bytes = len(content.encode('utf-8'))
    
    # 检查是否需要截断
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            output_lines=total_lines,
            total_bytes=total_bytes,
            output_bytes=total_bytes,
            next_offset=0,
        )
    
    # 检查首行是否超过限制（单行长文本）
    if lines:
        first_line_bytes = len(lines[0].encode('utf-8'))
        if first_line_bytes > max_bytes:
            # 截取首行的一部分
            truncated_first = lines[0][:max_bytes // 4]  # 粗略估计
            return TruncationResult(
                content=truncated_first,
                truncated=True,
                truncated_by="bytes",
                total_lines=total_lines,
                output_lines=1,
                total_bytes=total_bytes,
                output_bytes=max_bytes,
                first_line_exceeds_limit=True,
                next_offset=2,  # 从第2行继续
            )
    
    # 按行截断
    if total_lines > max_lines:
        output_lines = lines[:max_lines]
        content_str = '\n'.join(output_lines)
        output_bytes = len(content_str.encode('utf-8'))
        
        # 计算 next_offset
        end_line = max_lines
        next_offset = end_line + 1
        
        return TruncationResult(
            content=content_str,
            truncated=True,
            truncated_by="lines",
            total_lines=total_lines,
            output_lines=max_lines,
            total_bytes=total_bytes,
            output_bytes=output_bytes,
            next_offset=next_offset,
        )
    
    # 按字节截断（在不超过行数限制的情况下）
    if total_bytes > max_bytes:
        bytes_count = 0
        line_count = 0
        
        for i, line in enumerate(lines):
            line_bytes = len(line.encode('utf-8')) + 1  # +1 for newline
            if bytes_count + line_bytes > max_bytes:
                break
            bytes_count += line_bytes
            line_count = i + 1
        
        output_lines = lines[:line_count]
        content_str = '\n'.join(output_lines)
        
        # 计算 next_offset
        next_offset = line_count + 1
        
        return TruncationResult(
            content=content_str,
            truncated=True,
            truncated_by="bytes",
            total_lines=total_lines,
            output_lines=line_count,
            total_bytes=total_bytes,
            output_bytes=bytes_count,
            next_offset=next_offset,
        )
    
    # 不应该到达这里
    return TruncationResult(
        content=content,
        truncated=False,
        truncated_by=None,
        total_lines=total_lines,
        output_lines=total_lines,
        total_bytes=total_bytes,
        output_bytes=total_bytes,
        next_offset=0,
    )


def truncate_tail(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """
    尾部截断 - 保留末尾
    
    用于命令输出、日志等场景。
    保留内容的最后部分（通常是更重要的）。
    
    Args:
        content: 原始内容
        max_lines: 最大行数
        max_bytes: 最大字节数
        
    Returns:
        TruncationResult
    """
    lines = content.split('\n')
    total_lines = len(lines)
    total_bytes = len(content.encode('utf-8'))
    
    # 检查是否需要截断
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            output_lines=total_lines,
            total_bytes=total_bytes,
            output_bytes=total_bytes,
            next_offset=0,
        )
    
    # 按行截断（从末尾开始）
    if total_lines > max_lines:
        start_idx = total_lines - max_lines
        output_lines = lines[start_idx:]
        content_str = '\n'.join(output_lines)
        output_bytes = len(content_str.encode('utf-8'))
        
        # 计算起始行号（用于提示）
        start_line_num = start_idx + 1  # 1-indexed
        
        return TruncationResult(
            content=content_str,
            truncated=True,
            truncated_by="lines",
            total_lines=total_lines,
            output_lines=max_lines,
            total_bytes=total_bytes,
            output_bytes=output_bytes,
            next_offset=start_line_num,
        )
    
    # 按字节截断（从末尾开始）
    if total_bytes > max_bytes:
        # 从末尾开始累加
        bytes_count = 0
        line_count = 0
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            line_bytes = len(line.encode('utf-8')) + 1  # +1 for newline
            
            if bytes_count + line_bytes > max_bytes:
                break
            
            bytes_count += line_bytes
            line_count += 1
        
        start_idx = len(lines) - line_count
        output_lines = lines[start_idx:]
        content_str = '\n'.join(output_lines)
        
        start_line_num = start_idx + 1
        
        return TruncationResult(
            content=content_str,
            truncated=True,
            truncated_by="bytes",
            total_lines=total_lines,
            output_lines=line_count,
            total_bytes=total_bytes,
            output_bytes=bytes_count,
            next_offset=start_line_num,
        )
    
    return TruncationResult(
        content=content,
        truncated=False,
        truncated_by=None,
        total_lines=total_lines,
        output_lines=total_lines,
        total_bytes=total_bytes,
        output_bytes=total_bytes,
        next_offset=0,
    )


def format_truncation_message(result: TruncationResult, mode: str = "head") -> str:
    """
    格式化截断提示信息
    
    Args:
        result: 截断结果
        mode: "head" 或 "tail"
        
    Returns:
        提示信息
    """
    if not result.truncated:
        return ""
    
    if mode == "head":
        # 头部截断提示
        if result.truncated_by == "lines":
            return (
                f"\n\n[Showing lines 1-{result.output_lines} of {result.total_lines}. "
                f"Use offset={result.next_offset} to continue.]"
            )
        elif result.truncated_by == "bytes":
            return (
                f"\n\n[Showing {result.output_bytes // 1024}KB of {result.total_bytes // 1024}KB. "
                f"Use offset={result.next_offset} to continue.]"
            )
    else:
        # 尾部截断提示
        if result.truncated_by == "lines":
            return (
                f"\n\n[Showing lines {result.next_offset}-{result.total_lines} of {result.total_lines}. "
                f"Full output in temporary file.]"
            )
        elif result.truncated_by == "bytes":
            return (
                f"\n\n[Showing last {result.output_bytes // 1024}KB of {result.total_bytes // 1024}KB. "
                f"Full output in temporary file.]"
            )
    
    return ""


# 便捷函数
def truncate_for_read(content: str, offset: int = 1, limit: Optional[int] = None) -> TruncationResult:
    """
    为文件读取截断
    
    应用 offset 和 limit，然后进行头部截断。
    
    Args:
        content: 原始内容
        offset: 起始行号（1-indexed）
        limit: 限制行数
        
    Returns:
        TruncationResult
    """
    lines = content.split('\n')
    
    # 应用 offset（转为 0-indexed）
    start_idx = max(0, offset - 1)
    
    # 应用 limit
    if limit is not None:
        end_idx = min(start_idx + limit, len(lines))
        selected = lines[start_idx:end_idx]
    else:
        selected = lines[start_idx:]
    
    content = '\n'.join(selected)
    
    # 再进行头部截断
    result = truncate_head(content)
    
    # 调整行号统计
    if result.truncated:
        result.next_offset = start_idx + result.output_lines + 1
    
    return result


def truncate_for_bash(content: str) -> TruncationResult:
    """
    为命令输出截断
    
    使用尾部截断，保留最后部分。
    """
    return truncate_tail(content)
