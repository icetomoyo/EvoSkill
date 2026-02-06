"""
EvoSkill - 会造工具的 AI 对话系统

一个具备自我进化能力的智能对话系统，能够自动调用 Skills 完成任务，
同时根据用户需求自动设计、实现并上线新的 Skills。
"""

__version__ = "0.1.0"
__author__ = "EvoSkill Team"

from evoskill.core.session import AgentSession
from evoskill.core.types import (
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Event,
    ToolDefinition,
)
from evoskill.core.prompts import (
    get_full_system_prompt,
    get_coding_agent_prompt,
)
from evoskill.config import (
    get_config,
    save_config,
    init_config,
    EvoSkillConfig,
    ConfigManager,
)

__all__ = [
    "AgentSession",
    "Message",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Event",
    "ToolDefinition",
    "get_config",
    "save_config",
    "init_config",
    "EvoSkillConfig",
    "ConfigManager",
]
