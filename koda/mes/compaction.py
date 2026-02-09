"""
Compaction - Context window management with summarization
Equivalent to Pi Mono's packages/coding-agent/src/core/compaction/

Strategies:
1. Simple truncation - Remove oldest messages
2. Branch summarization - Summarize side branches
3. Smart compaction - Keep important messages, summarize others
"""
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime


class CompactionStrategy(Enum):
    """Compaction strategies"""
    TRUNCATE_OLDEST = "truncate_oldest"
    SUMMARIZE_BRANCH = "summarize_branch"
    SMART_COMPACT = "smart_compact"


@dataclass
class CompactionSummary:
    """Summary of a compacted conversation segment"""
    id: str
    original_message_count: int
    summary: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "original_message_count": self.original_message_count,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class CompactionResult:
    """Result of a compaction operation"""
    original_count: int
    compacted_count: int
    removed_count: int
    summaries: List[CompactionSummary] = field(default_factory=list)
    strategy_used: CompactionStrategy = CompactionStrategy.TRUNCATE_OLDEST
    
    @property
    def reduction_ratio(self) -> float:
        if self.original_count == 0:
            return 0.0
        return (self.original_count - self.compacted_count) / self.original_count


class MessageCompactor:
    """
    Compacts message history to fit within context window.
    Equivalent to Pi Mono's compaction system.
    """
    
    def __init__(
        self,
        max_tokens: int = 128000,
        reserve_tokens: int = 4000,
        summarizer: Optional[Callable[[List[Dict]], str]] = None
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.summarizer = summarizer
        self._summaries: Dict[str, CompactionSummary] = {}
    
    def compact(
        self,
        messages: List[Dict],
        current_tokens: int,
        strategy: CompactionStrategy = CompactionStrategy.SMART_COMPACT,
        keep_system: bool = True
    ) -> CompactionResult:
        """
        Compact messages to fit within token limit.
        
        Args:
            messages: List of message dicts with 'role', 'content', etc.
            current_tokens: Current token count
            strategy: Compaction strategy to use
            keep_system: Whether to preserve system messages
        
        Returns:
            CompactionResult with new message list
        """
        available_tokens = self.max_tokens - self.reserve_tokens
        
        if current_tokens <= available_tokens:
            return CompactionResult(
                original_count=len(messages),
                compacted_count=len(messages),
                removed_count=0,
                strategy_used=strategy
            )
        
        if strategy == CompactionStrategy.TRUNCATE_OLDEST:
            return self._truncate_oldest(messages, available_tokens, keep_system)
        elif strategy == CompactionStrategy.SUMMARIZE_BRANCH:
            return self._summarize_branch(messages, available_tokens, keep_system)
        else:
            return self._smart_compact(messages, available_tokens, keep_system)
    
    def _truncate_oldest(
        self, 
        messages: List[Dict], 
        max_tokens: int,
        keep_system: bool
    ) -> CompactionResult:
        """Simple truncation - remove oldest messages"""
        if keep_system:
            system_msgs = [m for m in messages if m.get("role") == "system"]
            other_msgs = [m for m in messages if m.get("role") != "system"]
        else:
            system_msgs = []
            other_msgs = messages
        
        # Keep removing from the front until under limit
        # (This is simplified - real implementation would use token counts)
        removed = 0
        while len(other_msgs) > 2 and len(messages) - removed > 10:
            other_msgs.pop(0)
            removed += 1
        
        result = CompactionResult(
            original_count=len(messages),
            compacted_count=len(system_msgs) + len(other_msgs),
            removed_count=removed,
            strategy_used=CompactionStrategy.TRUNCATE_OLDEST
        )
        
        return result
    
    def _summarize_branch(
        self,
        messages: List[Dict],
        max_tokens: int,
        keep_system: bool
    ) -> CompactionResult:
        """
        Summarize conversation branches.
        Keeps recent messages, summarizes older ones.
        """
        if not self.summarizer:
            # Fall back to truncation if no summarizer
            return self._truncate_oldest(messages, max_tokens, keep_system)
        
        # Split messages into recent and older
        split_point = max(len(messages) // 2, 5)
        older_msgs = messages[:split_point]
        recent_msgs = messages[split_point:]
        
        # Summarize older messages
        try:
            summary_text = self.summarizer(older_msgs)
            summary = CompactionSummary(
                id=f"summary_{datetime.now().timestamp()}",
                original_message_count=len(older_msgs),
                summary=summary_text,
                metadata={"type": "branch_summary"}
            )
            
            # Create summary message
            summary_msg = {
                "role": "system",
                "content": f"[Earlier conversation summary]: {summary_text}",
                "_compaction_summary": True,
                "_original_count": len(older_msgs)
            }
            
            system_msgs = []
            if keep_system:
                system_msgs = [m for m in recent_msgs if m.get("role") == "system"]
                recent_msgs = [m for m in recent_msgs if m.get("role") != "system"]
            
            compacted = system_msgs + [summary_msg] + recent_msgs
            
            return CompactionResult(
                original_count=len(messages),
                compacted_count=len(compacted),
                removed_count=len(older_msgs) - 1,
                summaries=[summary],
                strategy_used=CompactionStrategy.SUMMARIZE_BRANCH
            )
        except Exception as e:
            # Fall back to truncation on error
            return self._truncate_oldest(messages, max_tokens, keep_system)
    
    def _smart_compact(
        self,
        messages: List[Dict],
        max_tokens: int,
        keep_system: bool
    ) -> CompactionResult:
        """
        Smart compaction - prioritize important messages.
        
        Priority order:
        1. System messages
        2. Tool results with errors
        3. Recent user messages
        4. Recent assistant messages
        5. Older messages (summarized or removed)
        """
        if not self.summarizer:
            return self._truncate_oldest(messages, max_tokens, keep_system)
        
        # Categorize messages by importance
        system_msgs = []
        important_msgs = []
        normal_msgs = []
        
        for msg in messages:
            role = msg.get("role", "")
            
            if role == "system":
                system_msgs.append(msg)
            elif role == "tool" and msg.get("is_error"):
                important_msgs.append(msg)
            elif role == "user" and msg.get("tool_calls"):
                important_msgs.append(msg)
            else:
                normal_msgs.append(msg)
        
        # Keep recent 50% of normal messages, summarize rest
        keep_count = max(len(normal_msgs) // 2, 3)
        recent_normal = normal_msgs[-keep_count:]
        older_normal = normal_msgs[:-keep_count]
        
        summaries = []
        if older_normal:
            try:
                summary_text = self.summarizer(older_normal)
                summary = CompactionSummary(
                    id=f"smart_{datetime.now().timestamp()}",
                    original_message_count=len(older_normal),
                    summary=summary_text,
                    metadata={"type": "smart_summary", "kept": len(recent_normal)}
                )
                summaries.append(summary)
                
                summary_msg = {
                    "role": "system",
                    "content": f"[Summary of earlier messages]: {summary_text}",
                    "_compaction_summary": True
                }
                
                compacted = system_msgs + [summary_msg] + important_msgs + recent_normal
            except Exception:
                compacted = system_msgs + important_msgs + recent_normal
        else:
            compacted = system_msgs + important_msgs + recent_normal
        
        return CompactionResult(
            original_count=len(messages),
            compacted_count=len(compacted),
            removed_count=len(messages) - len(compacted),
            summaries=summaries,
            strategy_used=CompactionStrategy.SMART_COMPACT
        )
    
    def estimate_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count for messages (simplified)"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Rough estimate: 1 token per 4 characters
                total += len(content) // 4
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        total += len(item["text"]) // 4
        return total + len(messages) * 4  # Add overhead per message


class ConversationBranch:
    """
    Represents a conversation branch for tree-based compaction.
    Equivalent to Pi Mono's branch management.
    """
    
    def __init__(self, id: str, parent_id: Optional[str] = None):
        self.id = id
        self.parent_id = parent_id
        self.messages: List[Dict] = []
        self.summaries: List[CompactionSummary] = []
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, message: Dict) -> None:
        """Add a message to this branch"""
        self.messages.append(message)
    
    def get_full_context(self, include_summaries: bool = True) -> List[Dict]:
        """Get full conversation context with optional summaries"""
        if not include_summaries or not self.summaries:
            return self.messages
        
        # Insert summaries before their respective positions
        result = []
        for msg in self.messages:
            # Add any summaries that should appear before this message
            for summary in self.summaries:
                if summary.metadata.get("insert_before") == id(msg):
                    result.append({
                        "role": "system",
                        "content": f"[Summary]: {summary.summary}",
                        "_is_summary": True
                    })
            result.append(msg)
        
        return result
    
    def compact(
        self,
        compactor: MessageCompactor,
        max_tokens: Optional[int] = None
    ) -> CompactionResult:
        """Compact this branch"""
        tokens = compactor.estimate_tokens(self.messages)
        result = compactor.compact(
            self.messages,
            tokens,
            strategy=CompactionStrategy.SMART_COMPACT
        )
        self.summaries.extend(result.summaries)
        return result


# Utility functions

def create_simple_summarizer(provider_fn: Callable[[str], str]) -> Callable[[List[Dict]], str]:
    """
    Create a simple summarizer from a provider function.
    
    Args:
        provider_fn: Function that takes a prompt and returns summary
    
    Returns:
        Summarizer function for MessageCompactor
    """
    def summarizer(messages: List[Dict]) -> str:
        # Extract content from messages
        texts = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "unknown")
            if content:
                texts.append(f"{role}: {content[:200]}")  # Truncate long messages
        
        prompt = """Summarize the following conversation concisely:

""" + "\n".join(texts) + """

Provide a brief summary (2-3 sentences) of what was discussed:"""
        
        try:
            return provider_fn(prompt)
        except Exception as e:
            return f"Conversation with {len(messages)} messages"
    
    return summarizer
