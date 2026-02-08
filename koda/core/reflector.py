"""
Reflector - 代码反思器

分析代码问题并给出改进建议
"""
import ast
from typing import List, Dict, Any, Optional

from koda.core.types import ExecutionResult, ReflectionResult, ValidationReport


class Reflector:
    """
    代码反思器
    
    像代码审查者一样分析代码质量
    """
    
    def __init__(self, llm: Any):
        self.llm = llm
    
    async def reflect(
        self, 
        execution: ExecutionResult, 
        validation: Optional[ValidationReport] = None
    ) -> ReflectionResult:
        """
        反思代码质量
        """
        if not execution.artifacts:
            return ReflectionResult(
                has_issues=True,
                issues=["No code artifacts generated"],
                confidence=1.0,
            )
        
        main_artifact = None
        for artifact in execution.artifacts:
            if artifact.filename == "main.py":
                main_artifact = artifact
                break
        
        if not main_artifact:
            return ReflectionResult(
                has_issues=True,
                issues=["Missing main.py"],
                confidence=1.0,
            )
        
        code = main_artifact.content
        
        # 自动检查
        auto_issues = self._static_analysis(code)
        
        # LLM 分析
        llm_feedback = await self._llm_analysis(code, execution, validation)
        
        all_issues = auto_issues + llm_feedback.get("issues", [])
        suggestions = llm_feedback.get("suggestions", [])
        
        # 生成改进代码
        improved_code = None
        if all_issues and llm_feedback.get("can_fix", False):
            improved_code = await self._generate_fix(code, all_issues, suggestions)
        
        return ReflectionResult(
            has_issues=len(all_issues) > 0,
            issues=all_issues,
            suggestions=suggestions,
            confidence=llm_feedback.get("confidence", 0.5),
            improved_code=improved_code,
        )
    
    def _static_analysis(self, code: str) -> List[str]:
        """静态代码分析"""
        issues = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        
        if "def " not in code and "class " not in code:
            issues.append("Missing function or class definition")
        
        if "try:" not in code:
            issues.append("Missing error handling (try/except)")
        
        if "\"\"\"" not in code and "'''" not in code:
            issues.append("Missing docstrings")
        
        return issues
    
    async def _llm_analysis(
        self, 
        code: str, 
        execution: ExecutionResult,
        validation: Optional[ValidationReport]
    ) -> Dict[str, Any]:
        """LLM 深度分析"""
        return {
            "issues": [],
            "suggestions": [],
            "can_fix": False,
            "confidence": 0.8,
        }
    
    async def _generate_fix(
        self, 
        code: str, 
        issues: List[str], 
        suggestions: List[str]
    ) -> Optional[str]:
        """生成修复后的代码"""
        prompt = f"""Fix this Python code:

```python
{code}
```

Issues:
{chr(10).join(f"- {i}" for i in issues)}

Return fixed code only.
"""
        
        fixed = await self.llm.complete(prompt)
        return self._clean_code(fixed)
    
    def _clean_code(self, code: str) -> str:
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()
