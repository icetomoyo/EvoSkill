# Koda vs Pi-mono 逐文件对比分析报告

## 模块: ai (AI Provider模块)

### 完全覆盖的文件 (功能对等)

| Pi-mono | Koda | 备注 |
|---------|------|------|
| types.ts | types.py | 功能对等，包含所有核心类型定义 |
| stream.ts | session.py | 功能对等，流式处理 |
| api-registry.ts | registry.py | 功能对等，API注册 |
| env-api-keys.ts | env_api_keys.py | 功能对等，环境变量API密钥 |
| models.ts | models/ | 功能对等，模型注册和管理 |
| utils/event-stream.ts | event_stream.py | 功能对等，事件流处理 |
| utils/json-parse.ts | json_parse.py/json_parser.py | 功能对等，JSON解析 |
| utils/overflow.ts | overflow.py | 功能对等，上下文溢出检测 |
| utils/validation.ts | validation.py | 功能对等，消息验证 |
| utils/oauth/* | providers/oauth/ | 功能对等，OAuth支持 |
| providers/register-builtins.ts | providers/register_builtins.py | 功能对等，内置Provider注册 |
| providers/anthropic.ts | providers/anthropic_provider.py | 功能对等，Anthropic支持 |
| providers/openai-completions.ts | providers/openai_provider.py | 功能对等，OpenAI支持 |
| providers/openai-responses.ts | providers/openai_responses.py | 功能对等，OpenAI Responses |
| providers/google.ts | providers/google_provider.py | 功能对等，Google支持 |
| providers/amazon-bedrock.ts | providers/bedrock_provider.py | 功能对等，AWS Bedrock |
| providers/azure-openai-responses.ts | providers/azure_provider.py | 功能对等，Azure支持 |
| providers/openai-codex-responses.ts | providers/openai_codex_provider.py | 功能对等，OpenAI Codex |
| providers/google-vertex.ts | providers/vertex_provider.py | 功能对等，Google Vertex |
| providers/google-gemini-cli.ts | providers/gemini_cli_provider.py | 功能对等，Gemini CLI |

### 缺失的文件 (需要实现)

| Pi-mono | 优先级 | 功能说明 |
|---------|--------|----------|
| utils/http-proxy.ts | P1 | HTTP代理支持 |
| utils/oauth/types.ts | P2 | OAuth类型定义（基础已实现） |
| utils/sanitize-unicode.ts | P2 | Unicode清理 |
| utils/typebox-helpers.ts | P2 | TypeBox辅助函数（Python不需要） |
| providers/simple-options.ts | P2 | 简化选项处理 |
| providers/transform-messages.ts | P2 | 消息转换工具 |
| providers/openai-responses-shared.ts | P2 | OpenAI Responses共享逻辑 |
| providers/google-shared.ts | P2 | Google共享逻辑 |
| cli.ts | P1 | AI模块CLI |
| scripts/generate-models.ts | P2 | 模型生成脚本 |

### Koda独有的文件

| 文件 | 说明 |
|------|------|
| factory.py | Provider工厂模式 |
| provider_base.py | Provider基类 |
| agent_proxy.py | Agent代理 |
| config.py | 配置解析 |
| rate_limiter.py | 速率限制 |
| retry.py | 重试机制 |
| token_counter.py | Token计数 |
| settings.py | 设置管理 |
| models/costs.py | 模型成本计算 |
| models/generated.py | 生成的模型定义 |

---

## 模块: agent (Agent模块)

### 完全覆盖的文件 (功能对等)

| Pi-mono | Koda | 备注 |
|---------|------|------|
| types.ts | events.py | 功能对等，事件类型定义 |
| agent.ts | agent.py | 功能对等，Agent核心类 |
| agent-loop.ts | loop.py | 功能对等，Agent循环 |
| proxy.ts | stream_proxy.py | 功能对等，流代理 |
| index.ts | __init__.py | 功能对等，模块导出 |

### 缺失的文件 (需要实现)

| Pi-mono | 优先级 | 功能说明 |
|---------|--------|----------|
| (无核心缺失) | - | Agent模块核心功能已覆盖 |

### Koda独有的文件

| 文件 | 说明 |
|------|------|
| events.py | 扩展的事件系统 |
| parallel.py | 并行执行支持 |
| queue.py | 消息队列（steering/follow-up） |
| tools.py | Agent工具注册表 |

---

## 模块: coding-agent (Coding Agent模块)

### 完全覆盖的文件 (功能对等)

| Pi-mono | Koda | 备注 |
|---------|------|------|
| core/auth-storage.ts | auth_storage.py | 功能对等，认证存储 |
| core/bash-executor.ts | bash_executor.py | 功能对等，Bash执行 |
| core/event-bus.ts | core/event_bus.py | 功能对等，事件总线 |
| core/model-resolver.ts | model_resolver.py | 功能对等，模型解析 |
| core/package-manager.ts | package_manager.py | 功能对等，包管理 |
| core/prompt-templates.ts | prompt_templates.py | 功能对等，提示模板 |
| core/resolve-config-value.ts | resolve_config_value.py | 功能对等，配置解析 |
| core/resource-loader.ts | resource_loader.py | 功能对等，资源加载 |
| core/session-manager.ts | session_manager.py | 功能对等，会话管理 |
| core/settings-manager.ts | settings_manager.py | 功能对等，设置管理 |
| core/skills.ts | skills.py | 功能对等，技能系统 |
| core/slash-commands.ts | slash_commands.py | 功能对等，斜杠命令 |
| core/system-prompt.ts | system_prompt.py | 功能对等，系统提示 |
| core/timings.ts | timings.py | 功能对等，计时 |
| core/tools/bash.ts | tools/shell_tool.py | 功能对等，Shell工具 |
| core/tools/read.ts | tools/file_tool.py | 功能对等，文件读取 |
| core/tools/write.ts | tools/file_tool.py | 功能对等，文件写入 |
| core/tools/edit.ts | tools/edit_*.py | 功能对等，编辑工具 |
| core/tools/grep.ts | tools/grep_tool.py | 功能对等，搜索工具 |
| core/tools/find.ts | tools/find_tool.py | 功能对等，查找工具 |
| core/tools/ls.ts | tools/ls_tool.py | 功能对等，列表工具 |
| core/compaction/*.ts | core/compaction/*.py | 功能对等，上下文压缩 |
| cli/*.ts | cli/*.py | 功能对等，CLI组件 |
| modes/interactive/*.ts | modes/interactive.py | 功能对等，交互模式 |
| modes/print-mode.ts | modes/print_mode.py | 功能对等，打印模式 |
| modes/rpc/*.ts | modes/rpc/*.py | 功能对等，RPC模式 |
| utils/clipboard.ts | utils/clipboard.py | 功能对等，剪贴板 |
| utils/git.ts | utils/git.py | 功能对等，Git工具 |
| utils/shell.ts | utils/shell.py | 功能对等，Shell工具 |

### 缺失的文件 (需要实现)

| Pi-mono | 优先级 | 功能说明 |
|---------|--------|----------|
| core/agent-session.ts | P0 | Agent会话核心（部分实现） |
| core/diagnostics.ts | P1 | 诊断系统 |
| core/exec.ts | P1 | 进程执行 |
| core/footer-data-provider.ts | P2 | 页脚数据提供 |
| core/model-registry.ts | P1 | 模型注册表 |
| core/sdk.ts | P1 | SDK接口 |
| core/tools/edit-diff.ts | P1 | 差异编辑 |
| core/tools/path-utils.ts | P2 | 路径工具 |
| core/tools/truncate.ts | P2 | 截断工具 |
| core/export-html/* | P2 | HTML导出 |
| core/extensions/loader.ts | P1 | 扩展加载器 |
| core/extensions/runner.ts | P1 | 扩展运行器 |
| core/extensions/wrapper.ts | P2 | 扩展包装器 |
| core/defaults.ts | P2 | 默认配置 |
| utils/clipboard-image.ts | P2 | 图片剪贴板 |
| utils/frontmatter.ts | P2 | Frontmatter解析 |
| utils/image-convert.ts | P2 | 图片转换 |
| utils/image-resize.ts | P2 | 图片调整 |

### Koda独有的文件

| 文件 | 说明 |
|------|------|
| _support/ | 支持模块 |
| _support/image_resize.py | 图片调整支持 |
| _support/multimodal_types.py | 多模态类型 |
| _support/truncation.py | 截断支持 |
| tools/edit_diff_tool.py | 差异编辑工具 |
| tools/edit_enhanced.py | 增强编辑 |
| tools/edit_fuzzy.py | 模糊编辑 |
| tools/edit_operations.py | 编辑操作 |
| tools/edit_utils.py | 编辑工具 |
| session_entries.py | 会话条目 |
| session_migration.py | 会话迁移 |
| download.py | 下载功能 |
| export_html.py | HTML导出（简化版） |
| oauth/google_oauth.py | Google OAuth |
| model_schema.py | 模型模式 |

---

## 模块: mom (Mom模块)

### 完全覆盖的文件 (功能对等)

| Pi-mono | Koda | 备注 |
|---------|------|------|
| src/context.ts | context.py | 功能对等，上下文管理 |
| src/store.ts | store.py | 功能对等，存储 |
| src/sandbox.ts | sandbox.py | 功能对等，沙箱 |

### 缺失的文件 (需要实现)

| Pi-mono | 优先级 | 功能说明 |
|---------|--------|----------|
| src/agent.ts | P0 | Mom Agent核心（Slack集成） |
| src/events.ts | P1 | 事件系统 |
| src/log.ts | P1 | 日志系统 |
| src/main.ts | P1 | 入口点 |
| src/download.ts | P2 | 下载功能 |
| src/slack.ts | P0 | Slack集成 |
| src/tools/*.ts | P1 | Mom工具集 |

### Koda独有的文件

无

---

## 总结

### 按优先级统计

| 优先级 | 缺失数量 | 关键文件 |
|--------|----------|----------|
| P0 (关键) | 5个 | agent-session.ts, agent.ts (mom), slack.ts, tools/index.ts, edit-diff.ts |
| P1 (重要) | 13个 | diagnostics.ts, exec.ts, model-registry.ts, sdk.ts, extensions/loader.ts, extensions/runner.ts, events.ts, log.ts, main.ts, http-proxy.ts, cli.ts, model-registry.ts |
| P2 (可选) | 20个 | 各种工具、辅助函数、导出功能 |

### 总体完成度

| 模块 | 完成度 | 备注 |
|------|--------|------|
| ai | 85% | 核心Provider、类型、流处理已完成；缺少部分OAuth和CLI |
| agent | 90% | 核心Agent、事件、循环已完成；Koda还有扩展功能 |
| coding-agent | 75% | 核心工具、会话、设置已完成；缺少部分扩展和导出功能 |
| mom | 40% | 基础存储和上下文已覆盖；核心Slack Agent尚未实现 |

### 关键差距分析

1. **Mom模块**：这是最大的差距。Pi-mono的mom是一个完整的Slack Bot实现，而Koda只有基础的存储和上下文管理。

2. **扩展系统**：Pi-mono有完整的扩展加载、运行和包装系统，Koda有基础的扩展框架但缺少完整的加载器。

3. **交互式TUI**：Pi-mono有完整的终端UI组件系统，Koda只有基础的交互模式实现。

4. **HTML导出**：Pi-mono有完整的HTML导出功能，Koda只有简化版。

5. **诊断系统**：Pi-mono有专门的诊断系统，Koda缺少这部分。

### 建议实现顺序

1. **Phase 1 (核心功能)**：
   - coding-agent/core/sdk.ts
   - coding-agent/core/agent-session.ts
   - coding-agent/core/model-registry.ts

2. **Phase 2 (扩展功能)**：
   - coding-agent/core/extensions/loader.ts
   - coding-agent/core/extensions/runner.ts
   - coding-agent/core/diagnostics.ts

3. **Phase 3 (Mom)**：
   - mom/src/agent.ts
   - mom/src/slack.ts
   - mom/src/tools/

4. **Phase 4 (完善)**：
   - 各种CLI和导出功能
   - 辅助工具和优化
