# Koda vs Pi-Mono 功能对比

**更新日期**: 2026-02-11  
**Pi-Mono版本**: main分支  
**Koda完成度**: 80%

---

## 总体完成度

| 模块 | 完成度 | 关键差距 |
|------|--------|----------|
| AI Core | 85% | HTTP代理、部分CLI |
| Agent | 90% | 核心完整，有扩展 |
| Coding | 75% | 扩展系统待完善 |
| Mom | 40% | **Slack Bot缺失** |
| **整体** | **80%** | - |

---

## 详细对比

### AI模块 (packages/ai/src/)

#### ✅ 完全覆盖 (20个文件)

| Pi-mono | Koda | 说明 |
|---------|------|------|
| types.ts | types.py | 核心类型定义 |
| stream.ts | session.py | 流式处理 |
| models.ts + models.generated.ts | models/ | 模型数据库(70+模型) |
| env-api-keys.ts | env_api_keys.py | 环境变量API密钥 |
| utils/oauth/*.ts | providers/oauth/ | OAuth认证 |
| providers/*.ts | providers/*.py | 所有Provider实现 |

#### ⏳ 缺失文件 (10个)

| 文件 | 优先级 | 说明 |
|------|--------|------|
| cli.ts | P1 | AI CLI入口（已实现） |
| utils/http-proxy.ts | P1 | HTTP代理 |
| utils/sanitize-unicode.ts | P2 | Unicode清理 |
| providers/simple-options.ts | P2 | 简化选项 |
| scripts/generate-models.ts | P2 | 模型生成脚本 |

#### ➕ Koda独有

| 文件 | 说明 |
|------|------|
| models/generated.py | 完整模型数据库 |
| models/costs.py | 成本计算工具 |
| factory.py | Provider工厂 |
| rate_limiter.py | 速率限制 |
| retry.py | 重试机制 |

---

### Agent模块 (packages/agent/src/)

#### ✅ 完全覆盖 (5个文件)

| Pi-mono | Koda | 说明 |
|---------|------|------|
| agent.ts | agent.py | Agent核心 |
| agent-loop.ts | loop.py | 事件循环 |
| proxy.ts | stream_proxy.py | 流代理 |

#### ➕ Koda扩展

| 文件 | 说明 |
|------|------|
| parallel.py | 并行执行 |
| queue.py | 消息队列 |
| tools.py | 工具注册表 |
| events.py | 事件系统 |

---

### Coding模块 (packages/coding-agent/src/core/)

#### ✅ 完全覆盖 (35个文件)

| Pi-mono | Koda | 说明 |
|---------|------|------|
| auth-storage.ts | auth_storage.py | 认证存储 |
| bash-executor.ts | bash_executor.py | Bash执行 |
| session-manager.ts | session_manager.py | 会话管理 |
| settings-manager.ts | settings_manager.py | 设置管理 |
| skills.ts | skills.py | 技能系统 |
| compaction/*.ts | core/compaction/*.py | 会话压缩 |
| tools/*.ts | tools/*.py | 所有工具 |
| cli/*.ts | cli/*.py | CLI组件 |
| modes/*.ts | modes/*.py | 运行模式 |

#### ⏳ 缺失文件 (17个)

| 文件 | 优先级 | 说明 |
|------|--------|------|
| agent-session.ts | P0 | Agent会话核心 |
| sdk.ts | P1 | SDK接口 |
| model-registry.ts | P1 | 模型注册表 |
| extensions/loader.ts | P1 | 扩展加载器 |
| extensions/runner.ts | P1 | 扩展运行器 |
| diagnostics.ts | P1 | 诊断（已实现基础） |
| export-html/*.ts | P2 | HTML导出（简化版已存在） |

---

### Mom模块 (packages/mom/src/)

#### ✅ 基础覆盖 (3个文件)

| Pi-mono | Koda | 说明 |
|---------|------|------|
| context.ts | context.py | 上下文 |
| store.ts | store.py | 存储 |
| sandbox.ts | sandbox.py | 沙箱 |

#### ❌ 缺失文件 (7个) - **最大差距**

| 文件 | 优先级 | 说明 |
|------|--------|------|
| **agent.ts** | **P0** | **Slack Bot Agent核心** |
| **slack.ts** | **P0** | **Slack集成** |
| events.ts | P1 | 事件系统 |
| log.ts | P1 | 日志系统 |
| main.ts | P1 | 入口点 |
| tools/*.ts | P1 | Mom工具集 |

---

## 待实现清单

### P0 - 关键 (阻塞生产使用)

- [ ] **Mom Slack Bot**
  - `mom/agent.py` - Agent核心
  - `mom/slack.py` - Slack API集成
  - `mom/tools/` - Mom专用工具

- [ ] **Coding SDK完整接口**
  - `coding/sdk.py` 完善

### P1 - 重要 (影响体验)

- [ ] **扩展系统**
  - `coding/core/extensions/loader.py`
  - `coding/core/extensions/runner.py`
  
- [ ] **Agent会话**
  - `coding/core/agent_session.py`

- [ ] **模型注册表**
  - `coding/core/model_registry.py`

- [ ] **HTTP代理**
  - `ai/http_proxy.py`

### P2 - 可选 (增强功能)

- [ ] HTML导出完整版
- [ ] 图片剪贴板
- [ ] 各种辅助工具
- [ ] TUI交互组件

---

## 使用建议

### 当前可用的功能

```python
# AI Provider
from koda.ai.models import get_model, calculate_cost
from koda.ai.providers import OpenAIProvider

# Agent
from koda.agent import Agent, AgentLoop

# Coding Tools
from koda.coding.tools import FileTool, ShellTool, EditTool
from koda.coding.core.compaction import SessionCompactor

# CLI
from koda.coding.cli import ConfigSelector, SessionPicker
```

### 暂不可用的功能

```python
# Mom Slack Bot - 未实现
from koda.mom import SlackBot  # ❌ 不存在

# 完整SDK - 部分实现
from koda.coding import SDK    # ⚠️ 基础实现
```

---

## 实现路线图

### Phase 1 (近期) - 核心功能
- Mom Slack Bot实现
- SDK接口完善

### Phase 2 (中期) - 扩展功能
- 扩展加载器
- 诊断系统完善

### Phase 3 (远期) - 完善
- TUI组件
- HTML导出
- 辅助工具

---

*最后更新: 2026-02-11*
