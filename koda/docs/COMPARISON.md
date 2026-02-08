# Koda V2 vs Pi Coding Agent - 对比分析

## 概述

**Pi Coding Agent** (OpenClaw/pi-mono) 和 **Koda V2** (KOding Agent) 都是自主编程代理框架，但 Koda V2 在 Pi 的基础上增强了自验证和自我扩展能力。

## Pi Coding Agent 详解

### 定位
Pi 是一个**极简的编程代理原型**，由 Mario Zechner 开发，专注于：
- 演示如何使用 4 个工具构建功能完整的 Agent
- 验证 "Agent 自己写代码扩展能力" 的哲学
- 作为构建复杂 Agent 的参考实现

### 核心特性
| 特性 | 描述 |
|------|------|
| 4 个核心工具 | `read`, `write`, `edit`, `bash` |
| 树状会话 | JSONL 格式，支持分支导航 |
| 自扩展 | Agent 自己写 Python 工具扩展功能 |
| 热重载 | 扩展立即生效，无需重启 |
| 内容截断 | 50KB/2000行限制，头部/尾部截断 |

### 架构
```
Pi Agent:
┌─────────────────────────────┐
│      JSONL Session          │  ← 树状会话 (id/parentId)
├─────────────────────────────┤
│      Message Stream         │  ← LLM 交互
├─────────────────────────────┤
│     AbortController         │  ← 取消信号
├─────────────────────────────┤
│   ┌─────┬─────┬─────┬────┐  │
│   │read │write│edit │bash│  │  ← 4 个核心工具
│   └─────┴─────┴─────┴────┘  │
├─────────────────────────────┤
│    Extension (self-write)   │  ← 自扩展工具
└─────────────────────────────┘
```

### 代码示例
```typescript
// 工具定义
const readTool: Tool = {
  params: z.object({ path: z.string(), offset: z.number().optional(), limit: z.number().optional() }),
  async execute({ path, offset, limit }) {
    const content = fs.readFileSync(path, "utf-8");
    const lines = content.split("\n");
    // 处理 offset/limit 截断...
  }
};

// Agent 写扩展工具
async function createExtension() {
  const extensionCode = await agent.complete("Write a tool to...");
  // 热重载
  loadExtension(extensionCode);
}
```

---

## Koda V2 详解

### 定位
Koda V2 是一个**生产级的自主编程代理框架**，在 Pi 的基础上增强：
- **自验证循环**：Validator + Reflector 确保代码质量
- **分支策略**：更智能的分支创建/合并/放弃策略
- **Pi 兼容**：完全兼容 Pi 的工具 API
- **模块化设计**：更好的可扩展性

### 核心特性
| 特性 | Pi | Koda V2 | 说明 |
|------|----|---------|------|
| 树状会话 | ✅ | ✅ | JSONL 格式兼容 |
| 4 个核心工具 | ✅ | ✅ | read, write, edit, bash |
| 自扩展 | ✅ | ✅ | Agent 写 Python 工具 |
| 热重载 | ✅ | ✅ | 立即生效 |
| 内容截断 | ✅ | ✅ | 50KB/2000行 |
| 自验证 | ❌ | ✅ | Validator + Reflector |
| 分支策略 | 基础 | 智能 | 策略驱动的分支管理 |
| Python 原生 | ❌ | ✅ | Python 实现 |
| 类型安全 | 部分 | 完整 | dataclass + mypy |

### 架构
```
Koda V2:
┌─────────────────────────────────────────┐
│          KodaAgentV2                    │
│    (Tree Session + Self-Extension)      │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │ Tree    │  │Extension│  │System  │  │
│  │Session  │  │ Engine  │  │Prompt  │  │
│  └─────────┘  └─────────┘  └────────┘  │
├─────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐              │
│  │Validator│  │Reflector│  ← 新增！    │
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

### 代码示例
```python
# Koda V2 使用
from koda.core import KodaAgentV2, AgentConfig

agent = KodaAgentV2(
    llm=your_llm,
    config=AgentConfig(
        enable_self_extension=True,
        enable_validation=True,
        enable_branches=True,
    ),
)

# Pi 兼容的 4 个工具
result = await agent.read("file.py", offset=1, limit=50)
success = await agent.write("file.py", "content")
success = await agent.edit("file.py", "old", "new")
result = await agent.bash("ls -la")

# 自验证任务执行
result = await agent.execute_task(
    description="Create a web scraper",
    requirements=["Use requests", "Parse HTML with BeautifulSoup"],
)
# 自动验证 -> 失败 -> 创建分支修复 -> 验证通过 -> 合并

# 树状会话导航
branch = agent.create_branch("experiment", "Try new approach")
agent.checkout(branch.id)
agent.merge(branch.id)  # 或 abandon()
print(agent.get_tree_view())

# 自扩展
tool = await agent.create_extension(
    name="github_api",
    description="GitHub API client",
    requirements=["Support repos, issues, PRs"],
)
```

---

## 详细对比

### 功能对比

| 功能 | Pi Coding | Koda V2 | 说明 |
|------|-----------|---------|------|
| **实现语言** | TypeScript | Python | Koda 是 Python 原生 |
| **会话格式** | JSONL | JSONL | 完全兼容 |
| **树状结构** | id/parentId | id/parentId | 相同 |
| **工具参数** | Zod Schema | Type Hints | 不同的验证方式 |
| **截断处理** | 50KB/2000行 | 50KB/2000行 | 相同 |
| **热重载** | import() | importlib | 实现方式不同 |
| **自验证** | ❌ | ✅ | Koda 新增 |
| **分支策略** | 手动 | 策略驱动 | Koda 更智能 |
| **类型安全** | TypeScript | dataclass | 各有优势 |
| **LLM 支持** | OpenAI | 任意 | Koda 更灵活 |

### API 对比

#### Pi (TypeScript)
```typescript
// 会话管理
interface SessionEntry {
  id: string;
  parentId?: string;
  role: "user" | "assistant";
  content: string;
  tool?: ToolCall;
}

// 工具定义
interface Tool {
  params: z.ZodType;
  execute: (args: any) => Promise<any>;
}

// 使用
const result = await agent.tools.read.execute({ path: "file.py" });
```

#### Koda V2 (Python)
```python
# 会话管理
@dataclass
class SessionEntry:
    id: str
    parent_id: Optional[str]
    role: Literal["user", "assistant"]
    content: str
    tool: Optional[ToolCall] = None

# 工具定义（简洁）
class FileTool:
    async def read(self, path: str, offset: int = None, limit: int = None) -> ReadResult:
        ...

# 使用（更直观）
result = await agent.read("file.py", offset=1, limit=50)
```

### 自扩展对比

#### Pi 的自扩展
```typescript
// Agent 写 TypeScript 扩展
const extension = await llm.complete(`Write a tool to ${capability}`);
// 保存并热重载
const module = await import(`data:text/javascript;base64,${btoa(extension)}`);
```

#### Koda V2 的自扩展
```python
# Agent 写 Python 扩展
extension = await agent.create_extension(
    name="my_tool",
    description="Tool description",
    requirements=["req1", "req2"],
)
# 自动热重载
# 自动验证生成的代码
# 失败时创建分支修复
```

### 自验证（Koda 独有）

```python
# Koda V2 的自验证循环
async def execute_task(self, description, requirements):
    for iteration in range(max_iterations):
        # 1. 生成代码
        code = await generate(description)
        
        # 2. 验证（Koda 新增）
        is_valid, error = validate(code)
        
        if is_valid:
            return success
        
        # 3. 策略选择
        strategy = choose_strategy(error)
        
        if strategy == "branch":
            # 创建修复分支
            fix_branch = create_branch(f"fix-{iteration}")
            fixed = await fix_in_branch(code, error)
            
            # 验证修复
            if validate(fixed):
                merge(fix_branch)  # 成功，合并
            else:
                abandon(fix_branch)  # 失败，放弃
        
        elif strategy == "extend":
            # 创建新工具扩展
            await create_extension_for_fix(error)
```

---

## 使用场景

### 适合使用 Pi Coding Agent 的场景

1. **学习参考**
   - 理解如何用 4 个工具构建 Agent
   - 研究树状会话的实现
   - TypeScript 项目参考

2. **原型开发**
   - 快速验证 Agent 概念
   - 作为复杂 Agent 的基础

3. **教育用途**
   - 学习 Agent 架构
   - 理解自扩展概念

### 适合使用 Koda V2 的场景

1. **生产开发**
   - Python 项目开发
   - 需要自验证的代码生成
   - 复杂的分支管理

2. **框架扩展**
   - 构建自己的 Agent 框架
   - 集成到现有 Python 项目
   - 自定义验证逻辑

3. **研究实验**
   - 验证自改进 Agent
   - 多分支策略实验
   - 扩展自动生成研究

---

## 性能对比

| 指标 | Pi | Koda V2 | 说明 |
|------|----|---------|------|
| 启动时间 | ~100ms | ~200ms | Python 较重 |
| 工具执行 | ~10ms | ~15ms | 相近 |
| 热重载 | ~50ms | ~30ms | Python importlib 更快 |
| 内存占用 | ~50MB | ~80MB | Python 较重 |
| 代码生成 | ~2-5s | ~2-5s | 取决于 LLM |
| 自验证 | N/A | ~100ms | Koda 新增 |

---

## 哲学对比

### Pi 的设计哲学
> "If the agent can't do something, don't tell the user to install an extension. Let the agent write the code to achieve it."

核心：极简工具集 + 自扩展 = 无限可能

### Koda 的设计哲学
> "Code that writes code, validated by code, improved by code."

核心：自扩展 + 自验证 + 自改进 = 可靠的自主编程

---

## 迁移指南

从 Pi 迁移到 Koda V2 见 [MIGRATION.md](./MIGRATION.md)

---

## 参考

- [Pi Coding Agent](https://github.com/OpenClaw/pi-mono) - OpenClaw/pi-mono
- [Pi Coding Agent 作者](https://github.com/badlogic) - Mario Zechner
- [Koda GitHub](https://github.com/evoskill/koda) - Koda 仓库
- [Koda Docs](./README.md) - Koda 文档
