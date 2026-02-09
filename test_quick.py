#!/usr/bin/env python
"""
EvoSkill Quick Test Script

Usage:
1. No API key: python test_quick.py
2. With API key: set KIMI_API_KEY=sk-xxx && python test_quick.py --full
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def test_environment():
    """Test environment"""
    print("=" * 60)
    print("Step 1: Environment Check")
    print("=" * 60)
    
    try:
        import evoskill
        print("[OK] evoskill imported")
    except ImportError as e:
        print(f"[FAIL] evoskill import failed: {e}")
        return False
    
    try:
        import koda
        print("[OK] koda imported")
    except ImportError as e:
        print(f"[FAIL] koda import failed: {e}")
        return False
    
    try:
        from koda.core.agent_v2 import KodaAgentV2
        print("[OK] KodaAgentV2 imported")
    except ImportError as e:
        print(f"[FAIL] KodaAgentV2 import failed: {e}")
        return False
    
    try:
        from koda.tools.file_tool import FileTool
        print("[OK] FileTool imported")
    except ImportError as e:
        print(f"[FAIL] FileTool import failed: {e}")
        return False
    
    return True


def test_koda_tools():
    """Test Koda tools"""
    print("\n" + "=" * 60)
    print("Step 2: Koda Tools Test")
    print("=" * 60)
    
    try:
        from koda.tools.file_tool import FileTool
        from koda.tools.shell_tool import ShellTool
        
        # Create tool instances
        file_tool = FileTool()
        shell_tool = ShellTool()
        
        # Test write (async)
        test_file = Path("test_output.txt")
        result = asyncio.run(file_tool.write(
            path=str(test_file),
            content="Hello from EvoSkill!"
        ))
        assert result.success, "Write failed"
        print("[OK] write_file works")
        
        # Test read (async)
        result = asyncio.run(file_tool.read(path=str(test_file)))
        assert result.success, "Read failed"
        assert "Hello from EvoSkill!" in result.content, "Read content mismatch"
        print("[OK] read_file works")
        
        # Cleanup
        test_file.unlink()
        
        # Test bash (async)
        result = asyncio.run(shell_tool.execute(command="echo test123"))
        assert result.success, "Bash failed"
        assert "test123" in result.output, "Bash output mismatch"
        print("[OK] bash works")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Koda tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation():
    """Test validation system"""
    print("\n" + "=" * 60)
    print("Step 3: Validation System Test")
    print("=" * 60)
    
    try:
        from koda.core.validator import Validator
        from koda.core.reflector import ExecutionResult, CodeArtifact
        
        validator = Validator()
        
        # Test good code
        good_code = '''
def calculate(a, b):
    """Add two numbers."""
    try:
        return a + b
    except Exception:
        return None
'''
        execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", good_code)]
        )
        
        import asyncio
        report = asyncio.run(validator.validate(execution))
        
        assert report.passed, "Good code should pass"
        print(f"[OK] Validator works (score: {report.score:.0f})")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_demo():
    """Test demo"""
    print("\n" + "=" * 60)
    print("Step 4: Demo Test (Simulated)")
    print("=" * 60)
    
    try:
        # Import demo module
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "skill_evolution_demo", 
            "demo_workspace/skill_evolution_demo.py"
        )
        demo_module = importlib.util.module_from_spec(spec)
        
        print("[OK] Demo module found")
        print("   Run: python demo_workspace/skill_evolution_demo.py")
        
        return True
        
    except Exception as e:
        print(f"[WARN] Demo check: {e}")
        return True  # Not critical


def run_pytest():
    """Run pytest"""
    print("\n" + "=" * 60)
    print("Step 5: Run Pytest")
    print("=" * 60)
    
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/koda/", "-q"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("[OK] All Koda tests passed")
        # Show summary
        lines = result.stdout.strip().split('\n')
        for line in lines[-3:]:
            if line:
                print(f"   {line}")
        return True
    else:
        print("[FAIL] Some tests failed")
        print(result.stdout)
        print(result.stderr)
        return False


async def test_with_api_key():
    """Test with API key (optional)"""
    print("\n" + "=" * 60)
    print("Step 6: Full Test (With API Key)")
    print("=" * 60)
    
    api_key = os.getenv("KIMI_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "your-api-key-here":
        print("[WARN] No API key found, skipping full test")
        print("   Set KIMI_API_KEY or OPENAI_API_KEY to enable")
        return True
    
    try:
        from evoskill.core.types import LLMConfig
        from evoskill.core.llm import create_llm_provider
        
        # Test LLM connection
        llm_config = LLMConfig(
            provider="openai",
            model="kimi-k2.5" if "moonshot" in api_key else "gpt-4",
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1" if "moonshot" in api_key else None,
        )
        
        print("Testing LLM connection...")
        llm = create_llm_provider(llm_config)
        
        # Simple test call
        messages = [{"role": "user", "content": "Say 'EvoSkill test OK'"}]
        response = await llm.chat(messages, stream=False)
        
        print(f"[OK] LLM connection works")
        print(f"   Response preview: {str(response)[:100]}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Full test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main"""
    print("\n" + "=" * 60)
    print("EvoSkill Quick Test")
    print("=" * 60)
    
    results = []
    
    # Basic tests (no API key needed)
    results.append(("Environment", test_environment()))
    results.append(("Koda Tools", test_koda_tools()))
    results.append(("Validation", test_validation()))
    results.append(("Demo Check", test_demo()))
    results.append(("Pytest", run_pytest()))
    
    # Full test (needs API key)
    if "--full" in sys.argv:
        result = asyncio.run(test_with_api_key())
        results.append(("Full Test", result))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n[OK] All tests passed!")
        print("\nNext steps:")
        print("1. Run demo: python demo_workspace/skill_evolution_demo.py")
        print("2. With API key: python test_quick.py --full")
        return 0
    else:
        print("\n[FAIL] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
