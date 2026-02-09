# Koda 模块设计文档

> 完全对标 Pi Mono (badlogic/pi-mono)

---

## 架构概览

```
koda/
├── ai/          # LLM 统一接口 (packages/ai)
├── mes/         # 消息优化 (packages/mom)
├── agent/       # Agent 框架 (packages/agent)
└── tools/       # 7 个内置工具 (coding-agent)
```

---

## 1. ai 模块 - LLM 统一接口

### 对标: packages/ai

### 功能
- 支持 15+ LLM 提供商
- 统一的消息格式
- 流式响应
- 自动模型发现

### 核心组件

```python
# 抽象接口
LLMProvider
├── chat(messages, tools, stream) → StreamEvent
├── get_models() → List[Model]
└── get_default_model() → str

# 消息格式
Message
├── role: str
├── content: str | List[ContentPart]
├── tool_calls: List[ToolCall]
└── tool_call_id: str

# Provider 实现
OpenAIProvider      # OpenAI + 兼容 API
AnthropicProvider   # Claude + thinking
KimiProvider        # Moonshot + Kimi For Coding
```

### 使用示例

```python
from koda import ai

# 创建 provider
provider = ai.create_provider("openai", api_key="sk-...")

# 或使用 Kimi
kimi = ai.create_provider("kimi", for_coding=True)

# 聊天
messages = [
    ai.Message.system("You are a coder"),
    ai.Message.user("Hello"),
]

async for event in provider.chat(messages, stream=True):
    if event.type == "text":
        print(event.data, end="")
```

---

## 2. mes 模块 - 消息优化

### 对标: packages/mom

### 功能
- Token 效率优化
- 上下文压缩
- 历史管理
- 分支支持

### 核心组件

```python
# 消息优化
MessageOptimizer
├── optimize(messages) → OptimizationResult
├── count_tokens(messages) → int
└── should_compact() → bool

# 格式化
MessageFormatter
├── format_messages(messages) → List[FormattedMessage]
└── format_tools(tools) → List[ToolDef]

# 历史管理
HistoryManager
├── add_message(msg)
├── compact() → CompactionResult
├── branch(name, from_id)
├── switch_branch(name)
├── save(path)
└── load(path)
```

### 使用示例

```python
from koda import mes

# 优化消息
optimizer = mes.MessageOptimizer(max_tokens=128000)
result = optimizer.optimize(messages)
print(f"Saved {result.savings} tokens")

# 格式化给不同 provider
formatter = mes.MessageFormatter("anthropic")
formatted = formatter.format_messages(messages)

# 管理历史
history = mes.HistoryManager()
history.add_message(ai.Message.user("Hello"))
history.compact()  # 自动压缩
history.save(Path("session.jsonl"))
```

---

## 3. agent 模块 - Agent 框架

### 对标: packages/agent

### 功能
- 事件驱动架构
- 消息队列
- 工具注册表
- 状态管理

### 核心组件

```python
# 事件系统
EventBus
├── on(event_type, handler)
├── once(event_type, handler)
├── emit(event)
└── emit_new(event_type, data)

EventType
├── AGENT_START/END
├── TURN_START/END
├── LLM_START/DELTA/END/ERROR
├── TOOL_CALL_START/END/RESULT/ERROR
├── COMPACTION_START/END
└── ERROR, CANCELLED

# 工具注册表
ToolRegistry
├── register(tool)
├── execute(name, args) → result
└── get_definitions() → List[ToolDef]

# 消息队列
MessageQueue
├── queue_steering(content)
├── queue_follow_up(content)
├── get_next() → QueuedMessage
└── DeliveryMode: STEERING, FOLLOW_UP

# Agent
Agent
├── run(user_input) → AsyncIterator[Event]
├── cancel()
├── queue_steering(content)
└── state: AgentState
```

### 使用示例

```python
from koda import agent, ai

# 创建 agent
provider = ai.create_provider("openai", api_key="sk-...")
cfg = agent.AgentConfig(max_iterations=10)
ag = agent.Agent(provider, cfg)

# 订阅事件
ag.events.on(agent.EventType.TOOL_CALL_START, lambda e: print(f"Tool: {e.data}"))

# 运行
async for event in ag.run("List files"):
    if event.type == agent.EventType.LLM_DELTA:
        print(event.data["text"], end="")
    elif event.type == agent.EventType.TOOL_RESULT:
        print(f"\nResult: {event.data['result']}")
```

---

## 4. 模块关系

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   EventBus   │  │  ToolRegistry│  │ MessageQueue │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              HistoryManager (mes)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       LLMProvider (ai)                      │
│              OpenAI / Anthropic / Kimi...                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 完全对标 Pi Mono

| Pi Mono Package | Koda Module | Status |
|-----------------|-------------|--------|
| packages/ai | koda/ai | ✅ Complete |
| packages/mom | koda/mes | ✅ Complete |
| packages/agent | koda/agent | ✅ Complete |
| packages/coding-agent/tools | koda/tools | ✅ Complete |
| packages/tui | (future) | ⏳ Optional |
| packages/pods | (future) | ⏳ Optional |

---

## 6. 使用完整示例

```python
import asyncio
from koda import ai, agent

async def main():
    # 1. 创建 LLM provider
    provider = ai.create_provider("kimi", 
        api_key="sk-...",
        for_coding=True
    )
    
    # 2. 配置 Agent
    config = agent.AgentConfig(
        max_iterations=10,
        enable_compaction=True,
        default_tools=["read", "write", "edit", "bash", "grep"],
    )
    
    # 3. 创建 Agent
    ag = agent.Agent(provider, config)
    
    # 4. 监听事件
    @ag.events.on(agent.EventType.LLM_DELTA)
    def on_text(event):
        print(event.data["text"], end="", flush=True)
    
    @ag.events.on(agent.EventType.TOOL_CALL_START)
    def on_tool_start(event):
        print(f"\n[Using {event.data['tool']}]\n")
    
    # 5. 运行
    async for event in ag.run("Create a hello.py file"):
        if event.type == agent.EventType.AGENT_END:
            print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. 关键设计决策

### 7.1 为什么这样分层?

**ai 模块**: LLM 接口是基础设施，需要独立
**mes 模块**: 消息优化是通用能力，可被多种 Agent 使用
**agent 模块**: 高层框架，组合 ai + mes + tools

### 7.2 与 Pi Mono 的差异

| 方面 | Pi Mono (TS) | Koda (Python) |
|------|--------------|---------------|
| 语言 | TypeScript | Python |
| 包管理 | npm | pip |
| 配置 | ~/.pi/agent/ | ~/.koda/ |
| 扩展 | TypeScript extensions | Python plugins (future) |

### 7.3 扩展性

通过 **hooks** 和 **event system**，可以扩展:
- 自定义 tools
- 自定义 LLM providers
- 自定义 event handlers
- 自定义 compaction strategies

---

**Next**: 添加 TUI (终端 UI) 模块?
