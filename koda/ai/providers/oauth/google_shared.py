"""
Google Shared Utilities
Equivalent to Pi Mono's packages/ai/src/providers/oauth/google-shared.ts

Shared utilities for Google AI providers.
"""
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class GoogleModel(str, Enum):
    """Google Gemini model identifiers"""
    GEMINI_15_PRO = "gemini-1.5-pro"
    GEMINI_15_FLASH = "gemini-1.5-flash"
    GEMINI_15_PRO_002 = "gemini-1.5-pro-002"
    GEMINI_15_FLASH_002 = "gemini-1.5-flash-002"
    GEMINI_15_PRO_LATEST = "gemini-1.5-pro-latest"
    GEMINI_15_FLASH_LATEST = "gemini-1.5-flash-latest"
    GEMINI_10_PRO = "gemini-1.0-pro"
    GEMINI_10_PRO_VISION = "gemini-1.0-pro-vision"
    GEMINI_ULTRA = "gemini-ultra"
    GEMINI_PRO = "gemini-pro"
    GEMINI_PRO_VISION = "gemini-pro-vision"


class GoogleEndpoint(str, Enum):
    """Google Generative AI API endpoints"""
    GENERATE_CONTENT = "/v1beta/models/{model}:generateContent"
    STREAM_GENERATE_CONTENT = "/v1beta/models/{model}:streamGenerateContent"
    COUNT_TOKENS = "/v1beta/models/{model}:countTokens"
    EMBED_CONTENT = "/v1beta/models/{model}:embedContent"
    BATCH_EMBED_CONTENTS = "/v1beta/models/{model}:batchEmbedContents"
    LIST_MODELS = "/v1beta/models"
    GET_MODEL = "/v1beta/models/{model}"


@dataclass
class GoogleConfig:
    """Shared Google AI configuration"""
    api_key: Optional[str] = None
    base_url: str = "https://generativelanguage.googleapis.com"
    vertex_base_url: str = "https://{location}-aiplatform.googleapis.com/v1"
    project_id: Optional[str] = None
    location: str = "us-central1"
    timeout: float = 60.0
    max_retries: int = 3
    default_model: GoogleModel = GoogleModel.GEMINI_15_PRO
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GEMINI_API_KEY")


class GoogleUtils:
    """
    Shared utilities for Google AI providers.
    
    Provides common functionality for Google Gemini API interactions.
    
    Example:
        >>> utils = GoogleUtils()
        >>> headers = utils.get_headers()
        >>> model = utils.resolve_model("gemini-1.5-pro")
    """
    
    # Token limits for models (context window)
    MODEL_TOKEN_LIMITS = {
        "gemini-1.5-pro": 2097152,  # 2M tokens
        "gemini-1.5-pro-002": 2097152,
        "gemini-1.5-pro-latest": 2097152,
        "gemini-1.5-flash": 1048576,  # 1M tokens
        "gemini-1.5-flash-002": 1048576,
        "gemini-1.5-flash-latest": 1048576,
        "gemini-1.0-pro": 32768,
        "gemini-1.0-pro-vision": 16384,
        "gemini-ultra": 32768,
        "gemini-pro": 32768,
        "gemini-pro-vision": 16384,
    }
    
    # Output token limits
    MODEL_OUTPUT_LIMITS = {
        "gemini-1.5-pro": 8192,
        "gemini-1.5-pro-002": 8192,
        "gemini-1.5-pro-latest": 8192,
        "gemini-1.5-flash": 8192,
        "gemini-1.5-flash-002": 8192,
        "gemini-1.5-flash-latest": 8192,
        "gemini-1.0-pro": 2048,
        "gemini-1.0-pro-vision": 2048,
        "gemini-ultra": 2048,
        "gemini-pro": 2048,
        "gemini-pro-vision": 2048,
    }
    
    # Model capabilities
    MODEL_CAPABILITIES = {
        "gemini-1.5-pro": ["text", "vision", "audio", "video", "code", "json"],
        "gemini-1.5-flash": ["text", "vision", "audio", "video", "code", "json"],
        "gemini-1.0-pro": ["text", "code", "json"],
        "gemini-1.0-pro-vision": ["text", "vision", "code"],
    }
    
    def __init__(self, config: Optional[GoogleConfig] = None):
        """
        Initialize Google utilities.
        
        Args:
            config: Configuration or None for defaults
        """
        self.config = config or GoogleConfig()
    
    def get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get standard headers for Google API requests.
        
        Args:
            extra_headers: Additional headers to include
            
        Returns:
            Headers dict
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.config.api_key:
            headers["x-goog-api-key"] = self.config.api_key
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """
        Get authorization headers with OAuth token.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            Headers dict
        """
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
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
        
        model_lower = model.lower().strip()
        
        # Check if it's already a known model
        for m in GoogleModel:
            if m.value == model_lower:
                return m.value
        
        # Check token limits keys
        if model_lower in self.MODEL_TOKEN_LIMITS:
            return model_lower
        
        # Return as-is if unknown
        return model_lower
    
    def get_token_limit(self, model: Optional[str] = None) -> int:
        """
        Get input token limit for model.
        
        Args:
            model: Model name or None for default
            
        Returns:
            Token limit
        """
        model = self.resolve_model(model)
        return self.MODEL_TOKEN_LIMITS.get(model, 32768)
    
    def get_output_limit(self, model: Optional[str] = None) -> int:
        """
        Get output token limit for model.
        
        Args:
            model: Model name or None for default
            
        Returns:
            Output token limit
        """
        model = self.resolve_model(model)
        return self.MODEL_OUTPUT_LIMITS.get(model, 2048)
    
    def get_capabilities(self, model: str) -> List[str]:
        """
        Get capabilities for model.
        
        Args:
            model: Model name
            
        Returns:
            List of capability strings
        """
        model = self.resolve_model(model)
        return self.MODEL_CAPABILITIES.get(model, ["text"])
    
    def supports_capability(self, model: str, capability: str) -> bool:
        """
        Check if model supports a capability.
        
        Args:
            model: Model name
            capability: Capability to check
            
        Returns:
            True if supported
        """
        capabilities = self.get_capabilities(model)
        return capability in capabilities
    
    def supports_vision(self, model: str) -> bool:
        """Check if model supports vision"""
        return self.supports_capability(model, "vision")
    
    def supports_audio(self, model: str) -> bool:
        """Check if model supports audio"""
        return self.supports_capability(model, "audio")
    
    def supports_video(self, model: str) -> bool:
        """Check if model supports video"""
        return self.supports_capability(model, "video")
    
    def build_gemini_url(self, endpoint: str, model: Optional[str] = None) -> str:
        """
        Build Gemini API URL.
        
        Args:
            endpoint: Endpoint template
            model: Model name for template substitution
            
        Returns:
            Full URL
        """
        base = self.config.base_url.rstrip("/")
        
        if model:
            endpoint = endpoint.format(model=self.resolve_model(model))
        
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"
    
    def build_vertex_url(self, endpoint: str, model: Optional[str] = None) -> str:
        """
        Build Vertex AI API URL.
        
        Args:
            endpoint: Endpoint path
            model: Model name
            
        Returns:
            Full URL
        """
        base = self.config.vertex_base_url.format(location=self.config.location)
        
        if self.config.project_id:
            # Vertex URLs include project
            if "projects/" not in endpoint:
                endpoint = f"/projects/{self.config.project_id}/locations/{self.config.location}/publishers/google/models/{model or 'gemini-pro'}"
        
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"
    
    def format_content_for_api(self, content: str, role: str = "user") -> Dict[str, Any]:
        """
        Format content for Gemini API.
        
        Args:
            content: Text content
            role: Role (user/model)
            
        Returns:
            Formatted content dict
        """
        return {
            "role": role,
            "parts": [{"text": content}],
        }
    
    def format_messages_for_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format messages for Gemini API.
        
        Args:
            messages: Raw messages
            
        Returns:
            Formatted contents
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Map OpenAI-style roles to Gemini roles
            gemini_role = "user" if role in ("user", "system") else "model"
            
            formatted.append(self.format_content_for_api(content, gemini_role))
        
        return formatted
    
    def get_default_generation_config(self, 
                                       model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get default generation config for API call.
        
        Args:
            model: Model name
            
        Returns:
            Generation config dict
        """
        return {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": self.get_output_limit(model),
            "responseMimeType": "text/plain",
        }
    
    def get_safety_settings(self) -> List[Dict[str, str]]:
        """
        Get default safety settings.
        
        Returns:
            Safety settings list
        """
        return [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]


# Convenience functions
def get_google_api_key() -> Optional[str]:
    """Get Google API key from environment"""
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GEMINI_API_KEY")


def has_google_key() -> bool:
    """Check if Google API key is configured"""
    return bool(get_google_api_key())


def create_google_utils(api_key: Optional[str] = None,
                        project_id: Optional[str] = None) -> GoogleUtils:
    """
    Create Google utilities instance.
    
    Args:
        api_key: API key or None for environment
        project_id: Vertex AI project ID
        
    Returns:
        GoogleUtils instance
    """
    config = GoogleConfig(api_key=api_key, project_id=project_id)
    return GoogleUtils(config)


__all__ = [
    "GoogleModel",
    "GoogleEndpoint",
    "GoogleConfig",
    "GoogleUtils",
    "get_google_api_key",
    "has_google_key",
    "create_google_utils",
]
