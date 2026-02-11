"""
Model Schema Validation
Equivalent to Pi Mono's packages/coding-agent/src/core/model-registry.ts schema validation

Validates models.json against schema using Pydantic.
"""
from typing import Optional, Dict, List, Any, Literal
from pydantic import BaseModel, Field, validator


class OpenRouterRoutingSchema(BaseModel):
    """OpenRouter routing preferences"""
    only: Optional[List[str]] = None
    order: Optional[List[str]] = None


class VercelGatewayRoutingSchema(BaseModel):
    """Vercel AI Gateway routing preferences"""
    only: Optional[List[str]] = None
    order: Optional[List[str]] = None


class OpenAICompletionsCompatSchema(BaseModel):
    """OpenAI Completions compatibility settings"""
    supports_store: Optional[bool] = None
    supports_developer_role: Optional[bool] = None
    supports_reasoning_effort: Optional[bool] = None
    supports_usage_in_streaming: Optional[bool] = None
    max_tokens_field: Optional[Literal["max_completion_tokens", "max_tokens"]] = None
    requires_tool_result_name: Optional[bool] = None
    requires_assistant_after_tool_result: Optional[bool] = None
    requires_thinking_as_text: Optional[bool] = None
    requires_mistral_tool_ids: Optional[bool] = None
    thinking_format: Optional[Literal["openai", "zai", "qwen"]] = None
    open_router_routing: Optional[OpenRouterRoutingSchema] = None
    vercel_gateway_routing: Optional[VercelGatewayRoutingSchema] = None
    supports_strict_mode: Optional[bool] = None


class OpenAIResponsesCompatSchema(BaseModel):
    """OpenAI Responses compatibility settings"""
    pass  # Reserved for future use


class CostSchema(BaseModel):
    """Cost per million tokens"""
    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0


class ModelDefinitionSchema(BaseModel):
    """Model definition in models.json"""
    id: str = Field(..., min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    api: Optional[str] = Field(None, min_length=1)
    reasoning: Optional[bool] = None
    input: Optional[List[Literal["text", "image"]]] = None
    cost: Optional[CostSchema] = None
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    compat: Optional[OpenAICompletionsCompatSchema] = None


class ModelOverrideSchema(BaseModel):
    """Model override in models.json"""
    name: Optional[str] = None
    reasoning: Optional[bool] = None
    input: Optional[List[Literal["text", "image"]]] = None
    cost: Optional[CostSchema] = None
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    compat: Optional[OpenAICompletionsCompatSchema] = None


class ProviderConfigSchema(BaseModel):
    """Provider configuration in models.json"""
    base_url: Optional[str] = Field(None, min_length=1)
    api_key: Optional[str] = Field(None, min_length=1)
    api: Optional[str] = Field(None, min_length=1)
    headers: Optional[Dict[str, str]] = None
    auth_header: Optional[bool] = None
    models: Optional[List[ModelDefinitionSchema]] = None
    model_overrides: Optional[Dict[str, ModelOverrideSchema]] = None


class ModelsConfigSchema(BaseModel):
    """Root models.json schema"""
    providers: Dict[str, ProviderConfigSchema]
    
    @validator('providers')
    def validate_providers(cls, v):
        if not v:
            raise ValueError("At least one provider must be defined")
        return v


def validate_models_config(config: Dict[str, Any]) -> ModelsConfigSchema:
    """
    Validate models.json configuration.
    
    Args:
        config: Parsed JSON configuration
        
    Returns:
        Validated config model
        
    Raises:
        ValidationError: If config is invalid
    """
    return ModelsConfigSchema(**config)


def validate_models_config_file(path: str) -> Optional[ModelsConfigSchema]:
    """
    Validate models.json file.
    
    Args:
        path: Path to models.json file
        
    Returns:
        Validated config model or None if file doesn't exist
        
    Raises:
        ValidationError: If config is invalid
        json.JSONDecodeError: If file is not valid JSON
    """
    import json
    from pathlib import Path
    
    path = Path(path)
    if not path.exists():
        return None
    
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return validate_models_config(config)


class ValidationResult:
    """Result of validation"""
    def __init__(self, valid: bool, errors: List[str] = None, data: Any = None):
        self.valid = valid
        self.errors = errors or []
        self.data = data
    
    def __bool__(self):
        return self.valid


def validate_config_safe(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate config safely, returning result instead of raising.
    
    Args:
        config: Configuration to validate
        
    Returns:
        ValidationResult with valid status and errors
    """
    try:
        validated = validate_models_config(config)
        return ValidationResult(True, data=validated)
    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            errors = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" 
                     for err in e.errors()]
            return ValidationResult(False, errors=errors)
        return ValidationResult(False, errors=[str(e)])
