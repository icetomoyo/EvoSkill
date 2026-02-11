"""
Google Gemini CLI OAuth
Equivalent to Pi Mono's packages/ai/src/providers/oauth/google-gemini-cli-oauth.ts

OAuth flow specifically for Google Gemini CLI authentication.
"""
import webbrowser
import urllib.parse
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from ...oauth_pkce import generate_pkce_challenge, PKCEChallenge


@dataclass
class GeminiCLIOAuthConfig:
    """Gemini CLI OAuth configuration"""
    client_id: str
    redirect_uri: str = "http://localhost:8080/callback"
    scopes: tuple = field(default_factory=lambda: (
        "https://www.googleapis.com/auth/generative-language",
        "https://www.googleapis.com/auth/cloud-platform",
    ))
    auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"
    audience: str = "https://generativelanguage.googleapis.com/"


@dataclass
class GeminiCLITokens:
    """Gemini CLI authentication tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    token_type: str = "Bearer"
    id_token: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "token_type": self.token_type,
            "id_token": self.id_token,
        }
    
    @property
    def is_valid(self) -> bool:
        """Check if token appears valid"""
        return bool(self.access_token and len(self.access_token) > 10)


class GoogleGeminiCLIOAuth:
    """
    Google Gemini CLI OAuth authentication flow.
    
    Specialized OAuth flow for Gemini CLI with appropriate scopes.
    
    Example:
        >>> oauth = GoogleGeminiCLIOAuth(client_id="your-client-id")
        >>> auth_url = oauth.get_authorization_url()
        >>> webbrowser.open(auth_url)
        >>> # After callback, exchange code
        >>> tokens = oauth.exchange_code_for_tokens(auth_code)
    """
    
    def __init__(self, config: Optional[GeminiCLIOAuthConfig] = None,
                 client_id: Optional[str] = None):
        """
        Initialize Gemini CLI OAuth.
        
        Args:
            config: Full configuration
            client_id: Client ID (if config not provided)
        """
        if config:
            self.config = config
        elif client_id:
            self.config = GeminiCLIOAuthConfig(client_id=client_id)
        else:
            raise ValueError("Either config or client_id must be provided")
        
        self._pkce: Optional[PKCEChallenge] = None
        self._state: Optional[str] = None
    
    def get_authorization_url(self, state: Optional[str] = None,
                              include_refresh: bool = True) -> str:
        """
        Generate authorization URL.
        
        Args:
            state: Optional state parameter
            include_refresh: Request refresh token
            
        Returns:
            Authorization URL
        """
        self._pkce = generate_pkce_challenge()
        self._state = state or self._generate_state()
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": self._state,
            "code_challenge": self._pkce.code_challenge,
            "code_challenge_method": self._pkce.method,
            "access_type": "offline" if include_refresh else "online",
        }
        
        if include_refresh:
            params["prompt"] = "consent"
        
        query = urllib.parse.urlencode(params)
        return f"{self.config.auth_url}?{query}"
    
    def open_authorization_url(self, state: Optional[str] = None) -> str:
        """Open auth URL in browser"""
        url = self.get_authorization_url(state)
        webbrowser.open(url)
        return url
    
    def exchange_code_for_tokens(self, auth_code: str,
                                  state: Optional[str] = None) -> GeminiCLITokens:
        """
        Exchange code for tokens.
        
        Args:
            auth_code: Authorization code
            state: State for verification
            
        Returns:
            Authentication tokens
        """
        if state and self._state and state != self._state:
            raise ValueError("State mismatch")
        
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
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        
        return GeminiCLITokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_in=result.get("expires_in"),
            scope=result.get("scope"),
            token_type=result.get("token_type", "Bearer"),
            id_token=result.get("id_token"),
        )
    
    def refresh_access_token(self, refresh_token: str) -> GeminiCLITokens:
        """Refresh access token"""
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
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        
        return GeminiCLITokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token") or refresh_token,
            expires_in=result.get("expires_in"),
            scope=result.get("scope"),
            token_type=result.get("token_type", "Bearer"),
            id_token=result.get("id_token"),
        )
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successful
        """
        revoke_url = "https://oauth2.googleapis.com/revoke"
        
        import urllib.request
        
        data = urllib.parse.urlencode({"token": token}).encode()
        
        req = urllib.request.Request(
            revoke_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
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
    
    def get_auth_headers(self, tokens: GeminiCLITokens) -> Dict[str, str]:
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


# Convenience factory
def create_gemini_cli_oauth(client_id: str,
                            redirect_uri: Optional[str] = None) -> GoogleGeminiCLIOAuth:
    """
    Create Gemini CLI OAuth instance.
    
    Args:
        client_id: OAuth client ID
        redirect_uri: Custom redirect URI
        
    Returns:
        OAuth instance
    """
    if redirect_uri:
        config = GeminiCLIOAuthConfig(client_id=client_id, redirect_uri=redirect_uri)
        return GoogleGeminiCLIOAuth(config=config)
    return GoogleGeminiCLIOAuth(client_id=client_id)


__all__ = [
    "GoogleGeminiCLIOAuth",
    "GeminiCLIOAuthConfig",
    "GeminiCLITokens",
    "create_gemini_cli_oauth",
]
