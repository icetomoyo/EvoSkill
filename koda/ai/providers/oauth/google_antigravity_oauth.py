"""
Google Antigravity OAuth
Equivalent to Pi Mono's packages/ai/src/providers/oauth/google-antigravity-oauth.ts

OAuth flow for Google Antigravity authentication.
"""
import webbrowser
import urllib.parse
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from ...oauth_pkce import generate_pkce_challenge, PKCEChallenge


@dataclass
class AntigravityAuthConfig:
    """Google Antigravity OAuth configuration"""
    client_id: str
    redirect_uri: str = "http://localhost:8080/callback"
    scopes: tuple = ("https://www.googleapis.com/auth/antigravity",)
    auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"


@dataclass
class AntigravityTokens:
    """Google Antigravity authentication tokens"""
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


class GoogleAntigravityOAuth:
    """
    Google Antigravity OAuth authentication flow.
    
    Implements OAuth 2.0 with PKCE for Google Antigravity API.
    
    Example:
        >>> oauth = GoogleAntigravityOAuth(client_id="your-client-id")
        >>> auth_url = oauth.get_authorization_url()
        >>> # Open browser and get authorization code
        >>> tokens = oauth.exchange_code_for_tokens(auth_code)
    """
    
    def __init__(self, config: Optional[AntigravityAuthConfig] = None, 
                 client_id: Optional[str] = None):
        """
        Initialize OAuth flow.
        
        Args:
            config: Full configuration or None to use defaults
            client_id: Client ID (used if config not provided)
        """
        if config:
            self.config = config
        elif client_id:
            self.config = AntigravityAuthConfig(client_id=client_id)
        else:
            raise ValueError("Either config or client_id must be provided")
        
        self._pkce: Optional[PKCEChallenge] = None
        self._state: Optional[str] = None
    
    def get_authorization_url(self, state: Optional[str] = None,
                              additional_params: Optional[Dict[str, str]] = None) -> str:
        """
        Generate OAuth authorization URL with PKCE.
        
        Args:
            state: Optional state parameter for security
            additional_params: Additional URL parameters
            
        Returns:
            Authorization URL to open in browser
        """
        # Generate PKCE challenge
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
            "access_type": "offline",
            "prompt": "consent",
        }
        
        if additional_params:
            params.update(additional_params)
        
        query = urllib.parse.urlencode(params)
        return f"{self.config.auth_url}?{query}"
    
    def open_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Open authorization URL in browser.
        
        Args:
            state: Optional state parameter
            
        Returns:
            The authorization URL that was opened
        """
        url = self.get_authorization_url(state)
        webbrowser.open(url)
        return url
    
    def exchange_code_for_tokens(self, auth_code: str,
                                  state: Optional[str] = None) -> AntigravityTokens:
        """
        Exchange authorization code for tokens.
        
        Args:
            auth_code: Authorization code from callback
            state: State parameter for verification
            
        Returns:
            Authentication tokens
            
        Raises:
            ValueError: If state mismatch or no PKCE challenge
        """
        if state and self._state and state != self._state:
            raise ValueError("State mismatch - possible CSRF attack")
        
        if not self._pkce:
            raise ValueError("No PKCE challenge - call get_authorization_url first")
        
        # Build token request
        data = {
            "client_id": self.config.client_id,
            "code": auth_code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": self._pkce.code_verifier,
        }
        
        # Exchange code for tokens
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
        
        return AntigravityTokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_in=result.get("expires_in"),
            scope=result.get("scope"),
            token_type=result.get("token_type", "Bearer"),
        )
    
    def refresh_access_token(self, refresh_token: str) -> AntigravityTokens:
        """
        Refresh access token using refresh token.
        
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
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
        
        return AntigravityTokens(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token") or refresh_token,
            expires_in=result.get("expires_in"),
            scope=result.get("scope"),
            token_type=result.get("token_type", "Bearer"),
        )
    
    def _generate_state(self) -> str:
        """Generate random state parameter"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_pkce_verifier(self) -> Optional[str]:
        """Get current PKCE verifier (for testing/debug)"""
        return self._pkce.code_verifier if self._pkce else None
    
    def get_state(self) -> Optional[str]:
        """Get current state parameter"""
        return self._state


# Convenience functions
def create_antigravity_oauth(client_id: str, 
                              redirect_uri: Optional[str] = None) -> GoogleAntigravityOAuth:
    """
    Create Antigravity OAuth instance.
    
    Args:
        client_id: Google OAuth client ID
        redirect_uri: Optional custom redirect URI
        
    Returns:
        Configured OAuth instance
    """
    config = None
    if redirect_uri:
        config = AntigravityAuthConfig(client_id=client_id, redirect_uri=redirect_uri)
    return GoogleAntigravityOAuth(config=config, client_id=client_id)


__all__ = [
    "GoogleAntigravityOAuth",
    "AntigravityAuthConfig",
    "AntigravityTokens",
    "create_antigravity_oauth",
]
