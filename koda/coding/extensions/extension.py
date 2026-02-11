"""
Extension Base Class
Base class for Koda extensions.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ExtensionMetadata:
    """Extension metadata"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""


class ExtensionAPI:
    """API provided to extensions"""
    
    def __init__(self, registry):
        self._registry = registry
    
    def register_hook(self, point: str, callback):
        """Register a hook"""
        from .hooks import HookManager
        HookManager.register(point, callback)
    
    def log(self, message: str):
        """Log message"""
        print(f"[Extension] {message}")


class Extension(ABC):
    """
    Base class for Koda extensions.
    
    Extensions can hook into various points of the agent lifecycle
    and modify behavior.
    """
    
    def __init__(self):
        self.metadata = self.get_metadata()
        self._api: ExtensionAPI = None
    
    @abstractmethod
    def get_metadata(self) -> ExtensionMetadata:
        """Return extension metadata"""
        pass
    
    def activate(self, api: ExtensionAPI):
        """
        Called when extension is activated.
        
        Args:
            api: API for interacting with Koda
        """
        self._api = api
    
    def deactivate(self):
        """Called when extension is deactivated"""
        pass
    
    def on_message_receive(self, message: str) -> str:
        """
        Hook: Called when user message is received.
        Can modify the message.
        """
        return message
    
    def on_response_send(self, response: str) -> str:
        """
        Hook: Called before response is sent.
        Can modify the response.
        """
        return response
    
    def on_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook: Called before tool execution.
        Can modify tool arguments.
        """
        return args
    
    def on_tool_result(self, tool_name: str, result: Any) -> Any:
        """
        Hook: Called after tool execution.
        Can modify tool result.
        """
        return result
