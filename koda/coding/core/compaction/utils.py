"""
Compaction Utilities
等效于 Pi-Mono 的 packages/coding-agent/src/core/compaction/utils.ts

压缩相关的工具函数。
"""

import re
from typing import List, Dict, Any, Optional


def estimate_tokens(text: str) -> int:
    """
    估计token数量
    
    使用简单的启发式算法：
    - 英文单词约0.75 tokens
    - 中文字符约1 token
    - 代码和特殊字符约1 token
    
    Args:
        text: 输入文本
    
    Returns:
        估计的token数
    
    Example:
        >>> estimate_tokens("Hello world")
        3
    """
    if not text:
        return 0
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    
    # 统计英文单词
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    
    # 统计数字
    numbers = len(re.findall(r'\d+', text))
    
    # 统计特殊字符（代码符号等）
    special_chars = len(re.findall(r'[^\w\s]', text))
    
    # 估算公式
    estimated = (
        chinese_chars * 1.0 +  # 中文字符
        english_words * 1.3 +  # 英文单词（平均长度）
        numbers * 1.0 +        # 数字
        special_chars * 0.5    # 特殊字符
    )
    
    return int(estimated) + 1  # +1 for overhead


def calculate_tokens(messages: List[Dict[str, Any]], 
                    token_calculator: Optional[callable] = None) -> int:
    """
    计算消息列表的总token数
    
    Args:
        messages: 消息列表
        token_calculator: 自定义token计算函数
    
    Returns:
        总token数
    """
    if token_calculator:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += token_calculator(content)
            elif isinstance(content, list):
                # Handle multi-part content
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += token_calculator(part["text"])
        return total
    
    # Use estimation
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if "text" in part:
                        total += estimate_tokens(part["text"])
    
    # Add overhead for message format
    return total + len(messages) * 4


def should_compact(messages: List[Dict[str, Any]], 
                   max_tokens: int,
                   threshold: float = 0.8) -> bool:
    """
    判断是否需要压缩
    
    Args:
        messages: 消息列表
        max_tokens: 最大token限制
        threshold: 压缩触发阈值（比例）
    
    Returns:
        是否需要压缩
    """
    current_tokens = calculate_tokens(messages)
    return current_tokens >= max_tokens * threshold


def truncate_text(text: str, max_tokens: int, 
                  suffix: str = "...") -> str:
    """
    截断文本到指定token数
    
    Args:
        text: 原始文本
        max_tokens: 最大token数
        suffix: 截断后缀
    
    Returns:
        截断后的文本
    """
    if estimate_tokens(text) <= max_tokens:
        return text
    
    # Binary search for truncation point
    low, high = 0, len(text)
    while low < high:
        mid = (low + high) // 2
        truncated = text[:mid] + suffix
        if estimate_tokens(truncated) <= max_tokens:
            low = mid + 1
        else:
            high = mid
    
    return text[:low-1] + suffix


def extract_key_points(text: str, max_points: int = 5) -> List[str]:
    """
    提取关键点
    
    Args:
        text: 文本内容
        max_points: 最大点数
    
    Returns:
        关键点列表
    """
    # Simple extraction based on sentence structure
    sentences = re.split(r'[.!?。！？]\s+', text)
    
    # Score sentences by importance (length, keywords)
    scored = []
    for sent in sentences:
        if len(sent) < 10:  # Skip very short sentences
            continue
        
        score = 0
        # Length factor
        score += min(len(sent) / 50, 2)
        
        # Keyword indicators
        indicators = ["important", "key", "critical", "main", "总结", "关键", "重要"]
        for indicator in indicators:
            if indicator.lower() in sent.lower():
                score += 1
        
        scored.append((score, sent))
    
    # Sort by score and return top points
    scored.sort(reverse=True)
    return [s for _, s in scored[:max_points]]


def format_summary(title: str, points: List[str], 
                   metadata: Optional[Dict] = None) -> str:
    """
    格式化摘要
    
    Args:
        title: 摘要标题
        points: 要点列表
        metadata: 元数据
    
    Returns:
        格式化的摘要文本
    """
    lines = [f"## {title}"]
    
    if metadata:
        lines.append("")
        for key, value in metadata.items():
            lines.append(f"- **{key}**: {value}")
    
    lines.append("")
    lines.append("### Key Points")
    lines.append("")
    
    for i, point in enumerate(points, 1):
        lines.append(f"{i}. {point}")
    
    return "\n".join(lines)


def compact_tool_result(content: str, max_length: int = 500) -> str:
    """
    压缩工具结果
    
    Args:
        content: 工具输出内容
        max_length: 最大长度
    
    Returns:
        压缩后的内容
    """
    if len(content) <= max_length:
        return content
    
    # For code/errors, try to preserve structure
    lines = content.split("\n")
    
    if len(lines) > 50:
        # Keep first 20 and last 10 lines
        header = "\n".join(lines[:20])
        footer = "\n".join(lines[-10:])
        return f"{header}\n\n... ({len(lines) - 30} lines omitted) ...\n\n{footer}"
    
    # Simple truncation with ellipsis
    return content[:max_length] + "..."


def calculate_message_importance(message: Dict[str, Any]) -> int:
    """
    计算消息重要性分数
    
    Args:
        message: 消息字典
    
    Returns:
        重要性分数 (0-100)
    """
    score = 50  # Base score
    
    role = message.get("role", "")
    content = str(message.get("content", ""))
    
    # Role-based scoring
    if role == "system":
        score += 30
    elif role == "user":
        score += 20
    elif role == "assistant":
        if "tool_calls" in message or "function_call" in message:
            score += 25  # Tool calls are important
        score += 10
    elif role == "tool":
        if "error" in content.lower():
            score += 20  # Errors are important
        score += 15
    
    # Content-based scoring
    if len(content) < 50:
        score -= 10  # Very short messages less important
    
    # Keywords
    important_keywords = ["error", "fail", "success", "complete", "result", "重要"]
    for keyword in important_keywords:
        if keyword.lower() in content.lower():
            score += 5
    
    return min(100, max(0, score))


__all__ = [
    "estimate_tokens",
    "calculate_tokens",
    "should_compact",
    "truncate_text",
    "extract_key_points",
    "format_summary",
    "compact_tool_result",
    "calculate_message_importance",
]
