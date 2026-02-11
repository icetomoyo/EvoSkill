"""
Event Bus
等效于 Pi-Mono 的 packages/coding-agent/src/core/event-bus.ts

事件总线实现，用于组件间通信。
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Event:
    """事件"""
    type: str
    data: Any
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


# 事件处理器类型
EventHandler = Callable[[Event], Any]
AsyncEventHandler = Callable[[Event], Awaitable[Any]]


class EventBus:
    """
    事件总线
    
    用于组件间的解耦通信。
    
    Example:
        >>> bus = EventBus()
        >>> bus.on("message", lambda e: print(e.data))
        >>> bus.emit(Event("message", "Hello!"))
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._async_handlers: Dict[str, List[AsyncEventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 1000
        self._enabled = True
    
    def on(self, event_type: str, handler: EventHandler) -> Callable:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        
        Returns:
            取消订阅函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        
        # Return unsubscribe function
        def unsubscribe():
            self.off(event_type, handler)
        
        return unsubscribe
    
    def on_async(self, event_type: str, handler: AsyncEventHandler) -> Callable:
        """
        订阅异步事件
        
        Args:
            event_type: 事件类型
            handler: 异步处理函数
        
        Returns:
            取消订阅函数
        """
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        
        self._async_handlers[event_type].append(handler)
        
        def unsubscribe():
            if event_type in self._async_handlers:
                if handler in self._async_handlers[event_type]:
                    self._async_handlers[event_type].remove(handler)
        
        return unsubscribe
    
    def once(self, event_type: str, handler: EventHandler) -> None:
        """
        一次性订阅
        
        处理一次后自动取消订阅。
        """
        def wrapper(event: Event):
            self.off(event_type, wrapper)
            return handler(event)
        
        self.on(event_type, wrapper)
    
    def off(self, event_type: str, handler: Optional[EventHandler] = None) -> None:
        """
        取消订阅
        
        Args:
            event_type: 事件类型
            handler: 处理函数，如果为None则移除该类型所有处理器
        """
        if handler is None:
            self._handlers.pop(event_type, None)
            self._async_handlers.pop(event_type, None)
        else:
            if event_type in self._handlers:
                if handler in self._handlers[event_type]:
                    self._handlers[event_type].remove(handler)
    
    def emit(self, event: Event) -> None:
        """
        发布事件
        
        Args:
            event: 事件对象
        """
        if not self._enabled:
            return
        
        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # Call sync handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Log error but don't break other handlers
                print(f"Event handler error: {e}")
        
        # Schedule async handlers
        async_handlers = self._async_handlers.get(event.type, [])
        if async_handlers:
            asyncio.create_task(self._run_async_handlers(event, async_handlers))
    
    async def _run_async_handlers(
        self,
        event: Event,
        handlers: List[AsyncEventHandler],
    ) -> None:
        """运行异步处理器"""
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Async event handler error: {e}")
    
    def emit_simple(self, event_type: str, data: Any, source: Optional[str] = None) -> None:
        """
        简单发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件源
        """
        self.emit(Event(type=event_type, data=data, source=source))
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 按类型筛选
            limit: 最大数量
        
        Returns:
            事件列表
        """
        events = self._history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        return events[-limit:]
    
    def clear_history(self) -> None:
        """清除历史"""
        self._history.clear()
    
    def enable(self) -> None:
        """启用事件总线"""
        self._enabled = True
    
    def disable(self) -> None:
        """禁用事件总线"""
        self._enabled = False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_handlers": sum(len(h) for h in self._handlers.values()),
            "total_async_handlers": sum(len(h) for h in self._async_handlers.values()),
            "event_types": list(set(self._handlers.keys()) | set(self._async_handlers.keys())),
            "history_size": len(self._history),
            "enabled": self._enabled,
        }


class EventLogger:
    """
    事件日志器
    
    记录和监听事件。
    """
    
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.logged_events: List[Event] = []
        self._unsubscribe = None
    
    def start_logging(self, event_types: Optional[List[str]] = None) -> None:
        """开始记录事件"""
        def handler(event: Event):
            if event_types is None or event.type in event_types:
                self.logged_events.append(event)
        
        self._unsubscribe = self.bus.on("*", handler)
    
    def stop_logging(self) -> None:
        """停止记录"""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
    
    def get_logs(self, event_type: Optional[str] = None) -> List[Event]:
        """获取日志"""
        if event_type:
            return [e for e in self.logged_events if e.type == event_type]
        return self.logged_events.copy()
    
    def clear(self) -> None:
        """清除日志"""
        self.logged_events.clear()


# Global event bus instance
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


# Common event types
class EventTypes:
    """常用事件类型"""
    MESSAGE_RECEIVED = "message:received"
    MESSAGE_SENT = "message:sent"
    TOOL_CALLED = "tool:called"
    TOOL_COMPLETED = "tool:completed"
    SESSION_STARTED = "session:started"
    SESSION_ENDED = "session:ended"
    ERROR_OCCURRED = "error:occurred"
    CONFIG_CHANGED = "config:changed"
    MODEL_CHANGED = "model:changed"


__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "AsyncEventHandler",
    "EventLogger",
    "get_event_bus",
    "EventTypes",
]
