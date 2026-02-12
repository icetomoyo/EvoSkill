"""
Async Sleep Utilities - 异步睡眠工具

提供可中断的异步睡眠功能。
"""
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Awaitable, Union
from enum import Enum
import time


class SleepState(Enum):
    """睡眠状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


@dataclass
class SleepResult:
    """睡眠结果"""
    state: SleepState
    elapsed: float  # 实际经过的时间（秒）
    remaining: float  # 剩余时间（秒）
    reason: Optional[str] = None


class SleepHandle:
    """
    可中断的睡眠句柄

    支持取消、中断和查询状态。

    Example:
        >>> handle = await async_sleep(10)
        >>> # 在其他地方
        >>> handle.cancel()
        >>> result = await handle.wait()
        >>> print(f"Sleep was {result.state.value}")
    """

    def __init__(self, duration: float):
        """
        初始化睡眠句柄

        Args:
            duration: 睡眠时长（秒）
        """
        self._duration = duration
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._state = SleepState.PENDING
        self._cancel_event = asyncio.Event()
        self._interrupt_event = asyncio.Event()
        self._completion_event = asyncio.Event()
        self._reason: Optional[str] = None
        self._on_cancel: Optional[Callable[[], Any]] = None
        self._on_interrupt: Optional[Callable[[str], Any]] = None
        self._on_complete: Optional[Callable[[], Any]] = None

    @property
    def duration(self) -> float:
        """计划睡眠时长"""
        return self._duration

    @property
    def state(self) -> SleepState:
        """当前状态"""
        return self._state

    @property
    def elapsed(self) -> float:
        """已经过的时间"""
        if self._start_time is None:
            return 0.0
        if self._end_time is not None:
            return self._end_time - self._start_time
        return time.monotonic() - self._start_time

    @property
    def remaining(self) -> float:
        """剩余时间"""
        return max(0.0, self._duration - self.elapsed)

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self._state == SleepState.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self._state == SleepState.CANCELLED

    @property
    def is_interrupted(self) -> bool:
        """是否被中断"""
        return self._state == SleepState.INTERRUPTED

    def cancel(self, reason: Optional[str] = None) -> bool:
        """
        取消睡眠

        Args:
            reason: 取消原因

        Returns:
            True 如果取消成功
        """
        if self._state not in (SleepState.PENDING, SleepState.RUNNING):
            return False

        self._state = SleepState.CANCELLED
        self._reason = reason
        self._cancel_event.set()

        if self._on_cancel:
            try:
                self._on_cancel()
            except Exception:
                pass

        return True

    def interrupt(self, reason: str = "") -> bool:
        """
        中断睡眠

        与取消不同，中断通常表示有外部事件需要处理。

        Args:
            reason: 中断原因

        Returns:
            True 如果中断成功
        """
        if self._state not in (SleepState.PENDING, SleepState.RUNNING):
            return False

        self._state = SleepState.INTERRUPTED
        self._reason = reason
        self._interrupt_event.set()

        if self._on_interrupt:
            try:
                self._on_interrupt(reason)
            except Exception:
                pass

        return True

    def on_cancel(self, callback: Callable[[], Any]) -> "SleepHandle":
        """
        设置取消回调

        Args:
            callback: 回调函数

        Returns:
            self 以便链式调用
        """
        self._on_cancel = callback
        return self

    def on_interrupt(self, callback: Callable[[str], Any]) -> "SleepHandle":
        """
        设置中断回调

        Args:
            callback: 回调函数，接收中断原因

        Returns:
            self 以便链式调用
        """
        self._on_interrupt = callback
        return self

    def on_complete(self, callback: Callable[[], Any]) -> "SleepHandle":
        """
        设置完成回调

        Args:
            callback: 回调函数

        Returns:
            self 以便链式调用
        """
        self._on_complete = callback
        return self

    async def wait(self) -> SleepResult:
        """
        等待睡眠完成

        Returns:
            SleepResult 对象
        """
        self._start_time = time.monotonic()
        self._state = SleepState.RUNNING

        try:
            # 创建睡眠任务
            sleep_task = asyncio.create_task(asyncio.sleep(self._duration))
            cancel_task = asyncio.create_task(self._cancel_event.wait())
            interrupt_task = asyncio.create_task(self._interrupt_event.wait())

            # 等待任一事件
            done, pending = await asyncio.wait(
                [sleep_task, cancel_task, interrupt_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 取消未完成的任务
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 记录结束时间
            self._end_time = time.monotonic()

            # 处理结果
            if self._state == SleepState.CANCELLED:
                pass  # 状态已在 cancel() 中设置
            elif self._state == SleepState.INTERRUPTED:
                pass  # 状态已在 interrupt() 中设置
            else:
                self._state = SleepState.COMPLETED
                if self._on_complete:
                    try:
                        self._on_complete()
                    except Exception:
                        pass

            return SleepResult(
                state=self._state,
                elapsed=self.elapsed,
                remaining=self.remaining,
                reason=self._reason
            )

        except asyncio.CancelledError:
            self._end_time = time.monotonic()
            self._state = SleepState.CANCELLED

            return SleepResult(
                state=self._state,
                elapsed=self.elapsed,
                remaining=self.remaining,
                reason="Task cancelled"
            )


async def async_sleep(
    duration: float,
    *,
    on_cancel: Optional[Callable[[], Any]] = None,
    on_interrupt: Optional[Callable[[str], Any]] = None,
    on_complete: Optional[Callable[[], Any]] = None
) -> SleepHandle:
    """
    创建可中断的异步睡眠

    Args:
        duration: 睡眠时长（秒）
        on_cancel: 取消回调
        on_interrupt: 中断回调
        on_complete: 完成回调

    Returns:
        SleepHandle 句柄

    Example:
        >>> handle = await async_sleep(10)
        >>> # 在其他协程中
        >>> handle.cancel()
        >>> # 等待结果
        >>> result = await handle.wait()
    """
    handle = SleepHandle(duration)

    if on_cancel:
        handle.on_cancel(on_cancel)
    if on_interrupt:
        handle.on_interrupt(on_interrupt)
    if on_complete:
        handle.on_complete(on_complete)

    return handle


async def sleep_with_timeout(
    duration: float,
    timeout: float,
    on_timeout: Optional[Callable[[], Awaitable[Any]]] = None
) -> SleepResult:
    """
    带超时的睡眠

    如果睡眠时间超过指定的超时时间，则提前结束。

    Args:
        duration: 睡眠时长（秒）
        timeout: 超时时间（秒）
        on_timeout: 超时回调（异步函数）

    Returns:
        SleepResult 对象
    """
    actual_duration = min(duration, timeout)
    handle = await async_sleep(actual_duration)
    result = await handle.wait()

    if duration > timeout and on_timeout:
        try:
            await on_timeout()
        except Exception:
            pass

    return result


class SleepManager:
    """
    睡眠管理器

    管理多个睡眠句柄，支持批量操作。

    Example:
        >>> manager = SleepManager()
        >>> handle1 = await manager.sleep(10, name="task1")
        >>> handle2 = await manager.sleep(20, name="task2")
        >>> manager.cancel_all()
    """

    def __init__(self):
        """初始化管理器"""
        self._handles: dict = {}
        self._counter = 0

    @property
    def active_count(self) -> int:
        """活跃睡眠数量"""
        return sum(
            1 for h in self._handles.values()
            if h.state in (SleepState.PENDING, SleepState.RUNNING)
        )

    def get_handle(self, name: str) -> Optional[SleepHandle]:
        """
        获取指定名称的句柄

        Args:
            name: 句柄名称

        Returns:
            SleepHandle 或 None
        """
        return self._handles.get(name)

    async def sleep(
        self,
        duration: float,
        name: Optional[str] = None
    ) -> SleepHandle:
        """
        创建并注册睡眠

        Args:
            duration: 睡眠时长（秒）
            name: 句柄名称（可选）

        Returns:
            SleepHandle 句柄
        """
        handle = await async_sleep(duration)

        if name is None:
            self._counter += 1
            name = f"sleep_{self._counter}"

        self._handles[name] = handle
        return handle

    def cancel(self, name: str, reason: Optional[str] = None) -> bool:
        """
        取消指定睡眠

        Args:
            name: 句柄名称
            reason: 取消原因

        Returns:
            True 如果取消成功
        """
        handle = self._handles.get(name)
        if handle:
            return handle.cancel(reason)
        return False

    def interrupt(self, name: str, reason: str = "") -> bool:
        """
        中断指定睡眠

        Args:
            name: 句柄名称
            reason: 中断原因

        Returns:
            True 如果中断成功
        """
        handle = self._handles.get(name)
        if handle:
            return handle.interrupt(reason)
        return False

    def cancel_all(self, reason: Optional[str] = None) -> int:
        """
        取消所有活跃睡眠

        Args:
            reason: 取消原因

        Returns:
            取消的数量
        """
        count = 0
        for handle in self._handles.values():
            if handle.state in (SleepState.PENDING, SleepState.RUNNING):
                if handle.cancel(reason):
                    count += 1
        return count

    def cleanup(self) -> int:
        """
        清理已完成的睡眠

        Returns:
            清理的数量
        """
        to_remove = [
            name for name, handle in self._handles.items()
            if handle.state in (SleepState.COMPLETED, SleepState.CANCELLED, SleepState.INTERRUPTED)
        ]

        for name in to_remove:
            del self._handles[name]

        return len(to_remove)

    def get_all_states(self) -> dict:
        """
        获取所有睡眠状态

        Returns:
            {name: state} 字典
        """
        return {name: handle.state for name, handle in self._handles.items()}


async def periodic_sleep(
    interval: float,
    callback: Callable[[], Awaitable[Any]],
    max_count: Optional[int] = None,
    stop_condition: Optional[Callable[[], bool]] = None
) -> int:
    """
    周期性睡眠并执行回调

    Args:
        interval: 间隔时间（秒）
        callback: 回调函数（异步）
        max_count: 最大执行次数（None 表示无限）
        stop_condition: 停止条件函数

    Returns:
        执行次数
    """
    count = 0

    while True:
        # 检查停止条件
        if stop_condition and stop_condition():
            break

        if max_count is not None and count >= max_count:
            break

        # 执行回调
        try:
            await callback()
        except Exception:
            pass

        count += 1

        # 睡眠（最后一轮不睡）
        if max_count is None or count < max_count:
            if stop_condition and stop_condition():
                break

            handle = await async_sleep(interval)
            result = await handle.wait()

            # 如果被取消或中断，停止循环
            if result.state != SleepState.COMPLETED:
                break

    return count


__all__ = [
    "SleepState",
    "SleepResult",
    "SleepHandle",
    "async_sleep",
    "sleep_with_timeout",
    "SleepManager",
    "periodic_sleep",
]
