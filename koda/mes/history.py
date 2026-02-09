"""
History Manager

Manages conversation history with compaction support.
Similar to Pi's session compaction.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from koda.ai.provider import Message
from koda.mes.optimizer import MessageOptimizer


@dataclass
class CompactionResult:
    """Result of history compaction"""
    success: bool
    summary: str
    original_count: int
    compacted_count: int
    tokens_saved: int


class HistoryManager:
    """
    Manages conversation history
    
    Features:
    - Tree-based branching
    - Automatic compaction
    - Token usage tracking
    - Session persistence
    """
    
    def __init__(
        self,
        max_tokens: int = 128000,
        compaction_threshold: float = 0.75,
        storage_path: Optional[Path] = None
    ):
        """
        Args:
            max_tokens: Maximum context window
            compaction_threshold: Trigger compaction at this ratio
            storage_path: Path for persistent storage
        """
        self.max_tokens = max_tokens
        self.compaction_threshold = compaction_threshold
        self.storage_path = storage_path
        self.optimizer = MessageOptimizer(max_tokens, compaction_threshold)
        
        # In-memory history
        self._messages: List[Message] = []
        self._branches: Dict[str, List[Message]] = {}
        self._current_branch: str = "main"
        
        # Metadata
        self._token_usage: List[int] = []
        self._last_compaction: Optional[datetime] = None
    
    def add_message(self, message: Message) -> None:
        """
        Add message to history
        
        Args:
            message: Message to add
        """
        self._messages.append(message)
        
        # Check if compaction needed
        if self.should_compact():
            self.compact()
    
    def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get recent messages
        
        Args:
            limit: Maximum number of messages
            
        Returns:
            List of messages
        """
        if limit is None:
            return list(self._messages)
        return self._messages[-limit:]
    
    def should_compact(self) -> bool:
        """Check if history needs compaction"""
        return self.optimizer.should_compact(self._messages)
    
    def compact(self, custom_instructions: Optional[str] = None) -> CompactionResult:
        """
        Compact history to fit within token limit
        
        Args:
            custom_instructions: Optional instructions for summarization
            
        Returns:
            CompactionResult with summary
        """
        original_count = len(self._messages)
        original_tokens = self.optimizer.count_tokens(self._messages)
        
        # Use optimizer
        result = self.optimizer.optimize(self._messages, aggressive=True)
        self._messages = result.messages
        
        # Update metadata
        self._last_compaction = datetime.now()
        self._token_usage.append(result.optimized_tokens)
        
        # Generate summary
        summary = self._generate_summary(original_count, len(self._messages), result.savings)
        
        return CompactionResult(
            success=True,
            summary=summary,
            original_count=original_count,
            compacted_count=len(self._messages),
            tokens_saved=result.savings,
        )
    
    def _generate_summary(
        self,
        original: int,
        compacted: int,
        tokens_saved: int
    ) -> str:
        """Generate human-readable summary"""
        messages_removed = original - compacted
        
        parts = ["History compacted:"]
        if messages_removed > 0:
            parts.append(f"{messages_removed} messages summarized")
        parts.append(f"{tokens_saved} tokens saved")
        
        return "; ".join(parts)
    
    def branch(self, branch_name: str, from_message_id: Optional[str] = None) -> None:
        """
        Create new branch from current position
        
        Args:
            branch_name: Name for new branch
            from_message_id: Message ID to branch from (default: current end)
        """
        # Save current branch
        self._branches[self._current_branch] = list(self._messages)
        
        # Create new branch
        if from_message_id:
            # Find message index
            idx = None
            for i, msg in enumerate(self._messages):
                if getattr(msg, 'id', None) == from_message_id:
                    idx = i
                    break
            
            if idx is not None:
                self._messages = self._messages[:idx + 1]
        
        self._current_branch = branch_name
        self._branches[branch_name] = list(self._messages)
    
    def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to existing branch
        
        Args:
            branch_name: Branch to switch to
            
        Returns:
            True if successful
        """
        if branch_name in self._branches:
            # Save current
            self._branches[self._current_branch] = list(self._messages)
            # Switch
            self._messages = list(self._branches[branch_name])
            self._current_branch = branch_name
            return True
        return False
    
    def list_branches(self) -> List[str]:
        """List all branch names"""
        return list(self._branches.keys()) + [self._current_branch]
    
    def clear(self) -> None:
        """Clear all history"""
        self._messages = []
        self._branches = {}
        self._current_branch = "main"
        self._token_usage = []
    
    def save(self, path: Optional[Path] = None) -> None:
        """
        Save history to JSONL
        
        Args:
            path: File path (uses storage_path if not specified)
        """
        save_path = path or self.storage_path
        if not save_path:
            raise ValueError("No storage path specified")
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            # Save metadata
            metadata = {
                "version": "1.0",
                "branch": self._current_branch,
                "timestamp": datetime.now().isoformat(),
                "message_count": len(self._messages),
            }
            f.write(json.dumps({"_meta": metadata}, ensure_ascii=False) + '\n')
            
            # Save messages
            for msg in self._messages:
                data = {
                    "role": msg.role,
                    "content": msg.content,
                }
                if msg.tool_calls:
                    data["tool_calls"] = [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in msg.tool_calls
                    ]
                if msg.tool_call_id:
                    data["tool_call_id"] = msg.tool_call_id
                if msg.name:
                    data["name"] = msg.name
                
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    def load(self, path: Optional[Path] = None) -> bool:
        """
        Load history from JSONL
        
        Args:
            path: File path (uses storage_path if not specified)
            
        Returns:
            True if successful
        """
        load_path = path or self.storage_path
        if not load_path or not load_path.exists():
            return False
        
        self.clear()
        
        with open(load_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                data = json.loads(line)
                
                # Skip metadata
                if "_meta" in data:
                    self._current_branch = data["_meta"].get("branch", "main")
                    continue
                
                # Parse message
                tool_calls = None
                if "tool_calls" in data:
                    tool_calls = [
                        ToolCall(tc["id"], tc["name"], tc.get("arguments", {}))
                        for tc in data["tool_calls"]
                    ]
                
                msg = Message(
                    role=data["role"],
                    content=data["content"],
                    tool_calls=tool_calls,
                    tool_call_id=data.get("tool_call_id"),
                    name=data.get("name"),
                )
                self._messages.append(msg)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics"""
        return {
            "message_count": len(self._messages),
            "branch_count": len(self._branches) + 1,
            "current_branch": self._current_branch,
            "estimated_tokens": self.optimizer.count_tokens(self._messages),
            "max_tokens": self.max_tokens,
            "last_compaction": self._last_compaction.isoformat() if self._last_compaction else None,
        }


# Import for type hints
from koda.ai.provider import ToolCall
