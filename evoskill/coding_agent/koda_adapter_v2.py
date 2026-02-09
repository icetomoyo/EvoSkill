"""
Koda Adapter V2 - 集成 Koda Agent V2 到 EvoSkill

支持:
1. 直接调用 Koda Agent 执行任务
2. Skill 热加载/卸载
3. 进化引擎集成
"""
import asyncio
from pathlib import Path
from typing import Any, Optional, List, Dict, AsyncIterator
from dataclasses import dataclass

from evoskill.core.llm import LLMProvider
from evoskill.core.types import Message, ToolResult, Event, EventType

# Koda 导入
from koda.core.agent_v2 import AgentV2
from koda.core.types import ExecutionResult


@dataclass
class KodaExecutionResult:
    """Koda 执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = None
    tool_calls: List[Dict[str, Any]] = None


class EvoSkillLLMWrapper:
    """
    将 EvoSkill 的 LLMProvider 包装为 Koda 可用的 LLM
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """完成提示词"""
        messages = [{"role": "user", "content": prompt}]
        
        # 收集流式响应
        response_parts = []
        try:
            async for chunk in self.llm.chat(messages, stream=True):
                if isinstance(chunk, dict):
                    content = chunk.get("content", "")
                    if content:
                        response_parts.append(content)
                elif isinstance(chunk, str):
                    response_parts.append(chunk)
        except Exception as e:
            # 如果流式失败，尝试非流式
            response = await self.llm.chat(messages, stream=False)
            if isinstance(response, dict):
                return response.get("content", str(response))
            return str(response)
        
        return "".join(response_parts)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话模式"""
        response_parts = []
        try:
            async for chunk in self.llm.chat(messages, stream=True):
                if isinstance(chunk, dict):
                    content = chunk.get("content", "")
                    if content:
                        response_parts.append(content)
                elif isinstance(chunk, str):
                    response_parts.append(chunk)
        except Exception:
            response = await self.llm.chat(messages, stream=False)
            if isinstance(response, dict):
                return response.get("content", str(response))
            return str(response)
        
        return "".join(response_parts)


class KodaAdapterV2:
    """
    Koda V2 适配器
    
    集成 Koda Agent V2 到 EvoSkill 会话系统
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        workspace: Optional[Path] = None,
        verbose: bool = True,
    ):
        self.workspace = workspace or Path.cwd()
        self.verbose = verbose
        
        # 包装 LLM
        llm_wrapper = EvoSkillLLMWrapper(llm_provider)
        
        # 创建 Koda Agent V2
        self.agent = AgentV2(
            llm=llm_wrapper,
            workspace=self.workspace,
            verbose=verbose,
        )
        
        # 执行历史
        self.execution_history: List[KodaExecutionResult] = []
    
    async def execute(
        self,
        task: str,
        context: Optional[List[Message]] = None,
    ) -> KodaExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务描述
            context: 上下文消息（可选）
            
        Returns:
            KodaExecutionResult: 执行结果
        """
        if self.verbose:
            print(f"[KodaAdapter] Executing task: {task[:100]}...")
        
        try:
            # 构建完整提示（包含上下文）
            full_task = self._build_task_with_context(task, context)
            
            # 执行
            result = await self.agent.execute(full_task)
            
            # 转换结果
            execution_result = KodaExecutionResult(
                success=result.success,
                output=result.output or "",
                error=result.error,
                artifacts=[
                    {"filename": a.filename, "content": a.content[:500]}
                    for a in result.artifacts
                ] if result.artifacts else [],
            )
            
            self.execution_history.append(execution_result)
            return execution_result
            
        except Exception as e:
            error_result = KodaExecutionResult(
                success=False,
                output="",
                error=str(e),
            )
            self.execution_history.append(error_result)
            return error_result
    
    def _build_task_with_context(
        self,
        task: str,
        context: Optional[List[Message]] = None,
    ) -> str:
        """构建带上下文的任务"""
        if not context:
            return task
        
        # 提取上下文中的关键信息
        context_parts = []
        for msg in context[-5:]:  # 最近 5 条消息
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                context_parts.append(f"{msg.role}: {msg.content[:200]}")
        
        if context_parts:
            context_str = "\n".join(context_parts)
            return f"Context:\n{context_str}\n\nTask: {task}"
        
        return task
    
    async def execute_with_stream(
        self,
        task: str,
        context: Optional[List[Message]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式执行任务
        
        Yields:
            Dict with keys: type, data
        """
        yield {"type": "start", "data": {"task": task}}
        
        try:
            result = await self.execute(task, context)
            
            yield {
                "type": "progress",
                "data": {"step": "executing", "status": "running"}
            }
            
            if result.success:
                yield {
                    "type": "complete",
                    "data": {
                        "success": True,
                        "output": result.output,
                        "artifacts": result.artifacts,
                    }
                }
            else:
                yield {
                    "type": "error",
                    "data": {
                        "error": result.error,
                    }
                }
                
        except Exception as e:
            yield {"type": "error", "data": {"error": str(e)}}
    
    def get_execution_history(self) -> List[KodaExecutionResult]:
        """获取执行历史"""
        return self.execution_history.copy()
    
    def clear_history(self) -> None:
        """清除执行历史"""
        self.execution_history.clear()


class SkillRegistry:
    """
    Skill 注册表
    
    管理 EvoSkill 与 Koda 的 Skill 映射
    """
    
    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._koda_tools: Dict[str, Any] = {}
    
    def register_skill(self, name: str, skill_data: Dict[str, Any]) -> None:
        """注册 Skill"""
        self._skills[name] = skill_data
        
    def unregister_skill(self, name: str) -> bool:
        """卸载 Skill"""
        if name in self._skills:
            del self._skills[name]
            return True
        return False
    
    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """获取 Skill"""
        return self._skills.get(name)
    
    def list_skills(self) -> List[str]:
        """列出所有 Skill 名称"""
        return list(self._skills.keys())
    
    def register_koda_tool(self, name: str, tool: Any) -> None:
        """注册 Koda 工具"""
        self._koda_tools[name] = tool
    
    def get_koda_tool(self, name: str) -> Optional[Any]:
        """获取 Koda 工具"""
        return self._koda_tools.get(name)


# 全局注册表
skill_registry = SkillRegistry()
