"""
HTTP Stream Proxy
Equivalent to Pi Mono's packages/ai/src/agent-proxy.ts

Proxies HTTP streams for agent communication.
This is an HTTP stream proxy, NOT multi-agent coordination.
"""
import asyncio
from typing import Optional, Dict, Any, AsyncIterator, Callable
from dataclasses import dataclass

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class ProxyOptions:
    """Proxy options"""
    target_url: str
    headers: Optional[Dict[str, str]] = None
    timeout: int = 60
    buffer_size: int = 8192


class HTTPStreamProxy:
    """
    HTTP Stream Proxy for agent communication.
    
    Proxies HTTP streams between client and target server,
    useful for adding authentication, logging, or modifying
    requests/responses.
    
    This is NOT multi-agent coordination - it's an HTTP proxy.
    
    Example:
        >>> proxy = HTTPStreamProxy()
        >>> async for chunk in proxy.stream("https://api.example.com"):
        ...     print(chunk)
    """
    
    def __init__(self, base_headers: Optional[Dict[str, str]] = None):
        """
        Initialize proxy.
        
        Args:
            base_headers: Headers to add to all requests
        """
        self.base_headers = base_headers or {}
    
    async def stream(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        timeout: int = 60,
        on_chunk: Optional[Callable[[bytes], None]] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream data through proxy.
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Additional headers
            data: Request body
            timeout: Request timeout
            on_chunk: Callback for each chunk
            
        Yields:
            Response chunks
        """
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp is required for HTTPStreamProxy. Install with: pip install aiohttp")
        
        # Merge headers
        request_headers = {**self.base_headers}
        if headers:
            request_headers.update(headers)
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.content.iter_chunked(8192):
                    if on_chunk:
                        on_chunk(chunk)
                    yield chunk
    
    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        timeout: int = 60
    ) -> bytes:
        """
        Make a non-streaming request through proxy.
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Additional headers
            data: Request body
            timeout: Request timeout
            
        Returns:
            Response body
        """
        chunks = []
        async for chunk in self.stream(url, method, headers, data, timeout):
            chunks.append(chunk)
        return b"".join(chunks)
    
    def with_auth(self, token: str, scheme: str = "Bearer") -> "HTTPStreamProxy":
        """
        Create proxy with authentication.
        
        Args:
            token: Auth token
            scheme: Auth scheme (Bearer, Basic, etc.)
            
        Returns:
            New proxy with auth header
        """
        return HTTPStreamProxy(
            base_headers={
                **self.base_headers,
                "Authorization": f"{scheme} {token}"
            }
        )


__all__ = [
    "HTTPStreamProxy",
    "ProxyOptions",
]
