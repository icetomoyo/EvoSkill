"""
Koda - Pi Coding Agent Python Implementation

Fully compatible with https://github.com/badlogic/pi-mono

Modules:
    ai: Unified LLM interface (packages/ai)
    mes: Model-Optimized Messages (packages/mom)
    agent: Agent framework (packages/agent)
    coding: Coding agent with 7 built-in tools (packages/coding-agent)

Example:
    >>> from koda import ai, agent, coding
    >>> from koda.ai import create_provider
    >>> 
    >>> # Create LLM provider
    >>> provider = create_provider("openai", api_key="sk-...")
    >>> 
    >>> # Use tools
    >>> from koda.coding.tools import FileTool
    >>> file_tool = FileTool()
    >>> 
    >>> # Create agent
    >>> ag = agent.Agent(provider)
"""

__version__ = "0.2.0"

# Submodules - lazy import to avoid circular dependencies
def __getattr__(name):
    if name == "ai":
        from koda import ai as module
        return module
    elif name == "mes":
        from koda import mes as module
        return module
    elif name == "agent":
        from koda import agent as module
        return module
    elif name == "coding":
        from koda import coding as module
        return module
    raise AttributeError(f"module 'koda' has no attribute '{name}'")

__all__ = [
    "__version__",
    "ai",
    "mes",
    "agent",
    "coding",
]
