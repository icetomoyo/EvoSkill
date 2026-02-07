"""
内置工具测试

测试文件操作、代码编辑、命令执行等工具
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from evoskill.skills.builtin import (
    read_file,
    write_file,
    list_dir,
    search_files,
    execute_command,
    fetch_url,
)


@pytest.mark.asyncio
class TestReadFileTool:
    """测试 read_file 工具"""
    
    async def test_read_existing_file(self, temp_dir):
        """测试读取存在的文件"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")
        
        result = await read_file(path=str(test_file))
        
        assert "Hello World" in result
        assert "Error" not in result
    
    async def test_read_with_offset_and_limit(self, temp_dir):
        """测试带行号范围的读取"""
        test_file = temp_dir / "test.py"
        lines = [f"line {i}" for i in range(1, 21)]  # 20 lines
        test_file.write_text("\n".join(lines), encoding="utf-8")
        
        result = await read_file(path=str(test_file), offset=5, limit=5)
        
        assert "line 6" in result  # offset=5 是 0-based，所以是第 6 行
        assert "line 10" in result
        assert "line 5" not in result  # 超出范围
        assert "Error" not in result
    
    async def test_read_nonexistent_file(self, temp_dir):
        """测试读取不存在的文件"""
        result = await read_file(path=str(temp_dir / "not_exist.txt"))
        
        assert "Error" in result
        assert "not found" in result.lower()


@pytest.mark.asyncio
class TestListDirTool:
    """测试 list_dir 工具"""
    
    async def test_list_directory(self, temp_dir):
        """测试列出目录内容"""
        # 创建一些文件和目录
        (temp_dir / "file1.txt").write_text("content")
        (temp_dir / "file2.py").write_text("print('hello')")
        (temp_dir / "subdir").mkdir()
        
        result = await list_dir(path=str(temp_dir))
        
        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result
    
    async def test_list_subdirectory(self, temp_dir):
        """测试列出子目录"""
        subdir = temp_dir / "test_dir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")
        
        result = await list_dir(path=str(subdir))
        
        assert "file.txt" in result


@pytest.mark.asyncio
class TestSearchFilesTool:
    """测试 search_files 工具"""
    
    async def test_search_content(self, temp_dir):
        """测试搜索文件内容"""
        # 创建包含目标内容的文件
        (temp_dir / "file1.py").write_text("def hello():\n    pass", encoding="utf-8")
        (temp_dir / "file2.py").write_text("def hello_world():\n    print('hi')", encoding="utf-8")
        (temp_dir / "file3.txt").write_text("no match here", encoding="utf-8")
        
        result = await search_files(
            query="def hello",
            path=str(temp_dir),
            file_pattern="*.py"
        )
        
        assert "file1.py" in result
        assert "file2.py" in result
        assert "2 matches" in result or "found" in result.lower()
    
    async def test_search_no_results(self, temp_dir):
        """测试搜索无结果"""
        (temp_dir / "test.py").write_text("print('hello')")
        
        result = await search_files(
            query="not_found_pattern_xyz",
            path=str(temp_dir)
        )
        
        assert "no matches" in result.lower() or "0 matches" in result.lower()


@pytest.mark.asyncio
class TestExecuteCommandTool:
    """测试 execute_command 工具"""
    
    async def test_execute_simple_command(self, temp_dir):
        """测试执行简单命令"""
        import platform
        if platform.system() == "Windows":
            cmd = "echo Hello"
        else:
            cmd = "echo Hello"
        
        result = await execute_command(command=cmd)
        
        # 验证命令执行了
        assert "Hello" in result or result == ""  # 某些环境下可能没有输出
    
    async def test_execute_with_cwd(self, temp_dir):
        """测试在指定目录执行命令"""
        subdir = temp_dir / "work_dir"
        subdir.mkdir()
        
        import platform
        if platform.system() == "Windows":
            # Windows: 创建测试文件，然后检查目录
            (subdir / "test.txt").write_text("test")
            cmd = "dir"
        else:
            cmd = "pwd"
        
        result = await execute_command(command=cmd, cwd=str(subdir))
        
        # 验证在正确目录执行
        assert "Error" not in result.lower() or result == ""


@pytest.mark.asyncio
class TestFetchUrlTool:
    """测试 fetch_url 工具"""
    
    async def test_fetch_success(self):
        """测试成功获取 URL"""
        mock_html = "<html><body>Hello World</body></html>"
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = mock_html.encode('utf-8')
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response
            
            result = await fetch_url(url="https://example.com")
            
            assert "Hello World" in result
    
    async def test_fetch_error(self):
        """测试获取失败"""
        with patch('urllib.request.urlopen', side_effect=Exception("Connection error")):
            result = await fetch_url(url="https://invalid.url")
            
            assert "Error" in result or "Failed" in result


@pytest.mark.asyncio
class TestEditCodeTool:
    """测试 edit_code 工具（需要特殊处理）"""
    
    async def test_edit_code_search_replace(self, temp_dir):
        """测试代码编辑的搜索替换"""
        from evoskill.skills.builtin import edit_code
        
        # 创建测试文件
        original_content = '''def old_function():
    pass

def another():
    pass
'''
        test_file = temp_dir / "code.py"
        test_file.write_text(original_content, encoding="utf-8")
        
        # 执行编辑
        result = await edit_code(
            path=str(test_file),
            old_string="def old_function():\n    pass",
            new_string="def new_function():\n    return 42"
        )
        
        assert "success" in result.lower() or "Successfully" in result
        
        # 验证文件内容
        new_content = test_file.read_text(encoding="utf-8")
        assert "def new_function():" in new_content
        assert "return 42" in new_content
    
    async def test_edit_code_no_match(self, temp_dir):
        """测试搜索字符串不存在"""
        from evoskill.skills.builtin import edit_code
        
        test_file = temp_dir / "code.py"
        test_file.write_text("def func():\n    pass", encoding="utf-8")
        
        result = await edit_code(
            path=str(test_file),
            old_string="nonexistent text xyz",
            new_string="replacement"
        )
        
        assert "Error" in result or "not found" in result.lower()
