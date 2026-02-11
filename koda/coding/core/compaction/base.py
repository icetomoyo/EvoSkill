"""
Compaction Base Classes
等效于 Pi-Mono 的 packages/coding-agent/src/core/compaction/index.ts

会话压缩的基础类和配置。
"""

from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class CompactionPriority(Enum):
    """消息优先级（用于决定哪些消息保留）"""
    CRITICAL = 4   # 系统消息、关键工具结果
    HIGH = 3       # 用户消息、助手消息（含工具调用）
    MEDIUM = 2     # 普通助手消息
    LOW = 1        # 可丢弃的元数据
    DISCARD = 0    # 可安全删除


@dataclass
class CompactionStrategy:
    """压缩策略配置"""
    
    # 目标token数
    max_tokens: int = 8000
    
    # 保留最近的消息数
    preserve_recent: int = 10
    
    # 启用摘要生成
    enable_summarization: bool = True
    
    # 摘要模型
    summary_model: Optional[str] = None
    
    # 压缩触发阈值（超过这个比例开始压缩）
    compact_threshold: float = 0.8
    
    # 是否保留所有工具调用
    preserve_tool_calls: bool = True
    
    # 是否保留所有系统消息
    preserve_system: bool = True
    
    # 最小消息保留数
    min_messages: int = 4


@dataclass
class CompactionResult:
    """压缩结果"""
    
    # 压缩后的消息
    messages: List[Dict[str, Any]]
    
    # 生成的摘要（如果有）
    summary: Optional[str] = None
    
    # 原始token数
    original_tokens: int = 0
    
    # 压缩后token数
    final_tokens: int = 0
    
    # 移除的消息数
    removed_count: int = 0
    
    # 是否执行了压缩
    was_compacted: bool = False
    
    @property
    def tokens_saved(self) -> int:
        """节省的token数"""
        return self.original_tokens - self.final_tokens
    
    @property
    def compression_ratio(self) -> float:
        """压缩比例"""
        if self.original_tokens == 0:
            return 0.0
        return self.tokens_saved / self.original_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "messages_count": len(self.messages),
            "summary": self.summary,
            "original_tokens": self.original_tokens,
            "final_tokens": self.final_tokens,
            "tokens_saved": self.tokens_saved,
            "compression_ratio": f"{self.compression_ratio:.1%}",
            "removed_count": self.removed_count,
            "was_compacted": self.was_compacted,
        }


@dataclass
class CompactorConfig:
    """压缩器配置"""
    
    # 策略
    strategy: CompactionStrategy = None
    
    # Token计算函数
    token_calculator: Optional[Callable[[str], int]] = None
    
    # 摘要生成函数
    summarizer: Optional[Callable[[List[Dict]], str]] = None
    
    # 日志回调
    log_callback: Optional[Callable[[str], None]] = None
    
    def __post_init__(self):
        if self.strategy is None:
            self.strategy = CompactionStrategy()


class MessagePriorityCalculator:
    """消息优先级计算器"""
    
    @staticmethod
    def calculate(message: Dict[str, Any]) -> CompactionPriority:
        """
        计算消息优先级
        
        Args:
            message: 消息字典
        
        Returns:
            优先级枚举
        """
        role = message.get("role", "")
        content = message.get("content", "")
        
        # 系统消息最高优先级
        if role == "system":
            return CompactionPriority.CRITICAL
        
        # 用户消息高优先级
        if role == "user":
            return CompactionPriority.HIGH
        
        # 助手消息
        if role == "assistant":
            # 包含工具调用的消息
            if message.get("tool_calls") or "tool_call" in str(content).lower():
                return CompactionPriority.HIGH
            # 普通消息
            return CompactionPriority.MEDIUM
        
        # 工具结果
        if role == "tool":
            # 检查是否包含错误
            if "error" in str(content).lower():
                return CompactionPriority.CRITICAL
            return CompactionPriority.HIGH
        
        return CompactionPriority.LOW


__all__ = [
    "CompactionPriority",
    "CompactionStrategy",
    "CompactionResult",
    "CompactorConfig",
    "MessagePriorityCalculator",
]
