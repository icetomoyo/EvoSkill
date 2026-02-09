"""
Koda - Pi Coding Agent 的 Python 实现

完全对标 https://github.com/badlogic/pi-mono

Modules:
    ai: Unified LLM interface supporting 15+ providers
    mes: Model-Optimized Messages (token efficiency)
    agent: Enhanced Agent framework (events, queue, tools)

Example:
    >>> from koda import ai, mes, agent
    >>> 
    >>> # Create LLM provider
    >>> provider = ai.create_provider("openai", api_key="sk-...")
    >>> 
    >>> # Create agent
    >>> cfg = agent.AgentConfig()
    >>> ag = agent.Agent(provider, cfg)
    >>> 
    >>> # Run
    >>> async for event in ag.run("Hello"):
    ...     print(event)
"""

# Version
__version__ = "0.2.0"

# Submodules
from koda import ai
from koda import mes
from koda import agent

# Direct exports for convenience
from koda.ai import (
    LLMProvider,
    Message,
    Model,
    ToolCall,
    ToolResult,
    create_provider,
    list_supported_providers,
)

from koda.mes import (
    MessageOptimizer,
    MessageFormatter,
    HistoryManager,
)

from koda.agent import (
    Agent,
    AgentConfig,
    AgentState,
    EventBus,
    Event,
    EventType,
    ToolRegistry,
    Tool,
    MessageQueue,
)

__all__ = [
    # Submodules
    "ai",
    "mes",
    "agent",
    
    # AI exports
    "LLMProvider",
    "Message",
    "Model",
    "ToolCall",
    "ToolResult",
    "create_provider",
    "list_supported_providers",
    
    # Mes exports
    "MessageOptimizer",
    "MessageFormatter",
    "HistoryManager",
    
    # Agent exports
    "Agent",
    "AgentConfig",
    "AgentState",
    "EventBus",
    "Event",
    "EventType",
    "ToolRegistry",
    "Tool",
    "MessageQueue",
]
