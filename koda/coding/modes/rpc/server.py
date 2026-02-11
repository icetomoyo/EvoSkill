"""
RPC Server
Equivalent to Pi Mono's packages/coding-agent/src/modes/rpc/server.ts

JSON-RPC server for remote agent access.
"""
import asyncio
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class RPCErrorCode(Enum):
    """JSON-RPC error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


@dataclass
class RPCRequest:
    """JSON-RPC request"""
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


@dataclass
class RPCResponse:
    """JSON-RPC response"""
    jsonrpc: str = "2.0"
    result: Any = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        response = {"jsonrpc": self.jsonrpc}
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
        if self.id is not None:
            response["id"] = self.id
        return response


class RPCServer:
    """
    JSON-RPC server for agent remote access.
    
    Provides programmatic access to agent functionality via JSON-RPC.
    
    Example:
        >>> server = RPCServer()
        >>> server.register_method("chat", handle_chat)
        >>> await server.start(host="localhost", port=8080)
    """
    
    def __init__(self):
        self._methods: Dict[str, Callable] = {}
        self._server: Optional[asyncio.Server] = None
        self._running = False
    
    def register_method(self, name: str, handler: Callable):
        """
        Register an RPC method.
        
        Args:
            name: Method name
            handler: Async function to handle calls
        """
        self._methods[name] = handler
    
    def unregister_method(self, name: str):
        """Unregister an RPC method"""
        if name in self._methods:
            del self._methods[name]
    
    async def start(self, host: str = "localhost", port: int = 8080):
        """
        Start RPC server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self._server = await asyncio.start_server(
            self._handle_client,
            host,
            port
        )
        self._running = True
        
        async with self._server:
            await self._server.serve_forever()
    
    def stop(self):
        """Stop the server"""
        self._running = False
        if self._server:
            self._server.close()
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection"""
        while self._running:
            try:
                # Read request
                data = await reader.readline()
                if not data:
                    break
                
                request_str = data.decode('utf-8').strip()
                response = await self._process_request(request_str)
                
                if response:
                    response_str = json.dumps(response.to_dict()) + "\n"
                    writer.write(response_str.encode('utf-8'))
                    await writer.drain()
                    
            except Exception as e:
                error_response = RPCResponse(
                    error={"code": RPCErrorCode.INTERNAL_ERROR.value, "message": str(e)}
                )
                writer.write(json.dumps(error_response.to_dict()).encode('utf-8'))
                await writer.drain()
        
        writer.close()
        await writer.wait_closed()
    
    async def _process_request(self, request_str: str) -> Optional[RPCResponse]:
        """
        Process JSON-RPC request.
        
        Args:
            request_str: Raw request string
            
        Returns:
            RPCResponse or None for notifications
        """
        # Parse request
        try:
            request_data = json.loads(request_str)
        except json.JSONDecodeError:
            return RPCResponse(
                error={"code": RPCErrorCode.PARSE_ERROR.value, "message": "Parse error"},
                id=None
            )
        
        # Validate request
        if not isinstance(request_data, dict):
            return RPCResponse(
                error={"code": RPCErrorCode.INVALID_REQUEST.value, "message": "Invalid Request"},
                id=None
            )
        
        jsonrpc = request_data.get("jsonrpc")
        method = request_data.get("method")
        request_id = request_data.get("id")
        params = request_data.get("params", {})
        
        if jsonrpc != "2.0" or not method:
            return RPCResponse(
                error={"code": RPCErrorCode.INVALID_REQUEST.value, "message": "Invalid Request"},
                id=request_id
            )
        
        # Find method
        handler = self._methods.get(method)
        if not handler:
            return RPCResponse(
                error={"code": RPCErrorCode.METHOD_NOT_FOUND.value, "message": f"Method not found: {method}"},
                id=request_id
            )
        
        # Execute method
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            
            # Don't respond to notifications (no id)
            if request_id is None:
                return None
            
            return RPCResponse(result=result, id=request_id)
            
        except TypeError as e:
            return RPCResponse(
                error={"code": RPCErrorCode.INVALID_PARAMS.value, "message": str(e)},
                id=request_id
            )
        except Exception as e:
            return RPCResponse(
                error={"code": RPCErrorCode.INTERNAL_ERROR.value, "message": str(e)},
                id=request_id
            )
    
    async def handle_http_request(self, body: str) -> str:
        """
        Handle HTTP POST request with JSON-RPC body.
        
        Args:
            body: Request body
            
        Returns:
            JSON response
        """
        response = await self._process_request(body)
        if response:
            return json.dumps(response.to_dict())
        return ""


__all__ = ["RPCServer", "RPCRequest", "RPCResponse", "RPCErrorCode"]
