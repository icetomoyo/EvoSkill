"""
Branch Summarizer
等效于 Pi-Mono 的 packages/coding-agent/src/core/compaction/branch-summarization.ts

分支摘要生成和管理。
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from .utils import extract_key_points, format_summary, calculate_tokens


@dataclass
class BranchSummary:
    """分支摘要"""
    
    # 唯一标识
    id: str
    
    # 分支名称/路径
    branch_path: str
    
    # 摘要内容
    summary: str
    
    # 关键要点
    key_points: List[str]
    
    # 统计信息
    message_count: int
    token_count: int
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "branch_path": self.branch_path,
            "summary": self.summary,
            "key_points": self.key_points,
            "message_count": self.message_count,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BranchSummary":
        """从字典创建"""
        return cls(
            id=data["id"],
            branch_path=data["branch_path"],
            summary=data["summary"],
            key_points=data.get("key_points", []),
            message_count=data.get("message_count", 0),
            token_count=data.get("token_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


class BranchSummarizer:
    """
    分支摘要器
    
    为会话分支生成和管理摘要。
    
    Example:
        >>> summarizer = BranchSummarizer()
        >>> summary = await summarizer.summarize_branch(messages, "feature/auth")
        >>> print(summary.key_points)
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        summary_model: Optional[str] = None,
    ):
        self.llm_client = llm_client
        self.summary_model = summary_model
        self._summaries: Dict[str, BranchSummary] = {}
    
    async def summarize_branch(
        self,
        messages: List[Dict[str, Any]],
        branch_path: str,
        force_refresh: bool = False,
    ) -> BranchSummary:
        """
        为分支生成摘要
        
        Args:
            messages: 分支消息
            branch_path: 分支路径
            force_refresh: 强制刷新
        
        Returns:
            分支摘要
        """
        # Check cache
        cache_key = self._generate_cache_key(messages, branch_path)
        
        if not force_refresh and cache_key in self._summaries:
            cached = self._summaries[cache_key]
            # Check if messages changed
            if cached.metadata.get("cache_key") == cache_key:
                return cached
        
        # Generate summary
        summary_text = await self._generate_summary(messages)
        key_points = extract_key_points(summary_text)
        
        summary = BranchSummary(
            id=cache_key,
            branch_path=branch_path,
            summary=summary_text,
            key_points=key_points,
            message_count=len(messages),
            token_count=calculate_tokens(messages),
            metadata={
                "cache_key": cache_key,
                "generated_by": self.summary_model or "default",
            },
        )
        
        # Cache result
        self._summaries[cache_key] = summary
        
        return summary
    
    async def _generate_summary(
        self,
        messages: List[Dict[str, Any]],
    ) -> str:
        """
        生成摘要文本
        
        如果有LLM客户端，使用它；否则使用启发式方法
        """
        if self.llm_client and self.summary_model:
            return await self._generate_with_llm(messages)
        
        return self._generate_heuristic(messages)
    
    async def _generate_with_llm(
        self,
        messages: List[Dict[str, Any]],
    ) -> str:
        """使用LLM生成摘要"""
        # Build prompt
        context = self._extract_context(messages)
        
        prompt = f"""Summarize the following conversation in 2-3 sentences:

{context}

Summary:"""
        
        try:
            # This would call the LLM client
            # response = await self.llm_client.complete(prompt)
            # return response.text
            return "LLM summary not implemented in this version"
        except Exception as e:
            # Fallback to heuristic
            return self._generate_heuristic(messages)
    
    def _generate_heuristic(self, messages: List[Dict[str, Any]]) -> str:
        """启发式生成摘要"""
        # Count message types
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        
        # Extract topics from user queries
        topics = []
        for msg in user_msgs[:3]:  # First 3 user messages
            content = str(msg.get("content", ""))
            # Simple topic extraction
            if content:
                topics.append(content[:50] + "..." if len(content) > 50 else content)
        
        # Check for errors
        has_errors = any(
            "error" in str(m.get("content", "")).lower() 
            for m in tool_msgs
        )
        
        # Build summary
        parts = [
            f"Branch contains {len(messages)} messages",
            f"({len(user_msgs)} user, {len(assistant_msgs)} assistant, {len(tool_msgs)} tool).",
        ]
        
        if topics:
            parts.append(f"Topics: {', '.join(topics[:2])}.")
        
        if has_errors:
            parts.append("Some tool executions encountered errors.")
        
        return " ".join(parts)
    
    def _extract_context(self, messages: List[Dict[str, Any]]) -> str:
        """提取对话上下文"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            
            # Truncate long content
            if len(content) > 200:
                content = content[:200] + "..."
            
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def _generate_cache_key(
        self,
        messages: List[Dict[str, Any]],
        branch_path: str,
    ) -> str:
        """生成缓存键"""
        content = f"{branch_path}:{len(messages)}:{hash(str(messages))}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_summary(self, branch_path: str) -> Optional[BranchSummary]:
        """获取已存在的摘要"""
        for summary in self._summaries.values():
            if summary.branch_path == branch_path:
                return summary
        return None
    
    def list_summaries(self) -> List[BranchSummary]:
        """列出所有摘要"""
        return list(self._summaries.values())
    
    def delete_summary(self, summary_id: str) -> bool:
        """删除摘要"""
        if summary_id in self._summaries:
            del self._summaries[summary_id]
            return True
        return False
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._summaries.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._summaries:
            return {"count": 0}
        
        total_messages = sum(s.message_count for s in self._summaries.values())
        total_tokens = sum(s.token_count for s in self._summaries.values())
        
        return {
            "count": len(self._summaries),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "avg_messages_per_branch": total_messages / len(self._summaries),
        }


class BranchSummaryStore:
    """
    分支摘要存储
    
    持久化存储分支摘要。
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._data: Dict[str, BranchSummary] = {}
        
        if storage_path:
            self._load()
    
    def save(self, summary: BranchSummary) -> None:
        """保存摘要"""
        self._data[summary.id] = summary
        self._persist()
    
    def load(self, summary_id: str) -> Optional[BranchSummary]:
        """加载摘要"""
        return self._data.get(summary_id)
    
    def list_all(self) -> List[BranchSummary]:
        """列出所有"""
        return list(self._data.values())
    
    def delete(self, summary_id: str) -> bool:
        """删除"""
        if summary_id in self._data:
            del self._data[summary_id]
            self._persist()
            return True
        return False
    
    def _load(self) -> None:
        """从磁盘加载"""
        import json
        from pathlib import Path
        
        path = Path(self.storage_path)
        if not path.exists():
            return
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            for item in data.values():
                summary = BranchSummary.from_dict(item)
                self._data[summary.id] = summary
        except Exception:
            pass
    
    def _persist(self) -> None:
        """持久化到磁盘"""
        import json
        from pathlib import Path
        
        if not self.storage_path:
            return
        
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {k: v.to_dict() for k, v in self._data.items()}
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


__all__ = [
    "BranchSummary",
    "BranchSummarizer",
    "BranchSummaryStore",
]
