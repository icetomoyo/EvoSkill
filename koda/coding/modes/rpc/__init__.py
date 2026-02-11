"""
RPC Mode
Equivalent to Pi Mono's packages/coding-agent/src/modes/rpc/

Remote Procedure Call mode for programmatic access.
"""
from .server import RPCServer, RPCRequest, RPCResponse
from .client import RPCClient, RPCClientConfig, RPCError
from .handlers import RPCHandlers

__all__ = [
    "RPCServer",
    "RPCRequest",
    "RPCResponse",
    "RPCClient",
    "RPCClientConfig",
    "RPCError",
    "RPCHandlers",
]
