"""
GitHub Copilot OAuth Provider
等效于 Pi-Mono 的 packages/ai/src/utils/oauth/github-copilot.ts

GitHub Copilot的OAuth和设备流认证实现。
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any

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


class GitHubCopilotOAuth:
    """
    GitHub Copilot OAuth Provider
    
    支持GitHub Copilot的设备流认证和设备码流程。
    
    Example:
        >>> oauth = GitHubCopilotOAuth()
        >>> creds = await oauth.login(
        ...     on_auth=lambda info: print(info.format_message()),
        ...     on_progress=lambda msg: print(msg)
        ... )
    """
    
    PROVIDER_INFO = OAuthProviderInfo(
        id=OAuthProviderId.GITHUB_COPILOT,
        name="GitHub Copilot",
        description="GitHub Copilot API",
        auth_url="https://github.com/login/device/code",
        token_url="https://github.com/login/oauth/access_token",
        scopes=["read:user", "copilot"],
        requires_auth_file=True,
    )
    
    # GitHub OAuth App client ID for Copilot
    CLIENT_ID = "Iv1.b507a08c87ecfe98"
    
    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or self.CLIENT_ID
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
        执行GitHub设备流认证
        
        Args:
            on_auth: 认证URL回调
            on_prompt: 用户输入回调
            on_progress: 进度回调
        
        Returns:
            OAuth凭证
        """
        if on_progress:
            on_progress("Starting GitHub device flow...")
        
        # Step 1: Request device code
        device_code_data = await self._request_device_code()
        
        user_code = device_code_data["user_code"]
        device_code = device_code_data["device_code"]
        verification_uri = device_code_data.get("verification_uri", "https://github.com/login/device")
        expires_in = device_code_data.get("expires_in", 900)
        interval = device_code_data.get("interval", 5)
        
        auth_info = AuthInfo(
            url=verification_uri,
            instructions=f"Enter code: {user_code}\nWaiting for authorization...",
        )
        
        if on_auth:
            on_auth(auth_info)
        
        if on_progress:
            on_progress(f"Please enter code '{user_code}' at {verification_uri}")
        
        # Step 2: Poll for access token
        credentials = await self._poll_for_token(
            device_code, 
            interval, 
            expires_in,
            on_progress,
        )
        
        self._credentials = credentials
        
        if on_progress:
            on_progress("Authentication successful!")
        
        return credentials
    
    async def _request_device_code(self) -> Dict[str, Any]:
        """请求设备码"""
        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "scope": " ".join(self.PROVIDER_INFO.scopes),
        }).encode()
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        req = urllib.request.Request(
            self.PROVIDER_INFO.auth_url,
            data=data,
            headers=headers,
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    
    async def _poll_for_token(
        self,
        device_code: str,
        interval: int,
        expires_in: int,
        on_progress: Optional[ProgressCallback],
    ) -> OAuthCredentials:
        """轮询获取access token"""
        start_time = time.time()
        
        while time.time() - start_time < expires_in:
            data = urllib.parse.urlencode({
                "client_id": self.client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }).encode()
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            req = urllib.request.Request(
                self.PROVIDER_INFO.token_url,
                data=data,
                headers=headers,
                method="POST",
            )
            
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode())
                    
                    if "access_token" in result:
                        return OAuthCredentials(
                            access_token=result["access_token"],
                            token_type=result.get("token_type", "Bearer"),
                        )
                    
                    error = result.get("error")
                    if error == "authorization_pending":
                        if on_progress:
                            on_progress("Waiting for authorization...")
                    elif error == "slow_down":
                        interval += 5
                    elif error:
                        raise Exception(f"OAuth error: {error}")
                        
            except urllib.error.HTTPError as e:
                if e.code == 428:  # Precondition Required - still pending
                    pass
                else:
                    raise
            
            await asyncio.sleep(interval)
        
        raise TimeoutError("Device code expired")
    
    async def refresh(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """
        刷新token
        
        GitHub tokens需要定期刷新，但通常是通过重新登录
        """
        # GitHub device flow doesn't support refresh tokens
        # User needs to re-authenticate
        return credentials
    
    async def logout(self) -> None:
        """登出"""
        self._credentials = None
    
    def get_api_headers(self, credentials: OAuthCredentials) -> Dict[str, str]:
        """获取API请求头"""
        return {
            "Authorization": f"{credentials.token_type} {credentials.access_token}",
            "Accept": "application/json",
        }


# Convenience function
async def login_github_copilot(**kwargs) -> OAuthCredentials:
    """便捷的GitHub Copilot登录函数"""
    oauth = GitHubCopilotOAuth()
    return await oauth.login(**kwargs)


__all__ = [
    "GitHubCopilotOAuth",
    "login_github_copilot",
]
