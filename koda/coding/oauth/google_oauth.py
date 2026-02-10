"""
Google OAuth - PKCE flow implementation
Equivalent to Pi Mono's google-gemini-cli.ts
"""
import secrets
import hashlib
import base64
import json
from typing import List, Optional
import aiohttp

from koda.coding.auth_storage import OAuthCredential, OAuthProviderInterface


class GoogleOAuth(OAuthProviderInterface):
    """
    Google OAuth PKCE implementation
    
    Supports:
    - Authorization Code flow with PKCE
    - Token refresh
    - Multiple scopes
    """
    
    def __init__(self, client_id: str, redirect_uri: str = "http://localhost:8085/callback"):
        super().__init__(
            id="google-gemini-cli",
            name="Google Gemini CLI",
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token"
        )
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self._code_verifier: Optional[str] = None
    
    def _generate_pkce(self) -> tuple:
        """Generate PKCE code verifier and challenge"""
        self._code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self._code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        return self._code_verifier, challenge
    
    async def start_flow(self, scopes: List[str]) -> str:
        """Start OAuth flow, return authorization URL"""
        verifier, challenge = self._generate_pkce()
        
        default_scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/generative-language.retro"
        ]
        
        all_scopes = list(set(default_scopes + scopes))
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(all_scopes),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
        
        from urllib.parse import urlencode
        auth_url = f"{self.authorization_endpoint}?{urlencode(params)}"
        
        return auth_url
    
    async def handle_callback(self, code: str, verifier: Optional[str] = None) -> OAuthCredential:
        """Exchange authorization code for tokens"""
        if verifier is None:
            verifier = self._code_verifier
        
        if not verifier:
            raise ValueError("No code verifier available")
        
        data = {
            "client_id": self.client_id,
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_endpoint, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Token exchange failed: {response.status} - {error_text}")
                
                token_data = await response.json()
                
                expires_in = token_data.get("expires_in", 3600)
                import time
                expires_at = int(time.time()) + expires_in
                
                return OAuthCredential(
                    type="oauth",
                    provider=self.id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", ""),
                    expires_at=expires_at,
                    scopes=token_data.get("scope", "").split(),
                    created_at=int(time.time())
                )
    
    async def refresh_token(self, credential: OAuthCredential) -> OAuthCredential:
        """Refresh access token"""
        if not credential.refresh_token:
            raise ValueError("No refresh token available")
        
        data = {
            "client_id": self.client_id,
            "refresh_token": credential.refresh_token,
            "grant_type": "refresh_token",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_endpoint, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Token refresh failed: {response.status} - {error_text}")
                
                token_data = await response.json()
                
                expires_in = token_data.get("expires_in", 3600)
                import time
                expires_at = int(time.time()) + expires_in
                
                credential.access_token = token_data["access_token"]
                credential.expires_at = expires_at
                
                if "refresh_token" in token_data:
                    credential.refresh_token = token_data["refresh_token"]
                
                return credential
