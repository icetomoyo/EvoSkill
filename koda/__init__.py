"""
Koda - Pi Coding Agent 的 Python 实现

完全对标 https://github.com/badlogic/pi-mono

Modules:
    ai: Unified LLM interface supporting 15+ providers
    mes: Model-Optimized Messages (token efficiency)  
    agent: Enhanced Agent framework (events, queue, tools)
    tools: 7 built-in Pi-compatible tools

Example:
    >>> from koda import ai, agent
    >>> 
    >>> # Create LLM provider
    >>> provider = ai.create_provider("openai", api_key="sk-...")
    >>> 
    >>> # Create agent
    >>> ag = agent.Agent(provider)
    >>> 
    >>> # Run
    >>> async for event in ag.run("Hello"):
    ...     print(event)
"""

__version__ = "0.2.0"

# Submodules
from koda import ai
from koda import mes
from koda import agent
from koda import tools

# Convenience exports
from koda.ai import (
    LLMProvider,
    Message,
    Model,
    create_provider,
    list_supported_providers,
)

__all__ = [
    # Submodules
    "ai",
    "mes", 
    "agent",
    "tools",
    
    # Quick access
    "LLMProvider",
    "Message",
    "Model",
    "create_provider",
    "list_supported_providers",
]
