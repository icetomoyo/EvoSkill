# Koda - Pi-Mono Python Implementation

Koda 是 [Pi-Mono](https://github.com/pi-mono/pi-mono) 的 Python 实现，提供 AI Agent、Coding Agent 和 Mom 功能。

> **注意**: 本项目排除 Slack Bot 集成和 TUI 组件部分，专注于核心 Agent 和 Coding 功能。

---

## 📊 项目状态 (2026-02-12 更新)

| 模块 | 完成度 | 主要功能 | 状态 |
|------|--------|---------|------|
| **AI** | **100%** | 统一流式API、100+模型数据库、Provider增强、HTTP代理 | ✅ 完成 |
| **Agent** | **100%** | Steering/Follow-up、waitForIdle、Transform、类型增强 | ✅ 完成 |
| **Coding** | **100%** | AgentSession、扩展系统、InteractiveMode增强 | ✅ 完成 |
| **Mom** | **100%** | Agent运行器、事件调度、日志、工具集、Docker支持 | ✅ 完成 |
| **总体** | **100%** | **Pi-Mono 核心功能完全对等** | ✅ 完成 |

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/icetomoyo/EvoSkill.git
cd EvoSkill/koda

# 安装依赖
pip install -e ".[dev]"
```

### 使用示例

```python
# 使用统一 API
from koda.ai.unified import UnifiedClient

client = UnifiedClient(default_model="claude-sonnet-4")

# 简单完成
response = await client.ask("What is Python?")
print(response)

# 流式响应
async for chunk in client.ask_stream("Write a poem"):
    print(chunk, end="")

# 使用 Agent
from koda.agent import Agent, AgentConfig
from koda.agent.loop import AgentLoop

# Agent 支持 steering 和 follow-up
agent = Agent(llm_provider, config)
agent.steer("Focus on Python code")

async for event in agent.run("Create a web scraper"):
    print(event)

# 使用 Mom Agent
from koda.mom.agent import MomAgent

mom = MomAgent(provider)
await mom.start()

async for event in mom.handle_message("channel-1", "user-1", "Hello"):
    print(event)
```

---

## 📁 模块说明

### koda.ai - AI Provider 模块 ✅ 100%

- **models/** - 模型数据库 (100+ 模型定义，9 个 Provider)
- **providers/** - Provider 实现 (OpenAI、Anthropic、Google、Azure、Bedrock、Vertex、Gemini CLI、Codex、Kimi)
- **providers/oauth/** - OAuth 认证 (5 个 Provider)
- **unified.py** - 统一流式入口 API
- **http_proxy.py** - HTTP 代理支持
- **json_parser.py** - Partial JSON 流式解析器
- **validation.py** - AJV 风格类型强制转换

### koda.agent - Agent 模块 ✅ 100%

- **agent.py** - Agent 核心 + 增强 (waitForIdle, continue_, steer/follow_up)
- **loop.py** - 事件循环 (steering, follow-up, agentLoopContinue)
- **transform.py** - 消息转换 (convert_to_llm, transform_context)
- **types.py** - 类型定义 (AgentMessage, ThinkingBudget, PendingToolCall)
- **stream_proxy.py** - 流代理
- **parallel.py** - 并行执行 (Koda 独有)

### koda.coding - Coding Agent 模块 ✅ 100%

- **core/** - 核心功能
  - agent_session.py - Agent 会话
  - event_bus.py - 事件总线
  - diagnostics.py - 诊断工具
  - compaction/ - 会话压缩
  - exec.py - 工具执行框架
- **tools/** - 工具集 (file, shell, edit, grep, find, ls, path_utils)
- **utils/** - 工具类 (changelog, mime, photon, sleep, tools_manager)
- **cli/** - CLI 选择器 (config, session, models)
- **modes/** - 运行模式 (interactive, print, rpc)
- **extensions/** - 扩展系统 (loader, runner, types, wrapper)
- **main.py** - CLI 主入口
- **config.py** - 配置管理

### koda.mom - Mom 模块 ✅ 100%

- **agent.py** - Mom Agent 运行器 + 多通道管理
- **context.py** - 上下文管理 + syncLogToSessionManager
- **sandbox.py** - 沙箱 + Docker 支持 (DockerExecutor, VolumeMount, NetworkConfig)
- **store.py** - 存储 + 附件处理 + 消息历史
- **events.py** - 事件调度 (Cron + 文件监控)
- **log.py** - 结构化日志 + Rich 输出
- **tools/** - 专用工具集 (attach, bash, edit, read, truncate, write)

---

## 📚 文档

### 核心文档
- **[PI_MONO_PARITY.md](PI_MONO_PARITY.md)** - Pi-Mono 功能对比和完成度 ⭐
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - 完整实施计划 ⭐

### 项目文档
- **[../PROJECT_STATUS.md](../PROJECT_STATUS.md)** - 项目状态总览

---

## 🔧 开发

### 环境设置

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 代码格式化
black koda/
```

### 使用 CLI

```bash
# AI CLI
python -m koda.ai.cli login
python -m koda.ai.cli models
python -m koda.ai.cli status

# Coding CLI
python -m koda.coding.main
python -m koda.coding.main --print "What is Python?"
```

---

## 🆚 与 Pi-Mono 的差异

| 方面 | Pi-Mono (TS) | Koda (Python) |
|------|--------------|---------------|
| **语言** | TypeScript | Python 3.10+ |
| **AI 模块** | 37 文件 | 57+ 文件 (增强) |
| **Agent 模块** | 5 文件 | 10 文件 (增强) |
| **Coding 模块** | 100+ 文件 | 70+ 文件 (无 TUI) |
| **Mom 模块** | 16 文件 | 13 文件 |
| **TUI** | React/Ink (35组件) | 未实现 (需 Python 框架) |
| **核心功能** | 100% | **100% 对等** |

---

## 📄 许可证

本项目采用 [MIT](../LICENSE) 许可证开源。

---

## 🔗 相关链接

- **Pi-Mono**: https://github.com/pi-mono/pi-mono
- **EvoSkill Repo**: https://github.com/icetomoyo/EvoSkill
- **Issues**: https://github.com/icetomoyo/EvoSkill/issues

---

**维护者**: @icetomoyo

**最后更新**: 2026-02-12

**版本**: v1.0.0 (100% Pi-Mono 核心功能对等)
