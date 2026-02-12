"""
HTTP Proxy Support
Equivalent to Pi Mono's packages/ai/src/utils/http-proxy.ts

HTTP proxy configuration for API requests with comprehensive support for:
- HTTP/HTTPS/SOCKS5 proxies
- Proxy authentication
- Connection pooling
- Environment variable configuration
"""
import asyncio
import base64
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import urlparse


class ProxyProtocol(Enum):
    """Proxy protocol types"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyAuth:
    """Proxy authentication credentials"""
    username: str
    password: str

    def to_header(self) -> str:
        """Generate Proxy-Authorization header value"""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def to_url_encoded(self) -> str:
        """Generate URL-encoded auth string"""
        return f"{self.username}:{self.password}"


@dataclass
class ProxyConfig:
    """
    HTTP Proxy configuration

    Supports HTTP, HTTPS, and SOCKS5 proxies with authentication.
    Can be loaded from environment variables or manually configured.
    """
    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    auth: Optional[ProxyAuth] = None

    # Connection pool settings
    pool_connections: int = 10
    pool_maxsize: int = 10
    connect_timeout: float = 30.0
    read_timeout: float = 60.0

    # Additional settings
    no_proxy_hosts: list = field(default_factory=list)
    trust_env: bool = True

    @property
    def url(self) -> str:
        """Get full proxy URL"""
        if self.auth:
            auth_str = f"{self.auth.username}:{self.auth.password}@"
        else:
            auth_str = ""

        protocol = "socks5" if self.protocol == ProxyProtocol.SOCKS5 else "http"
        return f"{protocol}://{auth_str}{self.host}:{self.port}"

    @property
    def url_without_auth(self) -> str:
        """Get proxy URL without credentials (for logging)"""
        protocol = "socks5" if self.protocol == ProxyProtocol.SOCKS5 else "http"
        return f"{protocol}://{self.host}:{self.port}"

    def should_use_proxy(self, target_url: str) -> bool:
        """
        Check if proxy should be used for a given URL

        Args:
            target_url: The URL to check

        Returns:
            True if proxy should be used, False otherwise
        """
        if not self.host:
            return False

        # Parse target URL
        parsed = urlparse(target_url)
        hostname = parsed.hostname or ""

        # Check no_proxy list
        for no_proxy_host in self.no_proxy_hosts:
            no_proxy_host = no_proxy_host.strip().lower()
            if hostname.lower() == no_proxy_host or hostname.lower().endswith(f".{no_proxy_host}"):
                return False

        return True

    def get_auth_header(self) -> Optional[Dict[str, str]]:
        """Get proxy authentication header if configured"""
        if self.auth:
            return {"Proxy-Authorization": self.auth.to_header()}
        return None

    def to_aiohttp_connector_kwargs(self) -> Dict[str, Any]:
        """
        Get connector kwargs for aiohttp

        Returns:
            Dictionary of kwargs for aiohttp.TCPConnector
        """
        return {
            "limit": self.pool_maxsize,
            "limit_per_host": self.pool_connections,
        }

    @classmethod
    def from_url(cls, proxy_url: str, **kwargs) -> "ProxyConfig":
        """
        Create ProxyConfig from a URL string

        Args:
            proxy_url: Proxy URL (e.g., "http://user:pass@host:port")
            **kwargs: Additional configuration options

        Returns:
            ProxyConfig instance
        """
        parsed = urlparse(proxy_url)

        # Determine protocol
        if parsed.scheme == "socks5" or parsed.scheme == "socks5h":
            protocol = ProxyProtocol.SOCKS5
        elif parsed.scheme == "https":
            protocol = ProxyProtocol.HTTPS
        else:
            protocol = ProxyProtocol.HTTP

        # Extract auth
        auth = None
        if parsed.username and parsed.password:
            auth = ProxyAuth(
                username=parsed.username,
                password=parsed.password
            )

        return cls(
            host=parsed.hostname or "",
            port=parsed.port or (1080 if protocol == ProxyProtocol.SOCKS5 else 8080),
            protocol=protocol,
            auth=auth,
            **kwargs
        )


def load_proxy_from_env(
    http_proxy_env: str = "HTTP_PROXY",
    https_proxy_env: str = "HTTPS_PROXY",
    no_proxy_env: str = "NO_PROXY",
    **kwargs
) -> Optional[ProxyConfig]:
    """
    Load proxy configuration from environment variables

    Checks the following environment variables (case-insensitive):
    - HTTP_PROXY / http_proxy
    - HTTPS_PROXY / https_proxy
    - ALL_PROXY / all_proxy
    - NO_PROXY / no_proxy

    Args:
        http_proxy_env: Name of HTTP proxy env var
        https_proxy_env: Name of HTTPS proxy env var
        no_proxy_env: Name of no_proxy env var
        **kwargs: Additional ProxyConfig options

    Returns:
        ProxyConfig if proxy is configured, None otherwise
    """
    # Get proxy URL (prefer HTTPS, fallback to HTTP, then ALL_PROXY)
    proxy_url = (
        os.getenv(https_proxy_env) or os.getenv(https_proxy_env.lower()) or
        os.getenv(http_proxy_env) or os.getenv(http_proxy_env.lower()) or
        os.getenv("ALL_PROXY") or os.getenv("all_proxy")
    )

    if not proxy_url:
        return None

    # Get no_proxy hosts
    no_proxy = os.getenv(no_proxy_env) or os.getenv(no_proxy_env.lower()) or ""
    no_proxy_hosts = [h.strip() for h in no_proxy.split(",") if h.strip()]

    # Add common localhost patterns
    no_proxy_hosts.extend(["localhost", "127.0.0.1", "::1"])

    # Merge with provided kwargs
    if "no_proxy_hosts" in kwargs:
        kwargs["no_proxy_hosts"].extend(no_proxy_hosts)
    else:
        kwargs["no_proxy_hosts"] = no_proxy_hosts

    try:
        return ProxyConfig.from_url(proxy_url, **kwargs)
    except Exception:
        return None


def get_proxy_config() -> Optional[ProxyConfig]:
    """
    Get proxy configuration from environment (convenience function)

    Returns:
        ProxyConfig if configured, None otherwise
    """
    return load_proxy_from_env()


async def create_proxy_session(
    proxy_config: Optional[ProxyConfig] = None,
    headers: Optional[Dict[str, str]] = None,
    trust_env: bool = True,
    **session_kwargs
):
    """
    Create an aiohttp ClientSession with proxy support

    This function creates a session configured for proxy use.
    For SOCKS5 proxies, requires aiohttp-socks package.

    Args:
        proxy_config: Proxy configuration (default: load from env)
        headers: Additional headers for the session
        trust_env: Whether to trust environment variables for proxy
        **session_kwargs: Additional aiohttp session kwargs

    Returns:
        Tuple of (aiohttp.ClientSession, proxy_url or None)

    Example:
        >>> session, proxy_url = await create_proxy_session()
        >>> async with session.get("https://api.example.com", proxy=proxy_url) as resp:
        ...     data = await resp.json()
    """
    try:
        import aiohttp
    except ImportError:
        raise ImportError("aiohttp package required. Install: pip install aiohttp")

    # Load proxy config from environment if not provided
    if proxy_config is None and trust_env:
        proxy_config = load_proxy_from_env()

    # Prepare headers
    session_headers = headers or {}

    # Prepare connector kwargs
    connector_kwargs = {}
    proxy_url = None

    if proxy_config:
        # Check if SOCKS5 proxy
        if proxy_config.protocol == ProxyProtocol.SOCKS5:
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy_config.url)
                connector_kwargs["connector"] = connector
                # No separate proxy URL needed for SOCKS5 connector
                proxy_url = None
            except ImportError:
                raise ImportError(
                    "aiohttp-socks package required for SOCKS5 proxy. "
                    "Install: pip install aiohttp-socks"
                )
        else:
            # HTTP/HTTPS proxy
            proxy_url = proxy_config.url
            connector_kwargs.update(proxy_config.to_aiohttp_connector_kwargs())

            # Add proxy auth header if needed
            auth_header = proxy_config.get_auth_header()
            if auth_header:
                session_headers.update(auth_header)

    # Set default timeout
    if "timeout" not in session_kwargs:
        timeout = proxy_config.connect_timeout if proxy_config else 30.0
        session_kwargs["timeout"] = aiohttp.ClientTimeout(total=timeout)

    # Create connector
    if "connector" not in connector_kwargs:
        connector_kwargs["connector"] = aiohttp.TCPConnector(
            limit=connector_kwargs.get("limit", 10),
            limit_per_host=connector_kwargs.get("limit_per_host", 10),
        )

    # Create session
    session = aiohttp.ClientSession(
        headers=session_headers,
        **connector_kwargs,
        **session_kwargs
    )

    return session, proxy_url


class ProxySessionManager:
    """
    Manages proxy-enabled HTTP sessions

    Provides a centralized way to manage sessions with proxy support,
    including connection pooling and automatic cleanup.
    """

    def __init__(
        self,
        proxy_config: Optional[ProxyConfig] = None,
        trust_env: bool = True
    ):
        """
        Initialize session manager

        Args:
            proxy_config: Proxy configuration
            trust_env: Whether to load proxy from environment
        """
        self._proxy_config = proxy_config
        self._trust_env = trust_env
        self._session = None
        self._proxy_url = None
        self._lock = asyncio.Lock()

    @property
    def proxy_config(self) -> Optional[ProxyConfig]:
        """Get current proxy configuration"""
        if self._proxy_config:
            return self._proxy_config
        if self._trust_env:
            return load_proxy_from_env()
        return None

    async def get_session(self):
        """
        Get or create the HTTP session

        Returns:
            aiohttp.ClientSession
        """
        async with self._lock:
            if self._session is None or self._session.closed:
                self._session, self._proxy_url = await create_proxy_session(
                    proxy_config=self._proxy_config,
                    trust_env=self._trust_env
                )
            return self._session

    async def get_proxy_url(self) -> Optional[str]:
        """
        Get proxy URL for requests

        Returns:
            Proxy URL or None
        """
        await self.get_session()  # Ensure session is created
        return self._proxy_url

    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ):
        """
        Make an HTTP request through the proxy

        Args:
            method: HTTP method
            url: Target URL
            **kwargs: Additional request kwargs

        Returns:
            aiohttp.ClientResponse
        """
        session = await self.get_session()
        proxy_url = await self.get_proxy_url()

        # Check if we should use proxy for this URL
        proxy_config = self.proxy_config
        if proxy_url and proxy_config:
            if not proxy_config.should_use_proxy(url):
                proxy_url = None

        return await session.request(method, url, proxy=proxy_url, **kwargs)

    async def get(self, url: str, **kwargs):
        """Make GET request"""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs):
        """Make POST request"""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs):
        """Make PUT request"""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs):
        """Make DELETE request"""
        return await self.request("DELETE", url, **kwargs)

    async def close(self):
        """Close the session"""
        async with self._lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
                self._proxy_url = None

    async def __aenter__(self):
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Legacy compatibility functions
def get_proxy_headers(proxy_config: Optional[ProxyConfig] = None) -> dict:
    """
    Get headers for proxy authentication (legacy compatibility)

    Args:
        proxy_config: Proxy configuration

    Returns:
        Headers dict with proxy auth if needed
    """
    if proxy_config is None:
        proxy_config = load_proxy_from_env()

    if proxy_config and proxy_config.auth:
        return proxy_config.get_auth_header() or {}

    return {}


def apply_proxy_to_session(session, proxy_config: Optional[ProxyConfig] = None):
    """
    Apply proxy configuration to aiohttp session (documentation only)

    Note: aiohttp uses proxy parameter per request, not per session.
    Use create_proxy_session() or ProxySessionManager instead.

    Args:
        session: aiohttp ClientSession
        proxy_config: Proxy configuration
    """
    pass


__all__ = [
    # Classes
    "ProxyProtocol",
    "ProxyAuth",
    "ProxyConfig",
    "ProxySessionManager",
    # Functions
    "load_proxy_from_env",
    "get_proxy_config",
    "create_proxy_session",
    "get_proxy_headers",
    "apply_proxy_to_session",
]
