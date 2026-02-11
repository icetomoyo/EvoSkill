"""
OAuth Types
等效于 Pi-Mono 的 packages/ai/src/utils/oauth/types.ts

OAuth相关类型定义。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Dict, Any, Protocol


class OAuthProviderId(str, Enum):
    """OAuth Provider ID枚举"""
    ANTHROPIC = "anthropic"
    GITHUB_COPILOT = "github-copilot"
    GOOGLE_ANTIGRAVITY = "google-antigravity"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    OPENAI_CODEX = "openai-codex"


@dataclass
class OAuthCredentials:
    """OAuth凭证"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None  # Unix timestamp
    token_type: str = "Bearer"
    
    def is_expired(self) -> bool:
        """检查token是否过期"""
        import time
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthCredentials":
        """从字典创建"""
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=data.get("expires_at"),
            token_type=data.get("token_type", "Bearer"),
        )


@dataclass
class AuthPrompt:
    """认证提示"""
    message: str
    placeholder: Optional[str] = None
    
    def __str__(self) -> str:
        if self.placeholder:
            return f"{self.message} ({self.placeholder}):"
        return f"{self.message}:"


@dataclass
class AuthInfo:
    """认证信息"""
    url: str
    instructions: Optional[str] = None
    code_verifier: Optional[str] = None  # For PKCE
    state: Optional[str] = None
    
    def format_message(self) -> str:
        """格式化认证消息"""
        lines = ["Open this URL in your browser:", f"\n{self.url}\n"]
        if self.instructions:
            lines.append(self.instructions)
        return "\n".join(lines)


@dataclass
class OAuthProviderInfo:
    """OAuth Provider信息"""
    id: OAuthProviderId
    name: str
    description: str
    auth_url: str
    token_url: str
    scopes: list[str]
    requires_auth_file: bool = False


# Type aliases for callbacks
AuthCallback = Callable[[AuthInfo], None]
PromptCallback = Callable[[AuthPrompt], Awaitable[str]]
ProgressCallback = Callable[[str], None]


@dataclass
class OAuthConfig:
    """OAuth配置"""
    client_id: str
    client_secret: Optional[str] = None
    auth_url: str = ""
    token_url: str = ""
    redirect_uri: str = "http://localhost:8080/callback"
    scopes: list[str] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []


class OAuthProvider(Protocol):
    """OAuth Provider协议"""
    
    @property
    def id(self) -> OAuthProviderId:
        """Provider ID"""
        ...
    
    @property
    def name(self) -> str:
        """Provider名称"""
        ...
    
    async def login(
        self,
        on_auth: Optional[AuthCallback] = None,
        on_prompt: Optional[PromptCallback] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> OAuthCredentials:
        """登录流程"""
        ...
    
    async def refresh(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """刷新token"""
        ...
    
    async def logout(self) -> None:
        """登出"""
        ...


class OAuthStorage(Protocol):
    """OAuth存储协议"""
    
    def load(self, provider_id: str) -> Optional[OAuthCredentials]:
        """加载凭证"""
        ...
    
    def save(self, provider_id: str, credentials: OAuthCredentials) -> None:
        """保存凭证"""
        ...
    
    def delete(self, provider_id: str) -> None:
        """删除凭证"""
        ...


__all__ = [
    "OAuthProviderId",
    "OAuthCredentials",
    "AuthPrompt",
    "AuthInfo",
    "OAuthProviderInfo",
    "OAuthConfig",
    "OAuthProvider",
    "OAuthStorage",
    "AuthCallback",
    "PromptCallback",
    "ProgressCallback",
]
