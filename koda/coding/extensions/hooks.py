"""
Hook System
Hook points for extensions.
"""
from enum import Enum
from typing import Callable, List, Any


class HookPoint(Enum):
    """Available hook points"""
    MESSAGE_RECEIVE = "message_receive"
    RESPONSE_SEND = "response_send"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class HookManager:
    """Manages hooks"""
    
    _hooks: dict = {}
    
    @classmethod
    def register(cls, point: str, callback: Callable):
        """Register a hook"""
        if point not in cls._hooks:
            cls._hooks[point] = []
        cls._hooks[point].append(callback)
    
    @classmethod
    def unregister(cls, point: str, callback: Callable):
        """Unregister a hook"""
        if point in cls._hooks and callback in cls._hooks[point]:
            cls._hooks[point].remove(callback)
    
    @classmethod
    def execute(cls, point: str, data: Any) -> Any:
        """
        Execute all hooks for a point.
        
        Each hook can modify the data and pass it to the next.
        """
        if point not in cls._hooks:
            return data
        
        result = data
        for callback in cls._hooks[point]:
            try:
                result = callback(result)
            except Exception as e:
                print(f"Hook error at {point}: {e}")
        
        return result
    
    @classmethod
    def clear(cls):
        """Clear all hooks"""
        cls._hooks.clear()


# Convenience functions
def on_message_receive(callback: Callable[[str], str]):
    """Decorator for message receive hook"""
    HookManager.register(HookPoint.MESSAGE_RECEIVE.value, callback)
    return callback


def on_response_send(callback: Callable[[str], str]):
    """Decorator for response send hook"""
    HookManager.register(HookPoint.RESPONSE_SEND.value, callback)
    return callback


def on_tool_call(callback: Callable[[Any], Any]):
    """Decorator for tool call hook"""
    HookManager.register(HookPoint.TOOL_CALL.value, callback)
    return callback
