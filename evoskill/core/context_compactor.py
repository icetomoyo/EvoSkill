"""
上下文压缩器 - 基于 Pi Agent 设计

当对话接近上下文上限时，智能压缩历史消息，保留关键信息。
"""
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from evoskill.core.types import (
    Message, UserMessage, AssistantMessage, ToolResultMessage,
    ToolDefinition, LLMConfig
)
from evoskill.core.llm import LLMProvider


@dataclass
class CompactResult:
    """上下文压缩结果"""
    new_messages: List[Message]  # 压缩后的消息列表
    summary: str  # 生成的摘要
    original_token_count: int  # 原始 token 数
    new_token_count: int  # 压缩后 token 数
    compacted_count: int  # 压缩了多少轮对话
    saved_ratio: float  # 节省比例


@dataclass
class WarningResult:
    """警告结果"""
    should_warn: bool  # 是否应该警告
    current_ratio: float  # 当前比例
    warning_threshold: float  # 警告阈值
    message: str  # 警告信息


class ContextCompactor:
    """
    上下文压缩器
    
    设计：
    - 75% 阈值：警告用户即将压缩
    - 80% 阈值：自动执行压缩
    - 保留：系统提示 + 工具定义 + 最近 3 轮 + 摘要
    """
    
    # 阈值配置
    WARNING_RATIO = 0.75  # 警告阈值
    COMPACT_RATIO = 0.80  # 压缩阈值
    
    # 保留配置
    KEEP_RECENT_ROUNDS = 3  # 保留最近 N 轮完整对话
    SUMMARY_MAX_TOKENS = 1500  # 摘要最大长度（约 750 字）
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        max_context_tokens: int = 128000,
    ):
        self.llm = llm_provider
        self.max_tokens = max_context_tokens
        self.warning_threshold = int(max_context_tokens * self.WARNING_RATIO)
        self.compact_threshold = int(max_context_tokens * self.COMPACT_RATIO)
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数（近似）
        
        规则：
        - 中文字符：约 1.5 tokens/字
        - 英文单词：约 1.3 tokens/词
        - 简单近似：字符数 // 2
        """
        if not text:
            return 0
        
        # 简单估算：假设平均每个字符 0.5 token
        # 英文单词会被分词，中文单字基本就是 1 token 左右
        return len(text) // 2
    
    def estimate_message_tokens(self, message: Message) -> int:
        """估算单条消息的 token 数"""
        # 消息格式开销
        overhead = 4
        
        # 内容 token
        content_tokens = 0
        if isinstance(message, UserMessage):
            content_tokens = self.estimate_tokens(message.content)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, 'text'):
                    content_tokens += self.estimate_tokens(block.text)
                elif hasattr(block, 'name'):  # ToolCallContent
                    content_tokens += self.estimate_tokens(str(block.arguments))
        elif isinstance(message, ToolResultMessage):
            for block in message.content:
                if hasattr(block, 'text'):
                    content_tokens += self.estimate_tokens(block.text)
        
        return overhead + content_tokens
    
    def estimate_messages_tokens(self, messages: List[Message]) -> int:
        """估算消息列表的总 token 数"""
        return sum(self.estimate_message_tokens(m) for m in messages)
    
    def check_status(self, messages: List[Message]) -> Dict[str, Any]:
        """
        检查当前上下文状态
        
        Returns:
            {
                "current_tokens": int,
                "max_tokens": int,
                "current_ratio": float,
                "should_warn": bool,  # 是否达到警告阈值
                "should_compact": bool,  # 是否达到压缩阈值
            }
        """
        current_tokens = self.estimate_messages_tokens(messages)
        current_ratio = current_tokens / self.max_tokens
        
        return {
            "current_tokens": current_tokens,
            "max_tokens": self.max_tokens,
            "current_ratio": current_ratio,
            "warning_threshold": self.warning_threshold,
            "compact_threshold": self.compact_threshold,
            "should_warn": current_tokens >= self.warning_threshold,
            "should_compact": current_tokens >= self.compact_threshold,
        }
    
    def get_warning_message(self, status: Dict[str, Any]) -> str:
        """生成警告信息"""
        return (
            f"[System] 上下文即将达到上限 "
            f"({status['current_tokens']}/{self.max_tokens} tokens, "
            f"{status['current_ratio']*100:.1f}%)。\n"
            f"达到 {self.COMPACT_RATIO*100:.0f}% 时将自动压缩对话历史。"
        )
    
    def split_messages(
        self,
        messages: List[Message],
    ) -> tuple[List[Message], List[Message]]:
        """
        分割消息列表
        
        Returns:
            (历史消息, 最近消息)
            最近消息保留 KEEP_RECENT_ROUNDS 轮完整对话
        """
        if len(messages) <= self.KEEP_RECENT_ROUNDS * 2:
            # 消息太少，不分割
            return messages, []
        
        # 保留最近 N 轮（每轮 = 用户 + 助手）
        keep_count = self.KEEP_RECENT_ROUNDS * 2
        
        history = messages[:-keep_count]
        recent = messages[-keep_count:]
        
        return history, recent
    
    async def generate_summary(
        self,
        messages: List[Message],
    ) -> str:
        """
        使用 LLM 生成对话摘要
        
        要求：
        1. 保留用户的意图和请求
        2. 保留重要的文件操作
        3. 保留关键决策和结果
        4. 简洁明了
        """
        if not messages:
            return ""
        
        # 构建对话历史文本
        conversation_text = []
        for msg in messages:
            if isinstance(msg, UserMessage):
                conversation_text.append(f"User: {msg.content}")
            elif isinstance(msg, AssistantMessage):
                # 提取文本内容
                texts = []
                tool_calls = []
                for block in msg.content:
                    if hasattr(block, 'text'):
                        texts.append(block.text)
                    elif hasattr(block, 'name'):
                        tool_calls.append(f"[{block.name}]")
                
                content = " ".join(texts)
                if tool_calls:
                    content += f" (使用了工具: {', '.join(tool_calls)})"
                conversation_text.append(f"Assistant: {content}")
            elif isinstance(msg, ToolResultMessage):
                # 工具结果简化显示
                result_preview = str(msg.content)[:100]
                conversation_text.append(f"Tool({msg.tool_name}): {result_preview}...")
        
        conversation_history = "\n".join(conversation_text)
        
        # 构建摘要 prompt
        summary_prompt = f"""请总结以下对话历史的关键信息。

要求：
1. 用中文总结
2. 保留用户的意图和主要请求
3. 保留重要的文件操作（读取/修改了哪些文件）
4. 保留关键的决策和结果
5. 简洁明了，不超过 500 字
6. 使用第三人称描述

对话历史：
{conversation_history}

请生成摘要："""

        # 调用 LLM 生成摘要
        try:
            summary_messages = [UserMessage(content=summary_prompt)]
            
            summary_text = ""
            async for event in self.llm.chat(
                messages=summary_messages,
                stream=False,
                max_tokens=self.SUMMARY_MAX_TOKENS,
            ):
                if event.get("type") == "text_delta":
                    summary_text += event.get("content", "")
            
            # 清理摘要格式
            summary_text = summary_text.strip()
            if summary_text.startswith("摘要："):
                summary_text = summary_text[3:].strip()
            
            return summary_text
            
        except Exception as e:
            # 生成失败，返回简单统计
            return f"[对话历史包含 {len(messages)} 轮消息，涉及文件操作和代码编辑。由于技术原因无法生成详细摘要。]"
    
    async def compact(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> CompactResult:
        """
        执行上下文压缩
        
        步骤：
        1. 分割消息（历史 vs 最近）
        2. 为历史生成摘要
        3. 组装新的消息列表
        """
        original_tokens = self.estimate_messages_tokens(messages)
        
        # 分割消息
        history, recent = self.split_messages(messages)
        
        if not history:
            # 消息太少，无需压缩
            return CompactResult(
                new_messages=messages,
                summary="",
                original_token_count=original_tokens,
                new_token_count=original_tokens,
                compacted_count=0,
                saved_ratio=0.0,
            )
        
        # 生成摘要
        summary = await self.generate_summary(history)
        
        # 构建摘要消息 - 作为 UserMessage 插入到历史中
        # 这样 AI 会将其视为对话历史的一部分
        summary_content = f"""[上下文摘要]
之前的对话历史已压缩。以下是关键信息：

{summary}

---
以下是最近 {self.KEEP_RECENT_ROUNDS} 轮完整对话："""

        summary_message = UserMessage(
            id="context_summary",
            content=summary_content,
        )
        
        # 组装新消息列表
        new_messages = [summary_message] + recent
        
        new_tokens = self.estimate_messages_tokens(new_messages)
        
        saved_tokens = original_tokens - new_tokens
        saved_ratio = saved_tokens / original_tokens if original_tokens > 0 else 0
        
        return CompactResult(
            new_messages=new_messages,
            summary=summary,
            original_token_count=original_tokens,
            new_token_count=new_tokens,
            compacted_count=len(history),
            saved_ratio=saved_ratio,
        )
