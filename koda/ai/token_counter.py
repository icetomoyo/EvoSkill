"""
Token Counter
Equivalent to Pi Mono's packages/ai/src/utils/token-counter.ts

Token counting utilities for various models.
"""
import re
from typing import Optional, Dict, Callable
from dataclasses import dataclass


@dataclass
class TokenCount:
    """Token count result"""
    tokens: int
    chars: int
    model: str
    method: str


class TokenCounter:
    """
    Token counter for various models.
    
    Provides approximate token counting when exact tokenizer unavailable.
    
    Example:
        >>> counter = TokenCounter("gpt-4")
        >>> count = counter.count("Hello, world!")
        >>> print(count.tokens)
    """
    
    # Average chars per token for different models
    CHARS_PER_TOKEN = {
        "gpt-4": 4.0,
        "gpt-4o": 4.0,
        "gpt-3.5-turbo": 4.0,
        "claude": 4.5,
        "claude-sonnet": 4.5,
        "claude-opus": 4.5,
        "gemini": 4.0,
        "default": 4.0,
    }
    
    def __init__(self, model: str = "default"):
        """
        Initialize token counter.
        
        Args:
            model: Model name for model-specific counting
        """
        self.model = model.lower()
        self._tokenizer: Optional[Callable] = None
        self._init_tokenizer()
    
    def _init_tokenizer(self):
        """Try to initialize exact tokenizer"""
        # Try tiktoken for OpenAI models
        try:
            import tiktoken
            if "gpt-4" in self.model or "gpt-3.5" in self.model:
                self._tokenizer = tiktoken.encoding_for_model(self.model)
        except (ImportError, KeyError):
            pass
        
        # Try transformers for other models
        if self._tokenizer is None:
            try:
                from transformers import AutoTokenizer
                # Map model names to HuggingFace models
                model_map = {
                    "claude": "anthropic/claude-tokenizer",
                    "gemini": "google/gemma-tokenizer",
                }
                for key, hf_model in model_map.items():
                    if key in self.model:
                        self._tokenizer = AutoTokenizer.from_pretrained(hf_model)
                        break
            except (ImportError, Exception):
                pass
    
    def count(self, text: str) -> TokenCount:
        """
        Count tokens in text.
        
        Args:
            text: Text to count
            
        Returns:
            TokenCount with token and character count
        """
        chars = len(text)
        
        # Use exact tokenizer if available
        if self._tokenizer:
            try:
                if hasattr(self._tokenizer, 'encode'):
                    tokens = len(self._tokenizer.encode(text))
                else:
                    tokens = len(self._tokenizer(text))
                return TokenCount(
                    tokens=tokens,
                    chars=chars,
                    model=self.model,
                    method="exact"
                )
            except Exception:
                pass
        
        # Fall back to approximation
        return self._estimate(text)
    
    def _estimate(self, text: str) -> TokenCount:
        """Estimate token count using character ratio"""
        chars = len(text)
        
        # Determine chars per token for this model
        cpt = self.CHARS_PER_TOKEN["default"]
        for model_key, ratio in self.CHARS_PER_TOKEN.items():
            if model_key in self.model:
                cpt = ratio
                break
        
        # Basic estimation
        tokens = int(chars / cpt)
        
        # Adjust for special cases
        # Code typically has lower chars/token ratio
        if self._is_code(text):
            tokens = int(tokens * 1.2)
        
        # Adjust for whitespace
        whitespace_count = len(re.findall(r'\s+', text))
        tokens += whitespace_count // 4  # Groups of whitespace
        
        return TokenCount(
            tokens=tokens,
            chars=chars,
            model=self.model,
            method="estimate"
        )
    
    def _is_code(self, text: str) -> bool:
        """Heuristic to detect if text is code"""
        code_indicators = [
            r'\b(def|class|function|var|let|const|import|from)\b',
            r'[{;}]\s*$',  # Lines ending with braces or semicolons
            r'\b(if|for|while|return)\s*\(',
        ]
        
        for indicator in code_indicators:
            if re.search(indicator, text, re.MULTILINE):
                return True
        return False
    
    def count_messages(self, messages: list) -> TokenCount:
        """
        Count tokens in a list of messages.
        
        Args:
            messages: List of message dicts with 'content' field
            
        Returns:
            TokenCount
        """
        total_tokens = 0
        total_chars = 0
        
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                count = self.count(content)
                total_tokens += count.tokens
                total_chars += count.chars
            elif isinstance(content, list):
                # Handle content blocks
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        count = self.count(block["text"])
                        total_tokens += count.tokens
                        total_chars += count.chars
        
        # Add overhead for message format (role, etc.)
        total_tokens += len(messages) * 4  # ~4 tokens per message overhead
        
        return TokenCount(
            tokens=total_tokens,
            chars=total_chars,
            model=self.model,
            method="messages"
        )
    
    def truncate(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated text
        """
        count = self.count(text)
        
        if count.tokens <= max_tokens:
            return text
        
        # Estimate chars to keep
        chars_per_token = count.chars / count.tokens
        chars_to_keep = int((max_tokens - 10) * chars_per_token)  # Leave some margin
        
        return text[:chars_to_keep] + "\n... [truncated]"


# Global cache for counters
_counter_cache: Dict[str, TokenCounter] = {}


def count_tokens(text: str, model: str = "default") -> int:
    """
    Count tokens in text (convenience function).
    
    Args:
        text: Text to count
        model: Model name
        
    Returns:
        Token count
    """
    if model not in _counter_cache:
        _counter_cache[model] = TokenCounter(model)
    
    return _counter_cache[model].count(text).tokens


def estimate_cost(tokens: int, model: str = "gpt-4") -> Dict[str, float]:
    """
    Estimate API cost for tokens.
    
    Args:
        tokens: Number of tokens
        model: Model name
        
    Returns:
        Cost estimate dict
    """
    # Cost per 1K tokens (approximate)
    costs = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-opus": {"input": 0.015, "output": 0.075},
        "claude-sonnet": {"input": 0.003, "output": 0.015},
        "default": {"input": 0.01, "output": 0.03},
    }
    
    model_key = "default"
    for key in costs:
        if key in model.lower():
            model_key = key
            break
    
    cost = costs[model_key]
    input_cost = (tokens / 1000) * cost["input"]
    output_cost = (tokens / 1000) * cost["output"]
    
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
        "currency": "USD"
    }


__all__ = [
    "TokenCounter",
    "TokenCount",
    "count_tokens",
    "estimate_cost",
]
