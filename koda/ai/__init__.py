"""
Koda AI Package

AI/LLM integration components.
"""
from .types import (
    AssistantMessage,
    TextContent,
    ToolCall,
    ToolResultMessage,
    UserMessage,
    Context,
    ModelInfo,
    StopReason,
    StreamOptions,
    ThinkingContent,
)
from .config import ConfigValueResolver, resolve_value
from .event_stream import AssistantMessageEventStream
from .json_parser import JSONStreamingParser, JSONParseEvent
from .overflow import is_context_overflow, get_overflow_patterns, add_overflow_pattern
from .settings import SettingsManager
from .agent_proxy import HTTPStreamProxy
from .json_schema import JSONSchemaValidator, validate_json_schema
from .validation import MessageValidator, ValidationResult
from .session import SessionManager, SessionEntry, SessionEntryType
from .edits import EditOperation, EditProcessor, EditResult
from .pkce import generate_code_verifier, generate_code_challenge, generate_pkce_challenge
from .transform_messages import transform_messages
from .token_counter import TokenCounter, TokenCount, count_tokens, estimate_cost
from .rate_limiter import RateLimiter, RateLimitConfig, RateLimitStrategy, MultiKeyRateLimiter, rate_limited
from .retry import RetryHandler, RetryConfig, RetryStrategy, CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerOpenError, ResilientClient, retry
from .env_api_keys import EnvAPIKeyManager, get_api_key, has_api_key, get_all_api_keys
from .sanitize_unicode import sanitize_surrogates, sanitize_for_json
from .typebox_helpers import SchemaBuilder, Validator, ValidationResult, validate_json
from .models import (
    MODELS,
    get_model,
    get_models,
    get_providers,
    ModelRegistry,
    register_model,
    find_models,
    calculate_cost,
    CostBreakdown,
    supports_xhigh,
    models_are_equal,
)

__all__ = [
    # Types
    "AssistantMessage",
    "TextContent",
    "ToolCall",
    "ToolResultMessage",
    "UserMessage",
    "Context",
    "ModelInfo",
    "StopReason",
    "StreamOptions",
    "ThinkingContent",
    # Config
    "ConfigValueResolver",
    "resolve_value",
    # Event stream
    "AssistantMessageEventStream",
    # JSON Parser
    "JSONStreamingParser",
    "JSONParseEvent",
    # Overflow
    "is_context_overflow",
    "get_overflow_patterns",
    "add_overflow_pattern",
    # Settings
    "SettingsManager",
    # Agent Proxy
    "HTTPStreamProxy",
    # JSON Schema
    "JSONSchemaValidator",
    "validate_json_schema",
    # Validation
    "MessageValidator",
    "ValidationResult",
    # Session
    "SessionManager",
    "SessionEntry",
    "SessionEntryType",
    # Edits
    "EditOperation",
    "EditProcessor",
    "EditResult",
    # PKCE
    "generate_code_verifier",
    "generate_code_challenge",
    "generate_pkce_challenge",
    # Transform messages
    "transform_messages",
    # Token counter
    "TokenCounter",
    "TokenCount",
    "count_tokens",
    "estimate_cost",
    # Rate limiter
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitStrategy",
    "MultiKeyRateLimiter",
    "rate_limited",
    # Retry
    "RetryHandler",
    "RetryConfig",
    "RetryStrategy",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitBreakerOpenError",
    "ResilientClient",
    "retry",
    # Environment API Keys
    "EnvAPIKeyManager",
    "get_api_key",
    "has_api_key",
    "get_all_api_keys",
    # TypeBox Helpers
    "SchemaBuilder",
    "Validator",
    "ValidationResult",
    "validate_json",
    # Models
    "MODELS",
    "get_model",
    "get_models",
    "get_providers",
    "ModelRegistry",
    "register_model",
    "find_models",
    "calculate_cost",
    "CostBreakdown",
    "supports_xhigh",
    "models_are_equal",
]
