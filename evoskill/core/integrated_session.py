"""
Integrated Session - EvoSkill Core + Koda 集成会话

支持:
- 使用 Koda 工具执行代码任务
- Skill 查询、创建、使用、进化
- 流式事件输出
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from evoskill.core.types import (
    Message, UserMessage, AssistantMessage, ToolResultMessage,
    Event, EventType, Skill, ToolDefinition, SessionMetadata, LLMConfig,
)
from evoskill.core.session import AgentSession
from evoskill.core.llm import LLMProvider
from evoskill.coding_agent.koda_adapter_v2 import KodaAdapterV2, skill_registry
from evoskill.skills.loader import SkillLoader


class IntegratedSession(AgentSession):
    """
    集成会话
    
    扩展 AgentSession，添加 Koda 集成能力
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        workspace: Optional[Path] = None,
        llm_config: Optional[LLMConfig] = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(session_id, workspace, llm_config, system_prompt)
        
        # Koda 适配器
        self._koda_adapter: Optional[KodaAdapterV2] = None
        
        # Skill 加载器
        self._skill_loader = SkillLoader()
        
        # 注册 Koda 工具为 Skills
        self._register_koda_tools()
    
    @property
    def koda_adapter(self) -> KodaAdapterV2:
        """获取或创建 Koda 适配器"""
        if self._koda_adapter is None:
            self._koda_adapter = KodaAdapterV2(
                llm_provider=self.llm_provider,
                workspace=self.workspace,
                verbose=False,
            )
        return self._koda_adapter
    
    def _register_koda_tools(self) -> None:
        """将 Koda 工具注册为 EvoSkill Skills"""
        # Koda 核心工具
        koda_tools = [
            ("read_file", "读取文件内容", ["file_path"]),
            ("write_file", "写入文件", ["file_path", "content"]),
            ("edit_file", "编辑文件", ["file_path", "old_string", "new_string"]),
            ("bash", "执行命令", ["command"]),
            ("grep", "文本搜索", ["pattern", "path"]),
            ("find", "文件查找", ["path"]),
            ("ls", "目录列表", ["path"]),
        ]
        
        for name, description, params in koda_tools:
            tool_def = ToolDefinition(
                name=name,
                description=description,
                parameters={p: {"type": "string"} for p in params},
            )
            self._tools[name] = tool_def
    
    async def prompt(self, user_input: str) -> AsyncIterator[Event]:
        """
        处理用户输入
        
        支持:
        - 普通对话
        - 工具调用
        - Skill 查询/创建/进化
        """
        # 添加用户消息
        user_msg = UserMessage(
            id=str(uuid.uuid4()),
            role="user",
            timestamp=datetime.now(),
            content=user_input,
        )
        self.messages.append(user_msg)
        
        # 检查是否是特殊命令
        if user_input.startswith("/"):
            async for event in self._handle_command(user_input):
                yield event
            return
        
        # 检查是否涉及代码/文件操作（使用 Koda）
        if self._should_use_koda(user_input):
            async for event in self._handle_with_koda(user_input):
                yield event
            return
        
        # 普通对话
        async for event in self._handle_normal_chat(user_input):
            yield event
    
    async def _handle_command(self, command: str) -> AsyncIterator[Event]:
        """处理命令"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "/skills" or cmd == "/list":
            # 列出所有 Skills
            skills = self._list_available_skills()
            yield Event(
                type=EventType.MESSAGE_END,
                data={"content": f"可用 Skills:\n{skills}"},
            )
            
        elif cmd == "/create":
            # 创建新 Skill
            if args:
                description = " ".join(args)
                async for event in self._create_skill(description):
                    yield event
            else:
                yield Event(
                    type=EventType.MESSAGE_END,
                    data={"content": "用法: /create <skill 描述>"},
                )
                
        elif cmd == "/evolve":
            # 进化现有 Skill
            if args:
                skill_name = args[0]
                request = " ".join(args[1:]) if len(args) > 1 else ""
                async for event in self._evolve_skill(skill_name, request):
                    yield event
            else:
                yield Event(
                    type=EventType.MESSAGE_END,
                    data={"content": "用法: /evolve <skill_name> <改进描述>"},
                )
        else:
            yield Event(
                type=EventType.MESSAGE_END,
                data={"content": f"未知命令: {cmd}\n可用命令: /skills, /create, /evolve"},
            )
    
    async def _handle_with_koda(self, user_input: str) -> AsyncIterator[Event]:
        """使用 Koda 处理任务"""
        yield Event(
            type=EventType.TOOL_EXECUTION_START,
            data={"tool": "koda_agent", "task": user_input},
        )
        
        # 调用 Koda
        result = await self.koda_adapter.execute(
            task=user_input,
            context=self.messages[-5:],  # 最近 5 条上下文
        )
        
        if result.success:
            yield Event(
                type=EventType.TOOL_EXECUTION_END,
                data={
                    "tool": "koda_agent",
                    "result": result.output,
                    "artifacts": result.artifacts,
                },
            )
            
            # 添加助手消息
            assistant_msg = AssistantMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                timestamp=datetime.now(),
                content=[{"type": "text", "text": result.output}],
                model=self.llm_config.model if self.llm_config else "unknown",
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
            )
            self.messages.append(assistant_msg)
            
            yield Event(
                type=EventType.MESSAGE_END,
                data={"content": result.output},
            )
        else:
            yield Event(
                type=EventType.TOOL_EXECUTION_END,
                data={
                    "tool": "koda_agent",
                    "error": result.error,
                },
            )
            yield Event(
                type=EventType.MESSAGE_END,
                data={"content": f"执行出错: {result.error}"},
            )
    
    async def _handle_normal_chat(self, user_input: str) -> AsyncIterator[Event]:
        """普通对话处理"""
        # 构建消息
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self.messages[-10:]:  # 最近 10 条
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                content = msg.content
                if isinstance(content, list):
                    content = content[0].get("text", "") if content else ""
                messages.append({"role": msg.role, "content": str(content)})
        
        yield Event(type=EventType.MESSAGE_START, data={})
        
        # 调用 LLM
        response_text = ""
        async for chunk in self.llm_provider.chat(messages, stream=True):
            if isinstance(chunk, dict):
                content = chunk.get("content", "")
            else:
                content = str(chunk)
            
            if content:
                response_text += content
                yield Event(
                    type=EventType.MESSAGE_UPDATE,
                    data={"content": content},
                )
        
        # 添加助手消息
        assistant_msg = AssistantMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            timestamp=datetime.now(),
            content=[{"type": "text", "text": response_text}],
            model=self.llm_config.model if self.llm_config else "unknown",
            usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
        )
        self.messages.append(assistant_msg)
        
        yield Event(type=EventType.MESSAGE_END, data={"content": response_text})
    
    def _should_use_koda(self, user_input: str) -> bool:
        """判断是否应使用 Koda"""
        koda_keywords = [
            "读", "写", "编辑", "修改", "创建文件", "删除",
            "read", "write", "edit", "create file", "delete",
            "执行", "运行", "bash", "command", "terminal",
            "搜索", "查找", "search", "find", "grep",
            "代码", "code", "file", "文件", "目录", "folder",
        ]
        user_lower = user_input.lower()
        return any(kw in user_lower for kw in koda_keywords)
    
    def _list_available_skills(self) -> str:
        """列出可用 Skills"""
        skills = []
        
        # EvoSkill 内置 Skills
        for name, tool in self._tools.items():
            skills.append(f"  - {name}: {tool.description}")
        
        # 已注册的 Skills
        registered = skill_registry.list_skills()
        for name in registered:
            skill_data = skill_registry.get_skill(name)
            desc = skill_data.get("description", "No description") if skill_data else "No description"
            skills.append(f"  - {name}: {desc}")
        
        if not skills:
            return "  (暂无可用 Skills)"
        
        return "\n".join(skills)
    
    async def _create_skill(self, description: str) -> AsyncIterator[Event]:
        """创建新 Skill"""
        yield Event(
            type=EventType.SKILL_CREATED,
            data={"status": "started", "description": description},
        )
        
        # 使用 Koda 生成 Skill
        task = f"""Create a new skill with the following description:
{description}

Requirements:
1. Create a SKILL.md file describing the skill
2. Create a main.py file with the implementation
3. Create a tests/test_main.py file with tests
4. All files should be in skills/<skill_name>/ directory
5. Use proper error handling and documentation
"""
        
        result = await self.koda_adapter.execute(task)
        
        if result.success:
            # 解析生成的 Skill 名称
            skill_name = self._extract_skill_name(result.output)
            
            # 注册 Skill
            skill_registry.register_skill(skill_name, {
                "description": description,
                "output": result.output,
                "artifacts": result.artifacts,
            })
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "status": "completed",
                    "skill_name": skill_name,
                    "output": result.output,
                },
            )
        else:
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "status": "failed",
                    "error": result.error,
                },
            )
    
    async def _evolve_skill(self, skill_name: str, request: str) -> AsyncIterator[Event]:
        """进化现有 Skill"""
        yield Event(
            type=EventType.SKILL_UPDATED,
            data={"status": "started", "skill_name": skill_name},
        )
        
        # 获取现有 Skill
        skill_data = skill_registry.get_skill(skill_name)
        if not skill_data:
            yield Event(
                type=EventType.SKILL_UPDATED,
                data={"status": "failed", "error": f"Skill '{skill_name}' not found"},
            )
            return
        
        # 生成改进任务
        task = f"""Evolve the skill '{skill_name}' with the following request:
{request}

Current skill info:
{skill_data.get('description', 'No description')}

Requirements:
1. Modify the existing skill to add the requested functionality
2. Update SKILL.md if needed
3. Update main.py with new implementation
4. Update tests
5. Maintain backward compatibility if possible
"""
        
        result = await self.koda_adapter.execute(task)
        
        if result.success:
            yield Event(
                type=EventType.SKILL_UPDATED,
                data={
                    "status": "completed",
                    "skill_name": skill_name,
                    "output": result.output,
                },
            )
        else:
            yield Event(
                type=EventType.SKILL_UPDATED,
                data={
                    "status": "failed",
                    "error": result.error,
                },
            )
    
    def _extract_skill_name(self, output: str) -> str:
        """从输出中提取 Skill 名称"""
        # 简单提取，实际可以用更复杂的方法
        import re
        match = re.search(r'skills/(\w+)', output)
        if match:
            return match.group(1)
        return "unnamed_skill"


async def demo():
    """演示集成会话"""
    from evoskill.core.types import LLMConfig
    
    # 创建会话
    session = IntegratedSession(
        workspace=Path.cwd(),
        llm_config=LLMConfig(provider="openai", model="gpt-4"),
    )
    
    print("Integrated Session Demo")
    print("=" * 50)
    
    # 演示 1: 查询 Skills
    print("\n1. Query Skills:")
    async for event in session.prompt("/skills"):
        if event.type == EventType.MESSAGE_END:
            print(event.data.get("content"))
    
    print("\n2. Create a time tool skill:")
    # 这里只是示例，实际会调用 Koda 生成代码
    
    print("\nDemo completed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
