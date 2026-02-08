# Pi Coding Agent 到 Koda V2 迁移指南

本指南帮助从 Pi Coding Agent (OpenClaw/pi-mono) 迁移到 Koda V2。

## 快速对比

| 方面 | Pi | Koda V2 |
|------|----|---------|
| 语言 | TypeScript | Python |
| 会话格式 | JSONL | JSONL (兼容) |
| 工具 API | 对象形式 | 方法形式 |
| 自扩展 | ✅ | ✅ (增强) |
| 自验证 | ❌ | ✅ |

## 会话迁移

### Pi 的 JSONL 格式
```jsonl
{"id":"root","role":"user","content":"Create a scraper"}
{"id":"n1","parentId":"root","role":"assistant","content":"I'll help..."}
{"id":"n2","parentId":"n1","role":"assistant","tool":{"name":"read","params":{"path":"main.py"}}}
```

### Koda V2 的兼容格式
```jsonl
{"id": "root", "parent_id": null, "role": "user", "content": "Create a scraper", "tool": null}
{"id": "n1", "parent_id": "root", "role": "assistant", "content": "I'll help...", "tool": null}
{"id": "n2", "parent_id": "n1", "role": "assistant", "content": "", "tool": {"name": "read", "params": {"path": "main.py"}}}
```

**迁移工具**：
```python
from koda.core.tree_session import TreeSession

# 自动迁移 Pi 的会话
session = TreeSession.from_pi_jsonl("pi-session.jsonl")
session.save()  # 保存为 Koda 格式
```

## 工具 API 迁移

### Pi 的工具使用

```typescript
// Pi: 通过 agent.tools 对象调用
const result = await agent.tools.read.execute({
  path: "file.py",
  offset: 1,
  limit: 50
});

// 写文件
await agent.tools.write.execute({
  path: "new.py",
  content: "print('hello')"
});

// 编辑文件
await agent.tools.edit.execute({
  path: "file.py",
  oldText: "old",
  newText: "new"
});

// 执行命令
const output = await agent.tools.bash.execute({
  command: "ls -la"
});
```

### Koda V2 的工具使用

```python
# Koda V2: 直接调用方法
result = await agent.read(
    path="file.py",
    offset=1,
    limit=50
)

# 写文件
success = await agent.write(
    path="new.py",
    content="print('hello')"
)

# 编辑文件
result = await agent.edit(
    path="file.py",
    old_text="old",
    new_text="new"
)

# 执行命令
result = await agent.bash(command="ls -la")
```

### 结果处理对比

#### Pi
```typescript
interface ReadResult {
  content: string;
  truncated: boolean;
  totalLines: number;
  outputLines: number;
}

const result = await agent.tools.read.execute({ path: "file.py" });
console.log(result.content);
```

#### Koda V2
```python
@dataclass
class ReadResult:
    content: str
    truncated: bool
    total_lines: int
    output_lines: int
    # ... 其他字段

result = await agent.read(path="file.py")
print(result.content)
```

## 自扩展迁移

### Pi 的自扩展

```typescript
// Pi: 生成 TypeScript 扩展
async function createExtension(capability: string) {
  const code = await llm.complete(`
    Write a TypeScript tool for: ${capability}
    Export a function execute(params) that returns { success, result, error }
  `);
  
  // 热重载
  const base64 = btoa(code);
  const module = await import(`data:text/javascript;base64,${base64}`);
  return module;
}
```

### Koda V2 的自扩展

```python
# Koda V2: 生成 Python 扩展
tool = await agent.create_extension(
    name="my_tool",
    description="Tool description",
    requirements=[
        "Support feature X",
        "Handle errors gracefully"
    ],
)

# 生成的扩展会自动热重载
# 并可通过 extension_engine 访问
extensions = agent.extension_engine.list_extensions()
```

### 扩展示例对比

#### Pi 扩展 (TypeScript)
```typescript
// extensions/myTool.ts
export async function execute(params: { url: string }) {
  try {
    const response = await fetch(params.url);
    const data = await response.json();
    return { success: true, result: data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}
```

#### Koda V2 扩展 (Python)
```python
# .koda/extensions/my_tool.py
import aiohttp
from typing import Dict, Any

async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch JSON from URL"""
    try:
        url = params.get("url")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return {"success": True, "result": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## 会话管理迁移

### Pi 的分支操作

```typescript
// Pi: 通过 session entries 管理
interface TreeSession {
  entries: SessionEntry[];
  leafId: string;
}

// 创建分支（手动设置 parentId）
const branchEntry = {
  id: generateId(),
  parentId: currentEntry.id,
  role: "assistant",
  content: "Branching..."
};

// 导航（重建 entries 列表）
function checkout(entryId: string) {
  const path = getPathToRoot(entryId);
  session.entries = path;
  session.leafId = entryId;
}
```

### Koda V2 的分支操作

```python
# Koda V2: 封装好的分支 API

# 创建分支
branch = agent.create_branch(
    name="experiment",
    description="Try new approach"
)

# 切换分支
agent.checkout(branch.id)

# 合并分支
agent.merge(branch.id)  # 合并到父节点

# 放弃分支
agent.abandon(branch.id)

# 查看树状结构
print(agent.get_tree_view())
```

## 配置迁移

### Pi 配置

```typescript
// Pi: 环境变量或硬编码
const config = {
  model: "gpt-4",
  maxTokens: 4000,
  temperature: 0.7,
  workspace: "./workspace",
};
```

### Koda V2 配置

```python
# Koda V2: dataclass 配置
from koda.core import AgentConfig

config = AgentConfig(
    # 自扩展
    enable_self_extension=True,
    auto_create_missing_tools=False,
    
    # 分支
    enable_branches=True,
    max_branches=10,
    
    # 验证
    enable_validation=True,
    max_iterations=3,
    
    # 工具
    default_tools=["read", "write", "edit", "bash"],
)

agent = KodaAgentV2(llm=llm, config=config)
```

## 完整迁移示例

### Pi 项目
```typescript
// main.ts
import { Agent } from "./agent";

async function main() {
  const agent = new Agent({ model: "gpt-4" });
  
  // 读取文件
  const file = await agent.tools.read.execute({ path: "main.py" });
  
  // 创建分支
  const branch = agent.session.createBranch("fix-bug");
  
  // 编辑文件
  await agent.tools.edit.execute({
    path: "main.py",
    oldText: "def old():",
    newText: "def new():"
  });
  
  // 验证并合并
  if (await validate()) {
    agent.session.merge(branch.id);
  }
}
```

### 迁移到 Koda V2
```python
# main.py
from koda.core import KodaAgentV2, AgentConfig

async def main():
    agent = KodaAgentV2(
        llm=your_llm,
        config=AgentConfig(
            enable_branches=True,
            enable_validation=True,
        ),
    )
    
    # 读取文件（Pi 兼容 API）
    result = await agent.read(path="main.py")
    
    # 创建分支
    branch = agent.create_branch(name="fix-bug", description="Fix the bug")
    
    # 编辑文件
    await agent.edit(
        path="main.py",
        old_text="def old():",
        new_text="def new():"
    )
    
    # 验证并合并（Koda 自动）
    result = await agent.execute_task(
        description="Fix the bug",
        requirements=["Fix function name"]
    )
    # 或手动：
    # if validate():
    #     agent.merge(branch.id)

if __name__ == "__main__":
    asyncio.run(main())
```

## 新增功能使用

### 自验证（Koda V2 独有）

```python
# 自动验证生成的代码
result = await agent.execute_task(
    description="Create a REST API",
    requirements=["Use Flask", "Support CRUD"]
)

if result["success"]:
    print(f"Success after {result['iterations']} iterations")
else:
    print(f"Failed: {result['error']}")
```

### 系统提示词构建

```python
from koda.core.system_prompt import SystemPromptBuilder

# 自定义系统提示词
builder = SystemPromptBuilder.with_agents_md(
    agents_md_path=Path("AGENTS.md"),
    tools=["read", "write", "edit", "bash"]
)
system_prompt = builder.build()
```

### 截断处理

```python
from koda.core.truncation import truncate_head, truncate_tail

# 头部截断（保留开头）- 用于文件读取
result = truncate_head(large_content, max_lines=100)

# 尾部截断（保留末尾）- 用于命令输出
result = truncate_tail(large_output, max_lines=100)
```

## 常见问题

### Q: 会话文件兼容吗？
**A**: 基本兼容。Koda V2 的 `parent_id` 对应 Pi 的 `parentId`，可以通过转换工具迁移。

### Q: 扩展可以复用吗？
**A**: 不能直接使用，因为语言不同（TypeScript vs Python）。但逻辑可以移植。

### Q: 工具 API 完全一样吗？
**A**: 功能相同，但调用方式不同：
- Pi: `agent.tools.read.execute(params)`
- Koda: `agent.read(**params)`

### Q: 性能有差异吗？
**A**: 
- 启动：Python 较慢 (~200ms vs ~100ms)
- 执行：相近
- 热重载：Python 稍快

### Q: 可以混用吗？
**A**: 不能直接混用，但可以通过 API 交互。

## 参考

- [Pi Coding Agent](https://github.com/OpenClaw/pi-mono)
- [Koda COMPARISON.md](./COMPARISON.md) - 详细对比
- [Koda API.md](./API.md) - API 文档
