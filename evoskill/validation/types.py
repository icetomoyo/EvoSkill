"""
验证系统类型定义
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class CodeArtifact:
    """代码产物"""
    filename: str
    content: str


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    artifacts: List[CodeArtifact] = None
    output: str = ""
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


@dataclass
class ValidationReport:
    """验证报告"""
    passed: bool
    score: float = 0.0
    checks: List[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.checks is None:
            self.checks = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ReflectionResult:
    """反思结果"""
    has_issues: bool
    issues: List[str] = None
    suggestions: List[str] = None
    confidence: float = 0.0
    improved_code: Optional[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.suggestions is None:
            self.suggestions = []
