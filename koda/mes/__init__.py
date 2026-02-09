"""
Koda Mes - Model-Optimized Messages

Token-efficient message format and context optimization.
Reduces token usage through smart compression and history management.
"""
from koda.mes.optimizer import MessageOptimizer, OptimizationResult
from koda.mes.formatter import MessageFormatter, FormattedMessage
from koda.mes.history import HistoryManager, CompactionResult as HistoryCompactionResult
from koda.mes.compaction import (
    MessageCompactor,
    CompactionStrategy,
    CompactionSummary,
    CompactionResult as MesCompactionResult,
    ConversationBranch,
    create_simple_summarizer,
)

__all__ = [
    # Optimizer
    "MessageOptimizer",
    "OptimizationResult",
    # Formatter
    "MessageFormatter",
    "FormattedMessage",
    # History
    "HistoryManager",
    "HistoryCompactionResult",
    # Advanced Compaction
    "MessageCompactor",
    "CompactionStrategy",
    "CompactionSummary",
    "MesCompactionResult",
    "ConversationBranch",
    "create_simple_summarizer",
]
