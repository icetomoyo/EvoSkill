"""
EditTool - 精确文本编辑工具

Pi Coding Agent 的核心工具之一。
实现模糊匹配 + 精确替换的编辑策略。
"""
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
from pathlib import Path


@dataclass
class EditResult:
    """编辑结果"""
    success: bool
    message: str
    diff: str
    first_changed_line: int


class EditTool:
    """
    精确文本编辑工具
    
    特点：
    1. 模糊匹配 - 处理空白字符差异
    2. 精确替换 - old_text 必须匹配
    3. 换行符保留 - 检测并保留原始换行符
    4. BOM 处理 - 检测并保留 UTF-8 BOM
    5. 重复检测 - 检测多个匹配位置
    
    Example:
        tool = EditTool("/workspace")
        result = await tool.edit(
            "main.py",
            old_text="def hello():\\n    print('hello')",
            new_text="def hello():\\n    print('hello world')"
        )
    """
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
    
    async def edit(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> EditResult:
        """
        编辑文件
        
        Args:
            path: 文件路径
            old_text: 要查找的文本（必须精确匹配）
            new_text: 替换后的文本
            
        Returns:
            EditResult
        """
        file_path = self._resolve_path(path)
        
        # 检查文件存在
        if not file_path.exists():
            return EditResult(
                success=False,
                message=f"File not found: {path}",
                diff="",
                first_changed_line=0,
            )
        
        # 读取文件
        try:
            raw_content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return EditResult(
                success=False,
                message=f"Failed to read file: {e}",
                diff="",
                first_changed_line=0,
            )
        
        # 处理 BOM
        bom, content = self._strip_bom(raw_content)
        
        # 检测换行符
        original_line_ending = self._detect_line_ending(content)
        
        # 统一转换为 LF 进行匹配
        normalized_content = self._normalize_to_lf(content)
        normalized_old = self._normalize_to_lf(old_text)
        normalized_new = self._normalize_to_lf(new_text)
        
        # 模糊查找
        match_result = self._fuzzy_find(normalized_content, normalized_old)
        
        if not match_result.found:
            # 未找到匹配
            return EditResult(
                success=False,
                message=f"Could not find the exact text in {path}.\n"
                        f"The old_text must match exactly (including whitespace).\n"
                        f"Please read the file first to see the exact content.",
                diff="",
                first_changed_line=0,
            )
        
        # 检查重复匹配
        fuzzy_content = self._normalize_for_fuzzy(normalized_content)
        fuzzy_old = self._normalize_for_fuzzy(normalized_old)
        occurrences = fuzzy_content.count(fuzzy_old)
        
        if occurrences > 1:
            return EditResult(
                success=False,
                message=f"Found {occurrences} occurrences of the text in {path}.\n"
                        f"The old_text must be unique. Please provide more context to make it unique.",
                diff="",
                first_changed_line=0,
            )
        
        # 执行替换
        base = match_result.content_for_replacement
        idx = match_result.index
        match_len = match_result.match_length
        
        new_content = base[:idx] + normalized_new + base[idx + match_len:]
        
        # 验证变更
        if base == new_content:
            return EditResult(
                success=False,
                message=f"No changes made to {path}. The old_text and new_text are identical.",
                diff="",
                first_changed_line=0,
            )
        
        # 恢复换行符
        final_content = bom + self._restore_line_endings(new_content, original_line_ending)
        
        # 写回文件
        try:
            file_path.write_text(final_content, encoding='utf-8')
        except Exception as e:
            return EditResult(
                success=False,
                message=f"Failed to write file: {e}",
                diff="",
                first_changed_line=0,
            )
        
        # 生成 diff
        diff_str, first_line = self._generate_diff(
            self._restore_line_endings(base, original_line_ending),
            self._restore_line_endings(new_content, original_line_ending),
        )
        
        return EditResult(
            success=True,
            message=f"Successfully replaced text in {path}.",
            diff=diff_str,
            first_changed_line=first_line,
        )
    
    # ============ 辅助方法 ============
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        if Path(path).is_absolute():
            return Path(path)
        return self.base_path / path
    
    def _strip_bom(self, content: str) -> Tuple[str, str]:
        """去除 BOM"""
        if content.startswith('\ufeff'):
            return '\ufeff', content[1:]
        return '', content
    
    def _detect_line_ending(self, content: str) -> str:
        """检测换行符类型"""
        if '\r\n' in content:
            return '\r\n'  # Windows
        return '\n'  # Unix/Mac
    
    def _normalize_to_lf(self, text: str) -> str:
        """统一换行符为 LF"""
        return text.replace('\r\n', '\n')
    
    def _restore_line_endings(self, text: str, ending: str) -> str:
        """恢复原始换行符"""
        if ending == '\r\n':
            return text.replace('\n', '\r\n')
        return text
    
    def _normalize_for_fuzzy(self, text: str) -> str:
        """
        为模糊匹配规范化文本
        
        处理：
        - 多空格转为单空格
        - 去除行首尾空白
        """
        # 多空格转为单空格
        text = re.sub(r' +', ' ', text)
        # 去除行首尾空白
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    def _fuzzy_find(self, content: str, old_text: str) -> "MatchResult":
        """
        模糊查找文本
        
        策略：
        1. 先尝试精确匹配
        2. 再尝试忽略首尾空白匹配
        3. 最后尝试规范化后匹配
        """
        # 1. 精确匹配
        if old_text in content:
            idx = content.index(old_text)
            return MatchResult(
                found=True,
                index=idx,
                match_length=len(old_text),
                content_for_replacement=content,
            )
        
        # 2. 忽略每行首尾空白匹配
        content_lines = content.split('\n')
        old_lines = old_text.split('\n')
        
        for i in range(len(content_lines) - len(old_lines) + 1):
            match = True
            for j, old_line in enumerate(old_lines):
                content_line = content_lines[i + j]
                # 比较去除首尾空白后的内容
                if content_line.strip() != old_line.strip():
                    match = False
                    break
            
            if match:
                # 计算在原始内容中的位置
                start_pos = sum(len(line) + 1 for line in content_lines[:i])
                end_pos = sum(len(line) + 1 for line in content_lines[:i + len(old_lines)]) - 1
                
                return MatchResult(
                    found=True,
                    index=start_pos,
                    match_length=end_pos - start_pos,
                    content_for_replacement=content,
                )
        
        # 3. 未找到
        return MatchResult(found=False, index=0, match_length=0, content_for_replacement=content)
    
    def _generate_diff(self, old: str, new: str) -> Tuple[str, int]:
        """
        生成简单的 diff 字符串
        
        Returns:
            (diff_str, first_changed_line)
        """
        old_lines = old.split('\n')
        new_lines = new.split('\n')
        
        # 找出第一个变更的行
        first_changed = 0
        for i, (o, n) in enumerate(zip(old_lines, new_lines)):
            if o != n:
                first_changed = i + 1  # 1-indexed
                break
        
        # 生成统一格式 diff（简化版）
        diff_lines = []
        diff_lines.append("--- old")
        diff_lines.append("+++ new")
        
        # 找到变更范围
        max_len = max(len(old_lines), len(new_lines))
        for i in range(max_len):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None
            
            if old_line != new_line:
                if old_line is not None:
                    diff_lines.append(f"-{old_line}")
                if new_line is not None:
                    diff_lines.append(f"+{new_line}")
            else:
                diff_lines.append(f" {old_line}")
        
        return '\n'.join(diff_lines), first_changed


@dataclass
class MatchResult:
    """匹配结果"""
    found: bool
    index: int
    match_length: int
    content_for_replacement: str
