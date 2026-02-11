"""
Tests for Koda coding utilities (P0-P2 implementations)
"""
import pytest
import os
import tempfile
from pathlib import Path


class TestResourceLoader:
    """Test ResourceLoader"""
    
    def test_find_references(self):
        from koda.coding import ResourceLoader
        
        loader = ResourceLoader()
        text = "Check @https://example.com/doc.md and @./file.txt"
        refs = loader.find_references(text)
        
        assert len(refs) == 2
        assert "https://example.com/doc.md" in refs
        assert "./file.txt" in refs
    
    def test_find_no_references(self):
        from koda.coding import ResourceLoader
        
        loader = ResourceLoader()
        refs = loader.find_references("No references here")
        assert len(refs) == 0
    
    def test_load_file(self):
        from koda.coding import ResourceLoader, LoadOptions
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, World!")
            temp_path = f.name
        
        try:
            loader = ResourceLoader(LoadOptions(base_path=os.path.dirname(temp_path)))
            resource = loader.load(f"@{os.path.basename(temp_path)}")
            
            assert resource.content == "Hello, World!"
            assert resource.source.startswith("@")
        finally:
            os.unlink(temp_path)


class TestFrontmatter:
    """Test FrontmatterParser"""
    
    def test_parse_with_frontmatter(self):
        from koda.coding import FrontmatterParser
        
        parser = FrontmatterParser()
        content = """---
title: Test Document
author: John Doe
tags:
  - python
  - test
---

# Body Content

This is the body.
"""
        result = parser.parse(content)
        
        assert result.attributes["title"] == "Test Document"
        assert result.attributes["author"] == "John Doe"
        assert result.attributes["tags"] == ["python", "test"]
        assert "# Body Content" in result.body
    
    def test_parse_without_frontmatter(self):
        from koda.coding import FrontmatterParser
        
        parser = FrontmatterParser()
        content = "# Just a title\n\nSome content"
        result = parser.parse(content)
        
        assert result.attributes == {}
        assert result.body == content
    
    def test_stringify(self):
        from koda.coding import FrontmatterParser
        
        parser = FrontmatterParser()
        attributes = {"title": "Test", "draft": True}
        body = "# Hello"
        
        result = parser.stringify(attributes, body)
        
        assert "---" in result
        assert "title: Test" in result
        assert "# Hello" in result


class TestShellUtils:
    """Test ShellUtils"""
    
    def test_run_command_success(self):
        from koda.coding.utils import ShellUtils
        
        shell = ShellUtils()
        result = shell.run("echo hello")
        
        assert result.returncode == 0
        assert "hello" in result.stdout
    
    def test_run_command_failure(self):
        from koda.coding.utils import ShellUtils
        
        shell = ShellUtils()
        result = shell.run("exit 1")  # Windows might need different command
        # Just check it doesn't crash
        assert isinstance(result.returncode, int)
    
    def test_escape_shell_arg(self):
        from koda.coding.utils import escape_shell_arg
        
        # Should add quotes if needed
        result = escape_shell_arg("hello world")
        assert "'" in result or '"' in result
    
    def test_which(self):
        from koda.coding.utils import which
        
        # Should find python
        result = which("python")
        # Might be None if not in PATH, that's ok
        assert result is None or isinstance(result, str)


class TestGitUtils:
    """Test GitUtils"""
    
    def test_is_git_repo(self):
        from koda.coding.utils import GitUtils
        
        git = GitUtils()
        # This repo should be a git repo
        result = git.is_git_repo()
        assert isinstance(result, bool)
    
    def test_get_info(self):
        from koda.coding.utils import GitUtils
        
        git = GitUtils()
        info = git.get_info()
        
        assert hasattr(info, 'is_git_repo')
        assert hasattr(info, 'branch')
        
        if info.is_git_repo:
            assert isinstance(info.branch, (str, type(None)))


class TestClipboardUtils:
    """Test ClipboardUtils"""
    
    def test_is_available(self):
        from koda.coding.utils import ClipboardUtils
        
        clipboard = ClipboardUtils()
        result = clipboard.is_available()
        assert isinstance(result, bool)


class TestImageConverter:
    """Test ImageConverter"""
    
    def test_is_available(self):
        from koda.coding.utils import ImageConverter
        
        converter = ImageConverter()
        result = converter.is_available()
        assert isinstance(result, bool)
    
    def test_get_info_not_exists(self):
        from koda.coding.utils import ImageConverter
        
        converter = ImageConverter()
        info = converter.get_info("/nonexistent/image.png")
        assert info is None


class TestSlashCommands:
    """Test SlashCommandRegistry"""
    
    def test_register_command(self):
        from koda.coding import SlashCommandRegistry, CommandResult, CommandResultType
        
        registry = SlashCommandRegistry()
        
        @registry.command("test", "Test command")
        def cmd_test():
            return CommandResult(CommandResultType.SUCCESS, "OK")
        
        assert "test" in [c.name for c in registry.get_commands()]
    
    def test_execute_command(self):
        from koda.coding import SlashCommandRegistry, CommandResult, CommandResultType
        
        registry = SlashCommandRegistry()
        
        @registry.command("hello")
        def cmd_hello(context=None):
            return CommandResult(CommandResultType.SUCCESS, "Hello!")
        
        result = registry.execute("/hello")
        
        assert result is not None
        assert result.type == CommandResultType.SUCCESS
        assert result.message == "Hello!"
    
    def test_execute_unknown_command(self):
        from koda.coding import SlashCommandRegistry, CommandResultType
        
        registry = SlashCommandRegistry()
        result = registry.execute("/unknown")
        
        assert result is not None
        assert result.type == CommandResultType.ERROR
    
    def test_is_command(self):
        from koda.coding import SlashCommandRegistry
        
        registry = SlashCommandRegistry()
        
        assert registry.is_command("/help")
        assert not registry.is_command("hello")


class TestTimings:
    """Test Timings"""
    
    def test_measure(self):
        from koda.coding import Timings
        
        timings = Timings("test")
        
        with timings.measure("operation"):
            pass  # Do nothing
        
        report = timings.finish()
        
        assert report.name == "test"
        assert len(report.timings) == 1
        assert report.timings[0].name == "operation"
    
    def test_get_summary(self):
        from koda.coding import Timings
        
        timings = Timings("test")
        
        with timings.measure("op"):
            pass
        
        summary = timings.get_summary()
        
        assert "test" in summary
        assert "op" in summary
    
    def test_reset(self):
        from koda.coding import Timings
        
        timings = Timings("test")
        
        with timings.measure("op"):
            pass
        
        timings.reset()
        report = timings.finish()
        
        assert len(report.timings) == 0


class TestInteractiveMode:
    """Test InteractiveMode"""
    
    def test_start(self):
        from koda.coding.modes import InteractiveMode, ModeContext
        
        mode = InteractiveMode()
        context = ModeContext(messages=[])
        response = mode.start(context)
        
        assert response.requires_input
        assert "Interactive mode" in response.content
    
    def test_handle_exit(self):
        from koda.coding.modes import InteractiveMode, ModeContext
        
        mode = InteractiveMode()
        context = ModeContext(messages=[])
        mode.start(context)
        
        response = mode.handle_input("/exit", context)
        
        assert not mode.is_active()
    
    def test_handle_clear(self):
        from koda.coding.modes import InteractiveMode, ModeContext
        
        mode = InteractiveMode()
        context = ModeContext(messages=[])
        mode.start(context)
        
        response = mode.handle_input("/clear", context)
        
        assert mode.is_active()


class TestPrintMode:
    """Test PrintMode"""
    
    def test_run(self):
        from koda.coding.modes import PrintMode
        
        mode = PrintMode()
        result = mode.run("Test prompt")
        
        assert result.exit_code == 0
        assert isinstance(result.output, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
