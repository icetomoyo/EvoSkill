"""
Tests for Advanced Compaction functionality
"""
import pytest
from datetime import datetime

from koda.mes.compaction_advanced import (
    TokenEstimator,
    find_cut_point,
    collect_entries_for_branch_summary,
    deduplicate_file_operations,
    generate_branch_summary,
    should_compact,
    AdvancedCompactor,
    create_compact_prompt,
    detect_file_patterns,
    SessionEntry,
    MessageEntry,
    FileEntry,
    CompactionEntry,
    FileOperation,
    FileOperationType,
    EntryType,
    CutPointResult,
    CollectEntriesResult,
    BranchSummary,
)


class TestTokenEstimator:
    """Test TokenEstimator"""
    
    def test_estimate_text_tokens(self):
        """Test text token estimation"""
        assert TokenEstimator.estimate_text_tokens("") == 0
        assert TokenEstimator.estimate_text_tokens("hello") == 2  # len // 4 + 1
        assert TokenEstimator.estimate_text_tokens("a" * 100) == 26
    
    def test_estimate_message_tokens(self):
        """Test message token estimation"""
        message = {"role": "user", "content": "Hello world"}
        tokens = TokenEstimator.estimate_message_tokens(message)
        assert tokens >= 8  # 4 base + ~3 for content + overhead
    
    def test_estimate_message_with_list_content(self):
        """Test message with list content"""
        message = {
            "role": "assistant",
            "content": [{"text": "Hello"}, {"text": "World"}]
        }
        tokens = TokenEstimator.estimate_message_tokens(message)
        assert tokens >= 8
    
    def test_estimate_entry_tokens(self):
        """Test entry token estimation"""
        entry = MessageEntry(id="1", content="Hello world")
        tokens = TokenEstimator.estimate_entry_tokens(entry)
        assert tokens >= 6


class TestFindCutPoint:
    """Test find_cut_point function"""
    
    def test_empty_entries(self):
        """Test with empty entries"""
        result = find_cut_point([], 1000, 100)
        assert result.index == 0
        assert result.reason == "empty_entries"
    
    def test_no_cut_needed(self):
        """Test when no cut is needed"""
        entries = [
            MessageEntry(id="1", content="Hello"),
            MessageEntry(id="2", content="World"),
        ]
        result = find_cut_point(entries, 10000, 100)
        assert result.index == 2
        assert result.reason == "no_cut_needed"
    
    def test_aggressive_strategy(self):
        """Test aggressive strategy"""
        entries = [MessageEntry(id=f"{i}", content="x" * 100) for i in range(20)]
        result = find_cut_point(entries, 100, 0, strategy="aggressive")
        assert result.index > 0
        assert result.index <= len(entries) - 2
    
    def test_conservative_strategy(self):
        """Test conservative strategy keeps more context"""
        entries = [MessageEntry(id=f"{i}", content="x" * 100) for i in range(20)]
        
        aggressive = find_cut_point(entries, 100, 0, strategy="aggressive")
        conservative = find_cut_point(entries, 100, 0, strategy="conservative")
        
        # Conservative should keep more entries
        assert conservative.index <= aggressive.index


class TestCollectEntriesForBranchSummary:
    """Test collect_entries_for_branch_summary"""
    
    def test_empty_cut_point(self):
        """Test with cut point 0"""
        entries = [MessageEntry(id="1", content="Hello")]
        result = collect_entries_for_branch_summary(entries, 0)
        
        assert result.entries == []
        assert result.total_tokens == 0
    
    def test_collect_entries(self):
        """Test collecting entries"""
        entries = [
            MessageEntry(id="1", content="First message"),
            MessageEntry(id="2", content="Second message"),
            FileEntry(id="3", operation=FileOperation("test.py", FileOperationType.READ)),
        ]
        result = collect_entries_for_branch_summary(entries, 2)
        
        assert len(result.entries) == 2
        assert len(result.file_operations) == 0  # Only first 2 entries
        assert result.total_tokens > 0
    
    def test_detect_errors(self):
        """Test detecting error entries"""
        entries = [
            MessageEntry(id="1", content="Hello"),
            MessageEntry(id="2", content="Error", metadata={"is_error": True}),
        ]
        result = collect_entries_for_branch_summary(entries, 2)
        
        assert result.has_errors is True


class TestDeduplicateFileOperations:
    """Test deduplicate_file_operations"""
    
    def test_remove_duplicate_reads(self):
        """Test removing duplicate reads"""
        entries = [
            FileEntry(id="1", operation=FileOperation("file.py", FileOperationType.READ)),
            FileEntry(id="2", operation=FileOperation("file.py", FileOperationType.READ)),
        ]
        result = deduplicate_file_operations(entries)
        
        assert len(result) == 1
        assert result[0].operation.operation == FileOperationType.READ
    
    def test_remove_read_after_write(self):
        """Test removing read after write"""
        entries = [
            FileEntry(id="1", operation=FileOperation("file.py", FileOperationType.WRITE)),
            FileEntry(id="2", operation=FileOperation("file.py", FileOperationType.READ)),
        ]
        result = deduplicate_file_operations(entries)
        
        assert len(result) == 1
        assert result[0].operation.operation == FileOperationType.WRITE
    
    def test_keep_write_after_write(self):
        """Test keeping only last write"""
        entries = [
            FileEntry(id="1", operation=FileOperation("file.py", FileOperationType.WRITE, "hash1")),
            FileEntry(id="2", operation=FileOperation("file.py", FileOperationType.WRITE, "hash2")),
        ]
        result = deduplicate_file_operations(entries)
        
        assert len(result) == 1
        assert result[0].operation.content_hash == "hash2"
    
    def test_keep_edit_after_read(self):
        """Test keeping edit after read"""
        entries = [
            FileEntry(id="1", operation=FileOperation("file.py", FileOperationType.READ)),
            FileEntry(id="2", operation=FileOperation("file.py", FileOperationType.EDIT)),
        ]
        result = deduplicate_file_operations(entries)
        
        assert len(result) == 2
    
    def test_mixed_entries_preserved(self):
        """Test non-file entries are preserved"""
        entries = [
            MessageEntry(id="1", content="Hello"),
            FileEntry(id="2", operation=FileOperation("file.py", FileOperationType.READ)),
            MessageEntry(id="3", content="World"),
        ]
        result = deduplicate_file_operations(entries)
        
        assert len(result) == 3
        assert isinstance(result[0], MessageEntry)


class TestDetectFilePatterns:
    """Test detect_file_patterns"""
    
    def test_empty_operations(self):
        """Test with empty operations"""
        result = detect_file_patterns([])
        assert result == {}
    
    def test_most_edited_files(self):
        """Test detecting most edited files"""
        ops = [
            FileOperation("file1.py", FileOperationType.EDIT),
            FileOperation("file1.py", FileOperationType.EDIT),
            FileOperation("file2.py", FileOperationType.EDIT),
            FileOperation("file1.py", FileOperationType.READ),
        ]
        result = detect_file_patterns(ops)
        
        assert "file1.py" in result["most_edited_files"]
        assert result["file_types"]["py"] == 2
    
    def test_file_type_counting(self):
        """Test counting file types"""
        ops = [
            FileOperation("a.py", FileOperationType.READ),
            FileOperation("b.py", FileOperationType.READ),
            FileOperation("c.js", FileOperationType.READ),
            FileOperation("d.md", FileOperationType.READ),
        ]
        result = detect_file_patterns(ops)
        
        assert result["file_types"]["py"] == 2
        assert result["file_types"]["js"] == 1
        assert result["unique_files"] == 4


class TestGenerateBranchSummary:
    """Test generate_branch_summary"""
    
    @pytest.mark.asyncio
    async def test_empty_entries(self):
        """Test with empty entries"""
        def summarizer(prompt):
            return "Summary"
        
        result = await generate_branch_summary([], summarizer)
        
        assert result.entry_count == 0
        assert "No entries" in result.summary
    
    @pytest.mark.asyncio
    async def test_generate_summary(self):
        """Test summary generation"""
        def summarizer(prompt):
            return "Test summary"
        
        entries = [
            MessageEntry(id="1", role="user", content="Hello"),
            MessageEntry(id="2", role="assistant", content="Hi there"),
        ]
        
        result = await generate_branch_summary(entries, summarizer)
        
        assert result.summary == "Test summary"
        assert result.entry_count == 2
    
    @pytest.mark.asyncio
    async def test_with_file_operations(self):
        """Test with file operations included"""
        captured_prompt = ""
        def summarizer(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Summary with files"
        
        entries = [
            MessageEntry(id="1", content="Edit the file"),
            FileEntry(id="2", operation=FileOperation("test.py", FileOperationType.EDIT)),
        ]
        
        result = await generate_branch_summary(entries, summarizer, include_file_context=True)
        
        assert "test.py" in captured_prompt
        assert result.summary == "Summary with files"


class TestShouldCompact:
    """Test should_compact function"""
    
    def test_no_compact_needed(self):
        """Test when compaction not needed"""
        entries = [MessageEntry(id="1", content="Hi")]
        
        assert should_compact(entries, 10000, 0.8) is False
    
    def test_compact_needed(self):
        """Test when compaction is needed"""
        # Create entries that exceed threshold
        entries = [MessageEntry(id=f"{i}", content="x" * 1000) for i in range(100)]
        
        assert should_compact(entries, 1000, 0.5) is True


class TestAdvancedCompactor:
    """Test AdvancedCompactor class"""
    
    def test_init(self):
        """Test initialization"""
        compactor = AdvancedCompactor(max_tokens=50000, reserve_tokens=2000)
        
        assert compactor.max_tokens == 50000
        assert compactor.reserve_tokens == 2000
    
    @pytest.mark.asyncio
    async def test_no_compact_needed(self):
        """Test when no compaction needed"""
        compactor = AdvancedCompactor(max_tokens=100000)
        
        entries = [MessageEntry(id="1", content="Hello")]
        result, summary = await compactor.compact_with_summary(entries)
        
        assert len(result) == 1
        assert summary.entry_count == 0  # No summary generated
    
    @pytest.mark.asyncio
    async def test_compact_with_summary(self):
        """Test compaction with summary generation"""
        def summarizer(prompt):
            return "Compacted summary"
        
        compactor = AdvancedCompactor(
            max_tokens=100,
            reserve_tokens=10,
            summarizer=summarizer
        )
        
        entries = [MessageEntry(id=f"{i}", content="x" * 100) for i in range(10)]
        result, summary = await compactor.compact_with_summary(entries)
        
        assert summary.summary == "Compacted summary"
        assert summary.entry_count > 0
        assert isinstance(result[0], CompactionEntry)
    
    def test_get_branch_summary(self):
        """Test getting branch summary"""
        compactor = AdvancedCompactor()
        compactor._branch_summaries["test_branch"] = BranchSummary(
            branch_id="test_branch",
            summary="Test",
            entry_count=5,
            file_operations=[]
        )
        
        summary = compactor.get_branch_summary("test_branch")
        assert summary is not None
        assert summary.summary == "Test"
        
        # Non-existent branch
        assert compactor.get_branch_summary("nonexistent") is None
    
    def test_clear_summaries(self):
        """Test clearing summaries"""
        compactor = AdvancedCompactor()
        compactor._branch_summaries["branch1"] = BranchSummary(
            branch_id="branch1",
            summary="Test",
            entry_count=1,
            file_operations=[]
        )
        
        compactor.clear_summaries()
        assert len(compactor._branch_summaries) == 0


class TestCreateCompactPrompt:
    """Test create_compact_prompt"""
    
    def test_empty_entries(self):
        """Test with empty entries"""
        result = create_compact_prompt([])
        assert result == ""
    
    def test_message_entries(self):
        """Test with message entries"""
        entries = [
            MessageEntry(id="1", role="user", content="Hello"),
            MessageEntry(id="2", role="assistant", content="Hi"),
        ]
        result = create_compact_prompt(entries)
        
        assert "user: Hello" in result
        assert "assistant: Hi" in result
    
    def test_file_entries(self):
        """Test with file entries"""
        entries = [
            FileEntry(id="1", operation=FileOperation("test.py", FileOperationType.READ)),
            FileEntry(id="2", operation=FileOperation("out.py", FileOperationType.WRITE)),
        ]
        result = create_compact_prompt(entries)
        
        assert "[READ test.py]" in result
        assert "[WRITE out.py]" in result
    
    def test_truncation(self):
        """Test long content truncation"""
        entries = [
            MessageEntry(id="1", content="x" * 500),
        ]
        result = create_compact_prompt(entries)
        
        assert "..." in result
        assert len(result) < 600


class TestDataClasses:
    """Test dataclass functionality"""
    
    def test_file_operation_hash(self):
        """Test FileOperation hashing"""
        op1 = FileOperation("file.py", FileOperationType.READ, "hash1")
        op2 = FileOperation("file.py", FileOperationType.READ, "hash1")
        op3 = FileOperation("file.py", FileOperationType.READ, "hash2")
        
        assert op1 == op2
        assert op1 != op3
        assert hash(op1) == hash(op2)
    
    def test_session_entry_defaults(self):
        """Test SessionEntry default values"""
        entry = SessionEntry(id="1", type=EntryType.MESSAGE)
        
        assert entry.branch_id == "main"
        assert entry.timestamp > 0
        assert entry.metadata == {}
    
    def test_message_entry_post_init(self):
        """Test MessageEntry post_init"""
        entry = MessageEntry(id="1")
        
        assert entry.type == EntryType.MESSAGE
        assert entry.role == "user"
    
    def test_file_entry_post_init(self):
        """Test FileEntry post_init"""
        entry = FileEntry(id="1")
        
        assert entry.type == EntryType.FILE


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_compaction_workflow(self):
        """Test full compaction workflow"""
        summarizer_calls = []
        def summarizer(prompt):
            summarizer_calls.append(prompt)
            return "Workflow summary"
        
        compactor = AdvancedCompactor(
            max_tokens=50,
            reserve_tokens=10,
            summarizer=summarizer
        )
        
        # Create entries with file operations
        entries = [
            MessageEntry(id="1", role="user", content="Create a file"),
            FileEntry(id="2", operation=FileOperation("main.py", FileOperationType.WRITE)),
            FileEntry(id="3", operation=FileOperation("main.py", FileOperationType.READ)),  # Duplicate
            MessageEntry(id="4", role="assistant", content="Created"),
            MessageEntry(id="5", role="user", content="Edit it"),
            FileEntry(id="6", operation=FileOperation("main.py", FileOperationType.EDIT)),
            MessageEntry(id="7", content="x" * 100),  # Force compaction
        ]
        
        result, summary = await compactor.compact_with_summary(entries)
        
        # Verify compaction happened
        assert isinstance(result[0], CompactionEntry)
        assert summary.summary == "Workflow summary"
        
        # Verify file operations were tracked (WRITE kept, READ deduplicated, EDIT kept)
        assert len(summary.file_operations) >= 1  # At least WRITE should be tracked
