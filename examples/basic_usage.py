"""
EvoSkill 基础使用示例

展示如何使用 EvoSkill SDK 进行对话。
"""

import asyncio
import os
from pathlib import Path

from evoskill.core.session import AgentSession
from evoskill.core.llm import LLMConfig
from evoskill.core.types import EventType
from evoskill.skills.builtin import register_builtin_tools


async def main():
    """主函数"""
    
    # 配置
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return
    
    # 创建 LLM 配置
    llm_config = LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key=api_key,
    )
    
    # 创建会话
    session = AgentSession(
        workspace=Path.cwd(),
        llm_config=llm_config,
    )
    
    # 注册内置工具
    register_builtin_tools(session)
    
    print("=" * 50)
    print("EvoSkill 基础示例")
    print("=" * 50)
    print()
    
    # 示例 1: 简单对话
    print("示例 1: 简单对话")
    print("-" * 50)
    
    user_input = "你好，请介绍一下你自己"
    print(f"用户: {user_input}")
    print("助手: ", end="", flush=True)
    
    async for event in session.prompt(user_input):
        if event.type == EventType.TEXT_DELTA:
            print(event.data.get("content", ""), end="", flush=True)
    
    print()
    print()
    
    # 示例 2: 使用工具
    print("示例 2: 使用工具")
    print("-" * 50)
    
    # 先创建一个测试文件
    test_file = Path("test_file.txt")
    test_file.write_text("Hello, EvoSkill!")
    
    user_input = f"请读取文件 {test_file} 的内容"
    print(f"用户: {user_input}")
    print("助手: ", end="", flush=True)
    
    async for event in session.prompt(user_input):
        if event.type == EventType.TEXT_DELTA:
            print(event.data.get("content", ""), end="", flush=True)
        elif event.type == EventType.TOOL_EXECUTION_START:
            print(f"\n[使用工具: {event.data.get('tool_name')}]")
    
    print()
    print()
    
    # 清理
    test_file.unlink(missing_ok=True)
    
    # 示例 3: 列出目录
    print("示例 3: 文件系统操作")
    print("-" * 50)
    
    user_input = "列出当前目录的内容"
    print(f"用户: {user_input}")
    print("助手: ", end="", flush=True)
    
    async for event in session.prompt(user_input):
        if event.type == EventType.TEXT_DELTA:
            content = event.data.get("content", "")
            print(content, end="", flush=True)
    
    print()
    print()
    
    print("=" * 50)
    print("示例结束")
    print("=" * 50)
    
    # 保存会话
    session_path = await session.save()
    print(f"会话已保存到: {session_path}")


if __name__ == "__main__":
    asyncio.run(main())
