"""
Session Compactor
等效于 Pi-Mono 的 packages/coding-agent/src/core/compaction/compaction.ts

会话压缩核心实现。
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .base import (
    CompactionStrategy, 
    CompactionResult, 
    CompactorConfig,
    MessagePriorityCalculator,
)
from .utils import calculate_tokens, should_compact, compact_tool_result


@dataclass
class CompactibleMessage:
    """可压缩消息包装"""
    original: Dict[str, Any]
    priority: int
    index: int
    estimated_tokens: int


class SessionCompactor:
    """
    会话压缩器
    
    压缩长会话以保持在token限制内。
    
    Example:
        >>> compactor = SessionCompactor()
        >>> result = await compactor.compact(messages)
        >>> print(f"Saved {result.tokens_saved} tokens")
    """
    
    def __init__(self, config: Optional[CompactorConfig] = None):
        self.config = config or CompactorConfig()
        self.strategy = self.config.strategy
    
    async def compact(
        self, 
        messages: List[Dict[str, Any]],
        force: bool = False,
    ) -> CompactionResult:
        """
        压缩消息列表
        
        Args:
            messages: 原始消息列表
            force: 是否强制压缩（忽略阈值）
        
        Returns:
            压缩结果
        """
        # Calculate current tokens
        original_tokens = calculate_tokens(
            messages, 
            self.config.token_calculator
        )
        
        # Check if compaction needed
        if not force and not should_compact(
            messages, 
            self.strategy.max_tokens,
            self.strategy.compact_threshold,
        ):
            return CompactionResult(
                messages=messages.copy(),
                original_tokens=original_tokens,
                final_tokens=original_tokens,
                was_compacted=False,
            )
        
        self._log(f"Compacting session: {original_tokens} tokens -> target {self.strategy.max_tokens}")
        
        # Phase 1: Separate preserved and compactible messages
        preserved, compactible = self._separate_messages(messages)
        
        preserved_tokens = calculate_tokens(preserved, self.config.token_calculator)
        available_tokens = self.strategy.max_tokens - preserved_tokens
        
        self._log(f"Preserved {len(preserved)} messages ({preserved_tokens} tokens)")
        self._log(f"Available for compaction: {available_tokens} tokens")
        
        # Phase 2: Compress compactible messages
        compressed = await self._compress_messages(
            compactible, 
            available_tokens,
        )
        
        # Combine results
        final_messages = preserved + compressed
        final_tokens = calculate_tokens(final_messages, self.config.token_calculator)
        
        # Generate summary if enabled
        summary = None
        if self.strategy.enable_summarization and self.config.summarizer:
            summary = await self._generate_summary(compactible)
        
        result = CompactionResult(
            messages=final_messages,
            summary=summary,
            original_tokens=original_tokens,
            final_tokens=final_tokens,
            removed_count=len(messages) - len(final_messages),
            was_compacted=True,
        )
        
        self._log(f"Compaction complete: {result.tokens_saved} tokens saved ({result.compression_ratio:.1%})")
        
        return result
    
    def _separate_messages(
        self, 
        messages: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[CompactibleMessage]]:
        """
        分离保留消息和可压缩消息
        
        Returns:
            (保留消息, 可压缩消息)
        """
        preserved = []
        compactible = []
        
        # Always preserve the most recent N messages
        recent_cutoff = max(0, len(messages) - self.strategy.preserve_recent)
        
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            
            # Determine if message should be preserved
            should_preserve = False
            
            # Recent messages
            if i >= recent_cutoff:
                should_preserve = True
            
            # System messages
            elif role == "system" and self.strategy.preserve_system:
                should_preserve = True
            
            # Tool calls (if configured)
            elif role == "assistant" and self.strategy.preserve_tool_calls:
                if msg.get("tool_calls") or msg.get("function_call"):
                    should_preserve = True
            
            # Tool results with errors
            elif role == "tool":
                content = str(msg.get("content", ""))
                if "error" in content.lower():
                    should_preserve = True
            
            if should_preserve:
                preserved.append(msg)
            else:
                priority = MessagePriorityCalculator.calculate(msg)
                tokens = calculate_tokens([msg], self.config.token_calculator)
                compactible.append(CompactibleMessage(
                    original=msg,
                    priority=priority.value if hasattr(priority, 'value') else 50,
                    index=i,
                    estimated_tokens=tokens,
                ))
        
        return preserved, compactible
    
    async def _compress_messages(
        self,
        messages: List[CompactibleMessage],
        available_tokens: int,
    ) -> List[Dict[str, Any]]:
        """
        压缩消息列表
        
        策略：
        1. 按优先级排序
        2. 优先保留高优先级消息
        3. 对低优先级消息进行截断或删除
        """
        if not messages:
            return []
        
        # Sort by priority (high first), then by index (recent first)
        sorted_msgs = sorted(
            messages,
            key=lambda m: (-m.priority, -m.index),
        )
        
        result = []
        remaining_tokens = available_tokens
        
        for msg in sorted_msgs:
            if remaining_tokens <= 0:
                break
            
            if msg.estimated_tokens <= remaining_tokens:
                # Keep full message
                result.append(msg.original)
                remaining_tokens -= msg.estimated_tokens
            else:
                # Try to truncate
                truncated = self._truncate_message(
                    msg.original,
                    remaining_tokens,
                )
                if truncated:
                    result.append(truncated)
                    remaining_tokens = 0
        
        # Sort back to original order
        result.sort(key=lambda m: messages.index(next(
            cm for cm in messages if cm.original is m
        )) if any(cm.original is m for cm in messages) else 0)
        
        return result
    
    def _truncate_message(
        self,
        message: Dict[str, Any],
        max_tokens: int,
    ) -> Optional[Dict[str, Any]]:
        """
        截断单个消息
        """
        if max_tokens < 10:
            return None
        
        content = message.get("content", "")
        if not isinstance(content, str):
            # Can't truncate non-string content easily
            return message
        
        # Estimate truncation point
        avg_tokens_per_char = 0.25  # Rough estimate
        max_chars = int(max_tokens / avg_tokens_per_char)
        
        truncated_content = content[:max_chars] + "..."
        
        return {
            **message,
            "content": truncated_content,
            "_truncated": True,
        }
    
    async def _generate_summary(
        self,
        messages: List[CompactibleMessage],
    ) -> Optional[str]:
        """
        生成会话摘要
        """
        if not self.config.summarizer:
            return None
        
        try:
            original_msgs = [m.original for m in messages]
            return await self.config.summarizer(original_msgs)
        except Exception as e:
            self._log(f"Summary generation failed: {e}")
            return None
    
    def _log(self, message: str) -> None:
        """记录日志"""
        if self.config.log_callback:
            self.config.log_callback(message)
    
    async def compact_stream(
        self,
        messages: List[Dict[str, Any]],
        callback: Optional[Callable[[str], None]] = None,
    ) -> CompactionResult:
        """
        流式压缩（带进度回调）
        """
        original_callback = self.config.log_callback
        
        def combined_log(msg: str):
            if original_callback:
                original_callback(msg)
            if callback:
                callback(msg)
        
        self.config.log_callback = combined_log
        
        try:
            return await self.compact(messages)
        finally:
            self.config.log_callback = original_callback


class IncrementalCompactor:
    """
    增量压缩器
    
    在会话过程中逐步压缩，避免突然大量压缩。
    """
    
    def __init__(self, config: Optional[CompactorConfig] = None):
        self.config = config or CompactorConfig()
        self.history: List[CompactionResult] = []
    
    async def maybe_compact(
        self,
        messages: List[Dict[str, Any]],
    ) -> Optional[CompactionResult]:
        """
        检查并可能执行压缩
        
        使用更激进的策略：在达到80%时就开始压缩
        """
        current_tokens = calculate_tokens(messages)
        threshold = self.config.strategy.max_tokens * 0.8
        
        if current_tokens < threshold:
            return None
        
        compactor = SessionCompactor(self.config)
        result = await compactor.compact(messages)
        
        if result.was_compacted:
            self.history.append(result)
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取压缩统计"""
        if not self.history:
            return {
                "total_compactions": 0,
                "total_tokens_saved": 0,
            }
        
        return {
            "total_compactions": len(self.history),
            "total_tokens_saved": sum(r.tokens_saved for r in self.history),
            "avg_compression_ratio": sum(r.compression_ratio for r in self.history) / len(self.history),
        }


__all__ = [
    "SessionCompactor",
    "IncrementalCompactor",
    "CompactibleMessage",
]
