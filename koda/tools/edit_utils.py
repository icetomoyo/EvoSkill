"""
Edit Utilities - Edit 工具辅助函数

实现 Pi Coding Agent 的编辑功能：
- BOM 处理
- 行尾检测和保留
- 模糊匹配（包括 Unicode 规范化、trailing whitespace 处理）
- Diff 生成
"""
import re
from typing import Tuple, Optional, List
from dataclasses import dataclass


# BOM 常量
BOM_UTF8 = '\ufeff'

# Unicode 规范化映射
FUZZY_CHAR_MAPPINGS = {
    '\u2018': "'", '\u2019': "'",  # Smart single quotes
    '\u201c': '"', '\u201d': '"',  # Smart double quotes
    '\u2013': '-', '\u2014': '-', '\u2010': '-', '\u2011': '-',  # Dashes
    '\u00a0': ' ', '\u2002': ' ', '\u2003': ' ', '\u2009': ' ', '\u202f': ' ',  # Spaces
}


@dataclass
class BOMResult:
    bom: str
    text: str


def strip_bom(content: str) -> BOMResult:
    """移除 BOM"""
    if content.startswith(BOM_UTF8):
        return BOMResult(bom=BOM_UTF8, text=content[len(BOM_UTF8):])
    return BOMResult(bom="", text=content)


def detect_line_ending(content: str) -> str:
    """检测行尾类型"""
    if '\r\n' in content:
        return '\r\n'
    elif '\r' in content:
        return '\r'
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


def normalize_unicode_chars(text: str) -> str:
    """将 Unicode 特殊字符规范化为 ASCII 等价物"""
    for unicode_char, ascii_char in FUZZY_CHAR_MAPPINGS.items():
        text = text.replace(unicode_char, ascii_char)
    return text


def normalize_line_for_fuzzy(line: str) -> str:
    """规范化单行文本用于模糊匹配"""
    line = normalize_unicode_chars(line)
    line = line.rstrip()  # 移除尾部空白
    line = re.sub(r'[ \t]+', ' ', line)  # 规范化内部空白
    return line


@dataclass
class FuzzyMatchResult:
    """模糊匹配结果"""
    found: bool
    index: int = 0
    match_length: int = 0
    content_for_replacement: str = ""
    replacement: str = ""  # 用于模糊匹配后的替换内容


def fuzzy_find_with_replacement(content: str, search_text: str, replacement_text: str) -> FuzzyMatchResult:
    """
    模糊查找文本并准备替换
    
    这是 Pi 的编辑工具的核心功能。它支持：
    - Unicode 字符规范化（智能引号、破折号等）
    - 尾部空白处理
    - 多行匹配
    
    Args:
        content: 原始内容（已规范化到 LF）
        search_text: 要查找的文本（已规范化到 LF）
        replacement_text: 替换文本（已规范化到 LF）
        
    Returns:
        FuzzyMatchResult，其中 replacement 是实际应该写入的内容
    """
    # 1. 首先尝试精确匹配
    if search_text in content:
        idx = content.index(search_text)
        return FuzzyMatchResult(
            found=True,
            index=idx,
            match_length=len(search_text),
            content_for_replacement=content,
            replacement=content[:idx] + replacement_text + content[idx + len(search_text):]
        )
    
    # 2. 尝试模糊匹配
    content_lines = content.split('\n')
    search_lines = search_text.split('\n')
    
    # 移除搜索文本末尾的空行（如果存在）
    if search_lines and search_lines[-1] == '':
        search_lines = search_lines[:-1]
    
    # 规范化所有行
    norm_content_lines = [normalize_line_for_fuzzy(line) for line in content_lines]
    norm_search_lines = [normalize_line_for_fuzzy(line) for line in search_lines]
    
    # 规范化后的搜索文本（用于多行匹配）
    norm_search_text = '\n'.join(norm_search_lines).strip()
    
    # 尝试行级别的匹配
    for start_idx in range(len(content_lines) - len(search_lines) + 1):
        match = True
        for i, search_line in enumerate(norm_search_lines):
            if search_line != norm_content_lines[start_idx + i]:
                match = False
                break
        
        if match:
            # 找到匹配！计算原始内容中的位置
            # 匹配的结束位置是 start_idx + len(search_lines) 行
            end_idx = start_idx + len(search_lines)
            
            # 构建替换后的内容
            before = '\n'.join(content_lines[:start_idx])
            after_lines = content_lines[end_idx:]
            # 移除末尾的空行（如果存在）
            if after_lines and after_lines[-1] == '':
                after_lines = after_lines[:-1]
            after = '\n'.join(after_lines)
            
            # 组合结果（保留适当的换行符）
            result_parts = []
            if before:
                result_parts.append(before)
            result_parts.append(replacement_text.rstrip('\n'))
            if after:
                result_parts.append(after)
            
            new_content = '\n'.join(result_parts)
            
            # 确保结果以换行符结尾（如果原始内容以换行符结尾）
            if content.endswith('\n') and not new_content.endswith('\n'):
                new_content += '\n'
            
            # 计算匹配的起始字符位置
            start_pos = sum(len(content_lines[i]) + 1 for i in range(start_idx))
            end_pos = sum(len(content_lines[i]) + 1 for i in range(end_idx))
            
            return FuzzyMatchResult(
                found=True,
                index=start_pos,
                match_length=end_pos - start_pos,
                content_for_replacement=content,
                replacement=new_content
            )
    
    # 3. 尝试整内容模糊匹配（简化情况）
    norm_content = '\n'.join(norm_content_lines).strip()
    if norm_search_text in norm_content:
        # 找到模糊匹配，但无法精确定位，返回整个内容作为替换基础
        return FuzzyMatchResult(
            found=True,
            index=0,
            match_length=len(content),
            content_for_replacement=content,
            replacement=replacement_text
        )
    
    return FuzzyMatchResult(found=False)


def count_occurrences(content: str, search_text: str) -> int:
    """统计 occurrences 数量（使用模糊匹配逻辑）"""
    content_lines = content.split('\n')
    search_lines = search_text.split('\n')
    
    # 移除搜索文本末尾的空行（如果存在）
    if search_lines and search_lines[-1] == '':
        search_lines = search_lines[:-1]
    
    norm_content_lines = [normalize_line_for_fuzzy(line) for line in content_lines]
    norm_search_lines = [normalize_line_for_fuzzy(line) for line in search_lines]
    
    if not norm_search_lines:
        return 0
    
    # 对于单行搜索，在内容中搜索（支持跨行边界）
    if len(norm_search_lines) == 1:
        search_term = norm_search_lines[0]
        if not search_term:
            return 0
        # 在整个规范化内容中搜索
        norm_content = ' '.join(norm_content_lines)  # 用空格连接以模拟词边界
        return norm_content.count(search_term)
    
    # 对于多行搜索，使用滑动窗口
    count = 0
    for start_idx in range(len(content_lines) - len(search_lines) + 1):
        match = True
        for i, search_line in enumerate(norm_search_lines):
            if search_line != norm_content_lines[start_idx + i]:
                match = False
                break
        if match:
            count += 1
    
    return count


@dataclass
class DiffResult:
    diff: str
    first_changed_line: Optional[int] = None


def generate_diff(old_content: str, new_content: str, context: int = 3) -> DiffResult:
    """生成统一格式的 diff"""
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    diff_lines = []
    first_changed = None
    
    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None
        
        if old_line != new_line:
            if first_changed is None:
                first_changed = i + 1
            
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
    return DiffResult(diff=diff_text, first_changed_line=first_changed)
