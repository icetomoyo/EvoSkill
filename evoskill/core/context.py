"""
上下文管理器

参考 OpenClaw/Pi Agent 的设计：
- 用户只配置 max_context_tokens
- 系统自动在接近上限时压缩
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

from evoskill.core.types import Message, UserMessage, AssistantMessage, TextContent


class ContextManager:
    """
    上下文管理器
    
    职责:
    1. 维护消息历史
    2. 估算 token 数
    3. 在接近上限时自动压缩
    """
    
    def __init__(self, max_tokens: int = 80000):
        """
        Args:
            max_tokens: 最大上下文 token 数
        """
        self.max_tokens = max_tokens
        # 在 80% 时触发压缩，给用户留缓冲区
        self.compact_threshold = int(max_tokens * 0.8)
        self.messages: List[Message] = []
    
    def add_message(self, message: Message) -> bool:
        """
        添加消息，如果触发压缩返回 True
        
        Args:
            message: 要添加的消息
            
        Returns:
            是否触发了压缩
        """
        self.messages.append(message)
        
        # 检查是否需要压缩
        current_tokens = self.estimate_tokens()
        if current_tokens > self.compact_threshold:
            return True
        
        return False
    
    def estimate_tokens(self, messages: Optional[List[Message]] = None) -> int:
        """
        估算 token 数
        
        简单估算:
        - 英文: 1 token ≈ 4 字符
        - 中文: 1 token ≈ 1-2 字符
        - 这里使用保守估算: 1 token ≈ 3 字符
        
        Args:
            messages: 要估算的消息列表，默认使用全部消息
            
        Returns:
            估算的 token 数
        """
        if messages is None:
            messages = self.messages
        
        total_chars = 0
        for msg in messages:
            if isinstance(msg, UserMessage):
                total_chars += len(msg.content)
            elif isinstance(msg, AssistantMessage):
                total_chars += len(msg.text)
            else:
                # 其他类型消息估算
                total_chars += 100  # 保守估算
        
        # 保守估算: 1 token ≈ 3 字符
        return int(total_chars / 3)
    
    async def compact(self) -> None:
        """
        压缩上下文
        
        策略:
        1. 保留系统提示词（如果有）
        2. 总结早期对话历史
        3. 保留最近 N 轮完整对话
        """
        if len(self.messages) < 10:
            # 消息太少，不压缩
            return
        
        # 保留最近的 6 轮对话（用户+助手 = 12 条消息）
        keep_recent = 12
        
        # 早期消息需要总结
        to_summarize = self.messages[:-keep_recent]
        recent_messages = self.messages[-keep_recent:]
        
        # 生成摘要（简化版）
        summary = self._generate_summary(to_summarize)
        
        # 重建消息列表
        self.messages = []
        
        # 添加摘要作为系统记忆
        if summary:
            self.messages.append(UserMessage(
                id="summary",
                content=f"[对话摘要] {summary}",
            ))
        
        # 添加近期完整对话
        self.messages.extend(recent_messages)
    
    def _generate_summary(self, messages: List[Message]) -> str:
        """
        生成对话摘要
        
        简化版：提取关键信息
        """
        # 提取关键信息
        key_points = []
        
        for msg in messages:
            if isinstance(msg, UserMessage):
                content = msg.content.strip()
                if content and not content.startswith("["):
                    # 提取前 50 个字符作为要点
                    key_points.append(content[:50] + "..." if len(content) > 50 else content)
        
        if not key_points:
            return ""
        
        # 合并要点（最多 3 个）
        return "; ".join(key_points[:3])
    
    def get_messages(self) -> List[Message]:
        """获取所有消息"""
        return self.messages.copy()
    
    def clear(self) -> None:
        """清空消息"""
        self.messages.clear()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "message_count": len(self.messages),
            "estimated_tokens": self.estimate_tokens(),
            "max_tokens": self.max_tokens,
            "threshold": self.compact_threshold,
            "usage_percent": int(self.estimate_tokens() / self.max_tokens * 100),
        }
