"""
事件发射器

实现异步事件订阅和发布机制
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from evoskill.core.types import Event, EventType


class EventEmitter:
    """
    事件发射器
    
    支持:
    1. 多订阅者
    2. 异步事件处理
    3. 事件过滤
    """
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable[[Event], Any]]] = {}
        self._global_handlers: List[Callable[[Event], Any]] = []
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def on(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """
        订阅特定类型的事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def on_any(self, handler: Callable[[Event], Any]) -> None:
        """
        订阅所有事件
        
        Args:
            handler: 处理函数
        """
        self._global_handlers.append(handler)
    
    def off(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """
        取消订阅
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
    
    def off_any(self, handler: Callable[[Event], Any]) -> None:
        """取消全局订阅"""
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)
    
    async def emit(self, event: Event) -> None:
        """
        发射事件
        
        Args:
            event: 事件对象
        """
        # 添加到队列
        await self._event_queue.put(event)
    
    async def emit_now(self, event: Event) -> None:
        """
        立即处理事件（同步方式）
        
        Args:
            event: 事件对象
        """
        await self._process_event(event)
    
    async def _process_event(self, event: Event) -> None:
        """
        处理单个事件
        
        Args:
            event: 事件对象
        """
        # 全局处理器
        for handler in self._global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                # 记录错误但不中断其他处理器
                print(f"Error in global handler: {e}")
        
        # 特定类型处理器
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    print(f"Error in handler for {event.type}: {e}")
    
    async def start(self) -> None:
        """启动事件处理循环"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._event_loop())
    
    async def stop(self) -> None:
        """停止事件处理循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _event_loop(self) -> None:
        """事件处理主循环"""
        while self._running:
            try:
                event = await self._event_queue.get()
                await self._process_event(event)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in event loop: {e}")
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class EventCollector:
    """
    事件收集器
    
    用于收集事件流，方便测试和调试
    """
    
    def __init__(self):
        self.events: List[Event] = []
    
    def __call__(self, event: Event) -> None:
        self.events.append(event)
    
    def get_events(self, event_type: Optional[EventType] = None) -> List[Event]:
        """
        获取收集的事件
        
        Args:
            event_type: 过滤特定类型
            
        Returns:
            事件列表
        """
        if event_type:
            return [e for e in self.events if e.type == event_type]
        return self.events
    
    def clear(self) -> None:
        """清空收集的事件"""
        self.events.clear()
