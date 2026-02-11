"""
OpenAI Shared Utilities
Equivalent to Pi Mono's packages/ai/src/providers/oauth/openai-shared.ts

Shared utilities for OpenAI providers.
"""
import os
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum


class OpenAIModel(str, Enum):
    """OpenAI model identifiers"""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GPT4_TURBO = "gpt-4-turbo"
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"
    O1 = "o1"
    O1_MINI = "o1-mini"
    O3_MINI = "o3-mini"
    CODEX = "codex"
    CODEX_LATEST = "codex-latest"


class OpenAIEndpoint(str, Enum):
    """OpenAI API endpoints"""
    CHAT_COMPLETIONS = "/v1/chat/completions"
    COMPLETIONS = "/v1/completions"
    MODELS = "/v1/models"
    EMBEDDINGS = "/v1/embeddings"
    IMAGES = "/v1/images/generations"
    AUDIO_TRANSCRIPTIONS = "/v1/audio/transcriptions"
    FILES = "/v1/files"
    FINE_TUNING = "/v1/fine_tuning/jobs"
    BATCH = "/v1/batches"
    ASSISTANTS = "/v1/assistants"
    THREADS = "/v1/threads"


@dataclass
class OpenAIConfig:
    """Shared OpenAI configuration"""
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com"
    organization: Optional[str] = None
    project: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 2
    default_model: OpenAIModel = OpenAIModel.GPT4O
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")


class OpenAIUtils:
    """
    Shared utilities for OpenAI providers.
    
    Provides common functionality for OpenAI API interactions.
    
    Example:
        >>> utils = OpenAIUtils()
        >>> headers = utils.get_headers()
        >>> model = utils.resolve_model("gpt-4o")
    """
    
    # Token limits for models
    MODEL_TOKEN_LIMITS = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
        "o1": 128000,
        "o1-mini": 128000,
        "o3-mini": 128000,
        "codex": 128000,
        "codex-latest": 128000,
    }
    
    # Pricing per 1K tokens (approximate, in USD)
    MODEL_PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    
    def __init__(self, config: Optional[OpenAIConfig] = None):
        """
        Initialize OpenAI utilities.
        
        Args:
            config: Configuration or None for defaults
        """
        self.config = config or OpenAIConfig()
    
    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get standard headers for OpenAI API requests.
        
        Args:
            extra_headers: Additional headers to include
            
        Returns:
            Headers dict
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization
        
        if self.config.project:
            headers["OpenAI-Project"] = self.config.project
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def resolve_model(self, model: Optional[str] = None) -> str:
        """
        Resolve model name to full identifier.
        
        Args:
            model: Model name or None for default
            
        Returns:
            Full model identifier
        """
        if model is None:
            return self.config.default_model.value
        
        # Normalize model name
        model_lower = model.lower().strip()
        
        # Check if it's already a known model
        for m in OpenAIModel:
            if m.value == model_lower:
                return m.value
        
        # Check token limits keys
        if model_lower in self.MODEL_TOKEN_LIMITS:
            return model_lower
        
        # Return as-is if unknown
        return model_lower
    
    def get_token_limit(self, model: Optional[str] = None) -> int:
        """
        Get token limit for model.
        
        Args:
            model: Model name or None for default
            
        Returns:
            Token limit
        """
        model = self.resolve_model(model)
        return self.MODEL_TOKEN_LIMITS.get(model, 4096)
    
    def get_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing for model.
        
        Args:
            model: Model name
            
        Returns:
            Pricing dict with input/output costs
        """
        return self.MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    
    def estimate_cost(self, model: str, input_tokens: int, 
                      output_tokens: int) -> float:
        """
        Estimate API call cost.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        pricing = self.get_pricing(model)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost
    
    def build_url(self, endpoint: str) -> str:
        """
        Build full API URL.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL
        """
        base = self.config.base_url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"
    
    def format_messages_for_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format messages for OpenAI API.
        
        Args:
            messages: Raw messages
            
        Returns:
            Formatted messages
        """
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": msg.get("role", "user"),
            }
            
            # Handle content
            content = msg.get("content")
            if content:
                formatted_msg["content"] = content
            
            # Handle tool calls
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                formatted_msg["tool_calls"] = tool_calls
            
            # Handle tool call ID
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id:
                formatted_msg["tool_call_id"] = tool_call_id
            
            formatted.append(formatted_msg)
        
        return formatted
    
    def is_reasoning_model(self, model: str) -> bool:
        """
        Check if model is a reasoning model (o1, o3, etc.).
        
        Args:
            model: Model name
            
        Returns:
            True if reasoning model
        """
        model_lower = model.lower()
        return any(m in model_lower for m in ["o1", "o3"])
    
    def get_default_parameters(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get default parameters for API call.
        
        Args:
            model: Model name
            
        Returns:
            Default parameters
        """
        params = {
            "model": self.resolve_model(model),
        }
        
        # Reasoning models use different parameters
        if model and self.is_reasoning_model(model):
            params["reasoning_effort"] = "medium"
        else:
            params["temperature"] = 0.7
            params["max_tokens"] = 4096
        
        return params


# Convenience functions
def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from environment"""
    return os.environ.get("OPENAI_API_KEY")


def has_openai_key() -> bool:
    """Check if OpenAI API key is configured"""
    return bool(get_openai_api_key())


def create_openai_utils(api_key: Optional[str] = None,
                        base_url: Optional[str] = None) -> OpenAIUtils:
    """
    Create OpenAI utilities instance.
    
    Args:
        api_key: API key or None for environment
        base_url: Custom base URL
        
    Returns:
        OpenAIUtils instance
    """
    config = OpenAIConfig(api_key=api_key, base_url=base_url or "https://api.openai.com")
    return OpenAIUtils(config)


__all__ = [
    "OpenAIModel",
    "OpenAIEndpoint",
    "OpenAIConfig",
    "OpenAIUtils",
    "get_openai_api_key",
    "has_openai_key",
    "create_openai_utils",
]
