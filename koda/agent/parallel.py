"""
Parallel Execution
Equivalent to Pi Mono's packages/agent/src/parallel.ts

Parallel tool execution with dependency management.
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional, Set
from dataclasses import dataclass
from enum import Enum
import graphlib


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of a parallel task"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    execution_time_ms: float = 0.0


@dataclass
class ParallelTask:
    """A task for parallel execution"""
    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    dependencies: Set[str] = None
    timeout: Optional[float] = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.dependencies is None:
            self.dependencies = set()


class ParallelExecutor:
    """
    Execute tasks in parallel with dependency management.
    
    Handles task dependencies, limits concurrency, and collects results.
    
    Example:
        >>> executor = ParallelExecutor(max_concurrency=5)
        >>> tasks = [
        ...     ParallelTask(id="a", func=fetch_data, args=("url1",)),
        ...     ParallelTask(id="b", func=fetch_data, args=("url2",), dependencies={"a"}),
        ... ]
        >>> results = await executor.execute(tasks)
    """
    
    def __init__(self, max_concurrency: int = 10):
        """
        Initialize parallel executor.
        
        Args:
            max_concurrency: Maximum number of concurrent tasks
        """
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._results: Dict[str, TaskResult] = {}
        self._tasks: Dict[str, ParallelTask] = {}
    
    async def execute(self, tasks: List[ParallelTask]) -> Dict[str, TaskResult]:
        """
        Execute tasks in parallel respecting dependencies.
        
        Args:
            tasks: List of tasks to execute
            
        Returns:
            Dict mapping task IDs to results
        """
        self._tasks = {t.id: t for t in tasks}
        self._results = {}
        
        # Build dependency graph
        dependency_graph = {t.id: t.dependencies for t in tasks}
        
        # Topological sort to get execution order
        try:
            sorter = graphlib.TopologicalSorter(dependency_graph)
            execution_order = list(sorter.static_order())
        except graphlib.CycleError as e:
            raise ValueError(f"Dependency cycle detected: {e}")
        
        # Group by levels (tasks that can run in parallel)
        levels = self._group_by_levels(dependency_graph, execution_order)
        
        # Execute level by level
        for level in levels:
            await self._execute_level(level)
        
        return self._results
    
    def _group_by_levels(
        self,
        dependencies: Dict[str, Set[str]],
        order: List[str]
    ) -> List[List[str]]:
        """Group tasks into levels based on dependencies"""
        levels = []
        completed = set()
        
        remaining = set(order)
        
        while remaining:
            # Find tasks with all dependencies completed
            level = []
            for task_id in list(remaining):
                deps = dependencies.get(task_id, set())
                if deps.issubset(completed):
                    level.append(task_id)
            
            if not level:
                raise ValueError("Unable to resolve dependencies")
            
            levels.append(level)
            completed.update(level)
            remaining -= set(level)
        
        return levels
    
    async def _execute_level(self, task_ids: List[str]):
        """Execute all tasks in a level concurrently"""
        coroutines = [
            self._execute_task(self._tasks[tid])
            for tid in task_ids
        ]
        await asyncio.gather(*coroutines, return_exceptions=True)
    
    async def _execute_task(self, task: ParallelTask):
        """Execute a single task with semaphore"""
        import time
        
        async with self._semaphore:
            start = time.perf_counter()
            
            try:
                # Check dependencies
                for dep_id in task.dependencies:
                    if dep_id in self._results:
                        dep_result = self._results[dep_id]
                        if dep_result.status == TaskStatus.FAILED:
                            raise Exception(f"Dependency {dep_id} failed")
                
                # Execute with timeout
                if asyncio.iscoroutinefunction(task.func):
                    if task.timeout:
                        result = await asyncio.wait_for(
                            task.func(*task.args, **task.kwargs),
                            timeout=task.timeout
                        )
                    else:
                        result = await task.func(*task.args, **task.kwargs)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    if task.timeout:
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs)),
                            timeout=task.timeout
                        )
                    else:
                        result = await loop.run_in_executor(None, lambda: task.func(*task.args, **task.kwargs))
                
                elapsed_ms = (time.perf_counter() - start) * 1000
                
                self._results[task.id] = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    execution_time_ms=elapsed_ms
                )
                
            except asyncio.TimeoutError:
                elapsed_ms = (time.perf_counter() - start) * 1000
                self._results[task.id] = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=TimeoutError(f"Task timed out after {task.timeout}s"),
                    execution_time_ms=elapsed_ms
                )
                
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                self._results[task.id] = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=e,
                    execution_time_ms=elapsed_ms
                )
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result for a specific task"""
        return self._results.get(task_id)
    
    def get_completed_count(self) -> int:
        """Get number of completed tasks"""
        return sum(
            1 for r in self._results.values()
            if r.status == TaskStatus.COMPLETED
        )
    
    def get_failed_count(self) -> int:
        """Get number of failed tasks"""
        return sum(
            1 for r in self._results.values()
            if r.status == TaskStatus.FAILED
        )


class ParallelToolExecutor(ParallelExecutor):
    """
    Specialized executor for parallel tool execution.
    
    Optimized for agent tool calls with result aggregation.
    """
    
    async def execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_executor: Callable[[str, Dict], Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute tool calls in parallel.
        
        Args:
            tool_calls: List of tool call dicts with 'id', 'name', 'arguments'
            tool_executor: Function to execute a tool
            
        Returns:
            List of tool results
        """
        tasks = []
        for call in tool_calls:
            task = ParallelTask(
                id=call["id"],
                func=tool_executor,
                args=(call["name"], call.get("arguments", {})),
                timeout=30.0
            )
            tasks.append(task)
        
        results = await self.execute(tasks)
        
        # Format results
        tool_results = []
        for call in tool_calls:
            result = results.get(call["id"])
            tool_results.append({
                "tool_call_id": call["id"],
                "name": call["name"],
                "result": result.result if result and result.status == TaskStatus.COMPLETED else None,
                "error": str(result.error) if result and result.error else None,
                "status": result.status.value if result else "failed"
            })
        
        return tool_results


# Convenience functions
async def execute_parallel(
    funcs: List[Callable],
    max_concurrency: int = 10,
    timeout: Optional[float] = None
) -> List[Any]:
    """
    Execute functions in parallel.
    
    Args:
        funcs: List of functions to execute
        max_concurrency: Max concurrent executions
        timeout: Timeout per function
        
    Returns:
        List of results
    """
    tasks = [
        ParallelTask(id=str(i), func=f, timeout=timeout)
        for i, f in enumerate(funcs)
    ]
    
    executor = ParallelExecutor(max_concurrency=max_concurrency)
    results = await executor.execute(tasks)
    
    return [results[str(i)].result for i in range(len(funcs))]


async def execute_with_dependencies(
    tasks: List[ParallelTask],
    max_concurrency: int = 10
) -> Dict[str, TaskResult]:
    """
    Execute tasks with dependencies.
    
    Args:
        tasks: List of tasks with dependencies
        max_concurrency: Max concurrent executions
        
    Returns:
        Dict of results
    """
    executor = ParallelExecutor(max_concurrency=max_concurrency)
    return await executor.execute(tasks)


__all__ = [
    "ParallelExecutor",
    "ParallelToolExecutor",
    "ParallelTask",
    "TaskResult",
    "TaskStatus",
    "execute_parallel",
    "execute_with_dependencies",
]
