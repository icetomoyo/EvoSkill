"""
Simple Options - Helper functions for stream options
Equivalent to Pi Mono's packages/ai/src/providers/simple-options.ts

Handles:
- Building base stream options
- Reasoning effort clamping
- Thinking budget calculations
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ThinkingBudgets:
    """Token budgets for each thinking level"""
    minimal: int = 1024
    low: int = 2048
    medium: int = 8192
    high: int = 16384


def build_base_options(
    model,
    options: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build base stream options from simple options.
    
    Args:
        model: Model configuration
        options: Simple stream options
        api_key: Optional API key
        
    Returns:
        Complete stream options
    """
    if options is None:
        options = {}
    
    return {
        "temperature": options.get("temperature"),
        "max_tokens": options.get("max_tokens") or min(
            getattr(model, "max_tokens", 32000), 32000
        ),
        "signal": options.get("signal"),
        "api_key": api_key or options.get("api_key"),
        "cache_retention": options.get("cache_retention"),
        "session_id": options.get("session_id"),
        "headers": options.get("headers"),
        "on_payload": options.get("on_payload"),
        "max_retry_delay_ms": options.get("max_retry_delay_ms"),
    }


def clamp_reasoning(effort: Optional[str]) -> Optional[str]:
    """
    Clamp reasoning effort to valid range.
    
    Maps 'xhigh' to 'high' since not all providers support it.
    
    Args:
        effort: Reasoning effort level
        
    Returns:
        Clamped effort level
    """
    if effort == "xhigh":
        return "high"
    return effort


def adjust_max_tokens_for_thinking(
    base_max_tokens: int,
    model_max_tokens: int,
    reasoning_level: str,
    custom_budgets: Optional[ThinkingBudgets] = None
) -> Dict[str, int]:
    """
    Adjust max tokens for thinking/reasoning.
    
    Calculates the appropriate token budget for thinking based on the reasoning level.
    
    Args:
        base_max_tokens: Base max tokens requested
        model_max_tokens: Model's maximum token limit
        reasoning_level: Reasoning level (minimal, low, medium, high)
        custom_budgets: Custom thinking budgets
        
    Returns:
        Dictionary with adjusted max_tokens and thinking_budget
        
    Example:
        >>> result = adjust_max_tokens_for_thinking(
        ...     base_max_tokens=4000,
        ...     model_max_tokens=8000,
        ...     reasoning_level="medium"
        ... )
        >>> result["thinking_budget"] > 0
        True
    """
    # Default budgets
    default_budgets = ThinkingBudgets()
    
    # Merge with custom budgets
    if custom_budgets:
        budgets = ThinkingBudgets(
            minimal=custom_budgets.minimal or default_budgets.minimal,
            low=custom_budgets.low or default_budgets.low,
            medium=custom_budgets.medium or default_budgets.medium,
            high=custom_budgets.high or default_budgets.high,
        )
    else:
        budgets = default_budgets
    
    # Minimum output tokens to reserve
    min_output_tokens = 1024
    
    # Get thinking budget for level
    level = clamp_reasoning(reasoning_level) or "medium"
    thinking_budget = getattr(budgets, level, budgets.medium)
    
    # Calculate max tokens
    max_tokens = min(base_max_tokens + thinking_budget, model_max_tokens)
    
    # Ensure we have room for output
    if max_tokens <= thinking_budget:
        thinking_budget = max(0, max_tokens - min_output_tokens)
    
    return {
        "max_tokens": max_tokens,
        "thinking_budget": thinking_budget,
    }


def get_thinking_budget(
    level: str,
    custom_budgets: Optional[ThinkingBudgets] = None
) -> int:
    """
    Get thinking budget for a reasoning level.
    
    Args:
        level: Reasoning level
        custom_budgets: Custom budgets
        
    Returns:
        Token budget
    """
    budgets = custom_budgets or ThinkingBudgets()
    level = clamp_reasoning(level) or "medium"
    return getattr(budgets, level, budgets.medium)


__all__ = [
    "ThinkingBudgets",
    "build_base_options",
    "clamp_reasoning",
    "adjust_max_tokens_for_thinking",
    "get_thinking_budget",
]
