"""
Integration tests for Koda's validation enhancements

Tests the complete validation loop: Validator + Reflector + Agent integration
"""
import pytest
import asyncio
from pathlib import Path

from koda.core.agent_v2 import KodaAgentV2, AgentConfig, TaskResult
from koda.core.validator import Validator
from koda.core.reflector import Reflector, ExecutionResult, CodeArtifact


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
- Variable name could be more descriptive

SUGGESTIONS:
- Add type annotations
- Use more descriptive variable names

CAN_FIX: yes

CONFIDENCE: 0.85
''')
        else:
            return self.responses.get('default', 'def test(): pass')
    
    async def chat(self, messages):
        return await self.complete(messages[0]["content"])


class TestValidator:
    """Test Validator component"""
    
    @pytest.mark.asyncio
    async def test_validate_good_code(self):
        """Validator should pass for good code"""
        validator = Validator()
        
        code = '''
"""Module docstring."""
import os

def process_data(data: str) -> str:
    """Process the data."""
    try:
        result = data.upper()
        return result
    except Exception as e:
        raise ValueError(f"Processing failed: {e}")

class DataProcessor:
    """Process data."""
    
    def process(self, data):
        """Process method."""
        return process_data(data)
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        report = await validator.validate(execution)
        
        assert report.passed is True
        assert report.score > 80
        assert len(report.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_bad_code(self):
        """Validator should catch issues in bad code"""
        validator = Validator()
        
        code = '''
# No docstring
# No imports

x = 1  # Hardcoded

def func():  # No docstring
    y = 2  # Another hardcoded value
    return y
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        report = await validator.validate(execution)
        
        # Should have warnings but might still pass
        assert len(report.warnings) > 0
        assert report.score < 100
    
    @pytest.mark.asyncio
    async def test_validate_syntax_error(self):
        """Validator should catch syntax errors"""
        validator = Validator()
        
        code = '''
def broken(
    print("missing closing paren")
)
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        report = await validator.validate(execution)
        
        # Syntax error should be caught
        assert report.score < 100  # Score should be reduced


class TestReflector:
    """Test Reflector component"""
    
    @pytest.mark.asyncio
    async def test_reflector_static_analysis(self):
        """Reflector should perform static analysis"""
        reflector = Reflector()  # No LLM
        
        code = '''
def test():
    x = 1
    return x
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        reflection = await reflector.reflect(execution, None)
        
        # Should find issues even without LLM
        assert reflection.has_issues is True
        assert len(reflection.issues) > 0
        # Should detect missing docstring and error handling
        assert any("docstring" in i.lower() for i in reflection.issues)
    
    @pytest.mark.asyncio
    async def test_reflector_with_llm(self):
        """Reflector should use LLM when available"""
        mock_llm = MockLLM({
            'reflect': '''
ISSUES:
- Function too long
- Missing type hints

SUGGESTIONS:
- Split into smaller functions
- Add type annotations

CAN_FIX: yes

CONFIDENCE: 0.9
'''
        })
        
        reflector = Reflector(mock_llm)
        
        code = '''
def process():
    """Process data."""
    x = 1
    y = 2
    return x + y
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code)]
        )
        
        reflection = await reflector.reflect(execution, None)
        
        assert reflection.has_issues is True
        # Should have issues from both static analysis and LLM
        assert len(reflection.issues) >= 2
        assert reflection.confidence == 0.9
        assert mock_llm.call_count > 0


class TestAgentValidationIntegration:
    """Test Agent with validation integration"""
    
    @pytest.mark.asyncio
    async def test_agent_executes_task_with_validation(self):
        """Agent should use validation during task execution"""
        mock_llm = MockLLM({
            'default': '''
import os

def main():
    """Main function."""
    try:
        result = "hello"
        return result
    except Exception as e:
        print(f"Error: {e}")
''',
            'reflect': '''
ISSUES:
- No major issues

SUGGESTIONS:
- Could add more error handling

CAN_FIX: no

CONFIDENCE: 0.95
'''
        })
        
        config = AgentConfig(
            enable_validation=True,
            enable_reflection=True,
            max_iterations=2,
            verbose=False
        )
        
        agent = KodaAgentV2(
            llm=mock_llm,
            config=config,
            workspace=Path('.')
        )
        
        result = await agent.execute_task(
            description="Create a simple function",
            requirements=["Return a string"]
        )
        
        assert isinstance(result, TaskResult)
        assert result.code is not None
        assert len(result.code) > 0
        assert result.validation_score > 0
    
    @pytest.mark.asyncio
    async def test_agent_disabled_validation(self):
        """Agent should work with validation disabled"""
        mock_llm = MockLLM({'default': 'print("hello")'})
        
        config = AgentConfig(
            enable_validation=False,
            enable_reflection=False,
            verbose=False
        )
        
        agent = KodaAgentV2(
            llm=mock_llm,
            config=config,
            workspace=Path('.')
        )
        
        result = await agent.execute_task(
            description="Create a hello world script"
        )
        
        assert isinstance(result, TaskResult)
        assert result.code is not None


class TestValidationFeatures:
    """Test specific validation features"""
    
    @pytest.mark.asyncio
    async def test_validation_checks_structure(self):
        """Validator should check code structure"""
        validator = Validator()
        
        # Code without functions or classes
        bad_code = '''
x = 1
y = 2
print(x + y)
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", bad_code)]
        )
        
        report = await validator.validate(execution)
        
        # Should warn about structure
        structure_check = next((c for c in report.checks if c.get("name") == "structure"), None)
        assert structure_check is not None
    
    @pytest.mark.asyncio
    async def test_validation_checks_error_handling(self):
        """Validator should check for error handling"""
        validator = Validator()
        
        code_without_try = '''
def risky():
    return 1 / 0  # No try/except
'''
        
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", code_without_try)]
        )
        
        report = await validator.validate(execution)
        
        # Should warn about missing error handling
        error_check = next((c for c in report.checks if c.get("name") == "error_handling"), None)
        assert error_check is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
