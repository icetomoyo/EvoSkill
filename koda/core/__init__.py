"""
Koda Core - 核心模块

包含 Koda V2 的所有核心组件：
- agent_v2: 主代理
- tree_session: 树状会话管理
- extension_engine: 自扩展引擎
- system_prompt: 系统提示词构建器
- truncation: 内容截断处理
- types: 类型定义
"""

from koda.core.agent_v2 import KodaAgentV2, KodaAgent, AgentConfig, ToolResult
from koda.core.tree_session import (
    TreeSession, TreeSessionManager, SessionNode, NodeStatus,
)
from koda.core.extension_engine import (
    ExtensionEngine, SelfExtendingAgent, ExtensionInfo
)
from koda.core.system_prompt import (
    SystemPromptBuilder, SystemPromptOptions,
    Skill, ContextFile, TOOL_DESCRIPTIONS
)
from koda.core.truncation import (
    truncate_head, truncate_tail, truncate_for_read, truncate_for_bash,
    TruncationResult, format_truncation_message,
    DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES
)

__all__ = [
    # Agent
    "KodaAgentV2",
    "KodaAgent",
    "AgentConfig",
    "ToolResult",
    
    # Tree Session
    "TreeSession",
    "TreeSessionManager",
    "SessionNode",
    "NodeStatus",
    
    # Extension
    "ExtensionEngine",
    "SelfExtendingAgent",
    "ExtensionInfo",
    
    # System Prompt
    "SystemPromptBuilder",
    "SystemPromptOptions",
    "Skill",
    "ContextFile",
    "TOOL_DESCRIPTIONS",
    
    # Truncation
    "truncate_head",
    "truncate_tail",
    "truncate_for_read",
    "truncate_for_bash",
    "TruncationResult",
    "format_truncation_message",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
]
