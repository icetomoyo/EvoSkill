"""
Agent Proxy - Multi-agent coordination and delegation

Equivalent to Pi Mono's agent-proxy.ts

Features:
- Agent discovery and registration
- Task delegation between agents
- Message routing
- Load balancing
- Agent lifecycle management
"""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncIterator, Set
import time
from uuid import uuid4

from koda.ai.types import (
    Context,
    AssistantMessage,
    UserMessage,
    AgentEvent,
    AgentEventType,
    Message,
)
from koda.agent.loop import AgentLoop, AgentTool


class AgentStatus(Enum):
    """Agent status"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentInfo:
    """Agent registration info"""
    id: str
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    total_tasks: int = 0
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Delegatable task"""
    id: str
    description: str
    priority: TaskPriority
    required_capabilities: List[str]
    context: Context
    callback: Optional[Callable[[AssistantMessage], None]] = None
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, assigned, completed, failed
    result: Optional[AssistantMessage] = None
    error: Optional[str] = None


@dataclass
class AgentProxyConfig:
    """AgentProxy configuration"""
    max_agents: int = 10
    max_queue_size: int = 100
    default_timeout: float = 300.0  # 5 minutes
    enable_load_balancing: bool = True
    enable_auto_scaling: bool = False
    task_retry_attempts: int = 2


class AgentProxy:
    """
    Agent Proxy for multi-agent coordination
    
    Manages multiple agent instances, handles task delegation,
    and routes messages between agents.
    """
    
    def __init__(self, config: Optional[AgentProxyConfig] = None):
        self.config = config or AgentProxyConfig()
        
        # Agent registry
        self._agents: Dict[str, AgentInfo] = {}
        self._agent_loops: Dict[str, AgentLoop] = {}
        self._agent_locks: Dict[str, asyncio.Lock] = {}
        
        # Task management
        self._tasks: Dict[str, Task] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=self.config.max_queue_size
        )
        self._task_handlers: Dict[str, asyncio.Task] = {}
        
        # Event handlers
        self._event_handlers: List[Callable[[AgentEvent], None]] = []
        
        # Stats
        self._stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_delegation_time_ms": 0,
        }
        
        # Running flag
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        agent_loop: AgentLoop,
        capabilities: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentInfo:
        """
        Register an agent with the proxy
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable name
            description: Agent description
            agent_loop: The agent loop instance
            capabilities: List of capabilities
            tools: List of tool names
            metadata: Additional metadata
            
        Returns:
            AgentInfo for the registered agent
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent with id '{agent_id}' already registered")
        
        if len(self._agents) >= self.config.max_agents:
            raise RuntimeError(f"Maximum number of agents ({self.config.max_agents}) reached")
        
        info = AgentInfo(
            id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities or [],
            tools=tools or [],
            status=AgentStatus.IDLE,
            metadata=metadata or {}
        )
        
        self._agents[agent_id] = info
        self._agent_loops[agent_id] = agent_loop
        self._agent_locks[agent_id] = asyncio.Lock()
        
        self._emit_event(AgentEvent(
            type=AgentEventType.AGENT_START,
            data={"agent_id": agent_id, "name": name},
            timestamp=int(time.time() * 1000)
        ))
        
        return info
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent was unregistered
        """
        if agent_id not in self._agents:
            return False
        
        # Cancel any running tasks
        if self._agents[agent_id].current_task:
            task_id = self._agents[agent_id].current_task
            if task_id in self._task_handlers:
                self._task_handlers[task_id].cancel()
        
        del self._agents[agent_id]
        del self._agent_loops[agent_id]
        del self._agent_locks[agent_id]
        
        self._emit_event(AgentEvent(
            type=AgentEventType.AGENT_END,
            data={"agent_id": agent_id},
            timestamp=int(time.time() * 1000)
        ))
        
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID"""
        return self._agents.get(agent_id)
    
    def list_agents(
        self,
        status: Optional[AgentStatus] = None,
        capability: Optional[str] = None
    ) -> List[AgentInfo]:
        """
        List registered agents with optional filtering
        
        Args:
            status: Filter by status
            capability: Filter by capability
            
        Returns:
            List of matching AgentInfo
        """
        agents = list(self._agents.values())
        
        if status:
            agents = [a for a in agents if a.status == status]
        
        if capability:
            agents = [a for a in agents if capability in a.capabilities]
        
        return agents
    
    def find_agents_for_task(
        self,
        required_capabilities: List[str],
        exclude: Optional[Set[str]] = None
    ) -> List[AgentInfo]:
        """
        Find agents capable of handling a task
        
        Args:
            required_capabilities: Required capabilities
            exclude: Agent IDs to exclude
            
        Returns:
            List of capable agents, sorted by availability
        """
        exclude = exclude or set()
        candidates = []
        
        for agent_id, info in self._agents.items():
            if agent_id in exclude:
                continue
            
            # Check capabilities
            if all(cap in info.capabilities for cap in required_capabilities):
                # Prefer idle agents
                score = 0 if info.status == AgentStatus.IDLE else 1
                candidates.append((score, info))
        
        # Sort by score (idle first), then by total tasks (less loaded)
        candidates.sort(key=lambda x: (x[0], x[1].total_tasks))
        
        return [info for _, info in candidates]
    
    async def delegate(
        self,
        description: str,
        context: Context,
        priority: TaskPriority = TaskPriority.NORMAL,
        required_capabilities: Optional[List[str]] = None,
        preferred_agent: Optional[str] = None,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[AgentEvent], None]] = None
    ) -> AssistantMessage:
        """
        Delegate a task to an agent
        
        Args:
            description: Task description
            context: Conversation context
            priority: Task priority
            required_capabilities: Required agent capabilities
            preferred_agent: Preferred agent ID
            timeout: Task timeout
            on_progress: Progress callback
            
        Returns:
            Task result
        """
        task_id = str(uuid4())
        
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            required_capabilities=required_capabilities or [],
            context=context
        )
        
        self._tasks[task_id] = task
        self._stats["tasks_created"] += 1
        
        # Find agent
        agent_id = preferred_agent
        if not agent_id or agent_id not in self._agents:
            capable = self.find_agents_for_task(task.required_capabilities)
            if not capable:
                raise RuntimeError(
                    f"No agent found with capabilities: {task.required_capabilities}"
                )
            agent_id = capable[0].id
        
        task.assigned_to = agent_id
        task.status = "assigned"
        
        # Update agent status
        self._agents[agent_id].status = AgentStatus.BUSY
        self._agents[agent_id].current_task = task_id
        self._agents[agent_id].total_tasks += 1
        
        self._emit_event(AgentEvent(
            type=AgentEventType.TURN_START,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "description": description
            },
            timestamp=int(time.time() * 1000)
        ))
        
        start_time = time.time()
        
        try:
            agent_loop = self._agent_loops[agent_id]
            
            # Execute with timeout
            timeout_val = timeout or self.config.default_timeout
            
            async def execute_with_events():
                events = []
                
                def event_handler(event: AgentEvent):
                    events.append(event)
                    if on_progress:
                        on_progress(event)
                    self._emit_event(event)
                
                result = await agent_loop.run(
                    context=task.context,
                    on_event=event_handler
                )
                return result, events
            
            result = await asyncio.wait_for(
                execute_with_events(),
                timeout=timeout_val
            )
            
            task.result = result[0]
            task.status = "completed"
            self._stats["tasks_completed"] += 1
            
            self._emit_event(AgentEvent(
                type=AgentEventType.AGENT_END,
                data={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "status": "completed"
                },
                timestamp=int(time.time() * 1000)
            ))
            
            return result[0]
            
        except asyncio.TimeoutError:
            task.status = "failed"
            task.error = f"Task timed out after {timeout_val}s"
            self._stats["tasks_failed"] += 1
            
            raise TimeoutError(f"Task '{description}' timed out after {timeout_val}s")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self._stats["tasks_failed"] += 1
            
            self._emit_event(AgentEvent(
                type=AgentEventType.ERROR,
                data={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "error": str(e)
                },
                timestamp=int(time.time() * 1000)
            ))
            
            raise
            
        finally:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._stats["total_delegation_time_ms"] += elapsed_ms
            
            # Reset agent status
            if agent_id in self._agents:
                self._agents[agent_id].status = AgentStatus.IDLE
                self._agents[agent_id].current_task = None
    
    async def broadcast(
        self,
        message: str,
        filter_fn: Optional[Callable[[AgentInfo], bool]] = None
    ) -> Dict[str, AssistantMessage]:
        """
        Broadcast a message to multiple agents
        
        Args:
            message: Message to broadcast
            filter_fn: Optional filter function
            
        Returns:
            Dict mapping agent_id to response
        """
        agents = list(self._agents.values())
        
        if filter_fn:
            agents = [a for a in agents if filter_fn(a)]
        
        tasks = []
        for agent_info in agents:
            context = Context(
                system_prompt="You are part of a multi-agent system. Respond to the broadcast.",
                messages=[UserMessage(role="user", content=message)]
            )
            
            task = self.delegate(
                description=f"Broadcast: {message[:50]}...",
                context=context,
                preferred_agent=agent_info.id
            )
            tasks.append((agent_info.id, task))
        
        results = {}
        for agent_id, task in tasks:
            try:
                result = await task
                results[agent_id] = result
            except Exception as e:
                results[agent_id] = AssistantMessage(
                    role="assistant",
                    content=[{"type": "text", "text": f"Error: {str(e)}"}],
                    error_message=str(e)
                )
        
        return results
    
    async def route_message(
        self,
        message: str,
        context: Context,
        routing_hint: Optional[str] = None
    ) -> AssistantMessage:
        """
        Route a message to the most appropriate agent
        
        Args:
            message: User message
            context: Conversation context
            routing_hint: Optional hint for routing (capability name)
            
        Returns:
            Agent response
        """
        # Simple routing: find agent with matching capability
        if routing_hint:
            capable = self.find_agents_for_task([routing_hint])
            if capable:
                return await self.delegate(
                    description=message,
                    context=context,
                    preferred_agent=capable[0].id
                )
        
        # Default to first available idle agent, or least busy
        idle_agents = self.list_agents(status=AgentStatus.IDLE)
        if idle_agents:
            return await self.delegate(
                description=message,
                context=context,
                preferred_agent=idle_agents[0].id
            )
        
        # Fall back to any agent
        all_agents = self.list_agents()
        if all_agents:
            # Sort by total tasks (least used)
            all_agents.sort(key=lambda a: a.total_tasks)
            return await self.delegate(
                description=message,
                context=context,
                preferred_agent=all_agents[0].id
            )
        
        raise RuntimeError("No agents available for routing")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        total_tasks = self._stats["tasks_created"]
        avg_time_ms = (
            self._stats["total_delegation_time_ms"] / total_tasks
            if total_tasks > 0 else 0
        )
        
        return {
            **self._stats,
            "avg_delegation_time_ms": round(avg_time_ms, 2),
            "registered_agents": len(self._agents),
            "active_tasks": sum(
                1 for t in self._tasks.values() if t.status == "assigned"
            ),
            "pending_tasks": sum(
                1 for t in self._tasks.values() if t.status == "pending"
            ),
        }
    
    def on_event(self, handler: Callable[[AgentEvent], None]) -> Callable[[AgentEvent], None]:
        """Register event handler"""
        self._event_handlers.append(handler)
        return handler
    
    def _emit_event(self, event: AgentEvent) -> None:
        """Emit event to all handlers"""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors break the proxy
    
    async def start(self) -> None:
        """Start the proxy"""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue())
    
    async def stop(self) -> None:
        """Stop the proxy"""
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel any running tasks
        for task in self._task_handlers.values():
            task.cancel()
        
        if self._task_handlers:
            await asyncio.gather(
                *self._task_handlers.values(),
                return_exceptions=True
            )
    
    async def _process_queue(self) -> None:
        """Background task queue processor"""
        while self._running:
            try:
                # Get next task from queue
                priority, task_id = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                task = self._tasks.get(task_id)
                if not task or task.status != "pending":
                    continue
                
                # Process task
                await self._execute_task(task)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._emit_event(AgentEvent(
                    type=AgentEventType.ERROR,
                    data={"error": str(e)},
                    timestamp=int(time.time() * 1000)
                ))
    
    async def _execute_task(self, task: Task) -> None:
        """Execute a queued task"""
        # Find capable agent
        capable = self.find_agents_for_task(task.required_capabilities)
        
        if not capable:
            task.status = "failed"
            task.error = "No capable agent available"
            return
        
        agent_id = capable[0].id
        task.assigned_to = agent_id
        task.status = "assigned"
        
        try:
            agent_loop = self._agent_loops[agent_id]
            result = await agent_loop.run(context=task.context)
            task.result = result
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)


class AgentPool:
    """
    Agent Pool for managing multiple similar agents
    
    Provides load balancing and failover across agent instances.
    """
    
    def __init__(
        self,
        proxy: AgentProxy,
        agent_factory: Callable[[], AgentLoop],
        pool_size: int = 2,
        name_prefix: str = "agent"
    ):
        self.proxy = proxy
        self.agent_factory = agent_factory
        self.pool_size = pool_size
        self.name_prefix = name_prefix
        self._agent_ids: List[str] = []
    
    async def initialize(
        self,
        capabilities: List[str],
        tools: List[str],
        description: str = "Pool agent"
    ) -> None:
        """Initialize the pool with agents"""
        for i in range(self.pool_size):
            agent_id = f"{self.name_prefix}-{i}"
            agent_loop = self.agent_factory()
            
            self.proxy.register_agent(
                agent_id=agent_id,
                name=f"{self.name_prefix.title()} Agent {i}",
                description=description,
                agent_loop=agent_loop,
                capabilities=capabilities,
                tools=tools
            )
            
            self._agent_ids.append(agent_id)
    
    async def execute(
        self,
        description: str,
        context: Context,
        timeout: Optional[float] = None
    ) -> AssistantMessage:
        """Execute task using pool (with load balancing)"""
        # Find least busy agent in pool
        agents = [
            self.proxy.get_agent(aid)
            for aid in self._agent_ids
            if self.proxy.get_agent(aid)
        ]
        
        if not agents:
            raise RuntimeError("No agents available in pool")
        
        # Sort by load (total tasks)
        agents.sort(key=lambda a: a.total_tasks)
        
        return await self.proxy.delegate(
            description=description,
            context=context,
            preferred_agent=agents[0].id,
            timeout=timeout
        )
    
    def get_agent_ids(self) -> List[str]:
        """Get all agent IDs in pool"""
        return list(self._agent_ids)
