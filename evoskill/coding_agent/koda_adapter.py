"""
Koda 适配器 - 将 Koda 框架集成到 EvoSkill
"""
from typing import Any, Optional, List, Dict

from koda.core.agent import KodaAgent, AgentConfig
from koda.core.task import Task, TaskResult
from koda.adapters.base import BaseLLMAdapter

from evoskill.core.llm import LLMProvider
from evoskill.evolution.designer import SkillDesign


class EvoSkillLLMAdapter(BaseLLMAdapter):
    """
    EvoSkill LLM 适配器
    
    将 EvoSkill 的 LLMProvider 适配为 Koda 的接口
    """
    
    def __init__(self, llm_provider: LLMProvider):
        super().__init__()
        self.llm = llm_provider
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """调用 EvoSkill LLM"""
        messages = [{"role": "user", "content": prompt}]
        
        # 收集流式响应
        response_parts = []
        async for event in self.llm.complete_stream(messages, **kwargs):
            if hasattr(event, 'data'):
                content = event.data.get("content", "")
                response_parts.append(content)
        
        return "".join(response_parts)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话模式"""
        response_parts = []
        async for event in self.llm.complete_stream(messages, **kwargs):
            if hasattr(event, 'data'):
                content = event.data.get("content", "")
                response_parts.append(content)
        
        return "".join(response_parts)


class KodaAdapter:
    """
    Koda 适配器
    
    将 Koda 框架集成到 EvoSkill 的代码生成流程。
    
    Example:
        adapter = PiCodingAdapter(llm_provider)
        result = await adapter.develop_skill(skill_design)
        
        # 获取生成的文件
        main_py = result.get_main_code()
        skill_md = result.get_doc()
    """
    
    def __init__(
        self, 
        llm_provider: LLMProvider,
        max_iterations: int = 3,
        verbose: bool = True,
    ):
        # 创建 LLM 适配器
        llm_adapter = EvoSkillLLMAdapter(llm_provider)
        
        # 配置
        config = AgentConfig(
            max_iterations=max_iterations,
            enable_reflection=True,
            enable_api_discovery=True,
            verbose=verbose,
        )
        
        # 创建 KodaAgent
        self.agent = KodaAgent(llm=llm_adapter, config=config)
    
    async def develop_skill(self, design: SkillDesign) -> TaskResult:
        """
        开发 Skill
        
        Args:
            design: Skill 设计
            
        Returns:
            TaskResult: 开发结果
        """
        # 转换为 Koda Task
        task = self._design_to_task(design)
        
        # 执行开发
        result = await self.agent.execute(task)
        
        return result
    
    def _design_to_task(self, design: SkillDesign) -> Task:
        """将 SkillDesign 转换为 Task"""
        # 构建需求列表
        requirements = []
        
        for tool in design.tools:
            req = f"实现 {tool.name}: {tool.description}"
            if tool.parameters:
                params = ", ".join([f"{n}({p.type})" for n, p in tool.parameters.items()])
                req += f"，参数: {params}"
            requirements.append(req)
        
        # 添加通用要求
        requirements.extend([
            "使用 Python 标准库优先",
            "完整的错误处理",
            "清晰的 API 配置指南（如需要）",
        ])
        
        return Task(
            description=design.description,
            requirements=requirements,
            constraints=[
                f"语言: Python",
                f"Skill 名称: {design.name}",
            ],
            context={
                "skill_name": design.name,
                "version": design.version,
                "author": design.author,
            },
            max_iterations=3,
        )
