"""
Koda Mes - Model-Optimized Messages

Token-efficient message format and context optimization.
Reduces token usage through smart compression and history management.
"""
from koda.mes.optimizer import MessageOptimizer, OptimizationResult
from koda.mes.formatter import MessageFormatter, FormattedMessage
from koda.mes.history import HistoryManager, CompactionResult

__all__ = [
    "MessageOptimizer",
    "OptimizationResult",
    "MessageFormatter",
    "FormattedMessage",
    "HistoryManager",
    "CompactionResult",
]
