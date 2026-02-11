"""
HTTP Proxy Support
Equivalent to Pi Mono's packages/ai/src/utils/http-proxy.ts

HTTP proxy configuration for API requests.
"""
import os
from typing import Optional
from urllib.parse import urlparse


class ProxyConfig:
    """HTTP Proxy configuration"""
    
    def __init__(
        self,
        http_proxy: Optional[str] = None,
        https_proxy: Optional[str] = None,
        no_proxy: Optional[str] = None,
    ):
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.no_proxy = no_proxy
    
    @classmethod
    def from_env(cls) -> "ProxyConfig":
        """Create proxy config from environment variables"""
        return cls(
            http_proxy=os.getenv("HTTP_PROXY") or os.getenv("http_proxy"),
            https_proxy=os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
            no_proxy=os.getenv("NO_PROXY") or os.getenv("no_proxy"),
        )
    
    def should_use_proxy(self, url: str) -> bool:
        """Check if proxy should be used for URL"""
        if not self.no_proxy:
            return True
        
        # Parse URL
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        
        # Check no_proxy list
        no_proxy_hosts = [h.strip().lower() for h in self.no_proxy.split(",")]
        for host in no_proxy_hosts:
            if hostname.endswith(host):
                return False
        
        return True
    
    def get_proxy_url(self, url: str) -> Optional[str]:
        """Get proxy URL for given target URL"""
        if not self.should_use_proxy(url):
            return None
        
        parsed = urlparse(url)
        if parsed.scheme == "https":
            return self.https_proxy or self.http_proxy
        return self.http_proxy
    
    def to_aiohttp(self) -> Optional[str]:
        """Get proxy URL for aiohttp"""
        return self.https_proxy or self.http_proxy


def get_proxy_config() -> ProxyConfig:
    """Get proxy configuration from environment"""
    return ProxyConfig.from_env()


def apply_proxy_to_session(session, proxy_config: Optional[ProxyConfig] = None):
    """
    Apply proxy configuration to aiohttp session.
    
    Args:
        session: aiohttp ClientSession
        proxy_config: Proxy configuration (default: from env)
    """
    # Note: aiohttp uses proxy parameter per request, not per session
    # This function is for documentation purposes
    pass


def get_proxy_headers(proxy_config: Optional[ProxyConfig] = None) -> dict:
    """
    Get headers for proxy authentication.
    
    Args:
        proxy_config: Proxy configuration
        
    Returns:
        Headers dict with proxy auth if needed
    """
    if proxy_config is None:
        proxy_config = get_proxy_config()
    
    headers = {}
    
    # Parse proxy URL for auth info
    proxy_url = proxy_config.https_proxy or proxy_config.http_proxy
    if proxy_url:
        parsed = urlparse(proxy_url)
        if parsed.username and parsed.password:
            import base64
            auth = base64.b64encode(
                f"{parsed.username}:{parsed.password}".encode()
            ).decode()
            headers["Proxy-Authorization"] = f"Basic {auth}"
    
    return headers
