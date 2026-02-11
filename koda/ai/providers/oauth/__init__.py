"""
OAuth Providers
等效于 Pi-Mono 的 packages/ai/src/utils/oauth/index.ts
"""

from .types import (
    OAuthProviderId,
    OAuthCredentials,
    AuthPrompt,
    AuthInfo,
    OAuthProviderInfo,
    OAuthConfig,
    AuthCallback,
    PromptCallback,
    ProgressCallback,
)
from .anthropic import AnthropicOAuth, login_anthropic
from .github_copilot_oauth import GitHubCopilotOAuth, login_github_copilot
from .google_antigravity_oauth import GoogleAntigravityOAuth
from .google_gemini_cli_oauth import GoogleGeminiCLIOAuth
from .openai_codex_oauth import OpenAICodexOAuth

__all__ = [
    # Types
    "OAuthProviderId",
    "OAuthCredentials",
    "AuthPrompt",
    "AuthInfo",
    "OAuthProviderInfo",
    "OAuthConfig",
    "AuthCallback",
    "PromptCallback",
    "ProgressCallback",
    # Providers
    "AnthropicOAuth",
    "GitHubCopilotOAuth",
    "GoogleAntigravityOAuth",
    "GoogleGeminiCLIOAuth",
    "OpenAICodexOAuth",
    # Convenience functions
    "login_anthropic",
    "login_github_copilot",
]


def get_oauth_providers() -> list:
    """获取所有OAuth providers信息"""
    return [
        AnthropicOAuth.PROVIDER_INFO,
        GitHubCopilotOAuth.PROVIDER_INFO,
        GoogleAntigravityOAuth.PROVIDER_INFO,
        GoogleGeminiCLIOAuth.PROVIDER_INFO,
        OpenAICodexOAuth.PROVIDER_INFO,
    ]


def get_oauth_provider(provider_id: str):
    """获取OAuth provider实例"""
    providers = {
        "anthropic": AnthropicOAuth,
        "github-copilot": GitHubCopilotOAuth,
        "google-antigravity": GoogleAntigravityOAuth,
        "google-gemini-cli": GoogleGeminiCLIOAuth,
        "openai-codex": OpenAICodexOAuth,
    }
    
    provider_class = providers.get(provider_id)
    if provider_class:
        return provider_class()
    return None
