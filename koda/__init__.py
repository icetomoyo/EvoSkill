"""
Koda - Pi Coding Agent 的 Python 实现

完全对标 https://github.com/badlogic/pi-mono

Modules:
    ai: Unified LLM interface (packages/ai)
    mes: Model-Optimized Messages (packages/mom)
    agent: Agent framework (packages/agent)
    coding: Coding agent with 7 built-in tools (packages/coding-agent)

Example:
    >>> from koda import ai, agent, coding
    >>> 
    >>> # Create LLM provider
    >>> provider = ai.create_provider("openai", api_key="sk-...")
    >>> 
    >>> # Use tools
    >>> file_tool = coding.FileTool()
    >>> 
    >>> # Create agent
    >>> ag = agent.Agent(provider)
"""

__version__ = "0.2.0"

# Submodules
from koda import ai
from koda import mes
from koda import agent
from koda import coding

# Convenience exports
from koda.ai import (
    LLMProvider,
    Message,
    Model,
    create_provider,
    list_supported_providers,
)

from koda.coding import (
    FileTool,
    ShellTool,
    GrepTool,
    FindTool,
    LsTool,
)

__all__ = [
    # Submodules
    "ai",
    "mes", 
    "agent",
    "coding",
    
    # Quick access - AI
    "LLMProvider",
    "Message",
    "Model",
    "create_provider",
    "list_supported_providers",
    
    # Quick access - Tools
    "FileTool",
    "ShellTool",
    "GrepTool",
    "FindTool",
    "LsTool",
]
