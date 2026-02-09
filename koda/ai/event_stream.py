"""
Koda AI Event Stream - 流式事件处理
等效于 Pi Mono 的 packages/ai/src/stream.ts + event-stream.ts
"""
import asyncio
from typing import AsyncIterator, Callable, List, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

from koda.ai.types import AssistantMessage, AssistantMessageEvent, StopReason, ToolCall


class EventType(Enum):
    """事件类型"""
    START = "start"
    TEXT_START = "text_start"
    TEXT_DELTA = "text_delta"
    TEXT_END = "text_end"
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_END = "thinking_end"
    TOOLCALL_START = "toolcall_start"
    TOOLCALL_DELTA = "toolcall_delta"
    TOOLCALL_END = "toolcall_end"
    DONE = "done"
    ERROR = "error"


class AssistantMessageEventStream:
    """
    助手消息事件流
    
    等效于 Pi Mono 的 AssistantMessageEventStream
    支持异步迭代和回调机制
    """
    
    def __init__(self):
        self._queue: asyncio.Queue[AssistantMessageEvent] = asyncio.Queue()
        self._closed: bool = False
        self._done: bool = False
        self._error: Optional[Exception] = None
        self._callbacks: List[Callable[[AssistantMessageEvent], None]] = []
        self._async_callbacks: List[Callable[[AssistantMessageEvent], Any]] = []
    
    def push(self, event: AssistantMessageEvent) -> None:
        """推送事件到流"""
        if self._closed:
            return
        
        self._queue.put_nowait(event)
        
        # 触发同步回调
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Event callback error: {e}")
        
        # 触发异步回调
        for callback in self._async_callbacks:
            asyncio.create_task(self._run_async_callback(callback, event))
    
    async def _run_async_callback(
        self,
        callback: Callable[[AssistantMessageEvent], Any],
        event: AssistantMessageEvent
    ) -> None:
        """运行异步回调"""
        try:
            await callback(event)
        except Exception as e:
            print(f"Async event callback error: {e}")
    
    def on_event(self, callback: Callable[[AssistantMessageEvent], None]) -> None:
        """注册同步事件回调"""
        self._callbacks.append(callback)
    
    def on_event_async(
        self,
        callback: Callable[[AssistantMessageEvent], Any]
    ) -> None:
        """注册异步事件回调"""
        self._async_callbacks.append(callback)
    
    def close(self) -> None:
        """关闭流"""
        self._closed = True
        self._done = True
    
    def set_error(self, error: Exception) -> None:
        """设置错误状态"""
        self._error = error
        self.push(AssistantMessageEvent(
            type=EventType.ERROR.value,
            error=error,
            reason=StopReason.ERROR
        ))
    
    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        """异步迭代器"""
        return self
    
    async def __anext__(self) -> AssistantMessageEvent:
        """获取下一个事件"""
        if self._done and self._queue.empty():
            raise StopAsyncIteration
        
        try:
            # 使用 timeout 以便检查 done 状态
            event = await asyncio.wait_for(
                self._queue.get(),
                timeout=0.1
            )
            
            # 检查是否是结束事件
            if event.type in (EventType.DONE.value, EventType.ERROR.value):
                self._done = True
            
            return event
        except asyncio.TimeoutError:
            if self._done:
                raise StopAsyncIteration
            # 继续等待
            return await self.__anext__()
    
    async def collect(self) -> AssistantMessage:
        """
        收集所有事件并返回完整消息
        
        用于非流式场景
        """
        message: Optional[AssistantMessage] = None
        current_text_index: Optional[int] = None
        current_thinking_index: Optional[int] = None
        current_tool_call_index: Optional[int] = None
        
        async for event in self:
            if event.type == EventType.START.value:
                message = event.partial
            elif event.type == EventType.TEXT_START.value:
                current_text_index = event.content_index
            elif event.type == EventType.TEXT_DELTA.value:
                if message and current_text_index is not None:
                    # 追加文本增量
                    if current_text_index < len(message.content):
                        content = message.content[current_text_index]
                        if content.type == "text":
                            content.text += event.delta or ""
            elif event.type == EventType.TEXT_END.value:
                current_text_index = None
            elif event.type == EventType.THINKING_START.value:
                current_thinking_index = event.content_index
            elif event.type == EventType.THINKING_DELTA.value:
                if message and current_thinking_index is not None:
                    if current_thinking_index < len(message.content):
                        content = message.content[current_thinking_index]
                        if content.type == "thinking":
                            content.thinking += event.delta or ""
            elif event.type == EventType.THINKING_END.value:
                current_thinking_index = None
            elif event.type == EventType.TOOLCALL_START.value:
                current_tool_call_index = event.content_index
            elif event.type == EventType.TOOLCALL_DELTA.value:
                # 工具调用增量通常是参数 JSON 片段
                pass
            elif event.type == EventType.TOOLCALL_END.value:
                if message and event.tool_call:
                    # 确保工具调用被正确添加到消息
                    if current_tool_call_index is not None:
                        if current_tool_call_index < len(message.content):
                            message.content[current_tool_call_index] = event.tool_call
                current_tool_call_index = None
            elif event.type == EventType.DONE.value:
                if message and event.partial:
                    # 更新最终状态
                    message.usage = event.partial.usage
                    message.stop_reason = event.reason or StopReason.STOP
                break
            elif event.type == EventType.ERROR.value:
                if message:
                    message.stop_reason = StopReason.ERROR
                    message.error_message = str(event.error)
                break
        
        return message or AssistantMessage()


class StreamBuffer:
    """
    流缓冲区
    
    用于处理 Provider 的 SSE (Server-Sent Events) 流
    """
    
    def __init__(self):
        self._buffer: str = ""
        self._lines: List[str] = []
    
    def append(self, data: str) -> List[str]:
        """追加数据并返回完整行"""
        self._buffer += data
        
        # 分割成行
        lines = self._buffer.split("\n")
        
        # 保留最后一个不完整的行在缓冲区
        self._buffer = lines[-1]
        complete_lines = lines[:-1]
        
        self._lines.extend(complete_lines)
        return complete_lines
    
    def flush(self) -> str:
        """刷新剩余缓冲区"""
        remaining = self._buffer
        self._buffer = ""
        return remaining


def create_event_stream() -> AssistantMessageEventStream:
    """创建新的事件流"""
    return AssistantMessageEventStream()


async def stream_to_string(stream: AssistantMessageEventStream) -> str:
    """将事件流转换为字符串（提取所有文本内容）"""
    parts: List[str] = []
    
    async for event in stream:
        if event.type == EventType.TEXT_DELTA.value:
            parts.append(event.delta or "")
        elif event.type == EventType.DONE.value:
            break
        elif event.type == EventType.ERROR.value:
            raise event.error or Exception("Stream error")
    
    return "".join(parts)


async def stream_to_messages(
    stream: AssistantMessageEventStream
) -> List[AssistantMessage]:
    """将事件流转换为消息列表"""
    messages: List[AssistantMessage] = []
    
    async for event in stream:
        if event.type == EventType.DONE.value and event.partial:
            messages.append(event.partial)
        elif event.type == EventType.ERROR.value:
            raise event.error or Exception("Stream error")
    
    return messages
