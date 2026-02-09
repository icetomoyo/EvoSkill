"""
Event System

Event-driven architecture for agent lifecycle.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class EventType(Enum):
    """Agent event types"""
    # Lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    
    # Messages
    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_END = "message_end"
    
    # Tools
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    
    # LLM
    LLM_START = "llm_start"
    LLM_DELTA = "llm_delta"
    LLM_END = "llm_end"
    LLM_ERROR = "llm_error"
    
    # Compaction
    COMPACTION_START = "compaction_start"
    COMPACTION_END = "compaction_end"
    
    # Errors
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class Event:
    """Agent event"""
    type: EventType
    data: Any = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        data: Any = None,
        source: Optional[str] = None
    ) -> "Event":
        return cls(type=event_type, data=data, source=source)


class EventBus:
    """
    Event bus for agent communication
    
    Supports:
    - Subscribe to events
    - Emit events
    - One-time listeners
    """
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._once_handlers: Dict[EventType, List[Callable]] = {}
    
    def on(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Subscribe to event
        
        Args:
            event_type: Event type to listen for
            handler: Callback function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def once(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Subscribe to event once
        
        Args:
            event_type: Event type to listen for
            handler: Callback function (called once)
        """
        if event_type not in self._once_handlers:
            self._once_handlers[event_type] = []
        self._once_handlers[event_type].append(handler)
    
    def off(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Unsubscribe from event
        
        Args:
            event_type: Event type
            handler: Handler to remove
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
    
    def emit(self, event: Event) -> None:
        """
        Emit event to all subscribers
        
        Args:
            event: Event to emit
        """
        # Regular handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Don't let handler errors break event chain
                print(f"Event handler error: {e}")
        
        # One-time handlers
        once_handlers = self._once_handlers.get(event.type, [])
        for handler in once_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")
        
        # Clear one-time handlers
        if once_handlers:
            self._once_handlers[event.type] = []
    
    def emit_new(
        self,
        event_type: EventType,
        data: Any = None,
        source: Optional[str] = None
    ) -> None:
        """Create and emit event"""
        self.emit(Event.create(event_type, data, source))
    
    def clear(self) -> None:
        """Clear all handlers"""
        self._handlers.clear()
        self._once_handlers.clear()
