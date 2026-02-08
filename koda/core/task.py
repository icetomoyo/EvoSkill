"""
任务定义 - Task 是 Koda 的核心工作单元
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path

from koda.core.types import (
    TaskStatus,
    CodeArtifact,
    ExecutionResult,
    ReflectionResult,
    APIDiscovery,
)


@dataclass
class Task:
    """
    任务定义
    
    描述需要完成的编程任务
    """
    description: str
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    language: str = "python"
    max_iterations: int = 3
    timeout_seconds: int = 120
    
    def to_prompt(self) -> str:
        """转换为 LLM Prompt"""
        lines = [
            f"Task: {self.description}",
            "",
            "Requirements:",
        ]
        for i, req in enumerate(self.requirements, 1):
            lines.append(f"{i}. {req}")
        
        if self.constraints:
            lines.extend(["", "Constraints:"])
            for i, cons in enumerate(self.constraints, 1):
                lines.append(f"{i}. {cons}")
        
        return "\n".join(lines)


@dataclass
class Step:
    """
    执行步骤
    """
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[ExecutionResult] = None
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """
    执行计划
    """
    task_id: str
    analysis: str
    approach: str
    steps: List[Step] = field(default_factory=list)
    apis: List[APIDiscovery] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_time: int = 0
    
    def get_next_step(self) -> Optional[Step]:
        """获取下一个待执行的步骤"""
        for step in self.steps:
            if step.status == TaskStatus.PENDING:
                deps_completed = all(
                    any(s.id == dep and s.status == TaskStatus.COMPLETED 
                        for s in self.steps)
                    for dep in step.depends_on
                )
                if deps_completed:
                    return step
        return None
    
    def is_complete(self) -> bool:
        """检查是否所有步骤都完成"""
        return all(
            step.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            for step in self.steps
        )


@dataclass
class TaskResult:
    """
    任务结果
    """
    task: Task
    success: bool
    status: TaskStatus
    
    artifacts: List[CodeArtifact] = field(default_factory=list)
    plan: Optional[Plan] = None
    
    iterations: int = 0
    execution_history: List[ExecutionResult] = field(default_factory=list)
    reflection_history: List[ReflectionResult] = field(default_factory=list)
    
    total_time_ms: int = 0
    tokens_used: int = 0
    
    error_message: str = ""
    
    def get_main_code(self) -> Optional[str]:
        """获取主代码文件内容"""
        for artifact in self.artifacts:
            if artifact.filename in ["main.py", "index.py", "app.py"]:
                return artifact.content
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "status": self.status.value,
            "iterations": self.iterations,
            "total_time_ms": self.total_time_ms,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "error_message": self.error_message,
        }
