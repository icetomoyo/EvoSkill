"""
Tests for OAuth module
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from koda.ai.oauth import (
    OAuthConfig,
    OAuthTokens,
    OAuthProvider,
    OAuthError,
    GoogleOAuth,
    GitHubOAuth,
    GitHubCopilotOAuth,
    OAuthManager,
    create_oauth,
)


class TestOAuthTokens:
    """Test OAuthTokens"""
    
    def test_token_creation(self):
        """Test creating tokens"""
        tokens = OAuthTokens(
            access_token="test_token",
            refresh_token="refresh_token",
            token_type="Bearer",
            scope="read write"
        )
        
        assert tokens.access_token == "test_token"
        assert tokens.refresh_token == "refresh_token"
        assert tokens.token_type == "Bearer"
        assert tokens.scope == "read write"
    
    def test_token_not_expired(self):
        """Test token not expired"""
        future = datetime.now() + timedelta(hours=1)
        tokens = OAuthTokens(
            access_token="test",
            expires_at=future
        )
        
        assert not tokens.is_expired
        assert tokens.expires_in_seconds > 0
    
    def test_token_expired(self):
        """Test token expired"""
        past = datetime.now() - timedelta(hours=1)
        tokens = OAuthTokens(
            access_token="test",
            expires_at=past
        )
        
        assert tokens.is_expired
        assert tokens.expires_in_seconds == 0
    
    def test_no_expiration(self):
        """Test token without expiration"""
        tokens = OAuthTokens(access_token="test")
        
        assert not tokens.is_expired
        assert tokens.expires_in_seconds is None


class TestOAuthConfig:
    """Test OAuthConfig"""
    
    def test_config_creation(self):
        """Test creating config"""
        config = OAuthConfig(
            client_id="client123",
            client_secret="secret456",
            redirect_uri="http://localhost:8080/callback",
            scope="read write",
            additional_params={"prompt": "consent"}
        )
        
        assert config.client_id == "client123"
        assert config.client_secret == "secret456"
        assert config.redirect_uri == "http://localhost:8080/callback"
        assert config.scope == "read write"
        assert config.additional_params == {"prompt": "consent"}


class TestGoogleOAuth:
    """Test Google OAuth"""
    
    def test_provider(self):
        """Test provider type"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        assert oauth.provider == OAuthProvider.GOOGLE
    
    def test_endpoints(self):
        """Test OAuth endpoints"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        assert "accounts.google.com" in oauth.authorization_endpoint
        assert "oauth2.googleapis.com" in oauth.token_endpoint
    
    def test_get_authorization_url(self):
        """Test generating authorization URL"""
        config = OAuthConfig(
            client_id="client123",
            redirect_uri="http://localhost:8080/callback",
            scope="profile email"
        )
        oauth = GoogleOAuth(config)
        
        url, state = oauth.get_authorization_url()
        
        assert "accounts.google.com" in url
        assert "client_id=client123" in url
        assert "response_type=code" in url
        assert "scope=profile+email" in url
        assert state is not None
        assert len(state) > 0
    
    def test_get_authorization_url_with_state(self):
        """Test generating URL with custom state"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        url, state = oauth.get_authorization_url(state="my_state_123")
        
        assert "state=my_state_123" in url
        assert state == "my_state_123"
    
    def test_is_authenticated(self):
        """Test authentication check"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        assert not oauth.is_authenticated()
        
        # Set tokens
        oauth._tokens = OAuthTokens(access_token="test")
        assert oauth.is_authenticated()
    
    def test_get_access_token_not_authenticated(self):
        """Test getting token when not authenticated"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        with pytest.raises(OAuthError, match="Not authenticated"):
            oauth.get_access_token()
    
    def test_get_access_token(self):
        """Test getting valid access token"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        future = datetime.now() + timedelta(hours=1)
        oauth._tokens = OAuthTokens(
            access_token="valid_token",
            expires_at=future
        )
        
        assert oauth.get_access_token() == "valid_token"


class TestGitHubOAuth:
    """Test GitHub OAuth"""
    
    def test_provider(self):
        """Test provider type"""
        config = OAuthConfig(client_id="test")
        oauth = GitHubOAuth(config)
        
        assert oauth.provider == OAuthProvider.GITHUB
    
    def test_endpoints(self):
        """Test OAuth endpoints"""
        config = OAuthConfig(client_id="test")
        oauth = GitHubOAuth(config)
        
        assert "github.com/login/oauth/authorize" in oauth.authorization_endpoint
        assert "github.com/login/oauth/access_token" in oauth.token_endpoint


class TestGitHubCopilotOAuth:
    """Test GitHub Copilot OAuth"""
    
    def test_provider(self):
        """Test provider type"""
        oauth = GitHubCopilotOAuth()
        
        assert oauth.provider == OAuthProvider.GITHUB_COPILOT
    
    def test_copilot_client_id(self):
        """Test Copilot uses correct client ID"""
        oauth = GitHubCopilotOAuth()
        
        assert oauth.config.client_id == "Iv1.b507a08c87ecfe98"


class TestOAuthManager:
    """Test OAuthManager"""
    
    def test_register_provider(self):
        """Test registering provider"""
        manager = OAuthManager()
        
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        manager.register_provider(OAuthProvider.GOOGLE, oauth)
        
        assert manager.get_provider(OAuthProvider.GOOGLE) is oauth
    
    def test_get_provider_not_registered(self):
        """Test getting unregistered provider"""
        manager = OAuthManager()
        
        assert manager.get_provider(OAuthProvider.GOOGLE) is None
    
    def test_is_authenticated(self):
        """Test authentication check"""
        manager = OAuthManager()
        
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        oauth._tokens = OAuthTokens(access_token="test")
        
        manager.register_provider(OAuthProvider.GOOGLE, oauth)
        
        assert manager.is_authenticated(OAuthProvider.GOOGLE)
        assert not manager.is_authenticated(OAuthProvider.ANTHROPIC)
    
    def test_is_authenticated_not_registered(self):
        """Test auth check for unregistered provider"""
        manager = OAuthManager()
        
        assert not manager.is_authenticated(OAuthProvider.GOOGLE)
    
    def test_logout(self):
        """Test logout"""
        manager = OAuthManager()
        
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        oauth._tokens = OAuthTokens(access_token="test")
        
        manager.register_provider(OAuthProvider.GOOGLE, oauth)
        manager._tokens_cache[OAuthProvider.GOOGLE] = oauth.to_dict()
        
        assert manager.is_authenticated(OAuthProvider.GOOGLE)
        
        manager.logout(OAuthProvider.GOOGLE)
        
        assert not manager.is_authenticated(OAuthProvider.GOOGLE)
        assert OAuthProvider.GOOGLE not in manager._tokens_cache


class TestCreateOAuth:
    """Test create_oauth factory"""
    
    def test_create_google(self):
        """Test creating Google OAuth"""
        oauth = create_oauth(
            OAuthProvider.GOOGLE,
            client_id="test",
            client_secret="secret",
            scope="profile"
        )
        
        assert isinstance(oauth, GoogleOAuth)
        assert oauth.config.client_id == "test"
        assert oauth.config.client_secret == "secret"
        assert oauth.config.scope == "profile"
    
    def test_create_github(self):
        """Test creating GitHub OAuth"""
        oauth = create_oauth(
            OAuthProvider.GITHUB,
            client_id="test",
            client_secret="secret"
        )
        
        assert isinstance(oauth, GitHubOAuth)
    
    def test_create_github_copilot(self):
        """Test creating GitHub Copilot OAuth"""
        oauth = create_oauth(
            OAuthProvider.GITHUB_COPILOT,
            client_id="ignored"  # Copilot uses fixed client ID
        )
        
        assert isinstance(oauth, GitHubCopilotOAuth)
        # Should use built-in client ID, not the parameter
        assert oauth.config.client_id == "Iv1.b507a08c87ecfe98"
    
    def test_create_unknown_provider(self):
        """Test creating unknown provider"""
        # Create a mock provider value
        mock_provider = Mock()
        mock_provider.value = "unknown"
        
        with pytest.raises(ValueError, match="Unknown provider"):
            create_oauth(mock_provider, client_id="test")


class TestOAuthError:
    """Test OAuthError"""
    
    def test_error_creation(self):
        """Test creating error"""
        error = OAuthError("Something went wrong")
        
        assert str(error) == "Something went wrong"
    
    def test_error_is_exception(self):
        """Test error is an Exception"""
        with pytest.raises(OAuthError):
            raise OAuthError("Test error")


class TestOAuthTokensSerialization:
    """Test OAuthTokens serialization"""
    
    def test_to_dict(self):
        """Test converting to dict"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        future = datetime.now() + timedelta(hours=1)
        oauth._tokens = OAuthTokens(
            access_token="token123",
            refresh_token="refresh456",
            expires_at=future,
            token_type="Bearer",
            scope="read write"
        )
        
        data = oauth.to_dict()
        
        assert data["authenticated"] is True
        assert data["access_token"] == "token123"
        assert data["refresh_token"] == "refresh456"
        assert data["token_type"] == "Bearer"
        assert data["scope"] == "read write"
        assert "expires_at" in data
    
    def test_to_dict_not_authenticated(self):
        """Test converting to dict when not authenticated"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        data = oauth.to_dict()
        
        assert data["authenticated"] is False
    
    def test_from_dict(self):
        """Test loading from dict"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        future = datetime.now() + timedelta(hours=1)
        data = {
            "authenticated": True,
            "access_token": "token123",
            "refresh_token": "refresh456",
            "expires_at": future.isoformat(),
            "token_type": "Bearer",
            "scope": "read write"
        }
        
        oauth.from_dict(data)
        
        assert oauth._tokens is not None
        assert oauth._tokens.access_token == "token123"
        assert oauth._tokens.refresh_token == "refresh456"
    
    def test_from_dict_not_authenticated(self):
        """Test loading from dict when not authenticated"""
        config = OAuthConfig(client_id="test")
        oauth = GoogleOAuth(config)
        
        oauth._tokens = OAuthTokens(access_token="test")
        
        oauth.from_dict({"authenticated": False})
        
        assert oauth._tokens is None
