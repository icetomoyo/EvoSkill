"""
Advanced Compaction - Branch summarization and smart context management

Equivalent to Pi Mono's packages/coding-agent/src/core/compaction/ advanced features:
- findCutPoint: Find optimal split point for compaction
- collectEntriesForBranchSummary: Collect entries for summarization
- generateBranchSummary: LLM-powered branch summarization
- deduplicateFileOperations: Remove duplicate file operations
"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple, Set
from datetime import datetime
from enum import Enum
import hashlib


class EntryType(Enum):
    """Session entry types"""
    MESSAGE = "message"
    COMPACTION = "compaction"
    MODEL_CHANGE = "model_change"
    THINKING_LEVEL_CHANGE = "thinking_level_change"
    CUSTOM = "custom"
    FILE = "file"


class FileOperationType(Enum):
    """File operation types"""
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"


@dataclass
class FileOperation:
    """File operation record"""
    path: str
    operation: FileOperationType
    content_hash: Optional[str] = None
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    
    def __hash__(self):
        return hash((self.path, self.operation.value, self.content_hash))
    
    def __eq__(self, other):
        if not isinstance(other, FileOperation):
            return False
        return (self.path == other.path and 
                self.operation == other.operation and 
                self.content_hash == other.content_hash)


@dataclass
class SessionEntry:
    """Base session entry"""
    id: str
    type: EntryType = EntryType.CUSTOM
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    metadata: Dict[str, Any] = field(default_factory=dict)
    branch_id: str = "main"


@dataclass
class MessageEntry(SessionEntry):
    """Message entry"""
    role: str = "user"
    content: str = ""
    
    def __post_init__(self):
        if self.type == EntryType.CUSTOM:  # Only set if not explicitly provided
            self.type = EntryType.MESSAGE


@dataclass
class FileEntry(SessionEntry):
    """File operation entry"""
    operation: FileOperation = field(default_factory=lambda: FileOperation("", FileOperationType.READ))
    
    def __post_init__(self):
        if self.type == EntryType.CUSTOM:
            self.type = EntryType.FILE


@dataclass
class CompactionEntry(SessionEntry):
    """Compaction record entry"""
    summary: str = ""
    entries_summarized: int = 0
    
    def __post_init__(self):
        if self.type == EntryType.CUSTOM:
            self.type = EntryType.COMPACTION


@dataclass
class CollectEntriesResult:
    """Result of collecting entries for summary"""
    entries: List[SessionEntry]
    total_tokens: int
    file_operations: List[FileEntry]
    has_errors: bool


@dataclass
class CutPointResult:
    """Result of finding cut point"""
    index: int
    reason: str
    estimated_tokens_before: int
    estimated_tokens_after: int


@dataclass
class BranchSummary:
    """Summary of a conversation branch"""
    branch_id: str
    summary: str
    entry_count: int
    file_operations: List[FileOperation]
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


class TokenEstimator:
    """Token estimation utilities"""
    
    @staticmethod
    def estimate_text_tokens(text: str) -> int:
        """Estimate tokens for text (rough approximation)"""
        if not text:
            return 0
        # GPT-style tokenization: ~4 chars per token on average
        return len(text) // 4 + 1
    
    @staticmethod
    def estimate_message_tokens(message: Dict[str, Any]) -> int:
        """Estimate tokens for a message"""
        tokens = 4  # Base overhead per message
        
        content = message.get("content", "")
        if isinstance(content, str):
            tokens += TokenEstimator.estimate_text_tokens(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        tokens += TokenEstimator.estimate_text_tokens(item["text"])
                    elif "thinking" in item:
                        tokens += TokenEstimator.estimate_text_tokens(item["thinking"])
        
        # Add overhead for role and other fields
        tokens += 4
        
        return tokens
    
    @staticmethod
    def estimate_entry_tokens(entry: SessionEntry) -> int:
        """Estimate tokens for a session entry"""
        if isinstance(entry, MessageEntry):
            return TokenEstimator.estimate_text_tokens(entry.content) + 4
        elif isinstance(entry, FileEntry):
            # File operations are typically small
            return 20
        elif isinstance(entry, CompactionEntry):
            return TokenEstimator.estimate_text_tokens(entry.summary) + 4
        else:
            return 10  # Default


def find_cut_point(
    entries: List[SessionEntry],
    max_tokens: int,
    reserve_tokens: int = 4000,
    strategy: str = "balanced"
) -> CutPointResult:
    """
    Find optimal cut point for compaction
    
    Strategies:
    - "aggressive": Cut earlier to maximize token savings
    - "conservative": Cut later to preserve more context
    - "balanced": Balance between token savings and context preservation
    
    Args:
        entries: List of session entries
        max_tokens: Maximum allowed tokens
        reserve_tokens: Tokens to reserve for response
        strategy: Cut point strategy
        
    Returns:
        CutPointResult with index and metadata
    """
    if not entries:
        return CutPointResult(
            index=0,
            reason="empty_entries",
            estimated_tokens_before=0,
            estimated_tokens_after=0
        )
    
    available_tokens = max_tokens - reserve_tokens
    total_tokens = sum(TokenEstimator.estimate_entry_tokens(e) for e in entries)
    
    if total_tokens <= available_tokens:
        return CutPointResult(
            index=len(entries),
            reason="no_cut_needed",
            estimated_tokens_before=total_tokens,
            estimated_tokens_after=total_tokens
        )
    
    # Find cut point based on strategy
    tokens_needed_to_save = total_tokens - available_tokens
    current_tokens = 0
    cut_index = 0
    
    # Don't cut the last N messages (preserve recent context)
    min_keep_count = {
        "aggressive": 2,
        "balanced": 4,
        "conservative": 6
    }.get(strategy, 4)
    
    max_cut_index = max(len(entries) - min_keep_count, 1)
    
    # Find the cut point that saves enough tokens
    for i, entry in enumerate(entries[:max_cut_index]):
        entry_tokens = TokenEstimator.estimate_entry_tokens(entry)
        current_tokens += entry_tokens
        
        if current_tokens >= tokens_needed_to_save:
            cut_index = i + 1
            break
    else:
        # If we haven't saved enough, cut at max_cut_index
        cut_index = max_cut_index
    
    # Ensure we don't cut mid-conversation if possible
    cut_index = _adjust_cut_point(entries, cut_index)
    
    tokens_after = sum(TokenEstimator.estimate_entry_tokens(e) for e in entries[cut_index:])
    
    return CutPointResult(
        index=cut_index,
        reason=f"{strategy}_strategy",
        estimated_tokens_before=total_tokens,
        estimated_tokens_after=tokens_after
    )


def _adjust_cut_point(entries: List[SessionEntry], proposed_index: int) -> int:
    """
    Adjust cut point to avoid cutting mid-conversation
    
    Try to cut at:
    1. End of a user-assistant exchange
    2. Before a compaction entry
    3. Before a model change
    """
    if proposed_index >= len(entries):
        return len(entries)
    
    # Look for better cut points near the proposed index
    search_range = 3
    start = max(0, proposed_index - search_range)
    end = min(len(entries), proposed_index + search_range + 1)
    
    best_index = proposed_index
    
    for i in range(start, end):
        entry = entries[i]
        
        # Prefer cutting before special entries
        if entry.type in (EntryType.COMPACTION, EntryType.MODEL_CHANGE):
            best_index = i
            break
        
        # Prefer cutting after user message (before assistant response)
        if isinstance(entry, MessageEntry) and entry.role == "assistant":
            if i > 0:
                prev = entries[i - 1]
                if isinstance(prev, MessageEntry) and prev.role == "user":
                    # Good cut point: after complete exchange
                    best_index = i + 1
    
    return min(best_index, len(entries))


def collect_entries_for_branch_summary(
    entries: List[SessionEntry],
    cut_point: int,
    include_file_ops: bool = True
) -> CollectEntriesResult:
    """
    Collect entries for branch summary generation
    
    Args:
        entries: All session entries
        cut_point: Index to cut at
        include_file_ops: Whether to include file operations in result
        
    Returns:
        CollectEntriesResult with entries and metadata
    """
    if cut_point <= 0 or cut_point > len(entries):
        return CollectEntriesResult(
            entries=[],
            total_tokens=0,
            file_operations=[],
            has_errors=False
        )
    
    entries_to_summarize = entries[:cut_point]
    
    # Calculate total tokens
    total_tokens = sum(TokenEstimator.estimate_entry_tokens(e) for e in entries_to_summarize)
    
    # Collect file operations
    file_operations = []
    if include_file_ops:
        for entry in entries_to_summarize:
            if isinstance(entry, FileEntry):
                file_operations.append(entry)
    
    # Check for errors
    has_errors = any(
        isinstance(e, MessageEntry) and e.metadata.get("is_error")
        for e in entries_to_summarize
    )
    
    return CollectEntriesResult(
        entries=entries_to_summarize,
        total_tokens=total_tokens,
        file_operations=file_operations,
        has_errors=has_errors
    )


def deduplicate_file_operations(entries: List[SessionEntry]) -> List[SessionEntry]:
    """
    Remove duplicate/redundant file operations
    
    Rules:
    1. Multiple reads of same file -> keep only last
    2. Write followed by write to same file -> keep only last
    3. Read after write to same file -> remove read (data is stale)
    4. Edit after read -> keep both
    
    Args:
        entries: Session entries
        
    Returns:
        Entries with deduplicated file operations
    """
    result = []
    last_file_op: Dict[str, FileEntry] = {}
    
    for entry in entries:
        if not isinstance(entry, FileEntry):
            result.append(entry)
            continue
        
        path = entry.operation.path
        op_type = entry.operation.operation
        
        # Check if this operation is redundant
        if path in last_file_op:
            last_op = last_file_op[path].operation.operation
            
            # Skip duplicate reads
            if op_type == FileOperationType.READ and last_op == FileOperationType.READ:
                continue
            
            # Skip read after write (stale)
            if op_type == FileOperationType.READ and last_op == FileOperationType.WRITE:
                continue
            
            # Replace previous write with new write
            if op_type == FileOperationType.WRITE and last_op == FileOperationType.WRITE:
                # Remove previous write from result
                result = [e for e in result if e != last_file_op[path]]
        
        result.append(entry)
        last_file_op[path] = entry
    
    return result


def detect_file_patterns(file_ops: List[FileOperation]) -> Dict[str, Any]:
    """
    Detect patterns in file operations
    
    Returns:
        Dict with patterns like most_edited_files, file_types, etc.
    """
    if not file_ops:
        return {}
    
    # Count operations per file
    file_counts: Dict[str, Dict[str, int]] = {}
    for op in file_ops:
        if op.path not in file_counts:
            file_counts[op.path] = {"read": 0, "write": 0, "edit": 0, "delete": 0}
        file_counts[op.path][op.operation.value] += 1
    
    # Most edited files
    most_edited = sorted(
        file_counts.items(),
        key=lambda x: x[1]["edit"],
        reverse=True
    )[:5]
    
    # File extensions
    extensions: Dict[str, int] = {}
    for path in file_counts.keys():
        ext = path.split(".")[-1] if "." in path else "no_extension"
        extensions[ext] = extensions.get(ext, 0) + 1
    
    return {
        "most_edited_files": [f[0] for f in most_edited if f[1]["edit"] > 0],
        "most_read_files": sorted(
            file_counts.items(),
            key=lambda x: x[1]["read"],
            reverse=True
        )[:3],
        "file_types": extensions,
        "total_operations": len(file_ops),
        "unique_files": len(file_counts)
    }


async def generate_branch_summary(
    entries: List[SessionEntry],
    summarizer: Callable[[str], str],
    include_file_context: bool = True
) -> BranchSummary:
    """
    Generate LLM-powered summary of conversation branch
    
    Args:
        entries: Entries to summarize
        summarizer: Function that takes prompt and returns summary
        include_file_context: Whether to include file operation context
        
    Returns:
        BranchSummary with generated summary
    """
    if not entries:
        return BranchSummary(
            branch_id="main",
            summary="No entries to summarize",
            entry_count=0,
            file_operations=[]
        )
    
    # Build prompt for summarization
    lines = []
    file_ops = []
    
    for entry in entries:
        if isinstance(entry, MessageEntry):
            content = entry.content[:500]  # Truncate long messages
            lines.append(f"{entry.role.upper()}: {content}")
        
        elif isinstance(entry, FileEntry):
            file_ops.append(entry.operation)
            if include_file_context:
                lines.append(f"[FILE {entry.operation.operation.value.upper()}: {entry.operation.path}]")
    
    # Add file patterns
    file_patterns = detect_file_patterns(file_ops)
    if file_patterns and include_file_context:
        lines.append("\n[FILE STATISTICS]")
        if file_patterns.get("most_edited_files"):
            lines.append(f"Most edited: {', '.join(file_patterns['most_edited_files'][:3])}")
    
    prompt = f"""Summarize the following conversation excerpt concisely.

CONVERSATION:
{"\n".join(lines)}

Provide a brief summary (2-4 sentences) capturing:
1. What was discussed or accomplished
2. Any key decisions or findings
3. Important file operations (if any)

Summary:"""
    
    # Run summarization
    try:
        if asyncio.iscoroutinefunction(summarizer):
            summary_text = await summarizer(prompt)
        else:
            # Run sync function in thread
            loop = asyncio.get_event_loop()
            summary_text = await loop.run_in_executor(None, summarizer, prompt)
    except Exception as e:
        summary_text = f"Conversation with {len(entries)} entries ({len(file_ops)} file operations)"
    
    return BranchSummary(
        branch_id=entries[0].branch_id if entries else "main",
        summary=summary_text,
        entry_count=len(entries),
        file_operations=file_ops
    )


def should_compact(
    entries: List[SessionEntry],
    max_tokens: int,
    threshold_ratio: float = 0.8
) -> bool:
    """
    Determine if compaction is needed
    
    Args:
        entries: Session entries
        max_tokens: Maximum token limit
        threshold_ratio: Trigger compaction at this ratio of max_tokens
        
    Returns:
        True if compaction should be performed
    """
    total_tokens = sum(TokenEstimator.estimate_entry_tokens(e) for e in entries)
    threshold = max_tokens * threshold_ratio
    
    return total_tokens > threshold


class AdvancedCompactor:
    """
    Advanced compaction with branch summarization
    
    Equivalent to Pi Mono's full compaction system
    """
    
    def __init__(
        self,
        max_tokens: int = 128000,
        reserve_tokens: int = 4000,
        summarizer: Optional[Callable[[str], str]] = None
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.summarizer = summarizer
        self._branch_summaries: Dict[str, BranchSummary] = {}
    
    async def compact_with_summary(
        self,
        entries: List[SessionEntry],
        branch_id: str = "main",
        strategy: str = "balanced"
    ) -> Tuple[List[SessionEntry], BranchSummary]:
        """
        Compact entries and generate branch summary
        
        Args:
            entries: All entries
            branch_id: Branch identifier
            strategy: Compaction strategy
            
        Returns:
            Tuple of (remaining entries, branch summary)
        """
        # Check if compaction needed
        if not should_compact(entries, self.max_tokens):
            return entries, BranchSummary(
                branch_id=branch_id,
                summary="",
                entry_count=0,
                file_operations=[]
            )
        
        # Find cut point
        cut_result = find_cut_point(
            entries,
            self.max_tokens,
            self.reserve_tokens,
            strategy
        )
        
        if cut_result.index == 0 or cut_result.index >= len(entries):
            # No cut needed or can't cut
            return entries, BranchSummary(
                branch_id=branch_id,
                summary="",
                entry_count=0,
                file_operations=[]
            )
        
        # Collect entries for summary
        collect_result = collect_entries_for_branch_summary(
            entries,
            cut_result.index
        )
        
        # Deduplicate file operations
        deduplicated = deduplicate_file_operations(collect_result.entries)
        
        # Generate summary
        if self.summarizer:
            summary = await generate_branch_summary(
                deduplicated,
                self.summarizer
            )
        else:
            summary = BranchSummary(
                branch_id=branch_id,
                summary=f"Earlier conversation ({len(deduplicated)} entries)",
                entry_count=len(deduplicated),
                file_operations=[e.operation for e in collect_result.file_operations]
            )
        
        # Store summary
        self._branch_summaries[branch_id] = summary
        
        # Create compaction entry
        compaction_entry = CompactionEntry(
            id=f"compaction_{int(datetime.now().timestamp() * 1000)}",
            summary=summary.summary,
            entries_summarized=summary.entry_count,
            metadata={
                "file_operations": len(summary.file_operations),
                "original_tokens": cut_result.estimated_tokens_before,
                "new_tokens": cut_result.estimated_tokens_after,
            }
        )
        
        # Return remaining entries with compaction entry prepended
        remaining = entries[cut_result.index:]
        result = [compaction_entry] + remaining
        
        return result, summary
    
    def get_branch_summary(self, branch_id: str) -> Optional[BranchSummary]:
        """Get stored summary for branch"""
        return self._branch_summaries.get(branch_id)
    
    def clear_summaries(self) -> None:
        """Clear all stored summaries"""
        self._branch_summaries.clear()


def create_compact_prompt(entries: List[SessionEntry]) -> str:
    """
    Create a compact string representation of entries for LLM summarization
    
    Args:
        entries: Session entries
        
    Returns:
        Compact string representation
    """
    lines = []
    
    for entry in entries:
        if isinstance(entry, MessageEntry):
            # Truncate long messages
            content = entry.content[:300] + "..." if len(entry.content) > 300 else entry.content
            lines.append(f"{entry.role}: {content}")
        
        elif isinstance(entry, FileEntry):
            lines.append(f"[{entry.operation.operation.value.upper()} {entry.operation.path}]")
        
        elif isinstance(entry, CompactionEntry):
            lines.append(f"[COMPACTED: {entry.summary[:100]}...]")
    
    return "\n".join(lines)


# Utility function for simple token counting
def count_tokens_simple(text: str) -> int:
    """Simple token count estimation"""
    return len(text) // 4 + 1
