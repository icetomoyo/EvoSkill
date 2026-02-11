"""
OpenAI Codex OAuth
Equivalent to Pi Mono's packages/ai/src/providers/oauth/openai-codex-oauth.ts

OAuth flow for OpenAI Codex authentication.
"""
import webbrowser
import urllib.parse
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from ...oauth_pkce import generate_pkce_challenge, PKCEChallenge


@dataclass
class OpenAICodexOAuthConfig:
    """OpenAI Codex OAuth configuration"""
    client_id: str
    redirect_uri: str = "http://localhost:8080/callback"
    scopes: tuple = field(default_factory=lambda: (
        "model.read",
        "model.request",
        "api.read",
    ))
    auth_url: str = "https://auth.openai.com/authorize"
    token_url: str = "https://auth.openai.com/token"
    api_base: str = "https://api.openai.com"


@dataclass
class OpenAICodexTokens:
    """OpenAI Codex authentication tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    token_type: str = "Bearer"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "token_type": self.token_type,
        }
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid"""
        return bool(self.access_token and len(self.access_token) > 20)


class OpenAICodexOAuth:
    """
    OpenAI Codex OAuth authentication flow.
    
    Implements OAuth 2.0 with PKCE for OpenAI Codex API access.
    
    Example:
        >>> oauth = OpenAICodexOAuth(client_id="your-client-id")
        >>> auth_url = oauth.get_authorization_url()
        >>> webbrowser.open(auth_url)
        >>> tokens = oauth.exchange_code_for_tokens(auth_code)
    """
    
    def __init__(self, config: Optional[OpenAICodexOAuthConfig] = None,
                 client_id: Optional[str] = None):
        """
        Initialize OpenAI Codex OAuth.
        
        Args:
            config: OAuth configuration
            client_id: Client ID (if config not provided)
        """
        if config:
            self.config = config
        elif client_id:
            self.config = OpenAICodexOAuthConfig(client_id=client_id)
        else:
            raise ValueError("Either config or client_id must be provided")
        
        self._pkce: Optional[PKCEChallenge] = None
        self._state: Optional[str] = None
    
    def get_authorization_url(self, state: Optional[str] = None,
                              additional_scopes: Optional[list] = None) -> str:
        """
        Generate authorization URL.
        
        Args:
            state: Optional state parameter
            additional_scopes: Additional scopes to request
            
        Returns:
            Authorization URL
        """
        self._pkce = generate_pkce_challenge()
        self._state = state or self._generate_state()
        
        scopes = list(self.config.scopes)
        if additional_scopes:
            scopes.extend(additional_scopes)
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": self._state,
            "code_challenge": self._pkce.code_challenge,
            "code_challenge_method": self._pkce.method,
        }
        
        query = urllib.parse.urlencode(params)
        return f"{self.config.auth_url}?{query}"
    
    def open_authorization_url(self, state: Optional[str] = None) -> str:
        """Open auth URL in browser"""
        url = self.get_authorization_url(state)
        webbrowser.open(url)
        return url
    
    def exchange_code_for_tokens(self, auth_code: str,
                                  state: Optional[str] = None) -> OpenAICodexTokens:
        """
        Exchange authorization code for tokens.
        
        Args:
            auth_code: Authorization code
            state: State for verification
            
        Returns:
            Authentication tokens
        """
        if state and self._state and state != self._state:
            raise ValueError("State mismatch - possible CSRF attack")
        
        if not self._pkce:
            raise ValueError("No PKCE challenge - call get_authorization_url first")
        
        data = {
            "client_id": self.config.client_id,
            "code": auth_code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": self._pkce.code_verifier,
        }
        
        import urllib.request
        import json
        
        req = urllib.request.Request(
            self.config.token_url,
            data=urllib.parse.urlencode(data).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        
        return OpenAICodexTokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_in=result.get("expires_in"),
            scope=result.get("scope"),
            token_type=result.get("token_type", "Bearer"),
        )
    
    def refresh_access_token(self, refresh_token: str) -> OpenAICodexTokens:
        """
        Refresh access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New tokens
        """
        data = {
            "client_id": self.config.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        import urllib.request
        import json
        
        req = urllib.request.Request(
            self.config.token_url,
            data=urllib.parse.urlencode(data).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        
        return OpenAICodexTokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token") or refresh_token,
            expires_in=result.get("expires_in"),
            scope=result.get("scope"),
            token_type=result.get("token_type", "Bearer"),
        )
    
    def get_auth_headers(self, tokens: OpenAICodexTokens) -> Dict[str, str]:
        """
        Get authorization headers for API requests.
        
        Args:
            tokens: Valid tokens
            
        Returns:
            Headers dict
        """
        return {
            "Authorization": f"Bearer {tokens.access_token}",
        }
    
    def validate_token(self, tokens: OpenAICodexTokens) -> bool:
        """
        Validate token by making a test API call.
        
        Args:
            tokens: Tokens to validate
            
        Returns:
            True if token is valid
        """
        import urllib.request
        
        headers = self.get_auth_headers(tokens)
        
        req = urllib.request.Request(
            f"{self.config.api_base}/v1/models",
            headers=headers,
            method="GET"
        )
        
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status == 200
        except Exception:
            return False
    
    def _generate_state(self) -> str:
        """Generate state parameter"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @property
    def pkce_verifier(self) -> Optional[str]:
        """Get current PKCE verifier"""
        return self._pkce.code_verifier if self._pkce else None


# Convenience functions
def create_openai_codex_oauth(client_id: str,
                               redirect_uri: Optional[str] = None) -> OpenAICodexOAuth:
    """
    Create OpenAI Codex OAuth instance.
    
    Args:
        client_id: OAuth client ID
        redirect_uri: Custom redirect URI
        
    Returns:
        OAuth instance
    """
    if redirect_uri:
        config = OpenAICodexOAuthConfig(client_id=client_id, redirect_uri=redirect_uri)
        return OpenAICodexOAuth(config=config)
    return OpenAICodexOAuth(client_id=client_id)


__all__ = [
    "OpenAICodexOAuth",
    "OpenAICodexOAuthConfig",
    "OpenAICodexTokens",
    "create_openai_codex_oauth",
]
