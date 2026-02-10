# Pi Mono vs Koda - 逐行详细对比

> 分析日期: 2026-02-09
> Pi Mono 来源: badlogic/pi-mono (GitHub)

---

## 1. packages/ai - AI Provider 接口

### 1.1 类型定义 (types.ts)

| 功能 | Pi Mono (TypeScript) | Koda (Python) | 状态 |
|------|---------------------|---------------|------|
| **KnownApi 联合类型** | 9 种 API 类型: openai-completions, openai-responses, azure-openai-responses, openai-codex-responses, anthropic-messages, bedrock-converse-stream, google-generative-ai, google-gemini-cli, google-vertex | 基础支持: openai, anthropic, kimi | ⚠️ 部分 |
| **KnownProvider** | 20+ 提供商: amazon-bedrock, anthropic, google, google-gemini-cli, google-vertex, openai, azure-openai-responses, openai-codex, github-copilot, xai, groq, cerebras, openrouter, kimi-coding 等 | 3 提供商: openai, anthropic, kimi | ❌ 缺失 |
| **ThinkingLevel** | minimal, low, medium, high, xhigh | 无 | ❌ 缺失 |
| **ThinkingBudgets** | 可配置的 token 预算 | 无 | ❌ 缺失 |
| **CacheRetention** | none, short, long | 无 | ❌ 缺失 |
| **StreamOptions** | temperature, maxTokens, signal, apiKey, cacheRetention, sessionId, onPayload, headers, maxRetryDelayMs | 部分: temperature, max_tokens, api_key | ⚠️ 部分 |
| **Message 类型** | UserMessage, AssistantMessage, ToolResultMessage 带完整元数据 | 基础 Message dataclass | ⚠️ 部分 |
| **Content 类型** | TextContent, ThinkingContent, ImageContent, ToolCall | 基础 content 字符串 | ⚠️ 部分 |
| **Usage 跟踪** | input, output, cacheRead, cacheWrite, totalTokens + 成本 | 无 | ❌ 缺失 |
| **StopReason** | stop, length, toolUse, error, aborted | 无 | ❌ 缺失 |
| **Tool 定义** | TypeBox schema 验证 | 基础 dict | ⚠️ 部分 |
| **Context** | systemPrompt, messages, tools | 类似结构 | ✅ 有 |
| **Model 接口** | 完整: id, name, api, provider, baseUrl, reasoning, input, cost, contextWindow, maxTokens, headers, compat | 部分: id, name, provider, context_window | ⚠️ 部分 |
| **OpenAICompletionsCompat** | 12+ 兼容性设置 | 无 | ❌ 缺失 |
| **OpenRouterRouting** | 提供商路由偏好 | 无 | ❌ 缺失 |

### 1.2 Model Registry (models.ts)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **自动生成的 MODELS** | models.generated.ts 从 API 自动生成 | 硬编码 9 个模型 | ⚠️ 基础 |
| **getModel()** | 类型安全的模型获取 | registry.get() | ✅ 有 |
| **getProviders()** | 返回 KnownProvider[] | list_providers() | ✅ 有 |
| **getModels()** | 按提供商获取模型 | list_models(provider=) | ✅ 有 |
| **calculateCost()** | 精确成本计算 ($/million tokens) | estimate_cost() | ✅ 有 |
| **supportsXhigh()** | 检测模型是否支持 xhigh 思考级别 | 无 | ❌ 缺失 |
| **modelsAreEqual()** | 模型相等比较 | 无 | ❌ 缺失 |

### 1.3 Providers

#### Anthropic Provider (~800 lines)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **streamAnthropic()** | 完整流式实现 | 基础实现 | ⚠️ 部分 |
| **Cache 控制** | cacheRetention, cacheControl | 无 | ❌ 缺失 |
| **Thinking/Effort** | thinkingEnabled, thinkingBudgetTokens, effort (low/medium/high/max) | 无 | ❌ 缺失 |
| **Interleaved Thinking** | 交错思考内容支持 | 无 | ❌ 缺失 |
| **Tool Choice** | auto, any, none, specific tool | 无 | ❌ 缺失 |
| **Claude Code 兼容** | 工具名规范化 (Read, Write, Edit, Bash...) | 无 | ❌ 缺失 |
| **OAuth Token 支持** | isOAuthToken 特殊处理 | 无 | ❌ 缺失 |
| **内容块转换** | 文本+图片混合内容 | 基础文本 | ⚠️ 部分 |
| **Signal 中断** | AbortSignal 完整支持 | 无 | ❌ 缺失 |
| **错误处理** | 详细的流式错误处理 | 基础 | ⚠️ 部分 |

#### OpenAI Provider (~1000+ lines)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **streamOpenAI()** | 多版本支持 | 基础实现 | ⚠️ 部分 |
| **Responses API** | openai-responses | 无 | ❌ 缺失 |
| **Completions API** | openai-completions | 类似 | ⚠️ 部分 |
| **Azure OpenAI** | azure-openai-responses | 无 | ❌ 缺失 |
| **Codex** | openai-codex-responses | 无 | ❌ 缺失 |
| **Reasoning Effort** | reasoning_effort 参数 | 无 | ❌ 缺失 |
| **Store 参数** | store: true/false | 无 | ❌ 缺失 |
| **开发者角色** | developer vs system | 无 | ❌ 缺失 |

#### Google Provider (~1500+ lines)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Google Generative AI** | google-generative-ai | 无 | ❌ 缺失 |
| **Gemini CLI** | google-gemini-cli | 无 | ❌ 缺失 |
| **Vertex AI** | google-vertex | 无 | ❌ 缺失 |
| **OAuth 流程** | 完整的 Google OAuth | 无 | ❌ 缺失 |
| **Thinking Signatures** | Google 特定思考签名 | 无 | ❌ 缺失 |

#### Amazon Bedrock (~600 lines)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Bedrock Converse Stream** | bedrock-converse-stream | 无 | ❌ 缺失 |
| **AWS SDK 集成** | 完整的 AWS 认证 | 无 | ❌ 缺失 |
| **交叉区域推理** | 自动区域选择 | 无 | ❌ 缺失 |

### 1.4 OAuth 系统 (utils/oauth/)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Google OAuth** | google-gemini-cli.ts, google-antigravity.ts | 无 | ❌ 缺失 |
| **Anthropic OAuth** | anthropic.ts | 无 | ❌ 缺失 |
| **GitHub Copilot OAuth** | github-copilot.ts | 无 | ❌ 缺失 |
| **OpenAI Codex OAuth** | openai-codex.ts | 无 | ❌ 缺失 |
| **PKCE 流程** | pkce.ts | 无 | ❌ 缺失 |
| **Token 刷新** | 自动刷新逻辑 | 无 | ❌ 缺失 |
| **本地回调服务器** | 本地 HTTP 服务器接收 token | 无 | ❌ 缺失 |

### 1.5 流处理 (stream.ts, event-stream.ts)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **AssistantMessageEventStream** | 完整的事件流类 | 无 | ❌ 缺失 |
| **事件类型** | start, text_start, text_delta, text_end, thinking_start, thinking_delta, thinking_end, toolcall_start, toolcall_delta, toolcall_end, done, error | 基础响应 | ⚠️ 部分 |
| **JSON 流解析** | parseStreamingJson | 无 | ❌ 缺失 |
| **溢出保护** | 上下文溢出检测 | 无 | ❌ 缺失 |
| **Unicode 清理** | sanitizeSurrogates | 无 | ❌ 缺失 |

---

## 2. packages/agent - Agent 核心

### 2.1 Agent Loop (agent-loop.ts)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **AgentLoop 类** | 完整的代理循环 | 基础实现 | ⚠️ 部分 |
| **工具执行** | 顺序工具调用执行 | 有 | ✅ 有 |
| **错误重试** | 指数退避重试 | 无 | ❌ 缺失 |
| **最大迭代限制** | 防止无限循环 | 无 | ❌ 缺失 |
| **并发控制** | 并发工具执行限制 | 无 | ❌ 缺失 |

### 2.2 Agent Proxy (proxy.ts)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Agent 代理** | 代理模式支持 | 无 | ❌ 缺失 |
| **多 Agent 协调** | 子 Agent 管理 | 无 | ❌ 缺失 |
| **负载均衡** | 请求分发 | 无 | ❌ 缺失 |

---

## 3. packages/coding-agent - 完整编码 Agent

### 3.1 Model Registry (core/model-registry.ts) ~500 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **自定义模型加载** | 从 models.json 加载 | 无 | ❌ 缺失 |
| **模型验证** | AJV schema 验证 | 无 | ❌ 缺失 |
| **Provider Override** | 基础 URL/headers/apiKey 覆盖 | 无 | ❌ 缺失 |
| **模型覆盖** | 每模型参数覆盖 | 无 | ❌ 缺失 |
| **动态 Provider 注册** | registerProvider() | 无 | ❌ 缺失 |
| **OAuth Provider 注册** | 集成 OAuth | 无 | ❌ 缺失 |
| **模型合并逻辑** | 内置+自定义模型合并 | 硬编码 | ⚠️ 基础 |
| **可用模型过滤** | getAvailable() 按认证过滤 | 无 | ❌ 缺失 |
| **配置值解析** | 环境变量+命令替换 | 无 | ❌ 缺失 |

### 3.2 Compaction 系统 (core/compaction/) ~800 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **compaction.ts** | 主压缩逻辑 | compaction.py | ⚠️ 基础 |
| **分支摘要** | branch-summarization.ts | 有基础 | ⚠️ 部分 |
| **CalculateContextTokens** | 精确 token 计算 | estimate_tokens() | ⚠️ 基础 |
| **CollectEntriesForBranchSummary** | 分支条目收集 | 无 | ❌ 缺失 |
| **FindCutPoint** | 智能切割点查找 | 无 | ❌ 缺失 |
| **GenerateBranchSummary** | 生成分支摘要 | 有基础 | ⚠️ 部分 |
| **SerializeConversation** | 会话序列化 | 有 | ✅ 有 |
| **ShouldCompact** | 压缩判断逻辑 | should_compact | ✅ 有 |
| **Turn 检测** | findTurnStartIndex | 无 | ❌ 缺失 |
| **FileOperations 跟踪** | 文件操作去重 | 无 | ❌ 缺失 |
| **Usage 跟踪** | getLastAssistantUsage | 无 | ❌ 缺失 |
| **DEFAULT_COMPACTION_SETTINGS** | 默认设置 | 硬编码 | ⚠️ 基础 |

### 3.3 Session Manager (core/session-manager.ts) ~1500 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **SessionManager 类** | 完整会话管理 | HistoryManager | ⚠️ 基础 |
| **树形分支导航** | 完整树操作 | 基础分支 | ⚠️ 部分 |
| **迁移系统** | migrateSessionEntries | 无 | ❌ 缺失 |
| **BuildSessionContext** | 构建会话上下文 | 无 | ❌ 缺失 |
| **SessionInfo 管理** | 元数据管理 | 无 | ❌ 缺失 |
| **导入/导出** | 会话导入导出 | save/load | ⚠️ 部分 |
| **标签系统** | 会话标签 | 无 | ❌ 缺失 |
| **修改时间跟踪** | modified timestamp | 无 | ❌ 缺失 |
| **垃圾回收** | 旧会话清理 | 无 | ❌ 缺失 |

### 3.4 Extension 系统 (core/extensions/) ~2000+ lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Extension API** | 完整扩展 API | 无 | ❌ 缺失 |
| **Extension 加载器** | loader.ts | 无 | ❌ 缺失 |
| **Extension 运行器** | runner.ts | 无 | ❌ 缺失 |
| **TypeScript 支持** | .ts 扩展直接加载 | 无 | ❌ 缺失 |
| **NPM 依赖** | 扩展可带 npm 依赖 | 无 | ❌ 缺失 |
| **事件系统** | 丰富的事件类型 | 基础事件 | ⚠️ 部分 |
| **UI 组件** | 自定义 UI 扩展 | 无 | ❌ 缺失 |
| **工具包装** | wrapToolWithExtensions | 无 | ❌ 缺失 |
| **Slash 命令** | 自定义命令 | 无 | ❌ 缺失 |
| **快捷键** | 自定义快捷键 | 无 | ❌ 缺失 |

### 3.5 工具系统 (core/tools/) ~2000+ lines

#### Edit Tool (edit.ts + edit-diff.ts) ~600 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **fuzzyFindText** | 模糊文本查找 | 无 | ❌ 缺失 |
| **normalizeForFuzzyMatch** | 智能引号/破折号规范化 | 无 | ❌ 缺失 |
| **detectLineEnding** | CRLF/LF 检测 | 无 | ❌ 缺失 |
| **restoreLineEndings** | 行尾恢复 | 无 | ❌ 缺失 |
| **stripBom** | UTF-8 BOM 处理 | 无 | ❌ 缺失 |
| **generateDiffString** | 统一 diff 生成 | generate_diff | ✅ 有 |
| **Plural operations** | 可插拔操作 | 硬编码 | ⚠️ 部分 |
| **AbortSignal 支持** | 可中断编辑 | 无 | ❌ 缺失 |

#### Bash Tool (bash.ts) ~400 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **spawn 上下文** | BashSpawnContext | 无 | ⚠️ 部分 |
| **_spawnHook** | 可插拔 spawn | 无 | ❌ 缺失 |
| **超时控制** | timeout 参数 | 无 | ❌ 缺失 |
| **环境变量** | env 参数注入 | 基础 | ⚠️ 部分 |
| **工作目录** | cwd 控制 | 有 | ✅ 有 |
| **Output 限制** | maxOutputBytes | 无 | ❌ 缺失 |
| **组合输出** | combined stdout/stderr | 有 | ✅ 有 |

#### Read/Write/Find/Grep/Ls Tools ~800 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Read** | 完整读取工具 | 有 | ✅ 有 |
| **Write** | 完整写入工具 | 有 | ✅ 有 |
| **Find** | Glob + 正则 | 有 | ✅ 有 |
| **Grep** | 递归搜索 | 有 | ✅ 有 |
| **Ls** | 目录列表 | 有 | ✅ 有 |
| **Truncate** | 智能截断 | 有 | ✅ 有 |

### 3.6 Auth Storage (core/auth-storage.ts) ~400 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **凭据类型** | ApiKeyCredential, OAuthCredential | 无 | ❌ 缺失 |
| **安全存储** | 加密存储 | 无 | ❌ 缺失 |
| **Token 刷新** | 自动刷新 | 无 | ❌ 缺失 |
| **Fallback Resolver** | 自定义解析器 | 无 | ❌ 缺失 |
| **OAuth Provider 管理** | getOAuthProviders | 无 | ❌ 缺失 |

### 3.7 Settings Manager (core/settings-manager.ts) ~500 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **设置分类** | Compaction, Image, Retry, PackageSource | 基础 Settings | ⚠️ 部分 |
| **层级配置** | 全局+项目级 | 无 | ❌ 缺失 |
| **实时重载** | 文件监视 | 无 | ❌ 缺失 |
| **验证** | schema 验证 | 无 | ❌ 缺失 |
| **迁移** | 设置迁移 | 无 | ❌ 缺失 |

### 3.8 Skills 系统 (core/skills.ts) ~600 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **SKILL.md 解析** | Frontmatter + 内容 | EvoSkill 有 | ✅ 有 |
| **技能加载** | loadSkillsFromDir | 有 | ✅ 有 |
| **技能格式化** | formatSkillsForPrompt | 有 | ✅ 有 |
| **技能块解析** | parseSkillBlock | 无 | ❌ 缺失 |
| **依赖解析** | 技能依赖 | 无 | ❌ 缺失 |

### 3.9 TUI 交互模式 (modes/interactive/) ~15000+ lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **InteractiveMode** | 主 TUI 类 | 无 | ❌ 缺失 |
| **组件系统** | 50+ 组件 | 无 | ❌ 缺失 |
| **ModelSelector** | 模型选择器 | 无 | ❌ 缺失 |
| **SessionSelector** | 会话选择器 | 无 | ❌ 缺失 |
| **ThemeSelector** | 主题选择 | 无 | ❌ 缺失 |
| **Diff 渲染** | renderDiff | 基础 | ⚠️ 部分 |
| **Footer 组件** | 状态栏 | 无 | ❌ 缺失 |
| **ToolExecution** | 工具执行显示 | 无 | ❌ 缺失 |
| **AssistantMessage** | 助手消息渲染 | 无 | ❌ 缺失 |
| **UserMessage** | 用户消息渲染 | 无 | ❌ 缺失 |
| **Theme 系统** | dark/light + 自定义 | 无 | ❌ 缺失 |
| **快捷键** | 键绑定系统 | 无 | ❌ 缺失 |
| **编辑器组件** | CustomEditor | 无 | ❌ 缺失 |
| **计数器** | CountdownTimer | 无 | ❌ 缺失 |
| **图片显示** | ShowImagesSelector | 无 | ❌ 缺失 |

### 3.10 Print Mode (modes/print-mode.ts) ~200 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **非交互模式** | runPrintMode | 无 | ❌ 缺失 |
| **流式输出** | stdout 流式 | 基础 | ⚠️ 部分 |
| **Markdown 渲染** | 终端 Markdown | 无 | ❌ 缺失 |

### 3.11 RPC Mode (modes/rpc/) ~600 lines

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **RPC 服务器** | runRpcMode | 无 | ❌ 缺失 |
| **RPC 客户端** | rpc-client.ts | 无 | ❌ 缺失 |
| **类型定义** | rpc-types.ts | 无 | ❌ 缺失 |
| **外部集成** | 外部程序集成 | 无 | ❌ 缺失 |

### 3.12 其他核心组件

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Event Bus** | createEventBus | EventBus | ✅ 有 |
| **Package Manager** | DefaultPackageManager | 无 | ❌ 缺失 |
| **Resource Loader** | DefaultResourceLoader | 无 | ❌ 缺失 |
| **Export HTML** | export-html/ | 无 | ❌ 缺失 |
| **Footer Data Provider** | ReadonlyFooterDataProvider | 无 | ❌ 缺失 |
| **Prompt Templates** | 动态提示模板 | 无 | ❌ 缺失 |
| **System Prompt** | 动态系统提示 | 无 | ❌ 缺失 |
| **Timings** | 性能跟踪 | 无 | ❌ 缺失 |
| **Diagnostics** | 诊断信息 | 无 | ❌ 缺失 |
| **Keybindings** | 键绑定管理 | 无 | ❌ 缺失 |
| **Clipboard** | 剪贴板集成 | 无 | ❌ 缺失 |
| **Shell Utils** | Shell 配置检测 | 无 | ❌ 缺失 |
| **Frontmatter** | YAML frontmatter | 无 | ❌ 缺失 |
| **Git Utils** | Git 操作 | 无 | ❌ 缺失 |
| **Image Processing** | 图片调整/转换 | 有 | ✅ 有 |

---

## 4. packages/mom - Model-Optimized Messages

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Agent 类** | 主 Agent | 无 | ❌ 缺失 |
| **Context 管理** | 动态上下文 | 基础 | ⚠️ 部分 |
| **Download** | 文件下载 | 无 | ❌ 缺失 |
| **Events** | 事件系统 | 有 | ✅ 有 |
| **Log** | 日志系统 | 基础 logging | ⚠️ 部分 |
| **Sandbox** | 沙箱环境 | 无 | ❌ 缺失 |
| **Slack Bot** | Slack 集成 | 无 | ❌ 缺失 |
| **Store** | 持久化存储 | 基础 | ⚠️ 部分 |

---

## 总结统计

| 类别 | 项目 | 已实现 | 部分实现 | 缺失 | 实现率 |
|------|------|--------|----------|------|--------|
| packages/ai | 45 | 5 | 8 | 32 | 22% |
| packages/agent | 6 | 2 | 2 | 2 | 50% |
| packages/coding-agent | 120 | 10 | 15 | 95 | 13% |
| packages/mom | 8 | 2 | 2 | 4 | 38% |
| **总计** | **179** | **19** | **27** | **133** | **17%** |

---

## 关键差距分析

### P0 - 关键缺失 (阻碍功能对等)

1. **TUI 系统** - 15,000+ 行代码，完全缺失
2. **Extension 系统** - 2,000+ 行代码，完全缺失
3. **OAuth 认证** - 多个提供商，完全缺失
4. **高级 Compaction** - 分支摘要、切割点检测
5. **Session Manager** - 树导航、迁移系统

### P1 - 重要缺失

6. **额外 LLM 提供商** - Google, Azure, Bedrock, Copilot
7. **高级工具功能** - 模糊匹配、可中断操作
8. **设置管理器** - 层级配置、实时重载
9. **导出功能** - HTML 导出

### P2 - 增强功能

10. **Package Manager** - 扩展市场
11. **RPC 模式** - 外部集成
12. **Sandbox** - 隔离执行
13. **Slack 集成** - 聊天机器人
