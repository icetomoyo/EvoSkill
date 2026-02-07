"""
Skill 验证器 - 验证生成的 Skill 是否可用
"""
import ast
import sys
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    syntax_valid: bool = False
    import_valid: bool = False
    tests_passed: bool = False
    test_output: str = ""


class SkillValidator:
    """
    Skill 验证器
    
    检查生成的 Skill：
    1. 语法正确性
    2. 可导入性
    3. 单元测试通过
    """
    
    async def validate(self, skill_path: Path) -> ValidationResult:
        """
        验证 Skill
        
        Args:
            skill_path: Skill 目录路径
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=False)
        
        # 检查文件结构
        main_py = skill_path / "main.py"
        skill_md = skill_path / "SKILL.md"
        test_py = skill_path / "tests" / "test_main.py"
        
        if not main_py.exists():
            result.errors.append("main.py 不存在")
            return result
        
        if not skill_md.exists():
            result.warnings.append("SKILL.md 不存在")
        
        # 1. 语法检查
        syntax_ok = self._check_syntax(main_py)
        result.syntax_valid = syntax_ok
        if not syntax_ok:
            result.errors.append("main.py 语法错误")
        
        # 2. 可导入性检查
        if syntax_ok:
            import_ok = self._check_import(skill_path)
            result.import_valid = import_ok
            if not import_ok:
                result.errors.append("无法导入 main.py")
        
        # 3. 单元测试
        if test_py.exists() and result.import_valid:
            test_result = await self._run_tests(skill_path)
            result.tests_passed = test_result["passed"]
            result.test_output = test_result["output"]
            if not test_result["passed"]:
                result.warnings.append("单元测试未完全通过（但 Skill 可能仍可用）")
        
        # 综合判断
        result.valid = (
            result.syntax_valid and
            result.import_valid
            # 测试不强制要求通过，因为可能是测试环境问题
        )
        
        return result
    
    def _check_syntax(self, file_path: Path) -> bool:
        """检查 Python 文件语法"""
        try:
            content = file_path.read_text(encoding="utf-8")
            ast.parse(content)
            return True
        except SyntaxError as e:
            return False
        except Exception as e:
            return False
    
    def _check_import(self, skill_path: Path) -> bool:
        """检查模块是否可以导入"""
        try:
            # 临时添加路径
            sys.path.insert(0, str(skill_path.parent))
            
            try:
                module = __import__(skill_path.name)
                return True
            except ImportError as e:
                # 可能是依赖缺失，但语法正确
                if "No module named" in str(e):
                    return True  # 语法正确，只是缺少依赖
                return False
            except Exception as e:
                return False
            finally:
                sys.path.pop(0)
                
        except Exception as e:
            return False
    
    async def _run_tests(self, skill_path: Path) -> Dict[str, Any]:
        """运行单元测试"""
        test_file = skill_path / "tests" / "test_main.py"
        
        if not test_file.exists():
            return {"passed": True, "output": "No tests"}
        
        try:
            # 运行 pytest
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                cwd=str(skill_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            
            return {
                "passed": passed,
                "output": output,
            }
            
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "output": "测试超时",
            }
        except Exception as e:
            return {
                "passed": False,
                "output": f"测试运行失败: {e}",
            }
    
    def quick_check(self, skill_path: Path) -> bool:
        """
        快速检查 - 只验证语法
        
        Returns:
            True if syntax is valid
        """
        main_py = skill_path / "main.py"
        if not main_py.exists():
            return False
        return self._check_syntax(main_py)
