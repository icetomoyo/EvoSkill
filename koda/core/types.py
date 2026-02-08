"""
Koda 类型定义
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CodeArtifact:
    """代码产物"""
    filename: str
    content: str
    language: str = "python"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "content": self.content,
            "language": self.language,
            "description": self.description,
        }


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    artifacts: List[CodeArtifact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionResult:
    """反思结果"""
    has_issues: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    improved_code: Optional[str] = None
    
    @property
    def needs_fix(self) -> bool:
        return self.has_issues and len(self.issues) > 0


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    required_permissions: List[str] = field(default_factory=list)


@dataclass
class APIDiscovery:
    """API 发现信息"""
    name: str
    provider: str
    description: str
    signup_url: str
    free_quota: str
    env_var: str
    auth_type: str = "api_key"
    docs_url: str = ""
    features: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """验证报告"""
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0
