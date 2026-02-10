"""
Koda Agent - Enhanced Agent Framework

Event-driven agent with message queue, tool registry, and state management.
Based on Pi Mono's agent package.
"""
from koda.agent.agent import Agent, AgentConfig, AgentState
from koda.agent.events import EventBus, Event, EventType
from koda.agent.tools import ToolRegistry, Tool, ToolContext
from koda.agent.queue import MessageQueue, QueuedMessage
from koda.agent.loop import AgentLoop, AgentLoopConfig, AgentTool
from koda.agent.proxy import (
    AgentProxy,
    AgentProxyConfig,
    AgentPool,
    AgentInfo,
    AgentStatus,
    Task,
    TaskPriority,
)

__all__ = [
    # Agent
    "Agent",
    "AgentConfig",
    "AgentState",
    # Events
    "EventBus",
    "Event",
    "EventType",
    # Tools
    "ToolRegistry",
    "Tool",
    "ToolContext",
    # Queue
    "MessageQueue",
    "QueuedMessage",
    # Loop
    "AgentLoop",
    "AgentLoopConfig",
    "AgentTool",
    # Proxy
    "AgentProxy",
    "AgentProxyConfig",
    "AgentPool",
    "AgentInfo",
    "AgentStatus",
    "Task",
    "TaskPriority",
]
