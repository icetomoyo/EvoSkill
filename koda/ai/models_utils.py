"""
Model utilities - helpers for model operations
Equivalent to Pi Mono's models.ts utilities
"""
from typing import Optional, TypeVar
from koda.ai.types import ModelInfo, Usage, ThinkingLevel

T = TypeVar('T')


def supports_xhigh(model: ModelInfo) -> bool:
    """
    Check if model supports xhigh thinking level
    
    Supported:
    - GPT-5.2 / GPT-5.3 families
    - Anthropic Messages API Opus 4.6 models
    
    Equivalent to Pi Mono's supportsXhigh()
    """
    model_id = model.id.lower()
    
    # GPT-5.2 / GPT-5.3
    if "gpt-5.2" in model_id or "gpt-5.3" in model_id:
        return True
    
    # Anthropic Opus 4.6
    if model.api == "anthropic-messages":
        if "opus-4-6" in model_id or "opus-4.6" in model_id:
            return True
    
    return False


def models_are_equal(a: Optional[ModelInfo], b: Optional[ModelInfo]) -> bool:
    """
    Check if two models are equal by comparing id and provider
    
    Returns False if either model is None
    
    Equivalent to Pi Mono's modelsAreEqual()
    """
    if not a or not b:
        return False
    
    return a.id == b.id and a.provider == b.provider


def calculate_cost(model: ModelInfo, usage: Usage) -> float:
    """
    Calculate cost for usage with model
    
    Cost = (input_cost/1M * input_tokens) + (output_cost/1M * output_tokens) + ...
    
    Equivalent to Pi Mono's calculateCost()
    """
    cost_input = (model.cost.get("input", 0) / 1000000) * usage.input
    cost_output = (model.cost.get("output", 0) / 1000000) * usage.output
    cost_cache_read = (model.cost.get("cache_read", 0) / 1000000) * usage.cache_read
    cost_cache_write = (model.cost.get("cache_write", 0) / 1000000) * usage.cache_write
    
    total = cost_input + cost_output + cost_cache_read + cost_cache_write
    
    usage.cost["input"] = cost_input
    usage.cost["output"] = cost_output
    usage.cost["cache_read"] = cost_cache_read
    usage.cost["cache_write"] = cost_cache_write
    usage.cost["total"] = total
    
    return total


def get_thinking_budget(level: ThinkingLevel, budgets: Optional[dict] = None) -> Optional[int]:
    """
    Get token budget for thinking level
    
    Default budgets if not specified:
    - minimal: 1024
    - low: 2048
    - medium: 4096
    - high: 8192
    - xhigh: 16384
    """
    if budgets:
        return budgets.get(level.value)
    
    default_budgets = {
        "minimal": 1024,
        "low": 2048,
        "medium": 4096,
        "high": 8192,
        "xhigh": 16384,
    }
    
    return default_budgets.get(level.value)


def resolve_model_alias(alias: str) -> str:
    """
    Resolve common model aliases to full model IDs
    
    Examples:
    - "gpt4" -> "gpt-4o"
    - "claude" -> "claude-3-5-sonnet-20241022"
    """
    aliases = {
        "gpt4": "gpt-4o",
        "gpt4o": "gpt-4o",
        "gpt4omini": "gpt-4o-mini",
        "claude": "claude-3-5-sonnet-20241022",
        "claudeopus": "claude-3-opus-20240229",
        "sonnet": "claude-3-5-sonnet-20241022",
        "haiku": "claude-3-5-haiku-20241022",
        "gemini": "gemini-1.5-pro",
    }
    
    return aliases.get(alias.lower(), alias)
