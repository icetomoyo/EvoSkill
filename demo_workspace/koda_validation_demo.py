"""
Koda Validation System Demo

展示 Koda 的核心验证能力 - 这是 Pi Coding Agent 没有的功能
"""
import asyncio

# 模拟 LLM
class MockLLM:
    async def complete(self, prompt):
        return '''{
            "issues": ["Function 'calculate' lacks type hints", "Consider using constants for magic numbers"],
            "suggestions": ["Add type hints to function parameters", "Extract 0.08 as a constant"],
            "can_fix": true,
            "confidence": 0.85
        }'''

async def main():
    print("=" * 60)
    print("Koda Validation System Demo")
    print("=" * 60)
    
    # 1. Validator 演示 - 多维度代码检查
    print("\n[Validator] Static Code Check")
    print("-" * 40)
    
    from koda.core.validator import Validator
    from koda.core.reflector import ExecutionResult, CodeArtifact
    
    validator = Validator()
    
    # 测试代码1：良好代码
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
    print(f"[OK] Good code validation:")
    print(f"   Passed: {report.passed}")
    print(f"   Score: {report.score:.1f}")
    print(f"   Checks: {len(report.checks)}")
    
    # 测试代码2：有问题的代码
    bad_code = '''
def calc(p, t):
    return p * t
'''
    
    execution = ExecutionResult(
        success=True,
        artifacts=[CodeArtifact("main.py", bad_code)]
    )
    
    report = await validator.validate(execution)
    print(f"\n[!] Bad code validation:")
    print(f"   Passed: {report.passed}")
    print(f"   Score: {report.score:.1f}")
    print(f"   Warnings: {len(report.warnings)}")
    for w in report.warnings:
        print(f"   - {w}")
    
    # 2. Reflector 演示 - LLM驱动的代码分析
    print("\n\n[Reflector] AI Code Analysis")
    print("-" * 40)
    
    from koda.core.reflector import Reflector
    
    llm = MockLLM()
    reflector = Reflector(llm)
    
    code_to_analyze = '''
def calculate(price, tax_rate=0.08):
    return price * (1 + tax_rate)
'''
    
    execution = ExecutionResult(
        success=True,
        artifacts=[CodeArtifact("main.py", code_to_analyze)]
    )
    
    reflection = await reflector.reflect(execution)
    print(f"Reflection result:")
    print(f"   Has issues: {reflection.has_issues}")
    print(f"   Issues found: {len(reflection.issues)}")
    for issue in reflection.issues:
        print(f"   - {issue}")
    print(f"   Suggestions: {len(reflection.suggestions)}")
    for suggestion in reflection.suggestions:
        print(f"   -> {suggestion}")
    print(f"   Confidence: {reflection.confidence:.0%}")
    
    # 3. 与 Pi Coding Agent 的对比
    print("\n\n[Compare] Koda vs Pi Coding Agent - Validation")
    print("-" * 40)
    print("""
Feature                    Pi Coding Agent    Koda
-----------------------------------------------------
Basic Code Execution       Yes               Yes
Syntax Validation          No                Validator
Structure Check            No                Validator
Best Practices             No                Reflector
AI Code Analysis           No                Reflector
Auto Fix Suggestions       No                Reflector
Quality Score              No                Validator

Conclusion: Koda provides complete validation capabilities!
""")
    
    print("\nDemo completed!")

if __name__ == "__main__":
    asyncio.run(main())
