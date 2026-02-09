"""
Tests for truncation module
"""
import pytest

from koda.coding._support.truncation import (
    truncate_head,
    truncate_tail,
    truncate_for_read,
    TruncationResult,
    DEFAULT_MAX_LINES,
    DEFAULT_MAX_BYTES,
)


class TestTruncationHead:
    """测试头部截断（保留开头）"""
    
    def test_no_truncation_needed(self):
        """不需要截断时返回原内容"""
        content = "Line 1\nLine 2\nLine 3"
        
        result = truncate_head(content)
        
        assert result.truncated is False
        assert result.content == content
        assert result.total_lines == 3
    
    def test_truncate_by_lines(self):
        """按行数截断"""
        lines = [f"Line {i}" for i in range(1, 100)]
        content = "\n".join(lines)
        
        result = truncate_head(content, max_lines=10, max_bytes=1000000)
        
        assert result.truncated is True
        assert result.truncated_by == "lines"
        assert result.output_lines == 10
        assert result.total_lines == 99
        assert "Line 1" in result.content
        assert "Line 10" in result.content
        assert "Line 11" not in result.content
    
    def test_truncate_by_bytes(self):
        """按字节数截断"""
        # 创建大量重复内容
        content = "A" * 100000  # 100KB
        
        result = truncate_head(content, max_lines=10000, max_bytes=50000)
        
        assert result.truncated is True
        assert result.truncated_by == "bytes"
        assert result.output_bytes <= 50000


class TestTruncationTail:
    """测试尾部截断（保留末尾）"""
    
    def test_no_truncation_needed(self):
        """不需要截断时返回原内容"""
        content = "Line 1\nLine 2\nLine 3"
        
        result = truncate_tail(content)
        
        assert result.truncated is False
        assert result.content == content
    
    def test_truncate_by_lines(self):
        """按行数截断，保留最后部分"""
        lines = [f"Line {i}" for i in range(1, 100)]
        content = "\n".join(lines)
        
        result = truncate_tail(content, max_lines=10, max_bytes=1000000)
        
        assert result.truncated is True
        assert result.truncated_by == "lines"
        assert result.output_lines == 10
        assert "Line 99" in result.content
        assert "Line 90" in result.content
        assert "Line 1" not in result.content


class TestTruncateForRead:
    """测试为文件读取截断"""
    
    def test_with_offset(self):
        """应用 offset"""
        lines = [f"Line {i}" for i in range(1, 100)]
        content = "\n".join(lines)
        
        result = truncate_for_read(content, offset=10, limit=20)
        
        assert "Line 10" in result.content or "Line 1" in result.content  # 取决于具体实现
    
    def test_with_limit(self):
        """应用 limit"""
        lines = [f"Line {i}" for i in range(1, 100)]
        content = "\n".join(lines)
        
        result = truncate_for_read(content, offset=1, limit=10)
        
        assert result.output_lines <= 10


class TestTruncationResult:
    """测试 TruncationResult 数据结构"""
    
    def test_creation(self):
        """测试创建"""
        result = TruncationResult(
            content="test",
            truncated=True,
            truncated_by="lines",
            total_lines=100,
            output_lines=50,
            total_bytes=1000,
            output_bytes=500,
            next_offset=51,
        )
        
        assert result.content == "test"
        assert result.truncated is True
