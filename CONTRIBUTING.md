# 贡献指南

感谢你对 EvoSkill 的兴趣！我们欢迎各种形式的贡献。

---

## 开发环境搭建

### 1. 克隆仓库

```bash
git clone https://github.com/evoskill/evoskill.git
cd evoskill
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -e ".[dev]"
```

### 4. 配置环境变量

```bash
export OPENAI_API_KEY=your-key
# 或
export EVOSKILL_API_KEY=your-key
```

---

## 项目结构

```
evoskill/
├── core/           # 核心引擎
│   ├── types.py    # 类型定义
│   ├── session.py  # Agent 会话
│   ├── events.py   # 事件系统
│   └── llm.py      # LLM 接口
├── skills/         # Skills 系统
│   ├── loader.py   # Skill 加载器
│   └── builtin.py  # 内置工具
├── evolution/      # Skill 进化引擎
│   ├── engine.py   # 进化主引擎
│   ├── analyzer.py # 需求分析
│   └── generator.py# 代码生成
├── cli/            # 命令行界面
│   └── main.py     # CLI 入口
└── server/         # 服务端（TODO）
```

---

## 代码规范

### Python 代码风格

我们使用以下工具保持代码质量：

```bash
# 格式化
black evoskill/

# 导入排序
isort evoskill/

# 类型检查
mypy evoskill/

# 代码检查
ruff check evoskill/
```

### 提交前检查

```bash
# 运行所有检查
pytest
black --check evoskill/
mypy evoskill/
```

---

## 如何贡献

### 报告 Bug

1. 先搜索是否已存在相关 Issue
2. 创建新 Issue，包含：
   - 问题描述
   - 复现步骤
   - 预期行为 vs 实际行为
   - 环境信息（Python 版本、OS 等）

### 提交功能请求

1. 描述你想要的功能
2. 说明使用场景
3. 如果可能，提供实现思路

### 提交代码

1. **Fork 仓库** 并创建分支
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **编写代码**
   - 遵循代码规范
   - 添加测试
   - 更新文档

3. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

   提交信息规范：
   - `feat:` 新功能
   - `fix:` 修复 bug
   - `docs:` 文档更新
   - `test:` 测试相关
   - `refactor:` 重构
   - `style:` 代码格式

4. **推送并创建 PR**
   ```bash
   git push origin feature/your-feature-name
   ```

---

## 创建 Skill

如果你想为 EvoSkill 创建一个新的 Skill：

### 1. 使用 CLI 创建模板

```bash
evoskill create my-skill -d "描述你的 Skill"
```

### 2. 编辑 SKILL.md

```markdown
---
name: my-skill
description: 描述你的 Skill
version: 1.0.0
author: your-name
tools:
  - name: my_tool
    description: 工具描述
    parameters:
      param1:
        type: string
        description: 参数说明
        required: true
---

# My Skill

详细说明...
```

### 3. 实现 main.py

```python
async def my_tool(param1: str) -> str:
    """工具函数"""
    return f"处理了: {param1}"
```

### 4. 添加测试

```python
import pytest
from ..main import my_tool

@pytest.mark.asyncio
async def test_my_tool():
    result = await my_tool("test")
    assert "test" in result
```

### 5. 测试你的 Skill

```bash
cd skills/my-skill
pip install -r requirements.txt
pytest tests/
```

---

## 核心模块开发指南

### 添加新的 LLM 提供商

在 `evoskill/core/llm.py` 中：

```python
class NewProvider(LLMProvider):
    async def chat(self, messages, tools=None, stream=True, **kwargs):
        # 实现提供商特定的逻辑
        pass
```

### 添加新的内置工具

在 `evoskill/skills/builtin.py` 中：

```python
async def my_new_tool(param: str) -> str:
    """工具实现"""
    return result

# 在 register_builtin_tools 中注册
session.register_tool(
    name="my_new_tool",
    description="工具描述",
    parameters={"param": {...}},
    handler=my_new_tool,
)
```

---

## 测试

### 运行测试

```bash
# 所有测试
pytest

# 带覆盖率
pytest --cov=evoskill

# 特定测试
pytest tests/test_session.py
```

### 编写测试

```python
import pytest
from evoskill.core.session import AgentSession

@pytest.mark.asyncio
async def test_session():
    session = AgentSession()
    # 测试代码
```

---

## 文档

- 代码文档：使用 Google Style Docstrings
- 架构文档：`docs/ARCHITECTURE.md`
- 提示词文档：`docs/PROMPTS.md`

---

## 获取帮助

- 查看 [文档](docs/)
- 加入 [Discord](https://discord.gg/evoskill)（TODO）
- 创建 [Issue](https://github.com/evoskill/evoskill/issues)

---

## 许可证

通过提交代码，你同意将其授权给 MIT 许可证。

感谢你的贡献！🚀
