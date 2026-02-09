"""
File Tool - 文件操作工具

Pi-compatible 文件操作：
- read: 读取文件内容，支持 offset/limit，支持图片
- write: 写入文件，自动创建目录
- edit: 精确文本替换编辑，支持 BOM、行尾、模糊匹配
"""
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor

from koda.tools._support.truncation import truncate_head, format_size
from koda.tools.edit_utils import (
    strip_bom, detect_line_ending, normalize_to_lf, restore_line_endings,
    fuzzy_find_with_replacement, count_occurrences, generate_diff
)
from koda.tools._support.image_resize import resize_image, format_dimension_note, PIL_AVAILABLE
from koda.tools._support.multimodal_types import ImageContent, TextContent


@dataclass
class ReadResult:
    """读取结果"""
    content: str
    path: str
    start_line: int
    end_line: int
    truncated: bool
    next_offset: int
    is_image: bool = False
    image_data: Optional[str] = None  # base64 encoded
    mime_type: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """是否成功（兼容 Pi 风格）"""
        return self.error is None


@dataclass
class EditResult:
    """编辑结果"""
    success: bool
    path: str
    diff: Optional[str] = None
    first_changed_line: Optional[int] = None
    error: Optional[str] = None


@dataclass
class WriteResult:
    """写入结果"""
    success: bool
    path: str
    bytes_written: int = 0
    error: Optional[str] = None


# 图片文件魔数 (Magic Numbers)
IMAGE_MAGIC_NUMBERS = [
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'\xff\xd8\xff', 'image/jpeg'),  # JPEG/JPG
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
    (b'RIFF', 'image/webp'),  # WebP starts with RIFF....WEBP
]


def detect_image_mime_type_from_magic(file_path: Path) -> Optional[str]:
    """
    通过文件魔数检测图片 MIME 类型
    
    这是 Pi 的方式：通过文件内容检测，而不是扩展名。
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)  # 读取前32字节
        
        for magic, mime_type in IMAGE_MAGIC_NUMBERS:
            if header.startswith(magic):
                # 特殊处理 WebP
                if mime_type == 'image/webp':
                    if b'WEBP' in header[:12]:
                        return mime_type
                else:
                    return mime_type
        
        return None
    except Exception:
        return None


class FileTool:
    """
    Pi-compatible 文件工具
    
    支持：
    - 读取（带 offset/limit，支持图片）
    - 写入（自动创建目录）
    - 编辑（精确文本替换 + 模糊匹配 + BOM/行尾处理）
    """
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        target = Path(path)
        if not target.is_absolute():
            target = self.base_path / target
        return target.resolve()
    
    async def read(
        self,
        path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        auto_resize_images: bool = True,
    ) -> ReadResult:
        """
        读取文件内容（Pi-compatible）
        
        Args:
            path: 文件路径
            offset: 起始行号（1-indexed）
            limit: 最大读取行数
            auto_resize_images: 是否自动调整图片大小
            
        Returns:
            ReadResult
        """
        def _read():
            try:
                target = self._resolve_path(path)
                
                if not target.exists():
                    return ReadResult(
                        content="",
                        path=str(target),
                        start_line=0,
                        end_line=0,
                        truncated=False,
                        next_offset=0,
                        error=f"File not found: {path}"
                    )
                
                if not target.is_file():
                    return ReadResult(
                        content="",
                        path=str(target),
                        start_line=0,
                        end_line=0,
                        truncated=False,
                        next_offset=0,
                        error=f"Not a file: {path}"
                    )
                
                # 检测是否是图片（通过文件魔数）
                mime_type = detect_image_mime_type_from_magic(target)
                
                if mime_type:
                    # 读取图片（Pi 方式）
                    with open(target, 'rb') as f:
                        image_bytes = f.read()
                    
                    base64_data = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # 图片调整大小（Pi 兼容：2000x2000, 4.5MB）
                    dimension_note = ""
                    if auto_resize_images and PIL_AVAILABLE:
                        resized = resize_image(base64_data, mime_type)
                        if resized.wasResized:
                            base64_data = resized.data
                            mime_type = resized.mimeType
                            note = format_dimension_note(resized)
                            if note:
                                dimension_note = f"\n{note}"
                    
                    return ReadResult(
                        content=f"Read image file [{mime_type}]{dimension_note}",
                        path=str(target),
                        start_line=0,
                        end_line=0,
                        truncated=False,
                        next_offset=0,
                        is_image=True,
                        image_data=base64_data,
                        mime_type=mime_type,
                    )
                
                # 读取文本文件
                with open(target, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # 处理 offset 和 limit
                lines = content.split('\n')
                total_lines = len(lines)
                
                # 计算起始和结束
                start_idx = max(0, (offset or 1) - 1)  # offset 是 1-indexed
                
                # 检查 offset 是否超出范围
                if start_idx >= total_lines:
                    return ReadResult(
                        content=f"",
                        path=str(target),
                        start_line=0,
                        end_line=0,
                        truncated=False,
                        next_offset=0,
                        error=f"Offset {offset} is beyond end of file ({total_lines} lines total)"
                    )
                
                end_idx = total_lines
                
                if limit is not None:
                    end_idx = min(start_idx + limit, total_lines)
                
                # 提取内容
                selected_lines = lines[start_idx:end_idx]
                selected_content = '\n'.join(selected_lines)
                
                # 应用截断
                truncated_result = truncate_head(selected_content)
                
                # 计算实际行号
                actual_start = start_idx + 1  # 1-indexed
                actual_end = start_idx + truncated_result.output_lines
                
                # 构建输出
                output_text = truncated_result.content
                
                if truncated_result.first_line_exceeds_limit:
                    first_line_size = len(lines[start_idx].encode('utf-8'))
                    output_text = f"[Line {actual_start} is {format_size(first_line_size)}, exceeds limit. Use bash: sed -n '{actual_start}p' {path} | head -c {truncated_result.max_bytes}]"
                elif truncated_result.truncated:
                    next_offset = actual_end + 1
                    if truncated_result.truncated_by == "lines":
                        output_text += f"\n\n[Showing lines {actual_start}-{actual_end} of {total_lines}. Use offset={next_offset} to continue.]"
                    else:
                        output_text += f"\n\n[Showing lines {actual_start}-{actual_end} of {total_lines} (limit). Use offset={next_offset} to continue.]"
                elif limit is not None and end_idx < total_lines:
                    remaining = total_lines - end_idx
                    next_offset = end_idx + 1
                    output_text += f"\n\n[{remaining} more lines in file. Use offset={next_offset} to continue.]"
                
                return ReadResult(
                    content=output_text,
                    path=str(target),
                    start_line=actual_start,
                    end_line=actual_end,
                    truncated=truncated_result.truncated,
                    next_offset=actual_end + 1 if truncated_result.truncated else 0,
                )
                
            except Exception as e:
                return ReadResult(
                    content="",
                    path=path,
                    start_line=0,
                    end_line=0,
                    truncated=False,
                    next_offset=0,
                    error=str(e)
                )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, _read)
    
    async def write(self, path: str, content: str) -> WriteResult:
        """
        写入文件
        
        Args:
            path: 文件路径
            content: 文件内容
            
        Returns:
            WriteResult
        """
        def _write():
            try:
                target = self._resolve_path(path)
                
                # 创建父目录
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # 写入文件
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                bytes_written = len(content.encode('utf-8'))
                
                return WriteResult(
                    success=True,
                    path=str(target),
                    bytes_written=bytes_written,
                )
                
            except Exception as e:
                return WriteResult(
                    success=False,
                    path=path,
                    error=str(e)
                )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, _write)
    
    async def edit(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> EditResult:
        """
        编辑文件 - Pi-compatible 实现
        
        特性：
        - BOM 处理
        - 行尾检测和保留
        - 模糊匹配回退（包括 Unicode 规范化）
        - 多 occurrences 检测
        - Diff 生成
        
        Args:
            path: 文件路径
            old_text: 要替换的文本（精确匹配优先）
            new_text: 新文本
            
        Returns:
            EditResult
        """
        def _edit():
            try:
                target = self._resolve_path(path)
                
                if not target.exists():
                    return EditResult(
                        success=False,
                        path=str(target),
                        error=f"File not found: {path}"
                    )
                
                # 读取文件
                with open(target, 'r', encoding='utf-8', errors='replace') as f:
                    raw_content = f.read()
                
                # 1. 处理 BOM
                bom_result = strip_bom(raw_content)
                bom = bom_result.bom
                content = bom_result.text
                
                # 2. 检测并保存原始行尾
                original_ending = detect_line_ending(content)
                
                # 3. 规范化到 LF 进行匹配
                normalized_content = normalize_to_lf(content)
                normalized_old_text = normalize_to_lf(old_text)
                normalized_new_text = normalize_to_lf(new_text)
                
                # 4. 检测多 occurrences（使用模糊匹配逻辑）
                occurrences = count_occurrences(normalized_content, normalized_old_text)
                if occurrences > 1:
                    return EditResult(
                        success=False,
                        path=str(target),
                        error=f"Found {occurrences} occurrences of the text in {path}. The text must be unique. Please provide more context to make it unique."
                    )
                
                # 5. 模糊查找文本并准备替换（包括 Unicode 规范化、trailing whitespace 处理）
                match_result = fuzzy_find_with_replacement(
                    normalized_content, 
                    normalized_old_text,
                    normalized_new_text
                )
                
                if not match_result.found:
                    return EditResult(
                        success=False,
                        path=str(target),
                        error=f"Could not find the exact text in {path}. The old text must match exactly including all whitespace and newlines."
                    )
                
                # 6. 使用模糊匹配返回的替换内容
                base_content = match_result.content_for_replacement
                new_content = match_result.replacement
                
                # 7. 验证替换是否产生了变化
                if base_content == new_content:
                    return EditResult(
                        success=False,
                        path=str(target),
                        error=f"No changes made to {path}. The replacement produced identical content."
                    )
                
                # 8. 恢复行尾和 BOM
                final_content = bom + restore_line_endings(new_content, original_ending)
                
                # 9. 写回文件
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                
                # 10. 生成 diff
                diff_result = generate_diff(base_content, new_content)
                
                return EditResult(
                    success=True,
                    path=str(target),
                    diff=diff_result.diff,
                    first_changed_line=diff_result.first_changed_line,
                )
                
            except Exception as e:
                return EditResult(
                    success=False,
                    path=path,
                    error=str(e)
                )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, _edit)
    
    async def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        try:
            target = self._resolve_path(path)
            return target.exists()
        except:
            return False
    
    async def is_directory(self, path: str) -> bool:
        """检查是否是目录"""
        try:
            target = self._resolve_path(path)
            return target.is_dir()
        except:
            return False
    
    def to_content_blocks(self, read_result: ReadResult) -> list:
        """
        Convert ReadResult to Pi-compatible content blocks for LLM
        
        Returns list of TextContent/ImageContent blocks
        """
        if read_result.is_image and read_result.image_data:
            # Return text note + image
            return [
                TextContent(type="text", text=read_result.content),
                ImageContent(
                    type="image",
                    data=read_result.image_data,
                    mimeType=read_result.mime_type or "image/png"
                )
            ]
        else:
            # Return text only
            return [TextContent(type="text", text=read_result.content)]


# Convenience function for direct use
async def read_file_for_llm(
    path: str,
    base_path: Path = None,
    offset: int = None,
    limit: int = None
) -> list:
    """
    Read a file and return Pi-compatible content blocks
    
    Returns:
        List of TextContent/ImageContent blocks ready for LLM
    """
    tool = FileTool(base_path)
    result = await tool.read(path, offset=offset, limit=limit)
    
    if result.error:
        return [TextContent(type="text", text=f"Error reading file: {result.error}")]
    
    return tool.to_content_blocks(result)
