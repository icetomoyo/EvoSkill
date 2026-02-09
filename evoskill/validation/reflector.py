"""
Reflector - 代码反思器 (Code Reflector)

Pi Coding Agent 没有的 Koda 增强功能：
- 深度代码分析
- LLM 驱动的代码审查
- 自动改进建议
- 智能代码修复
"""
import ast
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ReflectionResult:
    """反思结果"""
    has_issues: bool
    issues: List[str]
    suggestions: List[str]
    confidence: float
    improved_code: Optional[str] = None


@dataclass
class ValidationReport:
    """验证报告"""
    passed: bool
    errors: List[str]
    warnings: List[str]
    checks: List[Dict[str, Any]]
    score: float


@dataclass
class CodeArtifact:
    """代码产物"""
    filename: str
    content: str


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    artifacts: List[CodeArtifact]
    error: Optional[str] = None


class Reflector:
    """
    代码反思器 - Koda 增强功能
    
    像资深代码审查者一样分析代码质量，提供改进建议。
    """
    
    def __init__(self, llm: Any = None):
        self.llm = llm
    
    async def reflect(
        self, 
        execution: ExecutionResult, 
        validation: Optional[ValidationReport] = None
    ) -> ReflectionResult:
        """
        反思代码质量
        
        结合静态分析和 LLM 深度分析，全面评估代码。
        """
        if not execution.artifacts:
            return ReflectionResult(
                has_issues=True,
                issues=["No code artifacts generated"],
                suggestions=["Generate code first"],
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
                suggestions=["Create main.py as the entry point"],
                confidence=1.0,
            )
        
        code = main_artifact.content
        
        # 1. 静态代码分析
        auto_issues = self._static_analysis(code)
        
        # 2. LLM 深度分析（如果提供了 LLM）
        llm_feedback = {"issues": [], "suggestions": [], "can_fix": False, "confidence": 0.5}
        if self.llm:
            llm_feedback = await self._llm_analysis(code, execution, validation)
        
        # 合并问题
        all_issues = list(set(auto_issues + llm_feedback.get("issues", [])))
        all_suggestions = llm_feedback.get("suggestions", [])
        
        # 3. 生成改进代码
        improved_code = None
        if all_issues and llm_feedback.get("can_fix", False) and self.llm:
            improved_code = await self._generate_fix(code, all_issues, all_suggestions)
        
        return ReflectionResult(
            has_issues=len(all_issues) > 0,
            issues=all_issues,
            suggestions=all_suggestions,
            confidence=llm_feedback.get("confidence", 0.5),
            improved_code=improved_code,
        )
    
    def _static_analysis(self, code: str) -> List[str]:
        """静态代码分析 - 快速发现问题"""
        issues = []
        
        # 语法检查
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error at line {e.lineno}: {e.msg}"]
        
        # 检查是否有函数或类定义
        has_function = False
        has_class = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_function = True
            if isinstance(node, ast.ClassDef):
                has_class = True
        
        if not has_function and not has_class:
            issues.append("Code lacks structure: no functions or classes defined")
        
        # 检查错误处理
        has_try = any(isinstance(n, ast.Try) for n in ast.walk(tree))
        if not has_try:
            issues.append("Missing error handling: consider adding try/except blocks")
        
        # 检查文档
        if '"""' not in code and "'''" not in code:
            issues.append("Missing docstrings: add documentation to functions/classes")
        
        # 检查过长函数
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 50:
                    issues.append(f"Function '{node.name}' is very long ({len(node.body)} lines), consider refactoring")
        
        # 检查硬编码值
        has_hardcoded_strings = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if len(node.value) > 10 and not node.value.startswith(("http", "/", "./")):
                    has_hardcoded_strings = True
        
        if has_hardcoded_strings:
            issues.append("Consider extracting hardcoded strings to constants")
        
        return issues
    
    async def _llm_analysis(
        self, 
        code: str, 
        execution: ExecutionResult,
        validation: Optional[ValidationReport]
    ) -> Dict[str, Any]:
        """LLM 深度分析"""
        if not self.llm:
            return {"issues": [], "suggestions": [], "can_fix": False, "confidence": 0.5}
        
        # 构建分析提示词
        validation_info = ""
        if validation:
            validation_info = f"""
Validation Results:
- Passed: {validation.passed}
- Score: {validation.score}/100
- Errors: {validation.errors}
- Warnings: {validation.warnings}
"""
        
        prompt = f"""You are a senior code reviewer. Analyze this Python code critically:

```python
{code}
```

{validation_info}

Provide your analysis in this exact format:

ISSUES:
- List specific code issues (if any)
- Focus on: logic errors, security issues, performance problems, maintainability
- Be specific and actionable

SUGGESTIONS:
- List improvement suggestions
- Include best practices
- Suggest refactoring opportunities

CAN_FIX: [yes/no] (can the issues be automatically fixed?)

CONFIDENCE: [0.0-1.0] (how confident are you in your assessment?)

Be thorough but concise."""

        try:
            # 调用 LLM
            if hasattr(self.llm, 'complete'):
                response = await self.llm.complete(prompt)
            elif hasattr(self.llm, 'chat'):
                response = await self.llm.chat([{"role": "user", "content": prompt}])
            else:
                return {"issues": [], "suggestions": [], "can_fix": False, "confidence": 0.5}
            
            # 解析响应
            return self._parse_llm_response(response)
            
        except Exception as e:
            return {
                "issues": [f"LLM analysis failed: {str(e)}"],
                "suggestions": [],
                "can_fix": False,
                "confidence": 0.0
            }
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        issues = []
        suggestions = []
        can_fix = False
        confidence = 0.5
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('ISSUES:'):
                current_section = 'issues'
                continue
            elif line.startswith('SUGGESTIONS:'):
                current_section = 'suggestions'
                continue
            elif line.startswith('CAN_FIX:'):
                can_fix = 'yes' in line.lower()
                current_section = None
                continue
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.split(':')[1].strip().split()[0])
                except:
                    pass
                current_section = None
                continue
            
            # 收集列表项
            if line.startswith('- ') or line.startswith('* '):
                item = line[2:].strip()
                if current_section == 'issues' and item:
                    issues.append(item)
                elif current_section == 'suggestions' and item:
                    suggestions.append(item)
            elif line and current_section and not line.endswith(':'):
                # 无标记的行也收集
                if current_section == 'issues':
                    issues.append(line)
                elif current_section == 'suggestions':
                    suggestions.append(line)
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "can_fix": can_fix,
            "confidence": confidence
        }
    
    async def _generate_fix(
        self, 
        code: str, 
        issues: List[str], 
        suggestions: List[str]
    ) -> Optional[str]:
        """生成修复后的代码"""
        if not self.llm:
            return None
        
        prompt = f"""Fix the following Python code based on the identified issues:

Original Code:
```python
{code}
```

Issues to Fix:
{chr(10).join(f"- {i}" for i in issues)}

Suggestions:
{chr(10).join(f"- {s}" for s in suggestions)}

Requirements:
1. Fix ALL the issues listed above
2. Maintain the original functionality
3. Follow Python best practices
4. Add proper error handling
5. Add docstrings where missing

Return ONLY the fixed code, no explanations:
"""
        
        try:
            if hasattr(self.llm, 'complete'):
                fixed = await self.llm.complete(prompt)
            elif hasattr(self.llm, 'chat'):
                fixed = await self.llm.chat([{"role": "user", "content": prompt}])
            else:
                return None
            
            return self._clean_code(fixed)
            
        except Exception:
            return None
    
    def _clean_code(self, code: str) -> str:
        """清理代码块标记"""
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()
    
    def get_quick_summary(self, reflection: ReflectionResult) -> str:
        """获取快速总结"""
        if not reflection.has_issues:
            return "✅ Code looks good!"
        
        lines = [f"Found {len(reflection.issues)} issues:"]
        for i, issue in enumerate(reflection.issues[:5], 1):
            lines.append(f"  {i}. {issue}")
        
        if len(reflection.issues) > 5:
            lines.append(f"  ... and {len(reflection.issues) - 5} more")
        
        if reflection.suggestions:
            lines.append(f"\n💡 {len(reflection.suggestions)} suggestions available")
        
        if reflection.improved_code:
            lines.append("\n✨ Auto-fix available")
        
        return "\n".join(lines)
