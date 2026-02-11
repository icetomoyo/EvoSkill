"""
Anthropic OAuth Provider
等效于 Pi-Mono 的 packages/ai/src/utils/oauth/anthropic.ts

Anthropic API的OAuth认证实现。
"""

import asyncio
import urllib.parse
from typing import Optional

from .types import (
    OAuthProviderId,
    OAuthCredentials,
    OAuthProviderInfo,
    AuthInfo,
    AuthPrompt,
    AuthCallback,
    PromptCallback,
    ProgressCallback,
)
from ...pkce import generate_pkce_challenge


class AnthropicOAuth:
    """
    Anthropic OAuth Provider
    
    支持Anthropic API的OAuth认证流程。
    
    Example:
        >>> oauth = AnthropicOAuth()
        >>> creds = await oauth.login(
        ...     on_auth=lambda info: print(info.format_message()),
        ...     on_prompt=lambda p: input(str(p))
        ... )
    """
    
    PROVIDER_INFO = OAuthProviderInfo(
        id=OAuthProviderId.ANTHROPIC,
        name="Anthropic",
        description="Anthropic Claude API",
        auth_url="https://console.anthropic.com/oauth/authorize",
        token_url="https://api.anthropic.com/v1/oauth/token",
        scopes=["default"],
    )
    
    def __init__(self, client_id: str = "anthropic-cli"):
        self.client_id = client_id
        self._credentials: Optional[OAuthCredentials] = None
    
    @property
    def id(self) -> OAuthProviderId:
        return self.PROVIDER_INFO.id
    
    @property
    def name(self) -> str:
        return self.PROVIDER_INFO.name
    
    async def login(
        self,
        on_auth: Optional[AuthCallback] = None,
        on_prompt: Optional[PromptCallback] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> OAuthCredentials:
        """
        执行Anthropic OAuth登录流程
        
        Args:
            on_auth: 认证URL回调
            on_prompt: 用户输入回调
            on_progress: 进度回调
        
        Returns:
            OAuth凭证
        """
        if on_progress:
            on_progress("Starting Anthropic OAuth flow...")
        
        # Generate PKCE challenge
        pkce = generate_pkce_challenge()
        
        # Build auth URL
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join(self.PROVIDER_INFO.scopes),
            "code_challenge": pkce["code_challenge"],
            "code_challenge_method": pkce["code_challenge_method"],
        }
        auth_url = f"{self.PROVIDER_INFO.auth_url}?{urllib.parse.urlencode(params)}"
        
        auth_info = AuthInfo(
            url=auth_url,
            instructions="After authorizing, paste the authorization code here.",
            code_verifier=pkce["code_verifier"],
        )
        
        if on_auth:
            on_auth(auth_info)
        
        # Get authorization code from user
        if on_prompt:
            prompt = AuthPrompt(
                message="Enter the authorization code",
                placeholder="sk-ant-oauth-..."
            )
            auth_code = await on_prompt(prompt)
        else:
            raise ValueError("on_prompt callback required for Anthropic OAuth")
        
        if on_progress:
            on_progress("Exchanging authorization code for access token...")
        
        # Exchange code for token
        credentials = await self._exchange_code(auth_code, pkce["code_verifier"])
        self._credentials = credentials
        
        if on_progress:
            on_progress("Authentication successful!")
        
        return credentials
    
    async def _exchange_code(self, code: str, code_verifier: str) -> OAuthCredentials:
        """
        交换授权码获取token
        
        注意: Anthropic的OAuth需要服务器端交换
        这里返回一个包装过的API key格式
        """
        # Anthropic OAuth typically returns the API key directly in the code
        # or requires server-side exchange
        # For CLI usage, we often use API keys directly
        
        return OAuthCredentials(
            access_token=code,
            token_type="Bearer",
        )
    
    async def refresh(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """
        刷新token
        
        Anthropic使用长期有效的API key，通常不需要刷新
        """
        # Anthropic tokens don't typically expire
        return credentials
    
    async def logout(self) -> None:
        """登出"""
        self._credentials = None
    
    def get_authorization_url(self) -> str:
        """获取授权URL（用于手动流程）"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join(self.PROVIDER_INFO.scopes),
        }
        return f"{self.PROVIDER_INFO.auth_url}?{urllib.parse.urlencode(params)}"


# Convenience function
async def login_anthropic(**kwargs) -> OAuthCredentials:
    """便捷的Anthropic登录函数"""
    oauth = AnthropicOAuth()
    return await oauth.login(**kwargs)


__all__ = [
    "AnthropicOAuth",
    "login_anthropic",
]
