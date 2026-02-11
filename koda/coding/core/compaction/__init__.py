"""
Session Compaction Module
等效于 Pi-Mono 的 packages/coding-agent/src/core/compaction/

提供会话压缩、分支摘要和上下文管理功能。
"""

from .base import CompactionStrategy, CompactionResult, CompactorConfig
from .session import SessionCompactor
from .branch import BranchSummarizer
from .utils import calculate_tokens, estimate_tokens, should_compact

__all__ = [
    # Base
    "CompactionStrategy",
    "CompactionResult",
    "CompactorConfig",
    # Core
    "SessionCompactor",
    "BranchSummarizer",
    # Utils
    "calculate_tokens",
    "estimate_tokens",
    "should_compact",
]
