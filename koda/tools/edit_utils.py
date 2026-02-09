"""
Edit Utilities - Edit 工具辅助函数

实现 Pi Coding Agent 的编辑功能：
- BOM 处理
- 行尾检测和保留
- 模糊匹配
- Diff 生成
"""
import re
from typing import Tuple, Optional, List
from dataclasses import dataclass


# BOM 常量
BOM_UTF8 = '\ufeff'
BOM_UTF16_LE = b'\xff\xfe'
BOM_UTF16_BE = b'\xfe\xff'


@dataclass
class BOMResult:
    """BOM 处理结果"""
    bom: str
    text: str


def strip_bom(content: str) -> BOMResult:
    """
    移除 BOM (Byte Order Mark)
    
    LLM 不会在 old_text 中包含 BOM，所以需要在匹配前移除。
    """
    if content.startswith(BOM_UTF8):
        return BOMResult(bom=BOM_UTF8, text=content[len(BOM_UTF8):])
    return BOMResult(bom="", text=content)


def detect_line_ending(content: str) -> str:
    """
    检测行尾类型
    
    Returns:
        '\r\n' for CRLF (Windows)
        '\n' for LF (Unix/Mac)
        '\r' for CR (old Mac)
    """
    if '\r\n' in content:
        return '\r\n'
    elif '\r' in content:
        return '\r'
    else:
        return '\n'


def normalize_to_lf(content: str) -> str:
    """将所有行尾规范化为 LF"""
    return content.replace('\r\n', '\n').replace('\r', '\n')


def restore_line_endings(content: str, original_ending: str) -> str:
    """恢复原始行尾"""
    if original_ending == '\r\n':
        return content.replace('\n', '\r\n')
    elif original_ending == '\r':
        return content.replace('\n', '\r')
    return content


def normalize_for_fuzzy_match(text: str) -> str:
    """
    为模糊匹配规范化文本
    
    - 移除首尾空白
    - 规范化内部空白（多个空格/制表符变为单个空格）
    """
    # 先规范化行尾
    text = normalize_to_lf(text)
    # 移除首尾空白
    text = text.strip()
    # 规范化内部空白
    text = re.sub(r'[ \t]+', ' ', text)
    return text


@dataclass
class FuzzyMatchResult:
    """模糊匹配结果"""
    found: bool
    index: int = 0
    match_length: int = 0
    content_for_replacement: str = ""


def fuzzy_find_text(content: str, search_text: str) -> FuzzyMatchResult:
    """
    模糊查找文本
    
    首先尝试精确匹配，然后尝试模糊匹配。
    
    Args:
        content: 原始内容（已规范化到 LF）
        search_text: 要查找的文本（已规范化到 LF）
        
    Returns:
        FuzzyMatchResult
    """
    # 1. 首先尝试精确匹配
    if search_text in content:
        return FuzzyMatchResult(
            found=True,
            index=content.index(search_text),
            match_length=len(search_text),
            content_for_replacement=content,
        )
    
    # 2. 尝试模糊匹配
    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_search = normalize_for_fuzzy_match(search_text)
    
    if fuzzy_search in fuzzy_content:
        # 找到模糊匹配，但需要映射回原始内容
        # 简化处理：返回整个内容作为替换基础
        return FuzzyMatchResult(
            found=True,
            index=0,  # 模糊匹配时无法确定精确位置
            match_length=len(content),
            content_for_replacement=content,
        )
    
    return FuzzyMatchResult(found=False)


def count_occurrences(content: str, search_text: str) -> int:
    """
    统计 occurrences 数量
    
    使用模糊匹配逻辑进行计数。
    """
    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_search = normalize_for_fuzzy_match(search_text)
    
    return fuzzy_content.count(fuzzy_search)


@dataclass
class DiffResult:
    """Diff 生成结果"""
    diff: str
    first_changed_line: Optional[int] = None


def generate_diff(old_content: str, new_content: str, context: int = 3) -> DiffResult:
    """
    生成统一格式的 diff
    
    Args:
        old_content: 原始内容
        new_content: 新内容
        context: 上下文行数
        
    Returns:
        DiffResult
    """
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    # 使用简单的行对比算法
    diff_lines = []
    first_changed = None
    
    # 找到第一个不同的行
    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None
        
        if old_line != new_line:
            if first_changed is None:
                first_changed = i + 1  # 1-indexed
            
            # 添加上下文
            start = max(0, i - context)
            end = min(max_len, i + context + 1)
            
            if diff_lines:
                diff_lines.append("...")
            
            for j in range(start, end):
                if j < len(old_lines) and j < len(new_lines):
                    if old_lines[j] != new_lines[j]:
                        diff_lines.append(f"-{old_lines[j]}")
                        diff_lines.append(f"+{new_lines[j]}")
                    else:
                        diff_lines.append(f" {old_lines[j]}")
                elif j < len(old_lines):
                    diff_lines.append(f"-{old_lines[j]}")
                else:
                    diff_lines.append(f"+{new_lines[j]}")
    
    diff_text = '\n'.join(diff_lines) if diff_lines else "No changes"
    
    return DiffResult(
        diff=diff_text,
        first_changed_line=first_changed,
    )


def generate_unified_diff(
    old_content: str,
    new_content: str,
    old_path: str = "a/file",
    new_path: str = "b/file",
) -> str:
    """
    生成标准 unified diff 格式
    
    类似于 `diff -u` 的输出。
    """
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    # 简化的 diff 算法
    result = [f"--- {old_path}", f"+++ {new_path}"]
    
    # 找到变更区域
    i = 0
    while i < max(len(old_lines), len(new_lines)):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None
        
        if old_line != new_line:
            # 找到变更块
            old_start = i
            new_start = i
            
            # 收集变更
            old_chunk = []
            new_chunk = []
            
            while i < max(len(old_lines), len(new_lines)):
                o = old_lines[i] if i < len(old_lines) else None
                n = new_lines[i] if i < len(new_lines) else None
                
                if o == n and len(old_chunk) > 0 and len(new_chunk) > 0:
                    break
                
                if o is not None:
                    old_chunk.append(o)
                if n is not None:
                    new_chunk.append(n)
                i += 1
            
            # 输出 hunk header
            old_count = len(old_chunk)
            new_count = len(new_chunk)
            result.append(f"@@ -{old_start + 1},{old_count} +{new_start + 1},{new_count} @@")
            
            # 输出变更行
            for line in old_chunk:
                result.append(f"-{line}")
            for line in new_chunk:
                result.append(f"+{line}")
        else:
            i += 1
    
    return '\n'.join(result)
