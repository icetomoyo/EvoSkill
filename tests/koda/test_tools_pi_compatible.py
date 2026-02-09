"""
Functional tests for Koda tools - Pi Coding Agent compatible

These tests mirror the test cases from Pi Coding Agent's tools.test.ts
to ensure 100% functional compatibility.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from koda.coding.tools.file_tool import FileTool
from koda.coding.tools.shell_tool import ShellTool


class TestReadTool:
    """Read tool tests - matching Pi's read tool tests"""
    
    @pytest.fixture
    def file_tool(self, tmp_path):
        return FileTool(tmp_path)
    
    @pytest.mark.asyncio
    async def test_read_file_within_limits(self, file_tool, tmp_path):
        """Should read file contents that fit within limits"""
        test_file = tmp_path / "test.txt"
        content = "Hello, world!\nLine 2\nLine 3"
        test_file.write_text(content, encoding='utf-8')
        
        result = await file_tool.read(str(test_file))
        
        assert result.content == content
        assert "Use offset=" not in result.content
        assert not result.truncated
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, file_tool, tmp_path):
        """Should handle non-existent files"""
        test_file = tmp_path / "nonexistent.txt"
        
        result = await file_tool.read(str(test_file))
        
        assert not result.success
        assert result.error is not None
        assert "not found" in result.error.lower() or "ENOENT" in result.error
    
    @pytest.mark.asyncio
    async def test_truncate_line_limit(self, file_tool, tmp_path):
        """Should truncate files exceeding line limit (2000 lines)"""
        test_file = tmp_path / "large.txt"
        lines = [f"Line {i+1}" for i in range(2500)]
        test_file.write_text("\n".join(lines), encoding='utf-8')
        
        result = await file_tool.read(str(test_file))
        
        assert "Line 1" in result.content
        assert "Line 2000" in result.content
        assert "Line 2001" not in result.content
        assert "Showing lines 1-2000 of 2500" in result.content
        assert "Use offset=2001 to continue" in result.content
        assert result.truncated
    
    @pytest.mark.asyncio
    async def test_truncate_byte_limit(self, file_tool, tmp_path):
        """Should truncate when byte limit exceeded (50KB)"""
        test_file = tmp_path / "large-bytes.txt"
        # Create file that exceeds 50KB but has fewer than 2000 lines
        lines = [f"Line {i+1}: {'x' * 200}" for i in range(500)]
        test_file.write_text("\n".join(lines), encoding='utf-8')
        
        result = await file_tool.read(str(test_file))
        
        assert "Line 1:" in result.content
        # Should show byte limit message
        import re
        assert re.search(r"Showing lines 1-\d+ of 500.*limit", result.content)
        assert "Use offset=" in result.content
    
    @pytest.mark.asyncio
    async def test_offset_parameter(self, file_tool, tmp_path):
        """Should handle offset parameter"""
        test_file = tmp_path / "offset-test.txt"
        lines = [f"Line {i+1}" for i in range(100)]
        test_file.write_text("\n".join(lines), encoding='utf-8')
        
        result = await file_tool.read(str(test_file), offset=51)
        
        assert "Line 50" not in result.content
        assert "Line 51" in result.content
        assert "Line 100" in result.content
        # No truncation message since file fits within limits
        assert "Use offset=" not in result.content or "more lines" in result.content
    
    @pytest.mark.asyncio
    async def test_limit_parameter(self, file_tool, tmp_path):
        """Should handle limit parameter"""
        test_file = tmp_path / "limit-test.txt"
        lines = [f"Line {i+1}" for i in range(100)]
        test_file.write_text("\n".join(lines), encoding='utf-8')
        
        result = await file_tool.read(str(test_file), limit=10)
        
        assert "Line 1" in result.content
        assert "Line 10" in result.content
        assert "Line 11" not in result.content
        assert "90 more lines in file" in result.content
        assert "Use offset=11 to continue" in result.content
    
    @pytest.mark.asyncio
    async def test_offset_and_limit_together(self, file_tool, tmp_path):
        """Should handle offset + limit together"""
        test_file = tmp_path / "offset-limit-test.txt"
        lines = [f"Line {i+1}" for i in range(100)]
        test_file.write_text("\n".join(lines), encoding='utf-8')
        
        result = await file_tool.read(str(test_file), offset=41, limit=20)
        
        assert "Line 40" not in result.content
        assert "Line 41" in result.content
        assert "Line 60" in result.content
        assert "Line 61" not in result.content
        assert "40 more lines in file" in result.content
        assert "Use offset=61 to continue" in result.content
    
    @pytest.mark.asyncio
    async def test_offset_beyond_file_length(self, file_tool, tmp_path):
        """Should show error when offset is beyond file length"""
        test_file = tmp_path / "short.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding='utf-8')
        
        result = await file_tool.read(str(test_file), offset=100)
        
        assert result.error is not None
        assert "Offset 100 is beyond end of file (3 lines total)" in result.error
    
    @pytest.mark.asyncio
    async def test_truncation_details(self, file_tool, tmp_path):
        """Should include truncation details when truncated"""
        test_file = tmp_path / "large-file.txt"
        lines = [f"Line {i+1}" for i in range(2500)]
        test_file.write_text("\n".join(lines), encoding='utf-8')
        
        result = await file_tool.read(str(test_file))
        
        assert result.truncated
        # Our implementation includes truncation info in content, not separate details
        assert "Showing lines" in result.content
    
    @pytest.mark.asyncio
    async def test_detect_image_mime_type_from_magic(self, file_tool, tmp_path):
        """Should detect image MIME type from file magic (not extension)"""
        # 1x1 PNG image base64
        png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2Z0AAAAASUVORK5CYII="
        import base64
        png_bytes = base64.b64decode(png_base64)
        
        test_file = tmp_path / "image.txt"  # Note: .txt extension
        test_file.write_bytes(png_bytes)
        
        result = await file_tool.read(str(test_file))
        
        assert result.is_image
        assert result.mime_type == "image/png"
        assert result.image_data is not None
        assert len(result.image_data) > 0
        assert "Read image file [image/png]" in result.content
    
    @pytest.mark.asyncio
    async def test_treat_non_image_content_as_text(self, file_tool, tmp_path):
        """Should treat files with image extension but non-image content as text"""
        test_file = tmp_path / "not-an-image.png"
        test_file.write_text("definitely not a png", encoding='utf-8')
        
        result = await file_tool.read(str(test_file))
        
        assert not result.is_image
        assert "definitely not a png" in result.content


class TestWriteTool:
    """Write tool tests"""
    
    @pytest.fixture
    def file_tool(self, tmp_path):
        return FileTool(tmp_path)
    
    @pytest.mark.asyncio
    async def test_write_file_contents(self, file_tool, tmp_path):
        """Should write file contents"""
        test_file = tmp_path / "write-test.txt"
        content = "Test content"
        
        result = await file_tool.write(str(test_file), content)
        
        assert result.success
        assert "write-test.txt" in result.path
        assert result.bytes_written == len(content.encode('utf-8'))
        
        # Verify file was written
        assert test_file.read_text(encoding='utf-8') == content
    
    @pytest.mark.asyncio
    async def test_create_parent_directories(self, file_tool, tmp_path):
        """Should create parent directories"""
        test_file = tmp_path / "nested" / "dir" / "test.txt"
        content = "Nested content"
        
        result = await file_tool.write(str(test_file), content)
        
        assert result.success
        assert test_file.read_text(encoding='utf-8') == content


class TestEditTool:
    """Edit tool tests - including fuzzy matching and CRLF handling"""
    
    @pytest.fixture
    def file_tool(self, tmp_path):
        return FileTool(tmp_path)
    
    @pytest.mark.asyncio
    async def test_replace_text_in_file(self, file_tool, tmp_path):
        """Should replace text in file"""
        test_file = tmp_path / "edit-test.txt"
        original_content = "Hello, world!"
        test_file.write_text(original_content, encoding='utf-8')
        
        result = await file_tool.edit(str(test_file), "world", "testing")
        
        assert result.success
        assert result.diff is not None
        assert "testing" in result.diff
        assert test_file.read_text(encoding='utf-8') == "Hello, testing!"
    
    @pytest.mark.asyncio
    async def test_fail_if_text_not_found(self, file_tool, tmp_path):
        """Should fail if text not found"""
        test_file = tmp_path / "edit-test.txt"
        test_file.write_text("Hello, world!", encoding='utf-8')
        
        result = await file_tool.edit(str(test_file), "nonexistent", "testing")
        
        assert not result.success
        assert "Could not find the exact text" in result.error
    
    @pytest.mark.asyncio
    async def test_fail_if_text_appears_multiple_times(self, file_tool, tmp_path):
        """Should fail if text appears multiple times"""
        test_file = tmp_path / "edit-test.txt"
        test_file.write_text("foo foo foo", encoding='utf-8')
        
        result = await file_tool.edit(str(test_file), "foo", "bar")
        
        assert not result.success
        assert "Found 3 occurrences" in result.error
    
    @pytest.mark.asyncio
    async def test_match_text_with_trailing_whitespace_stripped(self, file_tool, tmp_path):
        """Should match text with trailing whitespace stripped"""
        test_file = tmp_path / "trailing-ws.txt"
        # File has trailing spaces on lines
        test_file.write_text("line one   \nline two  \nline three\n", encoding='utf-8')
        
        # oldText without trailing whitespace should still match
        result = await file_tool.edit(str(test_file), "line one\nline two\n", "replaced\n")
        
        assert result.success
        content = test_file.read_text(encoding='utf-8')
        assert content == "replaced\nline three\n"
    
    @pytest.mark.asyncio
    async def test_match_smart_single_quotes_to_ascii(self, file_tool, tmp_path):
        """Should match smart single quotes to ASCII quotes"""
        test_file = tmp_path / "smart-quotes.txt"
        # File has smart/curly single quotes (U+2018, U+2019)
        test_file.write_text("console.log('hello');\n", encoding='utf-8')
        
        # oldText with ASCII quotes should match
        result = await file_tool.edit(str(test_file), "console.log('hello');", "console.log('world');")
        
        assert result.success
        content = test_file.read_text(encoding='utf-8')
        assert "world" in content
    
    @pytest.mark.asyncio
    async def test_match_unicode_dashes_to_ascii(self, file_tool, tmp_path):
        """Should match Unicode dashes to ASCII hyphen"""
        test_file = tmp_path / "unicode-dashes.txt"
        # File has en-dash (U+2013) and em-dash (U+2014)
        test_file.write_text("range: 1\u20135\nbreak\u2014here\n", encoding='utf-8')
        
        # oldText with ASCII hyphens should match
        result = await file_tool.edit(str(test_file), "range: 1-5\nbreak-here", "range: 10-50\nbreak--here")
        
        assert result.success
        content = test_file.read_text(encoding='utf-8')
        assert "10-50" in content
    
    @pytest.mark.asyncio
    async def test_match_non_breaking_space_to_regular(self, file_tool, tmp_path):
        """Should match non-breaking space to regular space"""
        test_file = tmp_path / "nbsp.txt"
        # File has non-breaking space (U+00A0)
        test_file.write_text("hello\u00A0world\n", encoding='utf-8')
        
        # oldText with regular space should match
        result = await file_tool.edit(str(test_file), "hello world", "hello universe")
        
        assert result.success
        content = test_file.read_text(encoding='utf-8')
        assert "universe" in content
    
    @pytest.mark.asyncio
    async def test_prefer_exact_match_over_fuzzy(self, file_tool, tmp_path):
        """Should prefer exact match over fuzzy match"""
        test_file = tmp_path / "exact-preferred.txt"
        test_file.write_text("const x = 'exact';\nconst y = 'other';\n", encoding='utf-8')
        
        result = await file_tool.edit(str(test_file), "const x = 'exact';", "const x = 'changed';")
        
        assert result.success
        content = test_file.read_text(encoding='utf-8')
        assert content == "const x = 'changed';\nconst y = 'other';\n"
    
    @pytest.mark.asyncio
    async def test_fail_when_text_not_found_even_with_fuzzy(self, file_tool, tmp_path):
        """Should still fail when text is not found even with fuzzy matching"""
        test_file = tmp_path / "no-match.txt"
        test_file.write_text("completely different content\n", encoding='utf-8')
        
        result = await file_tool.edit(str(test_file), "this does not exist", "replacement")
        
        assert not result.success
        assert "Could not find the exact text" in result.error
    
    @pytest.mark.asyncio
    async def test_detect_duplicates_after_fuzzy_normalization(self, file_tool, tmp_path):
        """Should detect duplicates after fuzzy normalization"""
        test_file = tmp_path / "fuzzy-dups.txt"
        # Two lines that are identical after trailing whitespace is stripped
        test_file.write_text("hello world   \nhello world\n", encoding='utf-8')
        
        result = await file_tool.edit(str(test_file), "hello world", "replaced")
        
        assert not result.success
        assert "Found 2 occurrences" in result.error


class TestEditToolCRLFHandling:
    """Edit tool CRLF handling tests"""
    
    @pytest.fixture
    def file_tool(self, tmp_path):
        return FileTool(tmp_path)
    
    @pytest.mark.asyncio
    async def test_match_lf_against_crlf_content(self, file_tool, tmp_path):
        """Should match LF oldText against CRLF file content"""
        test_file = tmp_path / "crlf-test.txt"
        test_file.write_bytes(b"line one\r\nline two\r\nline three\r\n")
        
        result = await file_tool.edit(str(test_file), "line two\n", "replaced line\n")
        
        assert result.success
    
    @pytest.mark.asyncio
    async def test_preserve_crlf_after_edit(self, file_tool, tmp_path):
        """Should preserve CRLF line endings after edit"""
        test_file = tmp_path / "crlf-preserve.txt"
        test_file.write_bytes(b"first\r\nsecond\r\nthird\r\n")
        
        await file_tool.edit(str(test_file), "second\n", "REPLACED\n")
        
        content = test_file.read_bytes()
        assert content == b"first\r\nREPLACED\r\nthird\r\n"
    
    @pytest.mark.asyncio
    async def test_preserve_lf_for_lf_files(self, file_tool, tmp_path):
        """Should preserve LF line endings for LF files"""
        test_file = tmp_path / "lf-preserve.txt"
        test_file.write_text("first\nsecond\nthird\n", encoding='utf-8')
        
        await file_tool.edit(str(test_file), "second\n", "REPLACED\n")
        
        content = test_file.read_text(encoding='utf-8')
        assert content == "first\nREPLACED\nthird\n"
    
    @pytest.mark.asyncio
    async def test_detect_duplicates_across_crlf_lf(self, file_tool, tmp_path):
        """Should detect duplicates across CRLF/LF variants"""
        test_file = tmp_path / "mixed-endings.txt"
        test_file.write_bytes(b"hello\r\nworld\r\n---\r\nhello\nworld\n")
        
        result = await file_tool.edit(str(test_file), "hello\nworld\n", "replaced\n")
        
        assert not result.success
        assert "Found 2 occurrences" in result.error
    
    @pytest.mark.asyncio
    async def test_preserve_utf8_bom_after_edit(self, file_tool, tmp_path):
        """Should preserve UTF-8 BOM after edit"""
        test_file = tmp_path / "bom-test.txt"
        test_file.write_bytes("\uFEFFfirst\r\nsecond\r\nthird\r\n".encode('utf-8'))
        
        await file_tool.edit(str(test_file), "second\n", "REPLACED\n")
        
        content = test_file.read_bytes()
        assert content.startswith(b'\xef\xbb\xbf')  # BOM
        assert b"REPLACED" in content


class TestBashTool:
    """Bash tool tests"""
    
    @pytest.fixture
    def shell_tool(self, tmp_path):
        return ShellTool(tmp_path)
    
    @pytest.mark.asyncio
    async def test_execute_simple_commands(self, shell_tool):
        """Should execute simple commands"""
        result = await shell_tool.execute("echo test output")
        
        assert result.success
        assert "test output" in result.output
    
    @pytest.mark.asyncio
    async def test_handle_command_errors(self, shell_tool):
        """Should handle command errors"""
        result = await shell_tool.execute("exit 1")
        
        assert not result.success
        assert result.exit_code == 1
    
    @pytest.mark.asyncio
    async def test_respect_timeout(self, shell_tool):
        """Should respect timeout"""
        import sys
        if sys.platform == 'win32':
            # Windows doesn't have sleep command by default
            pytest.skip("Sleep command not available on Windows")
        
        result = await shell_tool.execute("sleep 5", timeout=1)
        
        assert not result.success
        assert "timed out" in result.error.lower() or "timeout" in result.output.lower()
    
    @pytest.mark.asyncio
    async def test_error_when_cwd_does_not_exist(self, tmp_path):
        """Should throw error when cwd does not exist"""
        nonexistent_cwd = tmp_path / "definitely" / "does" / "not" / "exist"
        shell_tool = ShellTool(nonexistent_cwd)
        
        result = await shell_tool.execute("echo test")
        
        assert not result.success
        assert "Working directory does not exist" in result.error
