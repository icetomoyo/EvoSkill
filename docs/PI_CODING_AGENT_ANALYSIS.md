# Pi Coding Agent (badlogic/pi-mono) 架构分析

> 真正的对标目标分析

## 一、项目信息

| 属性 | 值 |
|------|-----|
| **作者** | Mario Zechner (@badlogic) |
| **项目** | pi-mono |
| **GitHub** | https://github.com/badlogic/pi-mono |
| **包名** | @mariozechner/pi-coding-agent |
| **语言** | TypeScript |

## 二、核心架构

### 2.1 内置工具 (7个)

Pi 提供 **4 个默认工具**，可通过 `--tools` 扩展到 7 个：

| 工具 | 默认 | 说明 |
|------|------|------|
| `read` | ✅ | 读取文件 |
| `write` | ✅ | 写入文件 |
| `edit` | ✅ | 编辑文件 (search/replace) |
| `bash` | ✅ | 执行命令 |
| `grep` | ❌ | 文本搜索 |
| `find` | ❌ | 文件查找 |
| `ls` | ❌ | 目录列表 |

### 2.2 核心设计哲学

**极简主义 + 可扩展性**:

1. **不内置复杂功能**:
   - ❌ 子代理 (sub-agents)
   - ❌ 计划模式 (plan mode)
   - ❌ MCP 协议
   - ❌ 权限弹窗
   - ❌ 后台 bash
   - ❌ 内置待办

2. **通过扩展实现**:
   - ✅ Extensions (TypeScript 模块)
   - ✅ Skills (Agent Skills 标准)
   - ✅ Prompt Templates

### 2.3 会话系统

**JSONL 格式 + 树状结构**:

```jsonl
{"id": "1", "role": "user", "content": "..."}
{"id": "2", "parentId": "1", "role": "assistant", "tool_calls": [...]}
{"id": "3", "parentId": "2", "role": "tool", "content": "..."}
```

- 支持分支 (`/tree`, `/fork`)
- 自动压缩 (compaction)
- 会话文件: `~/.pi/agent/sessions/`

### 2.4 文件结构

```
~/.pi/agent/
├── sessions/          # 会话存储
├── AGENTS.md          # 全局上下文
├── SYSTEM.md          # 系统提示词 (可选)
├── settings.json      # 设置
├── keybindings.json   # 快捷键
├── models.json        # 自定义模型
├── skills/            # 技能
├── extensions/        # 扩展
├── prompts/           # 提示词模板
└── themes/            # 主题
```

### 2.5 核心模块

根据 AGENTS.md，项目分为:

| 包 | 说明 |
|----|------|
| `packages/ai` | LLM 工具包 |
| `packages/agent` | Agent 框架 |
| `packages/coding-agent` | Pi Coding Agent |
| `packages/tui` | 终端 UI |
| `packages/mom` | 消息格式 |
| `packages/pods` | 进程管理 |
| `packages/web-ui` | Web UI |

## 三、与当前 Koda 的差异

### 3.1 Koda 多实现的功能

| 功能 | Koda 当前 | Pi 实际 | 处理方式 |
|------|-----------|---------|----------|
| 验证系统 | ✅ Validator/Reflector | ❌ 无 | **移除** |
| 扩展引擎 | ✅ extension_engine | ❌ 无 | **移除** |
| 计划模式 | ✅ plan.py/planner.py | ❌ 无 | **移除** |
| 自动修复 | ✅ _generate_fix | ❌ 无 | **移除** |
| 工具数量 | 7 个 (正确) | 7 个 | ✅ 保留 |

### 3.2 Pi 有但 Koda 缺少的

| 功能 | Pi | Koda | 优先级 |
|------|----|------|--------|
| JSONL 会话存储 | ✅ | ❌ | P0 |
| 树状分支 | ✅ | ❌ | P0 |
| 自动压缩 | ✅ | ❌ | P1 |
| Skills 系统 | ✅ | ❌ | P1 |
| Prompt 模板 | ✅ | ❌ | P1 |
| AGENTS.md | ✅ | ❌ | P0 |

## 四、重构计划

### 4.1 需要移除的

```
koda/core/
├── validator.py        → 删除 (移到 EvoSkill)
├── reflector.py        → 删除 (移到 EvoSkill)
├── extension_engine.py → 删除
├── plan.py             → 删除
├── planner.py          → 删除
├── multimodal_types.py → 评估是否需要
```

### 4.2 需要实现的

```
koda/
├── core/
│   ├── agent.py        → 简化，只保留核心循环
│   ├── session.py      → JSONL 树状会话
│   ├── tools.py        → 7 个工具统一接口
│   └── compaction.py   → 上下文压缩
├── config.py           → Pi 风格配置
├── cli.py              → 简化命令行
└── skills/             → Skills 系统
```

### 4.3 核心简化

**Agent 循环**:
```python
class Agent:
    def run(self, user_input):
        # 1. 添加到消息历史
        # 2. 调用 LLM (streaming)
        # 3. 解析工具调用
        # 4. 执行工具
        # 5. 返回结果
        # 6. 保存会话
```

**工具接口**:
```python
class Tool:
    name: str
    description: str
    parameters: dict
    
    def execute(self, **kwargs) -> ToolResult:
        pass
```

## 五、验证标准

Koda 重构完成后应能:

1. ✅ 7 个工具完全对标 Pi
2. ✅ JSONL 会话存储
3. ✅ 树状分支支持
4. ✅ 自动上下文压缩
5. ✅ AGENTS.md 上下文加载
6. ✅ 无验证系统、无扩展引擎
7. ✅ 极简核心，功能通过 Skills 扩展

## 六、Skill 进化位置

Skill 进化引擎 **不属于 Koda**，应该在:

```
evoskill/
├── evolution/          ← Skill 进化引擎
│   ├── engine.py
│   ├── analyzer.py
│   ├── generator.py
│   └── ...
└── koda_adapter.py     ← EvoSkill 调用 Koda
```

Koda 只提供基础的 Agent + 工具能力。
