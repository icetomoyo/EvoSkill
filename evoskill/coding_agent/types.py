"""
Coding Agent 类型定义
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class CodingResult:
    """代码生成结果"""
    success: bool
    skill_name: str
    files: Dict[str, str]  # 文件名 -> 内容
    main_py: str
    skill_md: str
    test_py: str
    iterations: int = 0
    test_passed: bool = False
    error_message: str = ""
    api_recommendations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ImplementationPlan:
    """实现计划"""
    analysis: str
    approach: str
    apis: List[Dict[str, Any]]
    dependencies: List[str]
    steps: List[str]
    risks: List[str]
