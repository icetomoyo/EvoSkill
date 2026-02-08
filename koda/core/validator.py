"""
Validator - 代码验证器

多维度验证代码质量
"""
import ast
from typing import List, Dict, Any, Optional

from koda.core.types import ExecutionResult, ValidationReport


class Validator:
    """
    代码验证器
    
    检查代码的语法、结构和最佳实践
    """
    
    def __init__(self):
        self.checks = [
            self._check_syntax,
            self._check_structure,
            self._check_imports,
            self._check_error_handling,
            self._check_documentation,
        ]
    
    async def validate(self, execution: ExecutionResult) -> ValidationReport:
        """
        验证执行结果
        """
        if not execution.success:
            return ValidationReport(
                passed=False,
                errors=[f"Execution failed: {execution.error}"],
                score=0,
            )
        
        checks = []
        errors = []
        warnings = []
        
        main_code = ""
        for artifact in execution.artifacts:
            if artifact.filename == "main.py":
                main_code = artifact.content
                break
        
        if not main_code:
            return ValidationReport(
                passed=False,
                errors=["Missing main.py"],
                score=0,
            )
        
        for check in self.checks:
            result = await check(main_code)
            checks.append(result)
            
            if result.get("type") == "error":
                errors.append(result.get("message", ""))
            elif result.get("type") == "warning":
                warnings.append(result.get("message", ""))
        
        score = self._calculate_score(checks, errors, warnings)
        
        return ValidationReport(
            passed=len(errors) == 0,
            checks=checks,
            errors=errors,
            warnings=warnings,
            score=score,
        )
    
    async def _check_syntax(self, code: str) -> Dict[str, Any]:
        """检查语法"""
        try:
            ast.parse(code)
            return {"name": "syntax", "type": "info", "message": "OK", "passed": True}
        except SyntaxError as e:
            return {"name": "syntax", "type": "error", "message": str(e), "passed": False}
    
    async def _check_structure(self, code: str) -> Dict[str, Any]:
        """检查代码结构"""
        tree = ast.parse(code)
        has_func = any(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
        has_class = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        
        if not has_func and not has_class:
            return {"name": "structure", "type": "warning", "message": "No functions/classes", "passed": False}
        return {"name": "structure", "type": "info", "message": "OK", "passed": True}
    
    async def _check_imports(self, code: str) -> Dict[str, Any]:
        """检查导入"""
        tree = ast.parse(code)
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        
        if not imports:
            return {"name": "imports", "type": "warning", "message": "No imports", "passed": False}
        return {"name": "imports", "type": "info", "message": f"{len(imports)} imports", "passed": True}
    
    async def _check_error_handling(self, code: str) -> Dict[str, Any]:
        """检查错误处理"""
        tree = ast.parse(code)
        has_try = any(isinstance(n, ast.Try) for n in ast.walk(tree))
        
        if not has_try:
            return {"name": "error_handling", "type": "warning", "message": "No try/except", "passed": False}
        return {"name": "error_handling", "type": "info", "message": "OK", "passed": True}
    
    async def _check_documentation(self, code: str) -> Dict[str, Any]:
        """检查文档"""
        if '"""' not in code and "'''" not in code:
            return {"name": "docs", "type": "warning", "message": "No docstrings", "passed": False}
        return {"name": "docs", "type": "info", "message": "OK", "passed": True}
    
    def _calculate_score(self, checks: List[Dict], errors: List[str], warnings: List[str]) -> float:
        """计算质量分数"""
        if not checks:
            return 0.0
        
        passed = sum(1 for c in checks if c.get("passed", False))
        base_score = (passed / len(checks)) * 100
        base_score -= len(errors) * 20
        base_score -= len(warnings) * 5
        
        return max(0, min(100, base_score))
