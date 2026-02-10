"""
OAuth Authentication Module

Supports:
- Google OAuth (for Google AI)
- Anthropic OAuth
- GitHub OAuth (for GitHub Copilot)
- GitHub Copilot specific OAuth flow

Based on Pi Mono's OAuth implementations.
"""
import asyncio
import json
import secrets
import webbrowser
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional, Callable, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
import urllib.request
import ssl


class OAuthProvider(Enum):
    """OAuth provider types"""
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    GITHUB = "github"
    GITHUB_COPILOT = "github_copilot"


@dataclass
class OAuthTokens:
    """OAuth token response"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    @property
    def expires_in_seconds(self) -> Optional[int]:
        """Get seconds until expiration"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now()
        return max(0, int(delta.total_seconds()))


@dataclass
class OAuthConfig:
    """OAuth configuration"""
    client_id: str
    client_secret: Optional[str] = None
    redirect_uri: str = "http://localhost:8080/callback"
    scope: str = ""
    additional_params: Optional[Dict[str, str]] = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""
    
    def __init__(self, callback_fn: Callable[[str], None], *args, **kwargs):
        self.callback_fn = callback_fn
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET request"""
        parsed = urlparse(self.path)
        
        if parsed.path == "/callback":
            query = parse_qs(parsed.query)
            
            if "code" in query:
                code = query["code"][0]
                self.callback_fn(code)
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html>
                <head><title>Authentication Successful</title></head>
                <body>
                <h1>Authentication Successful</h1>
                <p>You can close this window and return to the application.</p>
                <script>window.close();</script>
                </body>
                </html>
                """)
            elif "error" in query:
                error = query["error"][0]
                self.callback_fn(f"error:{error}")
                
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                <h1>Authentication Failed</h1>
                <p>Error: {error}</p>
                </body>
                </html>
                """.encode())
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress log messages"""
        pass


class BaseOAuth(ABC):
    """Base OAuth implementation"""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self._tokens: Optional[OAuthTokens] = None
        self._callback_code: Optional[str] = None
        self._callback_event = asyncio.Event()
    
    @property
    @abstractmethod
    def authorization_endpoint(self) -> str:
        """Authorization endpoint URL"""
        pass
    
    @property
    @abstractmethod
    def token_endpoint(self) -> str:
        """Token endpoint URL"""
        pass
    
    @property
    @abstractmethod
    def provider(self) -> OAuthProvider:
        """Provider type"""
        pass
    
    def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate authorization URL
        
        Returns:
            Tuple of (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "state": state,
        }
        
        if self.config.scope:
            params["scope"] = self.config.scope
        
        if self.config.additional_params:
            params.update(self.config.additional_params)
        
        auth_url = f"{self.authorization_endpoint}?{urlencode(params)}"
        return auth_url, state
    
    async def authenticate(self, timeout: float = 300.0) -> OAuthTokens:
        """
        Complete OAuth flow with local callback server
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            OAuth tokens
        """
        # Generate state
        auth_url, state = self.get_authorization_url()
        
        # Start local callback server
        server = await self._start_callback_server()
        
        try:
            # Open browser
            webbrowser.open(auth_url)
            
            # Wait for callback
            await asyncio.wait_for(
                self._callback_event.wait(),
                timeout=timeout
            )
            
            if self._callback_code.startswith("error:"):
                error = self._callback_code[6:]
                raise OAuthError(f"OAuth error: {error}")
            
            # Exchange code for tokens
            tokens = await self._exchange_code(self._callback_code)
            self._tokens = tokens
            
            return tokens
            
        finally:
            server.shutdown()
    
    async def _start_callback_server(self) -> HTTPServer:
        """Start local callback server"""
        parsed = urlparse(self.config.redirect_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        
        def handler(*args, **kwargs):
            return OAuthCallbackHandler(self._handle_callback, *args, **kwargs)
        
        server = HTTPServer((host, port), handler)
        
        # Run server in thread
        import threading
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        
        return server
    
    def _handle_callback(self, code: str):
        """Handle OAuth callback"""
        self._callback_code = code
        self._callback_event.set()
    
    async def _exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
        }
        
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret
        
        # Run in thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._do_token_request, data)
    
    def _do_token_request(self, data: Dict[str, str]) -> OAuthTokens:
        """Execute token request (blocking)"""
        req = urllib.request.Request(
            self.token_endpoint,
            data=urlencode(data).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            method="POST"
        )
        
        # Create SSL context that allows us to connect to HTTPS
        ssl_context = ssl.create_default_context()
        
        try:
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                result = json.loads(response.read().decode())
                
                access_token = result["access_token"]
                refresh_token = result.get("refresh_token")
                token_type = result.get("token_type", "Bearer")
                scope = result.get("scope")
                
                # Calculate expiration
                expires_at = None
                if "expires_in" in result:
                    expires_at = datetime.now() + timedelta(seconds=result["expires_in"])
                
                return OAuthTokens(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    token_type=token_type,
                    scope=scope
                )
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise OAuthError(f"Token exchange failed: {error_body}")
    
    async def refresh_tokens(self) -> OAuthTokens:
        """
        Refresh access token using refresh token
        
        Returns:
            New OAuth tokens
        """
        if not self._tokens or not self._tokens.refresh_token:
            raise OAuthError("No refresh token available")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._tokens.refresh_token,
            "client_id": self.config.client_id,
        }
        
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret
        
        loop = asyncio.get_event_loop()
        tokens = await loop.run_in_executor(None, self._do_token_request, data)
        self._tokens = tokens
        
        return tokens
    
    def get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary
        
        Returns:
            Valid access token
        """
        if not self._tokens:
            raise OAuthError("Not authenticated. Call authenticate() first.")
        
        # Check if token needs refresh
        if self._tokens.is_expired and self._tokens.refresh_token:
            # Refresh token synchronously
            import threading
            result = {"tokens": None, "error": None}
            
            def do_refresh():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result["tokens"] = loop.run_until_complete(self.refresh_tokens())
                except Exception as e:
                    result["error"] = e
            
            thread = threading.Thread(target=do_refresh)
            thread.start()
            thread.join()
            
            if result["error"]:
                raise result["error"]
            
            return result["tokens"].access_token
        
        return self._tokens.access_token
    
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self._tokens is not None and not self._tokens.is_expired
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        if not self._tokens:
            return {"authenticated": False}
        
        return {
            "authenticated": True,
            "access_token": self._tokens.access_token,
            "refresh_token": self._tokens.refresh_token,
            "expires_at": self._tokens.expires_at.isoformat() if self._tokens.expires_at else None,
            "token_type": self._tokens.token_type,
            "scope": self._tokens.scope,
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load from dictionary"""
        if not data.get("authenticated"):
            self._tokens = None
            return
        
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
        
        self._tokens = OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope")
        )


class GoogleOAuth(BaseOAuth):
    """Google OAuth implementation"""
    
    @property
    def authorization_endpoint(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"
    
    @property
    def token_endpoint(self) -> str:
        return "https://oauth2.googleapis.com/token"
    
    @property
    def provider(self) -> OAuthProvider:
        return OAuthProvider.GOOGLE


class AnthropicOAuth(BaseOAuth):
    """Anthropic OAuth implementation"""
    
    @property
    def authorization_endpoint(self) -> str:
        return "https://auth.anthropic.com/oauth/authorize"
    
    @property
    def token_endpoint(self) -> str:
        return "https://auth.anthropic.com/oauth/token"
    
    @property
    def provider(self) -> OAuthProvider:
        return OAuthProvider.ANTHROPIC


class GitHubOAuth(BaseOAuth):
    """GitHub OAuth implementation"""
    
    @property
    def authorization_endpoint(self) -> str:
        return "https://github.com/login/oauth/authorize"
    
    @property
    def token_endpoint(self) -> str:
        return "https://github.com/login/oauth/access_token"
    
    @property
    def provider(self) -> OAuthProvider:
        return OAuthProvider.GITHUB
    
    async def _exchange_code(self, code: str) -> OAuthTokens:
        """GitHub uses a different Accept header"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
        }
        
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._do_github_token_request, data)
    
    def _do_github_token_request(self, data: Dict[str, str]) -> OAuthTokens:
        """GitHub token request (blocking)"""
        req = urllib.request.Request(
            self.token_endpoint,
            data=urlencode(data).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            },
            method="POST"
        )
        
        ssl_context = ssl.create_default_context()
        
        try:
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                result = json.loads(response.read().decode())
                
                # GitHub may return errors in JSON
                if "error" in result:
                    raise OAuthError(f"GitHub OAuth error: {result['error']}")
                
                access_token = result["access_token"]
                token_type = result.get("token_type", "bearer")
                scope = result.get("scope", "")
                
                return OAuthTokens(
                    access_token=access_token,
                    refresh_token=None,  # GitHub doesn't use refresh tokens
                    expires_at=None,  # GitHub tokens don't expire
                    token_type=token_type,
                    scope=scope
                )
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise OAuthError(f"Token exchange failed: {error_body}")


class GitHubCopilotOAuth(BaseOAuth):
    """
    GitHub Copilot OAuth implementation
    
    Special flow for GitHub Copilot authentication.
    """
    
    COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
    
    def __init__(self):
        config = OAuthConfig(
            client_id=self.COPILOT_CLIENT_ID,
            redirect_uri="http://localhost:8080/callback",
            scope="read:user"
        )
        super().__init__(config)
        self._github_oauth = GitHubOAuth(config)
    
    @property
    def authorization_endpoint(self) -> str:
        return "https://github.com/login/oauth/authorize"
    
    @property
    def token_endpoint(self) -> str:
        return "https://github.com/login/oauth/access_token"
    
    @property
    def provider(self) -> OAuthProvider:
        return OAuthProvider.GITHUB_COPILOT
    
    async def authenticate(self, timeout: float = 300.0) -> OAuthTokens:
        """
        Authenticate with GitHub Copilot
        
        This uses the standard GitHub OAuth flow with the Copilot client ID.
        """
        # Use GitHub OAuth with Copilot client ID
        self._github_oauth.config.client_id = self.COPILOT_CLIENT_ID
        tokens = await self._github_oauth.authenticate(timeout)
        self._tokens = tokens
        return tokens


class OAuthError(Exception):
    """OAuth error"""
    pass


class OAuthManager:
    """
    OAuth Manager
    
    Manages OAuth tokens for multiple providers with secure storage.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._providers: Dict[OAuthProvider, BaseOAuth] = {}
        self._tokens_cache: Dict[OAuthProvider, Dict[str, Any]] = {}
        
        # Load cached tokens
        if storage_path:
            self._load_tokens()
    
    def register_provider(self, provider: OAuthProvider, oauth: BaseOAuth) -> None:
        """Register OAuth provider"""
        self._providers[provider] = oauth
        
        # Restore cached tokens if available
        if provider in self._tokens_cache:
            oauth.from_dict(self._tokens_cache[provider])
    
    def get_provider(self, provider: OAuthProvider) -> Optional[BaseOAuth]:
        """Get OAuth provider"""
        return self._providers.get(provider)
    
    async def authenticate(
        self,
        provider: OAuthProvider,
        timeout: float = 300.0
    ) -> OAuthTokens:
        """
        Authenticate with a provider
        
        Args:
            provider: OAuth provider
            timeout: Timeout in seconds
            
        Returns:
            OAuth tokens
        """
        oauth = self._providers.get(provider)
        if not oauth:
            raise OAuthError(f"Provider {provider} not registered")
        
        tokens = await oauth.authenticate(timeout)
        
        # Save tokens
        self._tokens_cache[provider] = oauth.to_dict()
        self._save_tokens()
        
        return tokens
    
    def get_access_token(self, provider: OAuthProvider) -> str:
        """Get access token for provider"""
        oauth = self._providers.get(provider)
        if not oauth:
            raise OAuthError(f"Provider {provider} not registered")
        
        token = oauth.get_access_token()
        
        # Update cache if refreshed
        self._tokens_cache[provider] = oauth.to_dict()
        self._save_tokens()
        
        return token
    
    def is_authenticated(self, provider: OAuthProvider) -> bool:
        """Check if provider is authenticated"""
        oauth = self._providers.get(provider)
        if not oauth:
            return False
        return oauth.is_authenticated()
    
    def logout(self, provider: OAuthProvider) -> None:
        """Logout from provider"""
        if provider in self._providers:
            self._providers[provider]._tokens = None
        
        if provider in self._tokens_cache:
            del self._tokens_cache[provider]
        
        self._save_tokens()
    
    def _load_tokens(self) -> None:
        """Load tokens from storage"""
        import os
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            for provider_name, tokens in data.items():
                try:
                    provider = OAuthProvider(provider_name)
                    self._tokens_cache[provider] = tokens
                except ValueError:
                    continue
        except Exception:
            pass
    
    def _save_tokens(self) -> None:
        """Save tokens to storage"""
        import os
        if not self.storage_path:
            return
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        # Convert to serializable format
        data = {
            p.value: t for p, t in self._tokens_cache.items()
        }
        
        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


def create_oauth(
    provider: OAuthProvider,
    client_id: str,
    client_secret: Optional[str] = None,
    scope: Optional[str] = None,
    redirect_uri: str = "http://localhost:8080/callback"
) -> BaseOAuth:
    """
    Factory function to create OAuth instances
    
    Args:
        provider: OAuth provider type
        client_id: OAuth client ID
        client_secret: OAuth client secret
        scope: OAuth scope
        redirect_uri: Redirect URI
        
    Returns:
        OAuth instance
    """
    config = OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope or ""
    )
    
    if provider == OAuthProvider.GOOGLE:
        return GoogleOAuth(config)
    elif provider == OAuthProvider.ANTHROPIC:
        return AnthropicOAuth(config)
    elif provider == OAuthProvider.GITHUB:
        return GitHubOAuth(config)
    elif provider == OAuthProvider.GITHUB_COPILOT:
        return GitHubCopilotOAuth()
    else:
        raise ValueError(f"Unknown provider: {provider}")
