# Koda vs Pi-Mono 详细对比报告

**对比日期**: 2026-02-11
**Koda路径**: `c:\Works\GitWorks\EvoSkill\koda`
**Pi-Mono路径**: `C:\Works\GitWorks\pi-mono\packages`

---

## 📊 整体统计

| 指标 | Pi-Mono (TS) | Koda (Python) | 状态 |
|------|--------------|---------------|------|
| **AI模块** | ~40个文件 | ~45个文件 | ✅ 覆盖 |
| **Agent模块** | 5个文件 | 8个文件 | ✅ 覆盖+扩展 |
| **Coding-Agent模块** | ~80个文件 | ~60个文件 | ⚠️ 部分简化 |
| **Mom模块** | 16个文件 | 3个文件 | ⚠️ 大幅简化 |

---

## 1️⃣ AI模块详细对比

### ✅ 完全覆盖 (命名差异)

| Pi-Mono | Koda | 说明 |
|---------|------|------|
| `env-api-keys.ts` | `env_api_keys.py` | 环境变量API Key管理 ✅ |
| `providers/register-builtins.ts` | `providers/register_builtins.py` | Provider自动注册 ✅ |
| `utils/typebox-helpers.ts` | `typebox_helpers.py` | JSON Schema验证 ✅ |
| `utils/validation.ts` | `validation.py` | 验证工具 ✅ |
| `utils/event-stream.ts` | `event_stream.py` | 事件流处理 ✅ |
| `utils/http-proxy.ts` | `http_proxy.py` | HTTP代理 ✅ |
| `utils/json-parse.ts` | `json_parse.py` + `json_parser.py` | JSON解析(拆分) ✅ |
| `utils/overflow.ts` | `overflow.py` | 上下文溢出处理 ✅ |
| `utils/sanitize-unicode.ts` | `sanitize_unicode.py` | Unicode清理 ✅ |
| `providers/anthropic.ts` | `providers/anthropic_provider_v2.py` | Anthropic Provider ✅ |
| `providers/openai-responses.ts` | `providers/openai_responses.py` | OpenAI Responses API ✅ |
| `providers/openai-codex-responses.ts` | `providers/openai_codex_provider.py` | Codex Provider ✅ |
| `providers/google.ts` | `providers/google_provider.py` | Google Provider ✅ |
| `providers/google-gemini-cli.ts` | `providers/gemini_cli_provider.py` | Gemini CLI ✅ |
| `providers/google-vertex.ts` | `providers/vertex_provider.py` | Vertex AI ✅ |
| `providers/azure-openai-responses.ts` | `providers/azure_provider.py` | Azure OpenAI ✅ |
| `providers/amazon-bedrock.ts` | `providers/bedrock_provider.py` | Bedrock Provider ✅ |
| `utils/oauth/google-antigravity.ts` | `providers/oauth/google_antigravity_oauth.py` | Google OAuth ✅ |
| `utils/oauth/google-gemini-cli.ts` | `providers/oauth/google_gemini_cli_oauth.py` | Gemini OAuth ✅ |
| `utils/oauth/openai-codex.ts` | `providers/oauth/openai_codex_oauth.py` | Codex OAuth ✅ |

### 🔴 真正缺失的功能

| Pi-Mono | 功能说明 | 优先级 | 影响 |
|---------|----------|--------|------|
| **`models.generated.ts`** | 自动生成的模型数据库(成本、上下文窗口等) | 🔴 **高** | 缺少完整模型元数据 |
| **`models.ts`** | 模型注册表和成本计算 | 🔴 **高** | 模型管理功能不完整 |
| **`cli.ts`** | AI包独立CLI(login/list命令) | 🟡 中 | 独立CLI工具缺失 |
| `utils/oauth/anthropic.ts` | Anthropic OAuth | 🟡 中 | 特定OAuth缺失 |
| `utils/oauth/github-copilot.ts` | GitHub Copilot OAuth | 🟡 中 | 特定OAuth缺失 |
| `utils/oauth/types.ts` | OAuth类型定义 | 🟢 低 | 类型安全 |

### ➕ Koda独有的功能

| Koda文件 | 功能说明 |
|----------|----------|
| `agent_proxy.py` | Agent代理功能 |
| `claude_code_mapping.py` | Claude Code兼容映射 |
| `config.py` | 统一配置管理 |
| `edits.py` | 编辑操作工具 |
| `factory.py` | Provider工厂模式 |
| `github_copilot.py` | GitHub Copilot支持 |
| `json_schema.py` | JSON Schema定义 |
| `models_utils.py` | 模型工具(部分替代models.ts) |
| `oauth.py` | 通用OAuth框架 |
| `provider.py` + `provider_base.py` | Provider抽象基类 |
| `rate_limiter.py` | 速率限制 |
| `registry.py` | Provider注册表(部分替代api-registry.ts) |
| `retry.py` | 重试机制 |
| `session.py` | 会话管理 |
| `settings.py` | 设置管理 |
| `token_counter.py` | Token计数 |

---

## 2️⃣ Agent模块详细对比

### ✅ 完全覆盖

| Pi-Mono | Koda | 说明 |
|---------|------|------|
| `agent.ts` | `agent.py` | 主Agent实现 ✅ |
| `agent-loop.ts` | `loop.py` | Agent事件循环 ✅ |
| `proxy.ts` | `stream_proxy.py` | 流代理 ✅ |

### 🔴 缺失

| Pi-Mono | 说明 |
|---------|------|
| `types.ts` | 专用类型定义(可能已合并到主types.py) |

### ➕ Koda扩展

| Koda文件 | 功能 |
|----------|------|
| `events.py` | 事件系统 |
| `parallel.py` | 并行Agent执行 |
| `queue.py` | 消息队列 |
| `tools.py` | 工具管理 |

---

## 3️⃣ Coding-Agent模块详细对比

### ✅ 核心功能覆盖

| Pi-Mono | Koda | 说明 |
|---------|------|------|
| `core/auth-storage.ts` | `auth_storage.py` | 认证存储 ✅ |
| `core/bash-executor.ts` | `bash_executor.py` | Bash执行器 ✅ |
| `core/extensions/*` | `extensions/*` | 扩展系统 ✅ |
| `core/footer-data-provider.ts` | `footer_data_provider.py` | Footer数据 ✅ |
| `core/frontmatter.ts` | `frontmatter.py` | Frontmatter解析 ✅ |
| `core/keybindings.ts` | `keybindings.py` | 快捷键 ✅ |
| `core/messages.ts` | `messages.py` | 消息处理 ✅ |
| `core/model-resolver.ts` | `model_resolver.py` | 模型解析 ✅ |
| `core/package-manager.ts` | `package_manager.py` | 包管理 ✅ |
| `core/prompt-templates.ts` | `prompt_templates.py` | 提示模板 ✅ |
| `core/resolve-config-value.ts` | `resolve_config_value.py` | 配置解析 ✅ |
| `core/resource-loader.ts` | `resource_loader.py` | 资源加载 ✅ |
| `core/sdk.ts` | `sdk.py` | SDK接口 ✅ |
| `core/session-manager.ts` | `session_manager.py` | 会话管理 ✅ |
| `core/settings-manager.ts` | `settings_manager.py` | 设置管理 ✅ |
| `core/skills.ts` | `skills.py` | Skills系统 ✅ |
| `core/slash-commands.ts` | `slash_commands.py` | Slash命令 ✅ |
| `core/system-prompt.ts` | `system_prompt.py` | 系统提示 ✅ |
| `core/timings.ts` | `timings.py` | 计时工具 ✅ |
| `core/tools/bash.ts` | `tools/shell_tool.py` | Shell工具 ✅ |
| `core/tools/edit*.ts` | `tools/edit_*.py` | 编辑工具(拆分实现) ✅ |
| `core/tools/find.ts` | `tools/find_tool.py` | Find工具 ✅ |
| `core/tools/grep.ts` | `tools/grep_tool.py` | Grep工具 ✅ |
| `core/tools/ls.ts` | `tools/ls_tool.py` | LS工具 ✅ |
| `modes/print-mode.ts` | `modes/print_mode.py` | 打印模式 ✅ |
| `modes/rpc/*` | `modes/rpc/*` | RPC模式 ✅ |
| `utils/clipboard.ts` | `utils/clipboard.py` | 剪贴板 ✅ |
| `utils/git.ts` | `utils/git.py` | Git工具 ✅ |
| `utils/image-convert.ts` | `utils/image_convert.py` | 图片转换 ✅ |
| `utils/shell.ts` | `utils/shell.py` | Shell工具 ✅ |

### ⚠️ 功能位置差异

| Pi-Mono | Koda | 说明 |
|---------|------|------|
| `core/compaction/*` | `koda/mes/*.py` | 压缩功能独立为mes模块 |
| `utils/image-resize.ts` | `coding/_support/image_resize.py` | 图片缩放 |
| `core/tools/read.ts` + `write.ts` | `tools/file_tool.py` | 合并为文件工具 |

### 🔴 真正缺失

| Pi-Mono | 功能说明 | 优先级 |
|---------|----------|--------|
| **`core/compaction/*`** | 会话压缩/摘要(在mes/中简化实现) | 🔴 **高** |
| `cli/config-selector.ts` | 配置选择器(TUI) | 🟡 中 |
| `cli/file-processor.ts` | 文件处理器 | 🟡 中 |
| `cli/list-models.ts` | 模型列表(TUI) | 🟡 中 |
| `cli/session-picker.ts` | 会话选择器(TUI) | 🟡 中 |
| `core/defaults.ts` | 默认值定义 | 🟢 低 |
| `core/diagnostics.ts` | 诊断工具 | 🟢 低 |
| `core/event-bus.ts` | 事件总线 | 🟢 低 |
| `core/exec.ts` | 执行工具 | 🟢 低 |
| `core/export-html/*` | HTML导出(简化实现) | 🟢 低 |
| `core/model-registry.ts` | 模型注册表 | 🟢 低 |
| `modes/interactive/*` | 交互式TUI组件 | 🟢 低 |
| `utils/clipboard-image.ts` | 图片剪贴板 | 🟢 低 |
| `utils/mime.ts` | MIME类型检测 | 🟢 低 |
| `utils/photon.ts` | Photon图像处理 | 🟢 低 |
| `utils/tools-manager.ts` | 工具管理器 | 🟢 低 |

---

## 4️⃣ Mom模块详细对比

### ⚠️ 大幅简化

| Pi-Mono | Koda | 状态 |
|---------|------|------|
| `agent.ts` | ❌ 缺失 | Mom Agent未实现 |
| `context.ts` | `context.py` | ✅ 存在 |
| `download.ts` | ❌ 缺失(移至coding) | 📝 位置变更 |
| `events.ts` | ❌ 缺失 | ⚠️ 缺失 |
| `log.ts` | ❌ 缺失 | ⚠️ 缺失 |
| `main.ts` | ❌ 缺失 | ⚠️ 缺失 |
| `sandbox.ts` | `sandbox.py` | ✅ 存在 |
| `slack.ts` | ❌ 缺失 | ⚠️ 缺失(用户说明不需要) |
| `store.ts` | `store.py` | ✅ 存在 |
| `tools/*.ts` | ❌ 缺失 | ⚠️ 工具未实现 |

**结论**: Mom模块在Koda中大幅简化，仅保留核心sandbox/context/store功能。

---

## 5️⃣ 核心缺失清单 (按优先级)

### 🔴 高优先级 (影响核心功能)

| # | 缺失项 | Pi-Mono位置 | 影响说明 |
|---|--------|-------------|----------|
| 1 | **模型数据库** | `ai/models.generated.ts` | 缺少完整模型元数据(成本、上下文等) |
| 2 | **模型注册表** | `ai/models.ts` | 模型管理和成本计算 |
| 3 | **会话压缩** | `coding-agent/core/compaction/*` | 长会话管理关键功能 |
| 4 | **Mom Agent** | `mom/agent.ts` | Mom完整功能缺失 |

### 🟡 中优先级 (功能增强)

| # | 缺失项 | Pi-Mono位置 | 影响说明 |
|---|--------|-------------|----------|
| 5 | AI包CLI | `ai/cli.ts` | 独立OAuth登录工具 |
| 6 | Anthropic OAuth | `ai/utils/oauth/anthropic.ts` | 特定Provider认证 |
| 7 | GitHub Copilot OAuth | `ai/utils/oauth/github-copilot.ts` | 特定Provider认证 |
| 8 | TUI选择器 | `coding-agent/cli/*-selector.ts` | 交互式配置选择 |
| 9 | 事件总线 | `coding-agent/core/event-bus.ts` | 组件间通信 |

### 🟢 低优先级 (可选增强)

| # | 缺失项 | Pi-Mono位置 | 影响说明 |
|---|--------|-------------|----------|
| 10 | OAuth类型 | `ai/utils/oauth/types.ts` | 类型定义 |
| 11 | 交互式TUI | `coding-agent/modes/interactive/*` | 完整TUI界面 |
| 12 | 诊断工具 | `coding-agent/core/diagnostics.ts` | 问题诊断 |
| 13 | 工具管理器 | `coding-agent/utils/tools-manager.ts` | 工具生命周期 |

---

## 6️⃣ 架构差异总结

| 方面 | Pi-Mono | Koda |
|------|---------|------|
| **语言** | TypeScript | Python |
| **模型定义** | 集中式`models.generated.ts` | 分散到各模块 |
| **OAuth位置** | `ai/utils/oauth/` | `ai/providers/oauth/` |
| **压缩功能** | `coding-agent/core/compaction/` | `koda/mes/` (独立模块) |
| **编辑工具** | 单文件`edit.ts` | 拆分为多个文件 |
| **Provider组织** | 单文件多版本 | 多文件区分版本(v2) |
| **流处理入口** | `ai/stream.ts` | 各Provider的`stream()`方法 |
| **工具组织** | `core/tools/` | `tools/` (更扁平) |

---

## 7️⃣ 完成度评估

| 模块 | 完成度 | 说明 |
|------|--------|------|
| **AI核心** | 90% | 缺少模型数据库和CLI |
| **Agent** | 95% | 功能完整，有扩展 |
| **Coding-Agent** | 85% | 核心功能完整，TUI简化 |
| **Mom** | 40% | 大幅简化，仅保留核心 |
| **整体** | **85%** | 生产可用，有改进空间 |

---

## 8️⃣ 建议行动

### 如需要100%复刻:

1. **实现模型数据库** (`ai/models/generated.py`)
   - 包含所有提供商的模型定义
   - 成本、上下文窗口、能力标记
   
2. **完善压缩功能** (将`mes/`整合到`coding/`)
   - 分支摘要
   - 会话压缩
   
3. **实现Mom完整功能**
   - Mom Agent
   - Mom工具

### 如当前版本已满足需求:

- **生产就绪**: 当前85%完成度已足够使用
- **核心功能**: AI、Agent、Coding核心功能完整
- **缺失功能**: 主要是TUI、独立CLI、完整模型数据库

---

*报告生成时间: 2026-02-11*
*对比工具: Manual code analysis + Kimi Code CLI*
