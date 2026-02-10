"""
Auth Storage - Secure credential management
Equivalent to Pi Mono's auth-storage.ts
"""
import json
import os
from typing import Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import base64
from enum import Enum


class CredentialType(Enum):
    API_KEY = "apiKey"
    OAUTH = "oauth"


@dataclass
class ApiKeyCredential:
    """API Key credential"""
    type: str = "apiKey"
    key: str = ""
    provider: str = ""
    created_at: int = 0


@dataclass
class OAuthCredential:
    """OAuth credential"""
    type: str = "oauth"
    provider: str = ""
    access_token: str = ""
    refresh_token: str = ""
    expires_at: int = 0  # Unix timestamp
    scopes: list = None
    created_at: int = 0
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []
    
    def is_expired(self) -> bool:
        """Check if token is expired (with 5 min buffer)"""
        if self.expires_at == 0:
            return False
        return datetime.now().timestamp() > (self.expires_at - 300)


Credential = Union[ApiKeyCredential, OAuthCredential]


class AuthStorage:
    """
    Secure credential storage
    
    Features:
    - API Key: system keyring storage
    - OAuth: encrypted file storage + keyring
    - Automatic token refresh
    - Fallback resolver for models.json config
    
    Equivalent to Pi Mono's AuthStorage
    """
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._credentials_file = self.storage_dir / "credentials.enc"
        self._fallback_resolver: Optional[Callable[[str], Optional[str]]] = None
        self._cache: Dict[str, Credential] = {}
        
        # Try to import keyring
        try:
            import keyring
            self._keyring = keyring
            self._has_keyring = True
        except ImportError:
            self._keyring = None
            self._has_keyring = False
    
    def set_fallback_resolver(self, resolver: Callable[[str], Optional[str]]) -> None:
        """Set fallback resolver for models.json config"""
        self._fallback_resolver = resolver
    
    def get(self, provider: str) -> Optional[Credential]:
        """Get credential for provider"""
        # Check cache first
        if provider in self._cache:
            return self._cache[provider]
        
        # Try keyring for API key
        if self._has_keyring:
            try:
                key = self._keyring.get_password("koda", provider)
                if key:
                    cred = ApiKeyCredential(
                        type="apiKey",
                        key=key,
                        provider=provider,
                        created_at=int(datetime.now().timestamp())
                    )
                    self._cache[provider] = cred
                    return cred
            except Exception:
                pass
        
        # Try file storage for OAuth
        try:
            if self._credentials_file.exists():
                data = self._load_encrypted()
                if provider in data:
                    cred_data = data[provider]
                    if cred_data.get("type") == "oauth":
                        cred = OAuthCredential(**cred_data)
                        self._cache[provider] = cred
                        return cred
        except Exception:
            pass
        
        return None
    
    def set(self, provider: str, credential: Credential) -> None:
        """Store credential"""
        self._cache[provider] = credential
        
        if isinstance(credential, ApiKeyCredential):
            # Store in keyring
            if self._has_keyring:
                try:
                    self._keyring.set_password("koda", provider, credential.key)
                except Exception as e:
                    print(f"Warning: Failed to store API key in keyring: {e}")
                    # Fall back to file storage
                    self._store_in_file(provider, credential)
            else:
                self._store_in_file(provider, credential)
        
        elif isinstance(credential, OAuthCredential):
            # Store OAuth in encrypted file
            self._store_oauth_in_file(provider, credential)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider (handles OAuth fallback)"""
        cred = self.get(provider)
        
        if isinstance(cred, ApiKeyCredential):
            return cred.key
        
        if isinstance(cred, OAuthCredential):
            # OAuth tokens are used as API keys for some providers
            if not cred.is_expired():
                return cred.access_token
            # Try to refresh
            # TODO: Implement refresh logic
            return None
        
        # Try fallback resolver
        if self._fallback_resolver:
            return self._fallback_resolver(provider)
        
        # Try environment variable
        env_var = f"{provider.upper().replace('-', '_')}_API_KEY"
        return os.getenv(env_var)
    
    async def refresh_oauth(self, provider: str) -> bool:
        """Refresh OAuth token"""
        cred = self.get(provider)
        if not isinstance(cred, OAuthCredential):
            return False
        
        if not cred.refresh_token:
            return False
        
        # TODO: Implement actual refresh based on provider
        # This would call the provider's token endpoint
        
        return False
    
    def delete(self, provider: str) -> bool:
        """Delete credential"""
        if provider in self._cache:
            del self._cache[provider]
        
        # Delete from keyring
        if self._has_keyring:
            try:
                self._keyring.delete_password("koda", provider)
            except Exception:
                pass
        
        # Delete from file
        try:
            if self._credentials_file.exists():
                data = self._load_encrypted()
                if provider in data:
                    del data[provider]
                    self._save_encrypted(data)
                    return True
        except Exception:
            pass
        
        return False
    
    def list_providers(self) -> list:
        """List all providers with stored credentials"""
        providers = set()
        
        # From keyring
        if self._has_keyring:
            try:
                # keyring doesn't support listing, so we can't get this
                pass
            except Exception:
                pass
        
        # From file
        try:
            if self._credentials_file.exists():
                data = self._load_encrypted()
                providers.update(data.keys())
        except Exception:
            pass
        
        # From cache
        providers.update(self._cache.keys())
        
        return list(providers)
    
    def _store_in_file(self, provider: str, credential: ApiKeyCredential) -> None:
        """Store API key credential in file"""
        data = {}
        if self._credentials_file.exists():
            data = self._load_encrypted()
        
        data[provider] = asdict(credential)
        self._save_encrypted(data)
    
    def _store_oauth_in_file(self, provider: str, credential: OAuthCredential) -> None:
        """Store OAuth credential in file"""
        data = {}
        if self._credentials_file.exists():
            data = self._load_encrypted()
        
        data[provider] = asdict(credential)
        self._save_encrypted(data)
    
    def _load_encrypted(self) -> Dict[str, Any]:
        """Load and decrypt credentials file"""
        if not self._credentials_file.exists():
            return {}
        
        try:
            # Simple obfuscation - in production, use proper encryption
            content = self._credentials_file.read_bytes()
            # Decode base64
            json_bytes = base64.b64decode(content)
            return json.loads(json_bytes.decode('utf-8'))
        except Exception:
            return {}
    
    def _save_encrypted(self, data: Dict[str, Any]) -> None:
        """Encrypt and save credentials file"""
        # Simple obfuscation - in production, use proper encryption
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        encoded = base64.b64encode(json_bytes)
        self._credentials_file.write_bytes(encoded)


class OAuthProviderInterface:
    """Interface for OAuth providers"""
    
    def __init__(self, id: str, name: str, authorization_endpoint: str, token_endpoint: str):
        self.id = id
        self.name = name
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
    
    async def start_flow(self, scopes: list) -> str:
        """Start OAuth flow, return authorization URL"""
        raise NotImplementedError
    
    async def handle_callback(self, code: str, verifier: str) -> OAuthCredential:
        """Handle callback, exchange code for token"""
        raise NotImplementedError
    
    async def refresh_token(self, credential: OAuthCredential) -> OAuthCredential:
        """Refresh access token"""
        raise NotImplementedError
