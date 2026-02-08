# Koda V2 Documentation

Koda V2 是一个融合 Pi Coding Agent 理念的自主编程代理框架。

## 核心特性

### 1. Pi-Compatible 工具 (100% 兼容)

Koda V2 实现了 Pi Coding Agent 的 4 个核心工具：

| 工具 | Pi API | Koda V2 API | 说明 |
|------|--------|-------------|------|
| `read` | `tools.read.execute({path})` | `await agent.read(path)` | 读取文件，支持 offset/limit |
| `write` | `tools.write.execute({path, content})` | `await agent.write(path, content)` | 写入文件 |
| `edit` | `tools.edit.execute({path, oldText, newText})` | `await agent.edit(path, old_text, new_text)` | 精确文本替换 |
| `bash` | `tools.bash.execute({command})` | `await agent.bash(command)` | 执行 shell 命令 |

### 2. 树状会话管理

```python
from koda.core import KodaAgentV2

agent = KodaAgentV2(llm=your_llm)

# 创建分支
branch = agent.create_branch(name="experiment", description="Try new approach")

# 切换分支
agent.checkout(branch.id)

# 合并分支
agent.merge(branch.id)

# 放弃分支
agent.abandon(branch.id)

# 查看树状结构
print(agent.get_tree_view())
```

### 3. 自扩展引擎

```python
# 让 Agent 自己写工具
tool = await agent.create_extension(
    name="github_api",
    description="GitHub API client for repos and issues",
    requirements=["Support rate limiting", "Handle pagination"],
)

# 热重载 - 立即可用
extensions = agent.list_extensions()
```

### 4. 自验证循环 (Koda 独有)

```python
# 执行任务，自动验证 -> 失败 -> 修复 -> 验证
result = await agent.execute_task(
    description="Create a REST API with Flask",
    requirements=[
        "Support CRUD operations",
        "Use SQLAlchemy for ORM",
        "Include error handling"
    ]
)

print(f"Success: {result['success']}")
print(f"Iterations: {result['iterations']}")
print(f"Final code: {result['code']}")
```

### 5. 内容截断

与 Pi 相同的 50KB/2000行 限制：

```python
from koda.core.truncation import truncate_head, truncate_tail

# 头部截断（保留开头）- 用于文件读取
result = truncate_head(large_content)
if result.truncated:
    print(f"Showing lines 1-{result.output_lines} of {result.total_lines}")

# 尾部截断（保留末尾）- 用于命令输出
result = truncate_tail(command_output)
```

## 快速开始

### 安装

```bash
cd koda
pip install -e .
```

### 基本使用

```python
import asyncio
from koda.core import KodaAgentV2, AgentConfig

# 配置
config = AgentConfig(
    enable_self_extension=True,
    enable_validation=True,
    enable_branches=True,
    verbose=True,
)

# 创建 Agent
agent = KodaAgentV2(
    llm=your_llm,  # 你的 LLM 客户端
    config=config,
    workspace="./my_project",
)

async def main():
    # 使用 Pi 兼容的工具
    result = await agent.read("main.py", offset=1, limit=50)
    print(result.content)
    
    # 执行任务（带自验证）
    result = await agent.execute_task(
        description="Add error handling to main.py",
        requirements=["Use try-except", "Log errors"],
    )
    
    # 查看会话树
    print(agent.get_tree_view())

asyncio.run(main())
```

## 架构

```
Koda V2:
┌─────────────────────────────────────────┐
│          KodaAgentV2                    │
│    (Pi-compatible + Self-Validation)    │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │ Tree    │  │Extension│  │System  │  │
│  │Session  │  │ Engine  │  │Prompt  │  │
│  └─────────┘  └─────────┘  └────────┘  │
├─────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐              │
│  │Validator│  │Reflector│  ← Koda 新增 │
│  │         │  │         │              │
│  └─────────┘  └─────────┘              │
├─────────────────────────────────────────┤
│  ┌────┐ ┌─────┐ ┌────┐ ┌────┐          │
│  │read│ │write│ │edit│ │bash│  ← Pi兼容│
│  └────┘ └─────┘ └────┘ └────┘          │
├─────────────────────────────────────────┤
│      Extension (Python, hot-reload)     │
└─────────────────────────────────────────┘
```

## 文档

- [COMPARISON.md](./COMPARISON.md) - Pi vs Koda 详细对比
- [MIGRATION.md](./MIGRATION.md) - 从 Pi 迁移到 Koda
- [API.md](./API.md) - API 参考（待完善）

## Pi 兼容性

Koda V2 保持与 Pi Coding Agent 的以下兼容：

1. **会话格式**: JSONL with id/parentId
2. **工具 API**: 4 个核心工具功能完全一致
3. **截断策略**: 50KB/2000行 限制
4. **热重载**: 扩展立即生效
5. **自扩展**: Agent 自己写工具

## 新增功能

Koda V2 在 Pi 基础上新增：

1. **自验证循环**: Validator + Reflector
2. **策略驱动分支**: 智能分支创建/合并/放弃
3. **系统提示词构建器**: 动态构建提示词
4. **Python 原生**: 更好的 Python 生态集成
5. **类型安全**: dataclass + mypy 支持

## 参考

- [Pi Coding Agent](https://github.com/OpenClaw/pi-mono) - OpenClaw/pi-mono
- [Koda GitHub](https://github.com/evoskill/koda) - 主仓库
