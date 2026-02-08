# Koda V2 - Self-Extending Coding Agent

> KOding Agent - 融合 Pi Coding Agent 理念的自主编程代理

## 核心特性

### 🌲 树状会话管理 (Tree Session)

类似 Git 分支的开发历史管理：

```python
# 创建新分支实验新功能
branch = agent.create_branch("experiment-auth", "Try new auth method")

# 在分支中开发...
# 如果成功，合并回主线
agent.merge(branch.id)

# 如果失败，放弃分支
agent.abandon(branch.id)

# 查看开发树
print(agent.get_tree_view())
```

### 🔧 自扩展机制 (Self-Extension)

代理自己编写工具扩展：

```python
# 代理发现自己缺少 weather API 工具
# 自动生成：
extension = await agent.self_extending.create_tool_for_capability(
    capability="fetch weather from API",
    requirements=["Support multiple cities", "Handle errors"]
)

# 立即使用新生成的工具
result = await agent.extension_engine.execute_extension(
    "weather_api", 
    city="Beijing"
)
```

### 🧪 自验证循环 (Self-Validation)

生成 → 验证 → 修复的闭环：

```python
# 1. 生成代码
code = await agent.generate_code(task)

# 2. 自动验证
report = await agent.validate_code(code)

# 3. 如果失败，创建分支修复
if not report.passed:
    fix_branch = agent.create_branch("fix-validation")
    fixed_code = await agent.fix_code(code, report)
    agent.merge(fix_branch.id)
```

### ⚡ 热重载 (Hot Reload)

扩展修改即时生效：

```python
# 改进现有工具
improved = await agent.self_extending.improve_tool(
    "weather_api",
    "Add support for Celsius and Fahrenheit"
)

# 自动热重载，立即使用新版本
```

## 快速开始

### 安装

```bash
pip install koda
```

### 基础使用

```python
import asyncio
from koda import KodaAgentV2, AgentConfig

async def main():
    # 配置
    config = AgentConfig(
        enable_self_extension=True,
        enable_branches=True,
        enable_validation=True,
        verbose=True,
    )
    
    # 创建代理
    agent = KodaAgentV2(
        llm=your_llm_adapter,
        config=config,
        workspace="./my_project"
    )
    
    # 执行任务
    result = await agent.execute(
        description="Create a weather query CLI tool",
        requirements=[
            "Use OpenWeatherMap API",
            "Support multiple cities",
            "Output as JSON",
            "Handle API errors",
        ]
    )
    
    # 查看结果
    print(f"Success: {result['success']}")
    print(f"Code:\n{result['code']}")
    
    # 查看开发历史树
    print(agent.get_tree_view())

asyncio.run(main())
```

### 高级使用：分支开发

```python
# 主线开发
main_result = await agent.execute("Create basic API client")

# 创建分支添加认证
auth_branch = agent.create_branch(
    "add-authentication",
    "Add API key authentication"
)

# 切换到分支
agent.checkout(auth_branch.id)

# 在分支中开发
auth_result = await agent.execute("Add API key auth to client")

# 如果成功，合并回主线
if auth_result['success']:
    agent.merge(auth_branch.id)
    print("Authentication feature merged!")
else:
    # 放弃失败的分支
    agent.abandon(auth_branch.id)
    print("Authentication approach abandoned")
```

### 高级使用：自扩展

```python
# 代理发现自己缺少数据库工具
# 自动生成工具
extension = await agent.self_extending.create_tool_for_capability(
    capability="query SQLite database",
    requirements=[
        "Connect to SQLite",
        "Execute SQL queries",
        "Return results as dict",
        "Handle connection errors"
    ]
)

# 查看生成的代码
print(f"Generated tool: {extension.name}")
print(extension.code)

# 使用新生成的工具
result = await agent.extension_engine.execute_extension(
    "sqlite_query",
    query="SELECT * FROM users LIMIT 10"
)
```

## 架构对比

### Koda V1 vs V2

| 特性 | Koda V1 | Koda V2 (New) |
|------|---------|---------------|
| 架构 | 线性 Pipeline | 树状 + 自扩展 |
| 会话 | 线性历史 | 🌲 树状分支 |
| 扩展 | 预置工具 | 🔧 自编写扩展 |
| 验证 | 基础检查 | 🧪 完整验证 + 自动修复 |
| 热重载 | ❌ | ✅ 扩展热重载 |
| 理念 | 模块化 | 代码写代码 |

### Koda V2 vs Pi Coding Agent

| 特性 | Pi Coding Agent | Koda V2 |
|------|-----------------|---------|
| 工具数量 | 4 (Read/Write/Edit/Bash) | 动态生成 |
| 扩展方式 | 自编写 | 自编写 + 验证 |
| 会话管理 | 🌲 树状 | 🌲 树状 + 验证状态 |
| 代码验证 | ❌ | ✅ 完整验证循环 |
| 自动修复 | ❌ | ✅ 分支修复 |

## 设计理念

### 1. 代码写代码 (Code Writes Code)

> "如果代理不能做某事，不要下载扩展，而是让代理自己写扩展。"

代理通过编写 Python 代码来增强自己的能力，形成正向循环。

### 2. 树状开发历史

开发历史像 Git 一样呈树状：
- 主线（main）：稳定代码
- 分支（branch）：实验性改动
- 可以合并成功的分支，放弃失败的分支

### 3. 自验证闭环

生成 → 验证 → 修复 → 验证...

确保生成的代码质量，自动修复问题。

## 配置文件

```yaml
# .koda.yaml
agent:
  enable_self_extension: true
  enable_branches: true
  enable_validation: true
  max_iterations: 3
  verbose: true

llm:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

extensions:
  auto_create_missing: true
  hot_reload: true
```

## API 参考

### KodaAgentV2

```python
class KodaAgentV2:
    def __init__(self, llm, config=None, workspace=None)
    
    async def execute(description, requirements=None) -> dict
    
    # 分支操作
    def create_branch(name, description) -> SessionNode
    def checkout(node_id) -> SessionNode
    def merge(from_node_id) -> SessionNode
    def abandon(node_id)
    def get_tree_view() -> str
    
    # 扩展操作
    async def ensure_tool_exists(capability) -> bool
```

### TreeSession

```python
class TreeSession:
    def create_branch(name, description, from_node_id=None) -> SessionNode
    def checkout(node_id) -> SessionNode
    def merge(from_node_id, to_node_id=None) -> SessionNode
    def abandon(node_id)
    def get_tree_visualization() -> str
    def get_path_to_root(node_id) -> List[SessionNode]
```

### ExtensionEngine

```python
class ExtensionEngine:
    async def generate_extension(name, description, requirements, llm_client) -> ExtensionInfo
    def load_extension(extension) -> Type
    def hot_reload(name) -> bool
    async def execute_extension(name, method="execute", **kwargs) -> dict
```

## 示例项目

见 `examples/` 目录：

- `koda_v2_demo.py` - V2 特性完整演示
- `tree_session_demo.py` - 树状会话演示
- `self_extension_demo.py` - 自扩展示演示

## 运行测试

```bash
# 运行示例
python examples/koda_v2_demo.py

# 运行测试
pytest tests/
```

## 路线图

### V2.0 (Current)
- ✅ 树状会话管理
- ✅ 自扩展机制
- ✅ 自验证循环
- ✅ 热重载

### V2.1 (Planned)
- 🔄 浏览器自动化工具
- 🔄 代码解释器
- 🔄 多 Agent 协作

### V2.2 (Planned)
- 🔄 IDE 插件
- 🔄 可视化树状界面
- 🔄 扩展市场

## 致谢

- 受 [Pi Coding Agent](https://github.com/mariozechner/openclaw) (Mario Zechner) 启发
- 融合自验证能力
- 保持开源精神

---

<p align="center">
  <b>Koda V2 - Code Writes Code, Tree Manages History, Validation Ensures Quality</b>
</p>
