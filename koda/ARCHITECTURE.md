# Koda 架构设计

## 整体架构

```
koda/
├── ai/              # AI Provider模块 - LLM API封装
├── agent/           # Agent模块 - 智能体核心
├── coding/          # Coding Agent模块 - 代码助手
├── mom/             # Mom模块 - Slack Bot（待完善）
└── mes/             # Message模块 - 消息处理
```

## 模块详情

### 1. AI模块 (koda.ai)

```
ai/
├── models/              # 模型数据库
│   ├── generated.py     # 70+模型定义
│   ├── registry.py      # 模型注册表
│   └── costs.py         # 成本计算
├── providers/           # Provider实现
│   ├── anthropic_provider.py
│   ├── openai_provider.py
│   ├── google_provider.py
│   ├── bedrock_provider.py
│   └── oauth/           # OAuth认证
├── cli.py               # AI CLI工具
├── types.py             # 核心类型
└── ...
```

**核心类**:
- `ModelInfo` - 模型信息（成本、能力、上下文）
- `BaseProvider` - Provider基类
- `ModelRegistry` - 模型注册表

### 2. Agent模块 (koda.agent)

```
agent/
├── agent.py         # Agent核心类
├── loop.py          # 事件循环
├── events.py        # 事件系统
├── parallel.py      # 并行执行
├── queue.py         # 消息队列
└── stream_proxy.py  # 流代理
```

**核心类**:
- `Agent` - 智能体核心
- `AgentLoop` - 事件循环
- `EventBus` - 事件总线

### 3. Coding模块 (koda.coding)

```
coding/
├── core/                # 核心功能
│   ├── compaction/      # 会话压缩
│   ├── event_bus.py     # 事件总线
│   └── diagnostics.py   # 诊断工具
├── tools/               # 工具集
│   ├── file_tool.py
│   ├── shell_tool.py
│   ├── edit_*.py        # 编辑工具
│   └── ...
├── cli/                 # CLI选择器
│   ├── config_selector.py
│   ├── session_picker.py
│   └── list_models.py
├── modes/               # 运行模式
│   ├── interactive.py
│   ├── print_mode.py
│   └── rpc/
└── ...
```

**核心类**:
- `SessionCompactor` - 会话压缩
- `FileTool` - 文件操作
- `EditTool` - 代码编辑
- `ConfigSelector` - 配置选择

### 4. Mom模块 (koda.mom)

```
mom/
├── context.py       # 上下文管理
├── store.py         # 存储
└── sandbox.py       # 沙箱

# 待实现:
├── agent.py         # Slack Bot Agent
├── slack.py         # Slack集成
└── tools/           # Mom工具
```

### 5. Message模块 (koda.mes)

```
mes/
├── compaction.py    # 消息压缩
├── history.py       # 历史管理
├── formatter.py     # 格式化
└── optimizer.py     # 优化器
```

## 数据流

```
用户输入 → Agent → AI Provider
              ↓
         工具调用 → Coding Tools
              ↓
         会话管理 → Compaction
              ↓
         输出 ← Stream
```

## 关键设计决策

### 1. Provider架构
- 使用 `BaseProvider` 抽象基类
- 每个Provider独立实现 `stream()` 和 `complete()`
- 统一的 `ModelInfo` 定义成本和上下文

### 2. 工具系统
- 工具继承基类，实现 `execute()` 方法
- 支持同步和异步执行
- 自动参数验证和错误处理

### 3. 会话管理
- `SessionManager` 管理会话生命周期
- `SessionCompactor` 自动压缩长会话
- `BranchSummarizer` 生成分支摘要

### 4. 扩展系统
- 基础扩展框架已实现
- 完整的加载器和运行器待实现

## 与Pi-Mono的架构差异

| 方面 | Pi-Mono | Koda |
|------|---------|------|
| 语言 | TypeScript | Python |
| 模型定义 | 集中式 | 模块化 |
| OAuth | `utils/oauth/` | `providers/oauth/` |
| 压缩 | `core/compaction/` | `mes/` + `core/compaction/` |
| 编辑工具 | 单文件 | 多文件拆分 |
| 事件系统 | 单文件 | 分层实现 |

## 性能考虑

- **异步优先**: 所有IO操作使用async/await
- **流式处理**: 支持SSE流式响应
- **Token计算**: 使用启发式算法估计
- **压缩策略**: 智能保留关键消息
