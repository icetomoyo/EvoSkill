"""
Plan 模块 - 执行计划定义
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Step:
    """执行步骤"""
    id: str
    description: str
    status: str = "pending"
    result: Optional[Any] = None
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """执行计划"""
    task_id: str
    analysis: str
    approach: str
    steps: List[Step] = field(default_factory=list)
    apis: List[Any] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_time: int = 0
    
    def get_next_step(self) -> Optional[Step]:
        """获取下一个待执行步骤"""
        for step in self.steps:
            if step.status == "pending":
                deps_completed = all(
                    any(s.id == dep and s.status == "completed" for s in self.steps)
                    for dep in step.depends_on
                )
                if deps_completed:
                    return step
        return None
    
    def is_complete(self) -> bool:
        """检查是否完成"""
        return all(s.status in ["completed", "failed"] for s in self.steps)
