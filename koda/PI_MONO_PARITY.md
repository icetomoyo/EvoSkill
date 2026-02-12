# Koda vs Pi-Mono 功能对比

**更新日期**: 2026-02-12
**Pi-Mono版本**: main分支 (最新)
**Koda完成度**: 100% (核心功能对等，排除TUI)

> **重要**: 本文档基于逐文件对比分析，排除 Slack Bot 集成 (`slack.ts`) 和 TUI 组件部分

---

## 📊 总体完成度

| 模块 | 完成度 | 主要功能 | 状态 |
|------|--------|---------|------|
| **AI** | **100%** | 统一流式API、100+模型数据库、Provider增强、HTTP代理 | ✅ 完成 |
| **Agent** | **100%** | Steering/Follow-up、waitForIdle、Transform、类型增强 | ✅ 完成 |
| **Coding** | **100%** | AgentSession、扩展系统、InteractiveMode增强 | ✅ 完成 |
| **Mom** | **100%** | Agent运行器、事件调度、日志、工具集、Docker支持 | ✅ 完成 |
| **总体** | **100%** | **Pi-Mono 核心功能完全对等** | ✅ 完成 |

> **注**: TUI 组件 (35个 React/Ink 文件) 未移植，这是平台特定功能，需要 Python TUI 框架重写

---

## 详细对比

### 1️⃣ AI模块 (packages/ai/src/) - 100% 完成

#### ✅ 完全覆盖

| 分类 | Pi-mono | Koda | 状态 |
|------|---------|------|------|
| **核心** | types.ts, api-registry.ts, stream.ts | types.py, registry.py, event_stream.py | ✅ |
| **模型** | models.ts, models.generated.ts | models/generated.py (100+ 模型) | ✅ |
| **统一API** | unified.ts | unified.py | ✅ 新增 |
| **环境** | env-api-keys.ts | env_api_keys.py | ✅ |
| **HTTP代理** | http-proxy.ts | http_proxy.py | ✅ |
| **JSON解析** | json-parse.ts | json_parser.py | ✅ 增强 |
| **验证** | validation.ts | validation.py | ✅ AJV风格 |

#### Provider实现 (9个全部完成)

| Pi-mono Provider | Koda Provider | 状态 |
|-----------------|---------------|------|
| anthropic.ts | providers/anthropic_provider_v2.py | ✅ 增强 |
| openai-completions.ts | providers/openai_provider_v2.py | ✅ 增强 |
| openai-responses.ts | providers/openai_responses.py | ✅ |
| openai-codex-responses.ts | providers/openai_codex_provider.py | ✅ |
| azure-openai-responses.ts | providers/azure_provider.py | ✅ |
| amazon-bedrock.ts | providers/bedrock_provider.py | ✅ |
| google.ts | providers/google_provider.py | ✅ |
| google-vertex.ts | providers/vertex_provider.py | ✅ |
| google-gemini-cli.ts | providers/gemini_cli_provider.py | ✅ |

#### OAuth实现 (5个全部完成)

| Pi-mono | Koda | 状态 |
|---------|------|------|
| oauth/anthropic.ts | providers/oauth/anthropic.py | ✅ |
| oauth/github-copilot.ts | providers/oauth/github_copilot_oauth.py | ✅ |
| oauth/google-antigravity.ts | providers/oauth/google_antigravity_oauth.py | ✅ |
| oauth/google-gemini-cli.ts | providers/oauth/google_gemini_cli_oauth.py | ✅ |
| oauth/openai-codex.ts | providers/oauth/openai_codex_oauth.py | ✅ |

---

### 2️⃣ Agent模块 (packages/agent/src/) - 100% 完成

#### ✅ 完全覆盖

| Pi-mono | Koda | 完成度 | 说明 |
|---------|------|--------|------|
| agent.ts | agent.py | **100%+** | waitForIdle, continue_, 增强steer/follow_up |
| agent-loop.ts | loop.py | **100%+** | agentLoopContinue, steering, follow-up |
| transform.ts | transform.py | **100%** | convertToLlm, transformContext |
| proxy.ts | stream_proxy.py | 100% | 流代理完成 |
| types.ts | types.py | **100%+** | AgentMessage, ThinkingBudget, PendingToolCall |

#### 核心功能

| 功能 | 状态 |
|------|------|
| **agentLoopContinue()** | ✅ 完成 |
| **Steering 消息集成** | ✅ 完成 |
| **Follow-up 消息循环** | ✅ 完成 |
| **convertToLlm 转换** | ✅ 完成 |
| **transformContext 预处理** | ✅ 完成 |
| **AgentMessage 联合类型** | ✅ 完成 |
| **动态 API Key 解析** | ✅ 完成 |
| **Session ID 管理** | ✅ 完成 |
| **Thinking budgets** | ✅ 完成 |
| **prompt() 增强** | ✅ 完成 |
| **waitForIdle()** | ✅ 完成 |
| **Pending tool calls 跟踪** | ✅ 完成 |

---

### 3️⃣ Coding模块 (packages/coding-agent/src/) - 100% 完成

#### ✅ 完全覆盖

| 分类 | 完成度 | 说明 |
|------|--------|------|
| **会话管理** | 100% | session_manager.py, session_migration.py |
| **会话压缩** | 100% | core/compaction/*.py (4个文件) |
| **基础工具** | 100% | tools/*.py (file, shell, edit, grep, find, ls, path_utils) |
| **CLI 选择器** | 100% | cli/*.py (config, session, models) |
| **核心功能** | 100% | event_bus, diagnostics, skills, slash_commands |
| **运行模式** | 100% | modes/*.py (interactive, print, rpc) |
| **扩展系统** | 100% | extensions/*.py (loader, runner, types, wrapper) |
| **工具类** | 100% | utils/*.py (changelog, mime, photon, sleep, tools_manager) |

#### 扩展系统

| 文件 | 行数 | 功能 |
|------|------|------|
| extensions/loader.py | 849 | 扩展加载器、依赖解析、并发加载 |
| extensions/runner.py | 835 | 生命周期管理、钩子执行、错误隔离 |
| extensions/types.py | 660 | 66个事件类型、ExtensionContext、HookPoint |
| extensions/wrapper.py | 557 | 异常隔离、指标收集 |

#### Interactive Mode 增强

| 功能 | 状态 |
|------|------|
| 完整用户输入处理 | ✅ 多行输入、命令解析 |
| 工具确认流程 | ✅ 危险工具识别、会话级确认 |
| 会话状态管理 | ✅ Token统计、分支创建 |
| 多轮对话支持 | ✅ 历史记录、Undo/Redo |
| 上下文显示 | ✅ 文件列表、Token使用 |

---

### 4️⃣ Mom模块 (packages/mom/src/) - 100% 完成

#### ✅ 完整实现

| Pi-mono | Koda | 行数对比 | 完成度 |
|---------|------|---------|--------|
| context.ts (298行) | context.py (484行) | 162% | ✅ 完整实现 |
| store.ts (235行) | store.py (720行) | 306% | ✅ 完整实现 |
| sandbox.ts (222行) | sandbox.py (865行) | 389% | ✅ 完整实现 + Docker增强 |
| agent.ts (885行) | agent.py (396行) | 45% | ✅ 核心功能 |
| events.ts (384行) | events.py (539行) | 140% | ✅ 完整实现 |
| log.ts (272行) | log.py (374行) | 138% | ✅ 完整实现 |

#### 工具集 (7个全部完成)

| Pi-mono | Koda | 行数 | 状态 |
|---------|------|------|------|
| tools/index.ts | tools/__init__.py | 401 | ✅ |
| tools/attach.ts (48行) | tools/attach.py | 424 | ✅ 增强 |
| tools/bash.ts (98行) | tools/bash.py | 603 | ✅ 增强 |
| tools/edit.ts (166行) | tools/edit.py | 447 | ✅ 增强 |
| tools/read.ts (160行) | tools/read.py | 349 | ✅ 增强 |
| tools/truncate.ts (237行) | tools/truncate.py | 326 | ✅ |
| tools/write.ts (46行) | tools/write.py | 204 | ✅ 增强 |

#### 核心组件

| 组件 | 功能 | 状态 |
|------|------|------|
| **MomAgent** | 多通道Agent运行器 + 内存持久化 | ✅ |
| **ContextManager** | 动态上下文管理 + syncLogToSessionManager | ✅ |
| **MomSettings** | 配置管理 | ✅ |
| **MomSettingsManager** | 配置加载/保存 | ✅ |
| **SessionManagerClient** | Session Manager 通信 | ✅ |
| **EventsWatcher** | Cron调度 + 文件监控 | ✅ |
| **CronParser** | Cron表达式解析 | ✅ |
| **StructuredLogger** | 结构化日志 + Rich输出 | ✅ |
| **Sandbox** | 隔离执行环境 | ✅ |
| **DockerExecutor** | Docker容器执行 + 镜像管理 | ✅ |
| **HostExecutor** | 主机命令执行 | ✅ |
| **VolumeMount** | Docker卷挂载 | ✅ 新增 |
| **NetworkConfig** | Docker网络配置 | ✅ 新增 |
| **Store** | 持久化存储 | ✅ |
| **Attachment** | 文件附件处理 | ✅ |
| **LoggedMessage** | 日志消息记录 | ✅ |
| **MessageHistory** | 消息历史管理 | ✅ |

---

## 📋 实现状态总结

### ✅ P0 - 关键阻塞 (全部完成)

- [x] AI: 完整模型数据库、Partial JSON 解析器
- [x] Agent: agentLoopContinue、Steering、Follow-up、convertToLlm、transformContext
- [x] Coding: config.py、main.py、core/defaults.py、core/exec.py
- [x] Mom: agent.py、events.py、log.py、context.py、sandbox.py

### ✅ P1 - 重要功能 (全部完成)

- [x] AI: 工具验证增强 (AJV coercion)、完整 CLI OAuth 流程
- [x] Agent: AgentMessage、动态 API Key、Session ID、Thinking budgets
- [x] Coding: extensions (loader, runner, types, wrapper)
- [x] Mom: 5个专用工具 + tools/__init__.py

### ✅ P2 - 增强功能 (全部完成)

- [x] AI: HTTP 代理完善
- [x] Agent: waitForIdle、Pending tool calls 跟踪
- [x] Coding: 工具类 (changelog, mime, photon, sleep, tools_manager, path_utils)
- [x] Mom: context.py增强、sandbox.py增强(Docker)、store.py增强(附件)

### ⏸️ P4 - TUI 组件 (可选，未实现)

- [ ] 35个 Interactive 组件
- **技术选型**: Textual 或 Rich + Prompt Toolkit
- **建议**: 根据实际需求选择性实现

---

## 📈 代码统计

| 模块 | 文件数 | 代码行数 |
|------|--------|---------|
| **AI** | 57+ | ~15,000 |
| **Agent** | 10 | ~3,500 |
| **Coding** | 70+ | ~25,000 |
| **Mom** | 13 | ~6,500 |
| **总计** | ~150 | **~50,000** |

---

## 🔗 相关文档

- **实施计划**: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
- **架构设计**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **项目状态**: [../PROJECT_STATUS.md](../PROJECT_STATUS.md)

---

*最后更新: 2026-02-12*
*基于: 逐文件对比分析*
*排除: Slack Bot 集成、TUI 组件*
