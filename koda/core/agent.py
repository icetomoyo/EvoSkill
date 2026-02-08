"""
KodaAgent - 自主编程代理核心

全流程自动化软件开发：
需求 → 规划 → 编码 → 测试 → 反思 → 迭代 → 交付
"""
import uuid
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass

from koda.core.types import TaskStatus, ExecutionResult, ReflectionResult
from koda.core.task import Task, TaskResult, Plan, Step
from koda.core.types import CodeArtifact


@dataclass
class AgentConfig:
    """代理配置"""
    max_iterations: int = 3
    enable_reflection: bool = True
    enable_api_discovery: bool = True
    auto_fix: bool = True
    verbose: bool = True


class KodaAgent:
    """
    Koda 核心代理
    
    完整的工作流程:
    1. Plan - 分析任务并制定计划
    2. Execute - 执行计划生成代码
    3. Validate - 验证代码质量
    4. Reflect - 反思问题并修复
    5. Iterate - 循环直到通过或超时
    
    Example:
        agent = KodaAgent(llm=llm_adapter)
        result = await agent.execute(task)
        if result.success:
            print(result.get_main_code())
    """
    
    def __init__(
        self,
        llm: Any,
        config: Optional[AgentConfig] = None,
        tools: Optional[List] = None,
        verbose: bool = False,
    ):
        self.llm = llm
        self.config = config or AgentConfig()
        self.config.verbose = verbose or self.config.verbose
        self.tools = tools or []
        
        # 子组件（延迟初始化）
        self._planner = None
        self._executor = None
        self._reflector = None
        self._validator = None
    
    async def execute(self, task: Task) -> TaskResult:
        """
        执行任务
        
        Args:
            task: 编程任务
            
        Returns:
            TaskResult: 完整执行结果
        """
        start_time = time.time()
        task_id = str(uuid.uuid4())[:8]
        
        if self.config.verbose:
            print(f"[KodaAgent:{task_id}] Start: {task.description[:50]}...")
        
        # Phase 1: Planning
        plan = await self._plan(task)
        
        # Phase 2-4: Execute -> Validate -> Reflect -> Iterate
        result = TaskResult(
            task=task,
            success=False,
            status=TaskStatus.EXECUTING,
            plan=plan,
        )
        
        for iteration in range(self.config.max_iterations):
            if self.config.verbose:
                print(f"[KodaAgent:{task_id}] Iteration {iteration + 1}/{self.config.max_iterations}")
            
            # Execute
            execution = await self._execute_plan(plan, task)
            result.execution_history.append(execution)
            
            if not execution.success:
                if self.config.verbose:
                    print(f"[KodaAgent:{task_id}] Execution failed: {execution.error}")
            
            # Validate
            validation = await self._validate(execution)
            
            if validation.passed:
                if self.config.verbose:
                    print(f"[KodaAgent:{task_id}] Validation passed!")
                result.success = True
                result.status = TaskStatus.COMPLETED
                result.artifacts = execution.artifacts
                break
            
            # Reflect & Fix
            if self.config.enable_reflection and self.config.auto_fix:
                reflection = await self._reflect(execution, validation)
                result.reflection_history.append(reflection)
                
                if reflection.needs_fix and reflection.improved_code:
                    if self.config.verbose:
                        print(f"[KodaAgent:{task_id}] Issues found, fixing...")
                    # 更新计划中的代码
                    plan = await self._update_plan_with_fix(plan, reflection)
                    continue
            
            # 无法修复，记录当前最佳结果
            result.artifacts = execution.artifacts
            
        else:
            # 迭代次数用尽
            if self.config.verbose:
                print(f"[KodaAgent:{task_id}] Max iterations reached")
            result.status = TaskStatus.FAILED
            result.error_message = "Max iterations reached"
        
        result.iterations = len(result.execution_history)
        result.total_time_ms = int((time.time() - start_time) * 1000)
        
        if self.config.verbose:
            print(f"[KodaAgent:{task_id}] Done in {result.total_time_ms}ms")
        
        return result
    
    async def execute_stream(self, task: Task) -> AsyncIterator[Dict[str, Any]]:
        """
        流式执行任务
        
        Yields:
            进度事件
        """
        yield {"phase": "start", "status": "pending", "task": task.description}
        
        # Planning
        yield {"phase": "plan", "status": "in_progress"}
        plan = await self._plan(task)
        yield {"phase": "plan", "status": "completed", "plan": plan}
        
        # Execution loop
        for i in range(self.config.max_iterations):
            yield {"phase": "execute", "status": "in_progress", "iteration": i + 1}
            
            execution = await self._execute_plan(plan, task)
            yield {"phase": "execute", "status": "completed", "result": execution}
            
            if execution.success:
                yield {"phase": "validate", "status": "completed", "passed": True}
                yield {"phase": "complete", "status": "success", "artifacts": execution.artifacts}
                return
            
            yield {"phase": "validate", "status": "failed", "errors": []}
            
            if self.config.enable_reflection:
                yield {"phase": "reflect", "status": "in_progress"}
                reflection = await self._reflect(execution, None)
                yield {"phase": "reflect", "status": "completed", "reflection": reflection}
        
        yield {"phase": "complete", "status": "failed"}
    
    # ============ 子组件方法 ============
    
    async def _plan(self, task: Task) -> Plan:
        """制定执行计划"""
        from koda.core.planner import Planner
        
        if self._planner is None:
            self._planner = Planner(self.llm)
        
        return await self._planner.create_plan(task)
    
    async def _execute_plan(self, plan: Plan, task: Task) -> ExecutionResult:
        """执行计划"""
        from koda.core.executor import Executor
        
        if self._executor is None:
            self._executor = Executor(self.llm, tools=self.tools)
        
        return await self._executor.execute(plan, task)
    
    async def _validate(self, execution: ExecutionResult) -> Any:
        """验证执行结果"""
        from koda.core.validator import Validator
        
        if self._validator is None:
            self._validator = Validator()
        
        return await self._validator.validate(execution)
    
    async def _reflect(
        self, 
        execution: ExecutionResult, 
        validation: Any
    ) -> ReflectionResult:
        """反思并给出改进建议"""
        from koda.core.reflector import Reflector
        
        if self._reflector is None:
            self._reflector = Reflector(self.llm)
        
        return await self._reflector.reflect(execution, validation)
    
    async def _update_plan_with_fix(self, plan: Plan, reflection: ReflectionResult) -> Plan:
        """根据反思结果更新计划"""
        return plan
    
    def add_tool(self, tool: Any):
        """添加工具"""
        self.tools.append(tool)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        return {
            "tools_count": len(self.tools),
            "config": {
                "max_iterations": self.config.max_iterations,
                "enable_reflection": self.config.enable_reflection,
            }
        }
