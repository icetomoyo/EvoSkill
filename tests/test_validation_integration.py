"""
Tests for EvoSkill's validation system

Tests the complete validation loop: Validator + Reflector
"""
import pytest
import asyncio
from pathlib import Path

from evoskill.validation.validator import Validator
from evoskill.validation.reflector import Reflector
from evoskill.validation.types import ExecutionResult, CodeArtifact


class MockLLM:
    """Mock LLM for testing"""
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_count = 0
    
    async def complete(self, prompt):
        self.call_count += 1
        
        # Return appropriate mock response based on prompt content
        if "Fix" in prompt and "code" in prompt:
            return self.responses.get('fix', 'def fixed(): pass')
        elif "reflector" in prompt.lower() or "review" in prompt.lower():
            return self.responses.get('reflect', '''
ISSUES:
- Missing type hints
SUGGESTIONS:
- Add type annotations
CAN_FIX: true
CONFIDENCE: 0.8
''')
        return self.responses.get('default', '{}')


class TestValidator:
    """Test Validator functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_good_code(self):
        """Test validation of good code"""
        validator = Validator()
        
        good_code = '''
def calculate(price, tax_rate):
    """Calculate total price with tax."""
    try:
        total = price * (1 + tax_rate)
        return total
    except (TypeError, ValueError) as e:
        print(f"Error: {e}")
        return None
'''
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", good_code)]
        )
        
        report = await validator.validate(execution)
        
        assert report.passed is True
        assert report.score > 50
        assert len(report.checks) == 5  # 5 validation checks
    
    @pytest.mark.asyncio
    async def test_validate_bad_code(self):
        """Test validation of code with issues"""
        validator = Validator()
        
        bad_code = '''
def calc(p, t):
    return p * t
'''
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", bad_code)]
        )
        
        report = await validator.validate(execution)
        
        # Bad code still passes (no errors) but with warnings
        assert report.passed is True
        assert len(report.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_validate_syntax_error(self):
        """Test validation of code with syntax error"""
        validator = Validator()
        
        bad_code = '''
def broken(
    print("missing paren")
'''
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", bad_code)]
        )
        
        report = await validator.validate(execution)
        
        assert report.passed is False
        assert len(report.errors) > 0


class TestReflector:
    """Test Reflector functionality"""
    
    @pytest.mark.asyncio
    async def test_reflector_static_analysis(self):
        """Test static analysis without LLM"""
        reflector = Reflector(llm=None)
        
        code = '''
def calc(a, b):
    return a / b
'''
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        reflection = await reflector.reflect(execution)
        
        # Should detect missing error handling
        assert reflection.has_issues is True
        assert len(reflection.issues) > 0
    
    @pytest.mark.asyncio
    async def test_reflector_with_llm(self):
        """Test reflection with LLM"""
        llm = MockLLM()
        reflector = Reflector(llm=llm)
        
        code = 'def calc(a,b): return a+b'
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        reflection = await reflector.reflect(execution)
        
        # Should have called LLM
        assert llm.call_count > 0


class TestValidationFeatures:
    """Test specific validation features"""
    
    @pytest.mark.asyncio
    async def test_validation_checks_structure(self):
        """Test structure checking"""
        validator = Validator()
        
        # Code with function
        code_with_func = 'def foo(): pass'
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code_with_func)]
        )
        
        report = await validator.validate(execution)
        structure_check = [c for c in report.checks if c.get("name") == "structure"]
        
        if structure_check:
            assert structure_check[0].get("passed") is True
    
    @pytest.mark.asyncio
    async def test_validation_checks_error_handling(self):
        """Test error handling checking"""
        validator = Validator()
        
        # Code with try/except
        code_with_try = '''
try:
    result = 1 / 0
except:
    pass
'''
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code_with_try)]
        )
        
        report = await validator.validate(execution)
        error_check = [c for c in report.checks if c.get("name") == "error_handling"]
        
        if error_check:
            assert error_check[0].get("passed") is True
