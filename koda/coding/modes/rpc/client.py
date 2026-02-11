"""
RPC Client
Equivalent to Pi Mono's packages/coding-agent/src/modes/rpc/client.ts

JSON-RPC client for connecting to agent server.
"""
import asyncio
import json
from typing import Any, Optional, Dict
from dataclasses import dataclass


@dataclass
class RPCClientConfig:
    """RPC client configuration"""
    host: str = "localhost"
    port: int = 8080
    timeout: float = 30.0


class RPCClient:
    """
    JSON-RPC client for agent server.
    
    Example:
        >>> client = RPCClient()
        >>> await client.connect()
        >>> result = await client.call("chat", {"message": "Hello"})
        >>> print(result)
    """
    
    def __init__(self, config: Optional[RPCClientConfig] = None):
        self.config = config or RPCClientConfig()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._request_id = 0
    
    async def connect(self):
        """Connect to RPC server"""
        self._reader, self._writer = await asyncio.open_connection(
            self.config.host,
            self.config.port
        )
        self._connected = True
    
    def disconnect(self):
        """Disconnect from server"""
        if self._writer:
            self._writer.close()
        self._connected = False
    
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        """
        Call RPC method.
        
        Args:
            method: Method name
            params: Method parameters
            timeout: Request timeout
            
        Returns:
            Method result
        """
        if not self._connected:
            await self.connect()
        
        self._request_id += 1
        request_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        request_str = json.dumps(request) + "\n"
        self._writer.write(request_str.encode('utf-8'))
        await self._writer.drain()
        
        # Read response with timeout
        to = timeout or self.config.timeout
        response_data = await asyncio.wait_for(
            self._reader.readline(),
            timeout=to
        )
        
        response = json.loads(response_data.decode('utf-8'))
        
        if "error" in response:
            raise RPCError(response["error"])
        
        return response.get("result")
    
    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None):
        """
        Send notification (no response expected).
        
        Args:
            method: Method name
            params: Method parameters
        """
        if not self._connected:
            await self.connect()
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        request_str = json.dumps(request) + "\n"
        self._writer.write(request_str.encode('utf-8'))
        await self._writer.drain()
    
    async def ping(self) -> bool:
        """Ping server to check connection"""
        try:
            result = await self.call("ping", timeout=5.0)
            return result == "pong"
        except Exception:
            return False


class RPCError(Exception):
    """RPC error"""
    def __init__(self, error: Dict[str, Any]):
        self.code = error.get("code", 0)
        self.message = error.get("message", "Unknown error")
        self.data = error.get("data")
        super().__init__(f"RPC Error {self.code}: {self.message}")


__all__ = ["RPCClient", "RPCClientConfig", "RPCError"]
