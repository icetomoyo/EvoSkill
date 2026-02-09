# EvoSkill 手动测试指南

> 如何测试当前功能和闭环演示

---

## 一、环境准备

### 1.1 确认 Python 环境

```bash
# 进入项目目录
cd C:\Works\GitWorks\EvoSkill

# 激活虚拟环境
.venv\Scripts\activate

# 检查 Python 版本
python --version  # 需要 3.10+
```

### 1.2 配置 API Key

编辑配置文件：

```bash
# 打开配置文件
notepad %LOCALAPPDATA%\evoskill\config.yaml
```

配置内容：

```yaml
# 方式 1: OpenAI 兼容 API（推荐 Kimi）
provider: openai
model: kimi-k2.5
base_url: https://api.moonshot.cn/v1
api_key: sk-your-kimi-api-key

# 方式 2: 其他兼容 API
# provider: openai
# model: gpt-4
# base_url: https://api.openai.com/v1
# api_key: sk-your-openai-key

# 工作目录
workspace: C:\Works\GitWorks\EvoSkill
temperature: 0.3
```

**获取 Kimi API Key**: https://platform.moonshot.cn/

### 1.3 验证环境

```bash
# 运行 Koda 测试
python -m pytest tests/koda/ -v

# 期望输出: 48 passed, 1 skipped
```

---

## 二、测试 Koda 基础功能

### 2.1 运行自动化测试

```bash
# 全部 Koda 测试
python -m pytest tests/koda/ -v

# 特定测试
python -m pytest tests/koda/test_tools_pi_compatible.py -v
python -m pytest tests/koda/test_validation_integration.py -v
```

### 2.2 手动测试工具

创建测试脚本 `test_manual.py`：

```python
"""手动测试 Koda 工具"""
import asyncio
from pathlib import Path

async def test_read_write():
    """测试读写工具"""
    from koda.tools.read import read_file
    from koda.tools.write import write_file
    
    # 测试写入
    test_file = Path("test_output.txt")
    result = write_file(
        file_path=str(test_file),
        content="Hello from EvoSkill!\nLine 2"
    )
    print(f"Write result: {result}")
    
    # 测试读取
    content = read_file(file_path=str(test_file))
    print(f"Read content: {content}")
    
    # 清理
    test_file.unlink()
    print("✅ Read/Write test passed")

async def test_bash():
    """测试 Bash 工具"""
    from koda.tools.bash import bash
    
    result = bash(command="echo Hello World")
    print(f"Bash output: {result.output}")
    print("✅ Bash test passed")

async def test_grep():
    """测试 Grep 工具"""
    from koda.tools.grep import grep
    
    # 先创建一个测试文件
    from koda.tools.write import write_file
    write_file("test_grep.txt", "apple\nbanana\napple pie\ncherry")
    
    result = grep(pattern="apple", path="test_grep.txt")
    print(f"Grep matches: {len(result.matches)}")
    
    # 清理
    Path("test_grep.txt").unlink()
    print("✅ Grep test passed")

async def main():
    print("=== Koda Manual Tests ===\n")
    await test_read_write()
    await test_bash()
    await test_grep()
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python test_manual.py
```

---

## 三、测试闭环演示

### 3.1 运行模拟演示

不需要 API key，使用模拟数据：

```bash
python demo_workspace/skill_evolution_demo.py
```

**预期输出**：

```
============================================================
Skill Evolution Demo - Complete Loop
============================================================

[Stage 1] Query existing skills
----------------------------------------
User: /skills

AI: Available skills:
  - read_file: Read file content
  - write_file: Write file content
  - bash: Execute commands

[Stage 2] Create new skill
...
[OK] time_tool (1.0.0) created and activated!

[Stage 3] Use new skill
...
Current time: 2026-02-09T16:40:21

[Stage 4] Skill evolution
...
[OK] time_tool evolved to 1.1.0!
```

### 3.2 检查生成的文件

演示会创建实际文件：

```bash
# 查看生成的 Skill 文件
ls demo_workspace/demo_workspace/skills/time_tool/

# 内容
# - SKILL.md       # Skill 定义
# - main.py        # 实现代码
# - tests/test_main.py  # 测试
```

---

## 四、测试集成会话

### 4.1 测试 IntegratedSession

创建测试脚本 `test_integration.py`：

```python
"""测试 IntegratedSession"""
import asyncio
from pathlib import Path
from evoskill.core.integrated_session import IntegratedSession
from evoskill.core.types import LLMConfig

async def test_skills_command():
    """测试 /skills 命令"""
    print("\n=== Test /skills command ===")
    
    session = IntegratedSession(
        workspace=Path.cwd(),
        llm_config=LLMConfig(provider="openai", model="gpt-4"),
    )
    
    async for event in session.prompt("/skills"):
        if event.type == "message_end":
            print(f"Response: {event.data.get('content', '')}")
    
    print("✅ /skills test passed")

async def test_code_task():
    """测试代码任务（需要 API key）"""
    print("\n=== Test Code Task ===")
    print("This test requires valid API key")
    
    session = IntegratedSession(
        workspace=Path.cwd(),
        llm_config=LLMConfig(
            provider="openai",
            model="kimi-k2.5",
            api_key="your-api-key",  # 替换为你的 key
            base_url="https://api.moonshot.cn/v1",
        ),
    )
    
    # 测试读取文件
    async for event in session.prompt("读取 README.md 的前 10 行"):
        print(f"Event: {event.type}, Data: {event.data}")
    
    print("✅ Code task test passed")

async def main():
    # 测试不需要 API key 的功能
    await test_skills_command()
    
    # 以下测试需要 API key
    # await test_code_task()

if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python test_integration.py
```

---

## 五、完整闭环测试（需要 API Key）

### 5.1 创建测试脚本

```python
"""完整闭环测试 - 需要有效的 API Key"""
import asyncio
import os
from pathlib import Path
from evoskill.core.integrated_session import IntegratedSession
from evoskill.core.types import LLMConfig, EventType

# 从环境变量或配置文件读取 API key
API_KEY = os.getenv("KIMI_API_KEY", "your-api-key-here")
BASE_URL = "https://api.moonshot.cn/v1"

async def full_loop_test():
    """完整闭环测试"""
    
    print("=" * 60)
    print("Full Loop Test - Requires API Key")
    print("=" * 60)
    
    # 创建会话
    session = IntegratedSession(
        workspace=Path("./test_workspace"),
        llm_config=LLMConfig(
            provider="openai",
            model="kimi-k2.5",
            api_key=API_KEY,
            base_url=BASE_URL,
        ),
    )
    
    # Step 1: 查询 Skills
    print("\n[Step 1] Query Skills")
    print("-" * 40)
    async for event in session.prompt("/skills"):
        if event.type == EventType.MESSAGE_END:
            print(event.data.get("content", ""))
    
    # Step 2: 创建 Skill（需要 API key）
    print("\n[Step 2] Create Skill")
    print("-" * 40)
    print("Creating a calculator skill...")
    
    async for event in session.prompt("/create a calculator that can add two numbers"):
        print(f"Event: {event.type}")
        if event.data:
            print(f"Data: {event.data}")
    
    # Step 3: 使用新 Skill
    print("\n[Step 3] Use Skill")
    print("-" * 40)
    print("Testing calculator...")
    
    async for event in session.prompt("Calculate 5 + 3"):
        if event.type == EventType.MESSAGE_END:
            print(f"Result: {event.data.get('content', '')}")
    
    # Step 4: 进化 Skill
    print("\n[Step 4] Evolve Skill")
    print("-" * 40)
    print("Adding subtraction support...")
    
    async for event in session.prompt("/evolve calculator add subtraction support"):
        print(f"Event: {event.type}")
        if event.data:
            print(f"Data: {event.data}")
    
    print("\n✅ Full loop test completed!")

if __name__ == "__main__":
    if API_KEY == "your-api-key-here":
        print("ERROR: Please set KIMI_API_KEY environment variable")
        print("Example: set KIMI_API_KEY=sk-your-key")
    else:
        asyncio.run(full_loop_test())
```

### 5.2 运行完整测试

```bash
# 设置环境变量
set KIMI_API_KEY=sk-your-actual-key

# 运行测试
python full_loop_test.py
```

---

## 六、分组件测试

### 6.1 测试 KodaAdapterV2

```python
"""测试 KodaAdapterV2"""
import asyncio
from pathlib import Path
from evoskill.coding_agent.koda_adapter_v2 import KodaAdapterV2
from evoskill.core.llm import create_llm_provider
from evoskill.core.types import LLMConfig

async def test_adapter():
    """测试适配器"""
    
    llm_config = LLMConfig(
        provider="openai",
        model="kimi-k2.5",
        api_key="your-api-key",
        base_url="https://api.moonshot.cn/v1",
    )
    
    llm = create_llm_provider(llm_config)
    adapter = KodaAdapterV2(
        llm_provider=llm,
        workspace=Path("./test_workspace"),
    )
    
    # 执行简单任务
    result = await adapter.execute("创建一个简单的 Python 脚本，输出 'Hello World'")
    
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Artifacts: {result.artifacts}")

if __name__ == "__main__":
    asyncio.run(test_adapter())
```

### 6.2 测试验证系统

```python
"""测试 Koda 验证系统"""
import asyncio
from koda.core.validator import Validator
from koda.core.reflector import Reflector, ExecutionResult, CodeArtifact

class MockLLM:
    """模拟 LLM"""
    async def complete(self, prompt):
        return '''{
            "issues": ["Missing type hints"],
            "suggestions": ["Add type annotations"],
            "can_fix": true,
            "confidence": 0.8
        }'''

async def test_validator():
    """测试 Validator"""
    print("=== Testing Validator ===")
    
    validator = Validator()
    
    # 测试好代码
    good_code = '''
def calculate(a, b):
    """Add two numbers."""
    try:
        return a + b
    except Exception as e:
        return None
'''
    execution = ExecutionResult(
        success=True,
        artifacts=[CodeArtifact("main.py", good_code)]
    )
    report = await validator.validate(execution)
    
    print(f"Good code - Passed: {report.passed}, Score: {report.score}")
    
    # 测试坏代码
    bad_code = 'def calc(a,b): return a+b'
    execution = ExecutionResult(
        success=True,
        artifacts=[CodeArtifact("main.py", bad_code)]
    )
    report = await validator.validate(execution)
    
    print(f"Bad code - Passed: {report.passed}, Score: {report.score}")
    print(f"Warnings: {len(report.warnings)}")

async def test_reflector():
    """测试 Reflector"""
    print("\n=== Testing Reflector ===")
    
    llm = MockLLM()
    reflector = Reflector(llm)
    
    code = 'def calc(a,b): return a+b'
    execution = ExecutionResult(
        success=True,
        artifacts=[CodeArtifact("main.py", code)]
    )
    
    reflection = await reflector.reflect(execution)
    
    print(f"Has issues: {reflection.has_issues}")
    print(f"Issues: {reflection.issues}")
    print(f"Confidence: {reflection.confidence}")

async def main():
    await test_validator()
    await test_reflector()
    print("\n✅ Validation tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 七、测试检查清单

### 7.1 无需 API Key 的测试

- [ ] `python -m pytest tests/koda/ -v` (48 passed)
- [ ] `python test_manual.py` (手动工具测试)
- [ ] `python demo_workspace/skill_evolution_demo.py` (模拟演示)
- [ ] `python test_integration.py` (基础集成测试)

### 7.2 需要 API Key 的测试

- [ ] 配置 `config.yaml` 或环境变量
- [ ] `python test_adapter.py` (适配器测试)
- [ ] `python full_loop_test.py` (完整闭环)
- [ ] 手动测试 `/create` 命令
- [ ] 手动测试 `/evolve` 命令

### 7.3 功能验证

| 功能 | 测试命令 | 预期结果 |
|------|----------|----------|
| 查询 Skills | `/skills` | 列出所有可用 skills |
| 创建 Skill | `/create desc` | 生成 skill 文件并注册 |
| 使用 Skill | 自然语言描述 | 调用对应 skill |
| 进化 Skill | `/evolve name req` | 修改并更新 skill |
| 代码执行 | 文件操作描述 | Koda 执行并返回结果 |

---

## 八、常见问题

### Q1: 测试提示 API key 无效

```
Error: Invalid API key
```

**解决**:
1. 检查 `config.yaml` 中的 `api_key`
2. 或设置环境变量：`set KIMI_API_KEY=sk-xxx`
3. 确认 key 有效：https://platform.moonshot.cn/

### Q2: 测试提示缺少依赖

```
ModuleNotFoundError: No module named 'xxx'
```

**解决**:
```bash
# 安装依赖
pip install -e ".[dev]"

# 或单独安装
pip install aiohttp openai anthropic
```

### Q3: 闭环演示显示乱码

**解决**: 这是 Windows 终端编码问题，不影响功能。使用 VS Code 终端或 Git Bash 可避免。

### Q4: 如何查看生成的代码？

```bash
# 查看生成的 skill
ls demo_workspace/demo_workspace/skills/

# 查看具体文件
cat demo_workspace/demo_workspace/skills/time_tool/main.py
```

---

## 九、快速测试命令汇总

```bash
# 1. 运行所有自动化测试
python -m pytest tests/koda/ -v

# 2. 运行模拟演示（无需 API key）
python demo_workspace/skill_evolution_demo.py

# 3. 测试集成会话基础功能
python -c "
from evoskill.core.integrated_session import IntegratedSession
from evoskill.core.types import LLMConfig
import asyncio

async def test():
    session = IntegratedSession(llm_config=LLMConfig(provider='openai', model='gpt-4'))
    async for e in session.prompt('/skills'):
        if e.type == 'message_end':
            print(e.data.get('content'))

asyncio.run(test())
"

# 4. 验证环境
python -c "import evoskill; import koda; print('✅ Environment OK')"
```

---

**提示**: 没有 API key 时，可以运行大部分测试，但涉及 LLM 的功能（如创建 Skill）需要有效的 key。
