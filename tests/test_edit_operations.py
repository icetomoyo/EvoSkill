"""
Tests for Edit Operations
"""
import pytest
from pathlib import Path

from koda.coding.tools.edit_operations import (
    LocalFileOperations,
    VirtualFileOperations,
    EditOperationsFactory,
    FileStat,
)


class TestVirtualFileOperations:
    """Test VirtualFileOperations"""
    
    def test_read_write_file(self):
        """Test basic read/write"""
        vfs = VirtualFileOperations()
        vfs.write_file("/test/file.txt", "Hello World")
        
        content = vfs.read_file("/test/file.txt")
        assert content == "Hello World"
    
    def test_read_write_bytes(self):
        """Test binary read/write"""
        vfs = VirtualFileOperations()
        data = b"\x00\x01\x02\x03"
        vfs.write_file_bytes("/test/binary.bin", data)
        
        content = vfs.read_file_bytes("/test/binary.bin")
        assert content == data
    
    def test_file_exists(self):
        """Test file existence check"""
        vfs = VirtualFileOperations()
        vfs.write_file("/exists.txt", "yes")
        
        assert vfs.file_exists("/exists.txt") is True
        assert vfs.file_exists("/notexists.txt") is False
    
    def test_access(self):
        """Test file access check"""
        vfs = VirtualFileOperations()
        vfs.write_file("/test.txt", "content")
        
        assert vfs.access("/test.txt") is True
        assert vfs.access("/nonexistent.txt") is False
    
    def test_stat(self):
        """Test file stats"""
        vfs = VirtualFileOperations()
        vfs.write_file("/stats.txt", "content here")
        
        stat = vfs.stat("/stats.txt")
        assert stat.exists is True
        assert stat.size > 0
        
        # Non-existent file
        stat = vfs.stat("/nonexistent.txt")
        assert stat.exists is False
    
    def test_mkdir_noop(self):
        """Test mkdir is no-op for virtual fs"""
        vfs = VirtualFileOperations()
        # Should not raise
        vfs.mkdir("/any/path")
        vfs.mkdir("/any/path", parents=True)
    
    def test_add_file_helper(self):
        """Test add_file helper"""
        vfs = VirtualFileOperations()
        vfs.add_file("/helper.txt", "helper content")
        
        assert vfs.read_file("/helper.txt") == "helper content"
    
    def test_get_file_helper(self):
        """Test get_file helper"""
        vfs = VirtualFileOperations()
        vfs.add_file("/get.txt", "got it")
        
        assert vfs.get_file("/get.txt") == "got it"
        assert vfs.get_file("/nonexistent.txt") is None
    
    def test_list_files(self):
        """Test listing files"""
        vfs = VirtualFileOperations()
        vfs.add_file("/a.txt", "a")
        vfs.add_file("/b.txt", "b")
        vfs.add_file("/c.txt", "c")
        
        files = vfs.list_files()
        assert len(files) == 3
        assert "/a.txt" in files
        assert "/b.txt" in files
        assert "/c.txt" in files
    
    def test_file_not_found(self):
        """Test reading non-existent file raises error"""
        vfs = VirtualFileOperations()
        
        with pytest.raises(FileNotFoundError):
            vfs.read_file("/nonexistent.txt")


class TestEditOperationsFactory:
    """Test EditOperationsFactory"""
    
    def test_create_local(self):
        """Test creating local operations"""
        ops = EditOperationsFactory.create_local()
        assert isinstance(ops, LocalFileOperations)
    
    def test_create_virtual(self):
        """Test creating virtual operations"""
        ops = EditOperationsFactory.create_virtual()
        assert isinstance(ops, VirtualFileOperations)
    
    def test_create_virtual_with_files(self):
        """Test creating virtual operations with initial files"""
        ops = EditOperationsFactory.create_virtual({
            "/init.txt": "initial"
        })
        
        assert ops.read_file("/init.txt") == "initial"
    
    def test_default_singleton(self):
        """Test default is singleton"""
        ops1 = EditOperationsFactory.get_default()
        ops2 = EditOperationsFactory.get_default()
        
        assert ops1 is ops2
    
    def test_set_default(self):
        """Test setting default"""
        original = EditOperationsFactory.get_default()
        try:
            new_ops = VirtualFileOperations()
            EditOperationsFactory.set_default(new_ops)
            
            assert EditOperationsFactory.get_default() is new_ops
        finally:
            EditOperationsFactory.set_default(original)


class TestLocalFileOperations:
    """Test LocalFileOperations (requires filesystem)"""
    
    def test_read_write_file(self, tmp_path):
        """Test basic read/write"""
        ops = LocalFileOperations()
        test_file = tmp_path / "test.txt"
        
        ops.write_file(test_file, "Hello Local")
        content = ops.read_file(test_file)
        
        assert content == "Hello Local"
    
    def test_read_write_bytes(self, tmp_path):
        """Test binary read/write"""
        ops = LocalFileOperations()
        test_file = tmp_path / "binary.bin"
        data = b"\x00\x01\x02\x03"
        
        ops.write_file_bytes(test_file, data)
        content = ops.read_file_bytes(test_file)
        
        assert content == data
    
    def test_file_exists(self, tmp_path):
        """Test file existence"""
        ops = LocalFileOperations()
        test_file = tmp_path / "exists.txt"
        
        assert ops.file_exists(test_file) is False
        
        ops.write_file(test_file, "content")
        assert ops.file_exists(test_file) is True
    
    def test_access(self, tmp_path):
        """Test file access"""
        ops = LocalFileOperations()
        test_file = tmp_path / "access.txt"
        
        # Non-existent file
        assert ops.access(test_file) is False
        
        # Create file
        ops.write_file(test_file, "content")
        assert ops.access(test_file) is True
    
    def test_stat(self, tmp_path):
        """Test file stats"""
        ops = LocalFileOperations()
        test_file = tmp_path / "stats.txt"
        
        # Non-existent file
        stat = ops.stat(test_file)
        assert stat.exists is False
        
        # Create and check
        ops.write_file(test_file, "content")
        stat = ops.stat(test_file)
        
        assert stat.exists is True
        assert stat.size == 7
        assert stat.mtime > 0
    
    def test_mkdir(self, tmp_path):
        """Test directory creation"""
        ops = LocalFileOperations()
        test_dir = tmp_path / "newdir"
        
        ops.mkdir(test_dir)
        
        assert test_dir.exists()
        assert test_dir.is_dir()
    
    def test_mkdir_parents(self, tmp_path):
        """Test recursive directory creation"""
        ops = LocalFileOperations()
        test_dir = tmp_path / "parent" / "child" / "grandchild"
        
        ops.mkdir(test_dir, parents=True)
        
        assert test_dir.exists()


class TestFileStat:
    """Test FileStat dataclass"""
    
    def test_creation(self):
        """Test creating FileStat"""
        stat = FileStat(
            size=100,
            mtime=1234567890.0,
            mode=0o644,
            exists=True
        )
        
        assert stat.size == 100
        assert stat.mtime == 1234567890.0
        assert stat.mode == 0o644
        assert stat.exists is True
