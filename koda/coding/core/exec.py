"""
Tool Execution Framework - Unified tool execution interface

Provides a unified interface for executing tools with:
- Timeout handling
- Error recovery and retry logic
- Result formatting
- Parallel execution support
- Execution logging

Equivalent to Pi Mono's tool execution infrastructure.
"""
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional, TypeVar, Union, Awaitable
)
from datetime import datetime
from pathlib import Path
from enum import Enum
import asyncio
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


logger = logging.getLogger(__name__)


# Type variables for generic results
T = TypeVar('T')
R = TypeVar('R')


class ExecutionStatus(Enum):
    """Execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRY_EXHAUSTED = "retry_exhausted"


class ErrorCategory(Enum):
    """Error categories for classification"""
    TIMEOUT = "timeout"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    VALIDATION = "validation"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass
class ExecutionError:
    """Execution error details"""
    category: ErrorCategory
    message: str
    exception: Optional[Exception] = None
    traceback: Optional[str] = None
    recoverable: bool = False

    @classmethod
    def from_exception(cls, exc: Exception) -> "ExecutionError":
        """Create ExecutionError from exception"""
        # Classify error
        if isinstance(exc, asyncio.TimeoutError) or isinstance(exc, TimeoutError):
            category = ErrorCategory.TIMEOUT
            recoverable = True
        elif isinstance(exc, PermissionError):
            category = ErrorCategory.PERMISSION
            recoverable = False
        elif isinstance(exc, (ConnectionError, OSError)):
            category = ErrorCategory.NETWORK
            recoverable = True
        elif isinstance(exc, (ValueError, TypeError)):
            category = ErrorCategory.VALIDATION
            recoverable = False
        elif isinstance(exc, (MemoryError, RuntimeError)):
            category = ErrorCategory.RESOURCE
            recoverable = True
        else:
            category = ErrorCategory.UNKNOWN
            recoverable = True

        return cls(
            category=category,
            message=str(exc),
            exception=exc,
            traceback=traceback.format_exc(),
            recoverable=recoverable
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "category": self.category.value,
            "message": self.message,
            "recoverable": self.recoverable,
            "traceback": self.traceback,
        }


@dataclass
class ExecutionResult(Generic[T]):
    """
    Generic execution result

    Attributes:
        success: Whether execution succeeded
        status: Execution status
        data: Result data if successful
        error: Error details if failed
        duration_ms: Execution duration in milliseconds
        attempts: Number of attempts made
        metadata: Additional metadata
    """
    success: bool
    status: ExecutionStatus
    data: Optional[T] = None
    error: Optional[ExecutionError] = None
    duration_ms: float = 0.0
    attempts: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "status": self.status.value,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    initial_delay_ms: float = 100.0
    max_delay_ms: float = 5000.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: List[ErrorCategory] = field(default_factory=lambda: [
        ErrorCategory.TIMEOUT,
        ErrorCategory.NETWORK,
        ErrorCategory.RESOURCE,
    ])

    def get_delay_ms(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        delay = self.initial_delay_ms * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay_ms)

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())

        return delay

    def should_retry(self, error: ExecutionError, attempt: int) -> bool:
        """Check if should retry"""
        if attempt >= self.max_attempts:
            return False
        if not error.recoverable:
            return False
        return error.category in self.retryable_errors


@dataclass
class ExecutionConfig:
    """Execution configuration"""
    timeout: float = 60.0  # seconds
    retry: RetryConfig = field(default_factory=RetryConfig)
    timeout_grace_period: float = 2.0  # extra time for cleanup
    cancel_on_timeout: bool = True
    capture_output: bool = True
    log_execution: bool = True
    log_level: int = logging.INFO


@dataclass
class ExecutionContext:
    """Context for tool execution"""
    tool_name: str
    arguments: Dict[str, Any]
    working_dir: Optional[Path] = None
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None  # For parallel execution tracking


@dataclass
class ExecutionLog:
    """Execution log entry"""
    execution_id: str
    tool_name: str
    arguments: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error: Optional[str] = None
    duration_ms: float = 0.0
    attempts: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "execution_id": self.execution_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
        }


class ExecutionLogger:
    """
    Logger for tool executions

    Provides structured logging of tool executions for
    debugging, auditing, and analysis.
    """

    def __init__(self, max_entries: int = 1000):
        self._entries: List[ExecutionLog] = []
        self._max_entries = max_entries
        self._lock = asyncio.Lock()

    async def log_start(
        self,
        execution_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ExecutionLog:
        """Log execution start"""
        entry = ExecutionLog(
            execution_id=execution_id,
            tool_name=tool_name,
            arguments=arguments,
            start_time=datetime.now(),
        )

        async with self._lock:
            self._entries.append(entry)
            # Trim old entries
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

        logger.debug(f"Execution started: {tool_name} ({execution_id})")
        return entry

    async def log_end(
        self,
        entry: ExecutionLog,
        status: ExecutionStatus,
        error: Optional[str] = None,
        attempts: int = 1
    ) -> None:
        """Log execution end"""
        entry.end_time = datetime.now()
        entry.status = status
        entry.error = error
        entry.duration_ms = (entry.end_time - entry.start_time).total_seconds() * 1000
        entry.attempts = attempts

        log_msg = f"Execution ended: {entry.tool_name} ({entry.execution_id}) - {status.value} ({entry.duration_ms:.1f}ms)"
        if error:
            logger.info(f"{log_msg} - Error: {error}")
        else:
            logger.debug(log_msg)

    def get_entries(
        self,
        tool_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100
    ) -> List[ExecutionLog]:
        """Get log entries with optional filtering"""
        entries = self._entries

        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]
        if status:
            entries = [e for e in entries if e.status == status]

        return entries[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._entries:
            return {
                "total_executions": 0,
                "success_rate": 0,
                "average_duration_ms": 0,
            }

        total = len(self._entries)
        successful = sum(1 for e in self._entries if e.status == ExecutionStatus.SUCCESS)
        total_duration = sum(e.duration_ms for e in self._entries)

        # Per-tool stats
        tool_stats = {}
        for entry in self._entries:
            if entry.tool_name not in tool_stats:
                tool_stats[entry.tool_name] = {
                    "count": 0,
                    "success": 0,
                    "total_duration_ms": 0,
                }
            tool_stats[entry.tool_name]["count"] += 1
            if entry.status == ExecutionStatus.SUCCESS:
                tool_stats[entry.tool_name]["success"] += 1
            tool_stats[entry.tool_name]["total_duration_ms"] += entry.duration_ms

        return {
            "total_executions": total,
            "success_rate": successful / total if total > 0 else 0,
            "average_duration_ms": total_duration / total if total > 0 else 0,
            "tools": tool_stats,
        }

    def clear(self) -> None:
        """Clear all entries"""
        self._entries.clear()


class ResultFormatter:
    """
    Formats execution results for different output needs

    Supports:
    - JSON serialization
    - Markdown output
    - Plain text
    - Structured data extraction
    """

    @staticmethod
    def to_json(result: ExecutionResult) -> str:
        """Convert result to JSON string"""
        import json
        return json.dumps(result.to_dict(), indent=2, default=str)

    @staticmethod
    def to_markdown(result: ExecutionResult, title: str = "Execution Result") -> str:
        """Convert result to markdown format"""
        lines = [f"## {title}", ""]

        lines.append(f"**Status**: {result.status.value}")
        lines.append(f"**Success**: {result.success}")
        lines.append(f"**Duration**: {result.duration_ms:.2f}ms")
        lines.append(f"**Attempts**: {result.attempts}")
        lines.append("")

        if result.data is not None:
            lines.append("### Result")
            lines.append("```")
            lines.append(str(result.data))
            lines.append("```")
            lines.append("")

        if result.error:
            lines.append("### Error")
            lines.append(f"- **Category**: {result.error.category.value}")
            lines.append(f"- **Message**: {result.error.message}")
            lines.append(f"- **Recoverable**: {result.error.recoverable}")
            if result.error.traceback:
                lines.append("")
                lines.append("```")
                lines.append(result.error.traceback)
                lines.append("```")

        return "\n".join(lines)

    @staticmethod
    def to_text(result: ExecutionResult) -> str:
        """Convert result to plain text"""
        if result.success:
            text = f"[OK] {result.status.value} ({result.duration_ms:.1f}ms)"
            if result.data is not None:
                text += f"\n{result.data}"
        else:
            text = f"[FAILED] {result.status.value}"
            if result.error:
                text += f": {result.error.message}"

        return text

    @staticmethod
    def extract_data(result: ExecutionResult, key: str = None) -> Any:
        """Extract data from result"""
        if not result.success or result.data is None:
            return None

        if key is None:
            return result.data

        if isinstance(result.data, dict):
            return result.data.get(key)

        return None


class ToolExecutor:
    """
    Unified tool execution interface

    Features:
    - Timeout handling with graceful cancellation
    - Error recovery and configurable retries
    - Result formatting
    - Parallel execution support
    - Execution logging

    Example:
        >>> executor = ToolExecutor()
        >>> result = await executor.execute(
        ...     handler=my_tool_handler,
        ...     arguments={"path": "/some/file.txt"},
        ...     config=ExecutionConfig(timeout=30.0)
        ... )
    """

    def __init__(
        self,
        default_config: Optional[ExecutionConfig] = None,
        logger: Optional[ExecutionLogger] = None,
    ):
        self._default_config = default_config or ExecutionConfig()
        self._execution_logger = logger or ExecutionLogger()
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._execution_counter = 0

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        self._execution_counter += 1
        return f"exec_{self._execution_counter}_{int(time.time() * 1000)}"

    async def execute(
        self,
        handler: Union[Callable[..., T], Callable[..., Awaitable[T]]],
        arguments: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionResult[T]:
        """
        Execute a tool handler with full error handling and retries.

        Args:
            handler: Tool handler (sync or async)
            arguments: Arguments to pass to handler
            context: Execution context
            config: Execution configuration

        Returns:
            ExecutionResult with data or error
        """
        config = config or self._default_config
        execution_id = self._generate_execution_id()
        tool_name = context.tool_name if context else handler.__name__

        # Log execution start
        log_entry = await self._execution_logger.log_start(
            execution_id=execution_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        start_time = time.perf_counter()
        last_error: Optional[ExecutionError] = None
        attempts = 0

        for attempt in range(1, config.retry.max_attempts + 1):
            attempts = attempt

            try:
                # Execute with timeout
                result_data = await self._execute_with_timeout(
                    handler=handler,
                    arguments=arguments,
                    timeout=config.timeout,
                )

                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log success
                await self._execution_logger.log_end(
                    entry=log_entry,
                    status=ExecutionStatus.SUCCESS,
                    attempts=attempts,
                )

                return ExecutionResult(
                    success=True,
                    status=ExecutionStatus.SUCCESS,
                    data=result_data,
                    duration_ms=duration_ms,
                    attempts=attempts,
                    metadata={"execution_id": execution_id},
                )

            except asyncio.CancelledError:
                duration_ms = (time.perf_counter() - start_time) * 1000

                await self._execution_logger.log_end(
                    entry=log_entry,
                    status=ExecutionStatus.CANCELLED,
                    attempts=attempts,
                )

                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.CANCELLED,
                    error=ExecutionError(
                        category=ErrorCategory.INTERNAL,
                        message="Execution was cancelled",
                    ),
                    duration_ms=duration_ms,
                    attempts=attempts,
                )

            except (asyncio.TimeoutError, TimeoutError) as e:
                last_error = ExecutionError.from_exception(e)

                if not config.retry.should_retry(last_error, attempt):
                    break

                # Wait before retry
                delay_ms = config.retry.get_delay_ms(attempt)
                logger.info(f"Timeout on attempt {attempt}, retrying in {delay_ms}ms...")
                await asyncio.sleep(delay_ms / 1000)

            except Exception as e:
                last_error = ExecutionError.from_exception(e)

                if not config.retry.should_retry(last_error, attempt):
                    break

                # Wait before retry
                delay_ms = config.retry.get_delay_ms(attempt)
                logger.info(f"Error on attempt {attempt}: {e}, retrying in {delay_ms}ms...")
                await asyncio.sleep(delay_ms / 1000)

        # All retries exhausted or unrecoverable error
        duration_ms = (time.perf_counter() - start_time) * 1000
        status = ExecutionStatus.RETRY_EXHAUSTED if attempts >= config.retry.max_attempts else ExecutionStatus.FAILED

        await self._execution_logger.log_end(
            entry=log_entry,
            status=status,
            error=last_error.message if last_error else "Unknown error",
            attempts=attempts,
        )

        return ExecutionResult(
            success=False,
            status=status,
            error=last_error,
            duration_ms=duration_ms,
            attempts=attempts,
            metadata={"execution_id": execution_id},
        )

    async def _execute_with_timeout(
        self,
        handler: Union[Callable[..., T], Callable[..., Awaitable[T]]],
        arguments: Dict[str, Any],
        timeout: float,
    ) -> T:
        """Execute handler with timeout"""
        # Check if handler is async
        if asyncio.iscoroutinefunction(handler):
            # Async handler
            return await asyncio.wait_for(
                handler(**arguments),
                timeout=timeout
            )
        else:
            # Sync handler - run in thread pool
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(
                    self._thread_pool,
                    lambda: handler(**arguments)
                ),
                timeout=timeout
            )

    async def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
        max_concurrency: int = 4,
        fail_fast: bool = False,
    ) -> List[ExecutionResult]:
        """
        Execute multiple tasks in parallel.

        Args:
            tasks: List of task definitions with keys:
                   - handler: Tool handler
                   - arguments: Arguments dict
                   - context: Optional ExecutionContext
                   - config: Optional ExecutionConfig
            max_concurrency: Maximum concurrent executions
            fail_fast: Cancel remaining tasks on first failure

        Returns:
            List of ExecutionResult in same order as tasks
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        results: List[ExecutionResult] = [None] * len(tasks)
        first_failure = asyncio.Event()

        async def run_task(index: int, task: Dict[str, Any]) -> None:
            async with semaphore:
                if fail_fast and first_failure.is_set():
                    results[index] = ExecutionResult(
                        success=False,
                        status=ExecutionStatus.CANCELLED,
                        error=ExecutionError(
                            category=ErrorCategory.INTERNAL,
                            message="Cancelled due to earlier failure",
                        ),
                    )
                    return

                result = await self.execute(
                    handler=task["handler"],
                    arguments=task.get("arguments", {}),
                    context=task.get("context"),
                    config=task.get("config"),
                )

                results[index] = result

                if fail_fast and not result.success:
                    first_failure.set()

        # Create all tasks
        coros = [run_task(i, task) for i, task in enumerate(tasks)]
        await asyncio.gather(*coros, return_exceptions=True)

        # Handle any exceptions that escaped
        for i, result in enumerate(results):
            if result is None:
                results[i] = ExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    error=ExecutionError(
                        category=ErrorCategory.INTERNAL,
                        message="Task did not complete",
                    ),
                )

        return results

    async def execute_batch(
        self,
        handler: Union[Callable[..., T], Callable[..., Awaitable[T]]],
        arguments_list: List[Dict[str, Any]],
        max_concurrency: int = 4,
        fail_fast: bool = False,
    ) -> List[ExecutionResult]:
        """
        Execute same handler with different arguments in parallel.

        Convenience method for batch processing.

        Args:
            handler: Tool handler
            arguments_list: List of argument dicts
            max_concurrency: Maximum concurrent executions
            fail_fast: Cancel remaining on first failure

        Returns:
            List of ExecutionResult
        """
        tasks = [
            {"handler": handler, "arguments": args}
            for args in arguments_list
        ]
        return await self.execute_parallel(tasks, max_concurrency, fail_fast)

    async def execute_chain(
        self,
        steps: List[Dict[str, Any]],
        stop_on_failure: bool = True,
    ) -> List[ExecutionResult]:
        """
        Execute tasks sequentially, optionally passing results between steps.

        Args:
            steps: List of step definitions with keys:
                   - handler: Tool handler
                   - arguments: Arguments dict or callable that receives previous result
                   - context: Optional ExecutionContext
                   - config: Optional ExecutionConfig
            stop_on_failure: Stop chain on first failure

        Returns:
            List of ExecutionResult
        """
        results = []
        previous_result = None

        for i, step in enumerate(steps):
            # Resolve arguments
            args = step.get("arguments", {})
            if callable(args):
                args = args(previous_result)

            result = await self.execute(
                handler=step["handler"],
                arguments=args,
                context=step.get("context"),
                config=step.get("config"),
            )

            results.append(result)
            previous_result = result

            if stop_on_failure and not result.success:
                break

        return results

    def get_execution_logger(self) -> ExecutionLogger:
        """Get the execution logger"""
        return self._execution_logger

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self._execution_logger.get_stats()

    async def shutdown(self) -> None:
        """Shutdown executor and cleanup resources"""
        # Cancel active executions
        for task in self._active_executions.values():
            task.cancel()

        if self._active_executions:
            await asyncio.gather(*self._active_executions.values(), return_exceptions=True)

        # Shutdown thread pool
        self._thread_pool.shutdown(wait=False)


class SyncToolExecutor:
    """
    Synchronous wrapper for ToolExecutor.

    Provides a synchronous interface for environments
    where async execution is not needed.
    """

    def __init__(
        self,
        default_config: Optional[ExecutionConfig] = None,
    ):
        self._executor = ToolExecutor(default_config=default_config)

    def execute(
        self,
        handler: Callable[..., T],
        arguments: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionResult[T]:
        """Execute handler synchronously"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._executor.execute(
                handler=handler,
                arguments=arguments,
                context=context,
                config=config,
            )
        )

    def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
        max_concurrency: int = 4,
        fail_fast: bool = False,
    ) -> List[ExecutionResult]:
        """Execute tasks in parallel synchronously"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._executor.execute_parallel(
                tasks=tasks,
                max_concurrency=max_concurrency,
                fail_fast=fail_fast,
            )
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self._executor.get_stats()


# Convenience functions
async def execute_tool(
    handler: Union[Callable[..., T], Callable[..., Awaitable[T]]],
    arguments: Dict[str, Any],
    timeout: float = 60.0,
    retries: int = 3,
) -> ExecutionResult[T]:
    """
    Convenience function for simple tool execution.

    Args:
        handler: Tool handler
        arguments: Arguments
        timeout: Timeout in seconds
        retries: Number of retries

    Returns:
        ExecutionResult
    """
    executor = ToolExecutor(
        default_config=ExecutionConfig(
            timeout=timeout,
            retry=RetryConfig(max_attempts=retries),
        )
    )
    return await executor.execute(handler=handler, arguments=arguments)


def execute_tool_sync(
    handler: Callable[..., T],
    arguments: Dict[str, Any],
    timeout: float = 60.0,
    retries: int = 3,
) -> ExecutionResult[T]:
    """
    Synchronous convenience function for tool execution.

    Args:
        handler: Tool handler
        arguments: Arguments
        timeout: Timeout in seconds
        retries: Number of retries

    Returns:
        ExecutionResult
    """
    executor = SyncToolExecutor(
        default_config=ExecutionConfig(
            timeout=timeout,
            retry=RetryConfig(max_attempts=retries),
        )
    )
    return executor.execute(handler=handler, arguments=arguments)


__all__ = [
    # Core classes
    "ToolExecutor",
    "SyncToolExecutor",
    "ExecutionConfig",
    "RetryConfig",
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionError",
    "ExecutionStatus",
    "ErrorCategory",
    # Logging
    "ExecutionLogger",
    "ExecutionLog",
    # Formatting
    "ResultFormatter",
    # Convenience functions
    "execute_tool",
    "execute_tool_sync",
]
