"""
Message Optimizer

Optimizes messages for token efficiency.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from koda.ai.provider import Message, Usage


@dataclass
class OptimizationResult:
    """Result of message optimization"""
    messages: List[Message]
    original_tokens: int
    optimized_tokens: int
    removed_count: int = 0
    
    @property
    def savings(self) -> int:
        """Token savings"""
        return self.original_tokens - self.optimized_tokens
    
    @property
    def savings_percent(self) -> float:
        """Percentage savings"""
        if self.original_tokens == 0:
            return 0.0
        return (self.savings / self.original_tokens) * 100


class MessageOptimizer:
    """
    Optimizes message history for token efficiency
    
    Strategies:
    1. Remove redundant system messages
    2. Summarize old conversation turns
    3. Compress tool output
    4. Remove duplicate content
    """
    
    def __init__(self, max_tokens: int = 128000, target_ratio: float = 0.8):
        """
        Args:
            max_tokens: Maximum context window
            target_ratio: Target usage ratio (0.0-1.0)
        """
        self.max_tokens = max_tokens
        self.target_tokens = int(max_tokens * target_ratio)
        self.tokenizer = self._create_tokenizer()
    
    def _create_tokenizer(self):
        """Create approximate tokenizer"""
        # Simple approximation: 4 chars ≈ 1 token
        class SimpleTokenizer:
            def count(self, text: str) -> int:
                return len(text) // 4
        return SimpleTokenizer()
    
    def count_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages"""
        total = 0
        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            # Base overhead per message
            total += 4
            # Content tokens
            total += self.tokenizer.count(content)
        return total
    
    def optimize(
        self,
        messages: List[Message],
        aggressive: bool = False
    ) -> OptimizationResult:
        """
        Optimize messages
        
        Args:
            messages: Original message list
            aggressive: Use more aggressive compression
            
        Returns:
            OptimizationResult with optimized messages
        """
        original_tokens = self.count_tokens(messages)
        
        if original_tokens <= self.target_tokens:
            # No optimization needed
            return OptimizationResult(
                messages=messages,
                original_tokens=original_tokens,
                optimized_tokens=original_tokens,
            )
        
        # Apply optimization strategies
        optimized = list(messages)
        
        # 1. Remove redundant system messages (keep only last)
        optimized = self._deduplicate_system(optimized)
        
        # 2. Compact tool results if too long
        optimized = self._compact_tools(optimized, aggressive)
        
        # 3. Summarize old messages if still over limit
        current_tokens = self.count_tokens(optimized)
        if current_tokens > self.target_tokens:
            optimized = self._summarize_history(optimized, aggressive)
        
        optimized_tokens = self.count_tokens(optimized)
        
        return OptimizationResult(
            messages=optimized,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            removed_count=len(messages) - len(optimized),
        )
    
    def _deduplicate_system(self, messages: List[Message]) -> List[Message]:
        """Keep only the last system message"""
        result = []
        last_system_idx = -1
        
        for i, msg in enumerate(messages):
            if msg.role == "system":
                last_system_idx = i
        
        for i, msg in enumerate(messages):
            if msg.role == "system" and i != last_system_idx:
                continue
            result.append(msg)
        
        return result
    
    def _compact_tools(self, messages: List[Message], aggressive: bool) -> List[Message]:
        """Compact long tool outputs"""
        result = []
        max_tool_length = 2000 if aggressive else 4000
        
        for msg in messages:
            if msg.role == "tool":
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if len(content) > max_tool_length:
                    # Truncate with indicator
                    truncated = content[:max_tool_length]
                    truncated += f"\n\n[... {len(content) - max_tool_length} chars truncated]"
                    msg = Message(
                        role=msg.role,
                        content=truncated,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                    )
            result.append(msg)
        
        return result
    
    def _summarize_history(self, messages: List[Message], aggressive: bool) -> List[Message]:
        """Summarize old conversation history"""
        # Keep system + recent messages
        keep_recent = 6 if aggressive else 10
        
        if len(messages) <= keep_recent + 1:
            return messages
        
        # Find split point (after system message)
        split_idx = 0
        for i, msg in enumerate(messages):
            if msg.role == "system":
                split_idx = i + 1
        
        # Keep system and recent messages
        system_msgs = messages[:split_idx]
        recent_msgs = messages[-keep_recent:]
        
        # Create summary placeholder for removed messages
        removed_count = len(messages) - split_idx - keep_recent
        if removed_count > 0:
            summary = Message.system(
                f"[Earlier conversation: {removed_count} messages summarized]"
            )
            return system_msgs + [summary] + recent_msgs
        
        return messages
    
    def should_compact(self, messages: List[Message]) -> bool:
        """Check if messages need compaction"""
        return self.count_tokens(messages) > self.target_tokens


def estimate_cost(
    usage: Usage,
    model: str,
    provider: str = "openai"
) -> float:
    """
    Estimate cost for token usage
    
    Args:
        usage: Token usage
        model: Model ID
        provider: Provider name
        
    Returns:
        Estimated cost in USD
    """
    # Price per 1K tokens (approximate)
    prices = {
        "openai": {
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
        },
        "anthropic": {
            "claude-3-5-sonnet": (0.003, 0.015),
            "claude-3-haiku": (0.00025, 0.00125),
        },
    }
    
    provider_prices = prices.get(provider, {})
    
    # Find matching model
    for model_prefix, (input_price, output_price) in provider_prices.items():
        if model.startswith(model_prefix):
            prompt_cost = (usage.prompt_tokens / 1000) * input_price
            completion_cost = (usage.completion_tokens / 1000) * output_price
            return prompt_cost + completion_cost
    
    # Default: $0.01 per 1K tokens
    return (usage.total_tokens / 1000) * 0.01
