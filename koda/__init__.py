"""
Koda V2 - 自扩展编程代理框架 (KOding Agent)

融合 Pi Coding Agent 理念：代码写代码，树状分支，自扩展。
增强自验证能力，形成完整闭环。

Quick Start:
    from koda import KodaAgentV2
    
    agent = KodaAgentV2(llm=llm_adapter, workspace="./workspace")
    
    result = await agent.execute(
        description="Create a weather query tool",
        requirements=["Use OpenWeatherMap API"]
    )
    
    print(result['code'])
    print(agent.get_tree_view())  # 查看开发树

New Features in V2:
  - Tree Session: Branching like git
  - Self-Extension: Agent writes its own tools
  - Self-Validation: Auto fix with validation
  - Hot Reload: Extensions reload instantly

Inspired by Pi Coding Agent (Mario Zechner), enhanced with validation.
"""

__version__ = "0.1.0"
__author__ = "EvoSkill Team"

# Core components
from koda.core.agent import KodaAgent  # V1 backward compatible
from koda.core.agent_v2 import KodaAgentV2  # V2 with Pi features
from koda.core.tree_session import TreeSession, TreeSessionManager
from koda.core.extension_engine import ExtensionEngine, SelfExtendingAgent
from koda.core.task import Task, TaskResult
from koda.core.plan import Plan, Step

# Types
from koda.core.types import (
    CodeArtifact,
    ExecutionResult,
    ReflectionResult,
    ToolDefinition,
)

__all__ = [
    # Core V1
    "KodaAgent",
    # Core V2 (Pi-inspired)
    "KodaAgentV2",
    "TreeSession",
    "TreeSessionManager", 
    "ExtensionEngine",
    "SelfExtendingAgent",
    # Task
    "Task", 
    "TaskResult",
    "Plan",
    "Step",
    # Types
    "CodeArtifact",
    "ExecutionResult", 
    "ReflectionResult",
    "ToolDefinition",
]
