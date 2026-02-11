# Pi Mono 完整模块分析

> 分析日期: 2026-02-09
> 分析范围: packages/ai, packages/agent, packages/mom, packages/coding-agent
> 方法: 逐个文件逐行阅读 pi-mono TypeScript 源码
> 
> 本文档合并了之前的逐文件分析和整体模块分析

---

## 目录

1. [重要纠正](#重要纠正-vs-之前分析)
2. [packages/ai 逐文件分析](#第一部分-packagesai-逐文件)
3. [packages/agent 逐文件分析](#第二部分-packagesagent-逐文件)
4. [packages/coding-agent 逐文件分析](#第三部分-packagescoding-agent-逐文件)
5. [packages/mom 逐文件分析](#第四部分-packagesmom-逐文件)
6. [实现状态总表](#第五部分-实现状态总表)
7. [缺失功能清单](#第六部分-缺失功能清单)

---

## 重要纠正 (vs 之前分析)

| 文件 | 之前误解 | 实际功能 |
|------|----------|----------|
| `agent/proxy.ts` | 多 Agent 协调、任务委派 | **代理服务器流** - 通过 HTTP 代理 LLM 调用 |
| `ai/utils/overflow.ts` | Token 溢出预防/管理 | **错误检测** - 通过正则匹配各 provider 错误消息 |
| `coding-agent/resolve-config-value.ts` | `$(command)` 语法 | **`!command`** 语法执行命令 |

---

## 第一部分: packages/ai (逐文件)

### 1.1 src/types.ts (295 lines)

**核心类型定义**

```typescript
// API 和 Provider 类型
KnownApi: 9 种 API 类型
KnownProvider: 22 个已知 Provider
ThinkingLevel: "minimal" | "low" | "medium" | "high" | "xhigh"
CacheRetention: "none" | "short" | "long"
StopReason: "stop" | "length" | "toolUse" | "error" | "aborted"

// 内容类型
TextContent: { type: "text", text, textSignature? }
ThinkingContent: { type: "thinking", thinking, thinkingSignature? }
ImageContent: { type: "image", data, mimeType }
ToolCall: { type: "toolCall", id, name, arguments, thoughtSignature? }

// 消息类型
UserMessage: { role: "user", content, timestamp }
AssistantMessage: { role: "assistant", content, api, provider, model, usage, stopReason, errorMessage?, timestamp }
ToolResultMessage: { role: "toolResult", toolCallId, toolName, content, details?, isError, timestamp }

// 模型定义
Model<TApi>: { id, name, api, provider, baseUrl, reasoning, input, cost, contextWindow, maxTokens, headers?, compat? }
OpenAICompletionsCompat: 13 个兼容选项
OpenRouterRouting / VercelGatewayRouting: 提供商路由偏好

// 流选项
StreamOptions: temperature, maxTokens, signal, apiKey, cacheRetention, sessionId, onPayload, headers, maxRetryDelayMs
SimpleStreamOptions: extends StreamOptions + reasoning, thinkingBudgets

// 事件类型 (11 种)
AssistantMessageEvent: start, text_start/delta/end, thinking_start/delta/end, toolcall_start/delta/end, done, error
```

**Koda 对应**: `koda/ai/types.py`  
**状态**: ✅ 完全实现

---

### 1.2 src/models.ts (77 lines)

**模型注册与成本计算**

```typescript
getModel(provider, modelId): 从 MODELS 获取模型定义
getProviders(): 返回所有 provider 列表
getModels(provider): 返回指定 provider 的所有模型
calculateCost(model, usage): 计算成本 ($/million tokens)
supportsXhigh(model): 检查是否支持 xhigh (GPT-5.2/5.3, Opus 4.6)
modelsAreEqual(a, b): 比较模型 id 和 provider
```

**Koda 对应**: `koda/ai/models_utils.py`  
**状态**: ✅ 完全实现

---

### 1.3 src/utils/event-stream.ts (87 lines)

**通用事件流基类**

```typescript
class EventStream<T, R> implements AsyncIterable<T> {
  - queue: T[]
  - waiting: resolve callbacks
  - done: boolean
  - finalResultPromise: Promise<R>
  
  + push(event): void
  + end(result?): void
  + [Symbol.asyncIterator](): AsyncIterator<T>
  + result(): Promise<R>
}

class AssistantMessageEventStream extends EventStream<AssistantMessageEvent, AssistantMessage>
```

**Koda 对应**: `koda/ai/event_stream.py`  
**状态**: ✅ 完全实现

---

### 1.4 src/utils/overflow.ts (121 lines)

**上下文溢出错误检测** ⚠️ 不是预防!

```typescript
// 16 个正则模式匹配各 provider 错误:
- Anthropic: /prompt is too long/i
- OpenAI: /exceeds the context window/i
- Google: /input token count.*exceeds the maximum/i
- xAI: /maximum prompt length is \d+/i
- Groq: /reduce the length of the messages/i
- OpenRouter: /maximum context length is \d+ tokens/i
- GitHub Copilot: /exceeds the limit of \d+/i
- llama.cpp: /exceeds the available context size/i
- LM Studio: /greater than the context length/i
- MiniMax: /context window exceeds limit/i
- Kimi: /exceeded model token limit/i
- Cerebras/Mistral: 400/413 status code (no body)

function isContextOverflow(message, contextWindow?): boolean
```

**Koda 状态**: ❌ 未实现

---

### 1.5 src/utils/json-parse.ts

**流式 JSON 解析**

```typescript
function parseStreamingJson(json: string): any | undefined
```

**Koda 状态**: ⚠️ 部分实现 (简单 JSON 解析)

---

### 1.6 src/utils/sanitize-unicode.ts

**Unicode 代理对清理**

```typescript
function sanitizeSurrogates(text: string): string
```

**Koda 状态**: ❌ 未实现

---

### 1.7 src/providers/anthropic.ts (~800 lines)

**Anthropic Messages API Provider**

```typescript
// 缓存控制
function resolveCacheRetention(cacheRetention?): CacheRetention
function getCacheControl(baseUrl, cacheRetention?): { retention, cacheControl? }

// Claude Code 工具名映射 (stealth mode)
const claudeCodeTools = ["Read", "Write", ..., "WebSearch"] // 17 个工具
const ccToolLookup = new Map(claudeCodeTools.map(t => [t.toLowerCase(), t]))
const toClaudeCodeName = (name) => ccToolLookup.get(name.toLowerCase()) ?? name
const fromClaudeCodeName = (name, tools?) => { ... }

// Anthropic 特定选项
interface AnthropicOptions extends StreamOptions {
  thinkingEnabled?: boolean
  thinkingBudgetTokens?: number  // 旧模型
  effort?: "low" | "medium" | "high" | "max"  // Opus 4.6+
  interleavedThinking?: boolean
  toolChoice?: "auto" | "any" | "none" | { type: "tool", name }
}

// 主函数
export const streamAnthropic: StreamFunction<"anthropic-messages", AnthropicOptions>
```

**Koda 对应**: `koda/ai/providers/anthropic_provider_v2.py` + `koda/ai/claude_code_mapping.py`  
**状态**: ✅ 实现 (2026-02-09 完成 tool mapping)

---

### 1.8 src/providers/openai-completions.ts (~600 lines)

**OpenAI Chat Completions API**

```typescript
// 支持 OpenAI 兼容 API (Groq, Cerebras, Mistral, etc.)
// 自动检测 baseUrl 决定 compat 设置
function detectCompatFromUrl(baseUrl): OpenAICompletionsCompat

// 主函数
export const streamOpenAICompletions: StreamFunction<"openai-completions">
```

**Koda 对应**: `koda/ai/providers/openai_provider_v2.py`  
**状态**: ✅ 实现

---

### 1.9 src/providers/openai-responses.ts (~700 lines)

**OpenAI Responses API**

```typescript
// 不同端点: /v1/responses
// 输入格式: input 数组
// 支持 store 参数
// 输出项: message, reasoning, function_call

// 事件类型:
- response.created
- response.output_item.added
- response.output_text.delta
- response.function_call_arguments.delta
- response.output_item.done
- response.completed
```

**Koda 对应**: `koda/ai/providers/openai_responses.py`  
**状态**: ✅ 实现

---

### 1.10 src/providers/azure-openai-responses.ts (~400 lines)

**Azure OpenAI Responses API**

```typescript
// 端点: https://{resource}.openai.azure.com/openai/deployments/{deployment}
// 认证: api-key header 或 Azure AD Bearer token
// API 版本: api-version=2024-10-21
```

**Koda 对应**: `koda/ai/providers/azure_provider.py`  
**状态**: ✅ 实现

---

### 1.11 src/providers/google.ts (~600 lines)

**Google Generative AI**

```typescript
// 端点: generativelanguage.googleapis.com/v1beta
// 认证: API Key in URL
// 内容: contents 数组
// 系统提示: systemInstruction
// 工具: functionDeclarations
// 特殊: thoughtSignature (Google 特有)
```

**Koda 对应**: `koda/ai/providers/google_provider.py`  
**状态**: ✅ 实现

---

### 1.12 src/providers/amazon-bedrock.ts (~600 lines)

**AWS Bedrock Converse Stream**

```typescript
// AWS SDK 集成
// 跨区域推理
// converse_stream API
// 支持 interleaved thinking
```

**Koda 对应**: `koda/ai/providers/bedrock_provider.py`  
**状态**: ✅ 实现

---

### 1.13 src/utils/oauth/*.ts (~4000 lines total)

**OAuth 系统**

```typescript
// 文件:
- types.ts: OAuthProviderInterface, OAuthCredential
- pkce.ts: generatePKCEChallenge()
- anthropic.ts: Anthropic OAuth flow
- github-copilot.ts: GitHub Copilot OAuth (device code flow)
- google-antigravity.ts: Google Antigravity OAuth
- google-gemini-cli.ts: Gemini CLI OAuth
- openai-codex.ts: OpenAI Codex OAuth
```

**Koda 对应**: `koda/ai/oauth.py`  
**状态**: ✅ 主要 OAuth 实现

---

## 第二部分: packages/agent (逐文件)

### 2.1 src/types.ts (194 lines)

**Agent 类型定义**

```typescript
interface AgentLoopConfig extends SimpleStreamOptions {
  model: Model<any>
  convertToLlm: (messages: AgentMessage[]) => Message[] | Promise<Message[]>
  transformContext?: (messages, signal?) => Promise<AgentMessage[]>
  getApiKey?: (provider) => Promise<string | undefined>
  getSteeringMessages?: () => Promise<AgentMessage[]>
  getFollowUpMessages?: () => Promise<AgentMessage[]>
}

type ThinkingLevel = "off" | "minimal" | "low" | "medium" | "high" | "xhigh"

// 可扩展的自定义消息
interface CustomAgentMessages { /* empty */ }
type AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages]

interface AgentState {
  systemPrompt: string
  model: Model<any>
  thinkingLevel: ThinkingLevel
  tools: AgentTool<any>[]
  messages: AgentMessage[]
  isStreaming: boolean
  streamMessage: AgentMessage | null
  pendingToolCalls: Set<string>
  error?: string
}

interface AgentTool extends Tool {
  label: string
  execute: (toolCallId, params, signal?, onUpdate?) => Promise<AgentToolResult>
}

// Agent 事件 (14 种)
type AgentEvent =
  | { type: "agent_start" }
  | { type: "agent_end", messages }
  | { type: "turn_start" }
  | { type: "turn_end", message, toolResults }
  | { type: "message_start", message }
  | { type: "message_update", message, assistantMessageEvent }
  | { type: "message_end", message }
  | { type: "tool_execution_start", toolCallId, toolName, args }
  | { type: "tool_execution_update", toolCallId, toolName, args, partialResult }
  | { type: "tool_execution_end", toolCallId, toolName, result, isError }
```

**Koda 对应**: `koda/agent/types.py`  
**状态**: ✅ 实现

---

### 2.2 src/agent-loop.ts (~400 lines)

**Agent 主循环**

```typescript
// 入口函数
export function agentLoop(prompts, context, config, signal?, streamFn?): EventStream<AgentEvent, AgentMessage[]>
export function agentLoopContinue(context, config, signal?, streamFn?): EventStream<AgentEvent, AgentMessage[]>

// 流程:
// 1. agent_start / turn_start 事件
// 2. 处理 pending messages (steering)
// 3. 流式获取 assistant 响应
// 4. 检查 stopReason (error/aborted -> 结束)
// 5. 执行 tool calls (串行或并行)
// 6. 发送 tool execution 事件
// 7. turn_end 事件
// 8. 检查 steering messages
// 9. 检查 follow-up messages
// 10. agent_end 事件
```

**Koda 对应**: `koda/agent/loop.py`  
**状态**: ✅ 实现

---

### 2.3 src/proxy.ts (340 lines) ⚠️ 重要纠正!

**代理服务器流 - 不是多 Agent 协调!**

```typescript
/**
 * Proxy stream function for apps that route LLM calls through a server.
 * The server manages auth and proxies requests to LLM providers.
 */

// 代理事件类型 (无 partial 字段，减少带宽)
type ProxyAssistantMessageEvent =
  | { type: "start" }
  | { type: "text_start", contentIndex }
  | { type: "text_delta", contentIndex, delta }
  | { type: "text_end", contentIndex, contentSignature? }
  | { type: "thinking_start", contentIndex }
  | { type: "thinking_delta", contentIndex, delta }
  | { type: "thinking_end", contentIndex, contentSignature? }
  | { type: "toolcall_start", contentIndex, id, toolName }
  | { type: "toolcall_delta", contentIndex, delta }
  | { type: "toolcall_end", contentIndex }
  | { type: "done", reason, usage }
  | { type: "error", reason, errorMessage?, usage }

interface ProxyStreamOptions extends SimpleStreamOptions {
  authToken: string
  proxyUrl: string  // e.g., "https://genai.example.com"
}

// 主函数: 通过 HTTP POST /api/stream 代理请求
export function streamProxy(model, context, options: ProxyStreamOptions): ProxyMessageEventStream
```

**之前误解**: 多 Agent 协调、任务委派、负载均衡  
**实际功能**: 通过 HTTP 代理 LLM 调用，服务器管理认证和路由

**Koda 状态**: ❌ 未实现 (之前的 koda/agent/proxy.py 已删除，实现错误)

---

### 2.4 src/agent.ts

**Agent 类包装器**

```typescript
class Agent {
  constructor(config: AgentConfig)
  prompt(messages: AgentMessage[]): EventStream<AgentEvent, AgentMessage[]>
  continue(): EventStream<AgentEvent, AgentMessage[]>
  abort(): void
}
```

**Koda 对应**: `koda/agent/agent.py`  
**状态**: ✅ 实现

---

## 第三部分: packages/coding-agent (逐文件)

### 3.1 src/core/resolve-config-value.ts (64 lines) ⚠️ 语法纠正!

**配置值解析**

```typescript
/**
 * Resolve a config value (API key, header value, etc.) to an actual value.
 * - If starts with "!", executes the rest as a shell command and uses stdout (cached)
 * - Otherwise checks environment variable first, then treats as literal (not cached)
 */
export function resolveConfigValue(config: string): string | undefined {
  if (config.startsWith("!")) {
    return executeCommand(config)
  }
  const envValue = process.env[config]
  return envValue || config
}

function executeCommand(commandConfig: string): string | undefined {
  // Cache for process lifetime
  // execSync with 10s timeout
}
```

**之前误解**: `$(command)` 语法  
**实际语法**: `!command` (如 `!echo $API_KEY`)

**Koda 对应**: 需检查/修复 `koda/coding/config_resolver.py`

---

### 3.2 src/core/model-registry.ts (~500 lines)

**模型注册表**

```typescript
class ModelRegistry {
  // Schema 验证 (AJV + TypeBox)
  - ModelDefinitionSchema
  - ModelOverrideSchema
  - ProviderConfigSchema
  - ModelsConfigSchema
  
  // 功能
  + loadCustomModels(path: string): CustomModelsResult
  + validateConfig(config): void  // AJV 验证
  + applyProviderOverrides(models): Model[]
  + applyModelOverride(model, override): Model
  + registerProvider(name, config): void
  + getAvailable(): Model[]  // 有认证的
  + isUsingOAuth(model): boolean
}

// 配置文件: ~/.koda/models.json
interface ModelsConfig {
  providers: Record<string, ProviderConfig>
}
```

**Koda 对应**: `koda/ai/registry.py`  
**状态**: ⚠️ 基础实现，无 Schema 验证

---

### 3.3 src/core/session-manager.ts (~1500 lines)

**会话管理器**

```typescript
interface SessionContext {
  id: string
  name: string
  createdAt: number
  modifiedAt: number
  currentBranch: string
  entries: SessionEntry[]
  branchSummaries: Record<string, BranchSummaryEntry>
  metadata: Record<string, any>
}

type SessionEntry =
  | SessionMessageEntry
  | CompactionEntry
  | ModelChangeEntry
  | ThinkingLevelChangeEntry
  | CustomEntry
  | FileEntry

class SessionManager {
  + create(name?): SessionContext
  + load(sessionId): SessionContext | null
  + save(session): void
  + delete(sessionId): void
  + list(): Session[]
  
  // 分支管理
  + forkBranch(fromEntryId, newBranchName): string
  + switchBranch(branchId): boolean
  + getBranchHistory(branchId): SessionEntry[]
  
  // 版本迁移
  + migrateSessionEntries(entries, fromVersion): SessionEntry[]
}

const CURRENT_SESSION_VERSION = 1
```

**Koda 对应**: `koda/coding/session_manager.py`  
**状态**: ⚠️ 基础实现

---

### 3.4 src/core/compaction/*.ts (~800 lines)

**上下文压缩**

```typescript
// compaction.ts
interface CompactionResult {
  shouldCompact: boolean
  cutPoint: number
  summary: string
  entriesToSummarize: SessionEntry[]
}

function shouldCompact(entries, maxTokens): boolean
function findCutPoint(entries): number
function collectEntriesForBranchSummary(entries, cutPoint): CollectEntriesResult
async function generateBranchSummary(entries, provider, model): Promise<string>
function deduplicateFileOperations(entries): SessionEntry[]
```

**Koda 对应**: `koda/mes/compaction.py` + `koda/mes/compaction_advanced.py`  
**状态**: ✅ 实现

---

### 3.5 src/core/tools/*.ts (~2000 lines)

**工具实现**

| 文件 | 功能 | Koda 对应 | 状态 |
|------|------|-----------|------|
| `read.ts` | 文件读取 (offset, limit, truncation) | `koda/coding/tools/file_tool.py` | ✅ |
| `write.ts` | 文件写入 (mkdir -p) | `koda/coding/tools/file_tool.py` | ✅ |
| `edit.ts` | 文本替换 (模糊匹配, BOM, CRLF) | `koda/coding/tools/edit_*.py` | ✅ |
| `edit-diff.ts` | Diff 生成 | `koda/coding/tools/edit_diff_tool.py` | ✅ |
| `bash.ts` | Shell 执行 (timeout, hooks) | `koda/coding/tools/shell_tool.py` | ✅ |
| `grep.ts` | 内容搜索 | `koda/coding/tools/grep_tool.py` | ✅ |
| `find.ts` | 文件查找 | `koda/coding/tools/find_tool.py` | ✅ |
| `ls.ts` | 目录列表 | `koda/coding/tools/ls_tool.py` | ✅ |
| `truncate.ts` | 截断算法 | `koda/coding/tools/truncate.py` | ✅ |

---

### 3.6 src/core/settings-manager.ts (~500 lines)

**层级设置管理**

```typescript
interface Settings {
  compaction: { maxTokens, reserveTokens, triggerRatio }
  images: { maxWidth, maxHeight, quality, format }
  retry: { maxAttempts, baseDelay, maxDelay }
  packageSources: PackageSource[]
}

class SettingsManager {
  // 层级配置:
  // - 全局: ~/.koda/settings.json
  // - 项目: .koda/settings.json
  
  + load(): Settings  // 合并全局和项目
  + save(settings, scope: 'global' | 'project'): void
  + watch(callback): void  // 文件监视
}
```

**Koda 状态**: ❌ 未实现

---

## 第四部分: packages/mom (逐文件)

### 4.1 src/agent.ts (~400 lines)

**MOM Agent 实现**

```typescript
// MOM = "Mother of all agents" - Slack Bot Agent

interface PendingMessage {
  userName: string
  text: string
  attachments: { local: string }[]
  timestamp: number
}

interface AgentRunner {
  run(ctx, store, pendingMessages?): Promise<{ stopReason, errorMessage? }>
  abort(): void
}

// 核心功能:
- getAnthropicApiKey(authStorage): string
- getImageMimeType(filename): string | undefined
- getMemory(channelDir): string  // 读取 MEMORY.md
- loadMomSkills(channelDir, workspacePath): Skill[]
- buildSystemPrompt(...): string
- createAgentRunner(...): AgentRunner
```

**Koda 状态**: ❌ 未实现 (MOM 是 Slack Bot)

---

### 4.2 src/context.ts

**MOM 上下文管理**

```typescript
class MomSettingsManager
function syncLogToSessionManager(...)
```

**Koda 状态**: ❌ 未实现

---

### 4.3 src/sandbox.ts

**沙箱执行**

```typescript
interface SandboxConfig {
  // Docker/容器配置
}

function createExecutor(config: SandboxConfig): Executor
```

**Koda 对应**: `koda/mom/sandbox.py`  
**状态**: ✅ 基础实现

---

### 4.4 src/store.ts

**频道存储**

```typescript
interface ChannelStore {
  get(key): Promise<any>
  set(key, value): Promise<void>
}
```

**Koda 对应**: `koda/mom/store.py`  
**状态**: ✅ 基础实现

---

### 4.5 src/slack.ts

**Slack 集成**

```typescript
interface SlackContext { ... }
interface ChannelInfo { ... }
interface UserInfo { ... }
```

**Koda 状态**: ❌ 未实现 (Slack Bot 功能)

---

## 第五部分: 实现状态总表

### packages/ai

| Pi Mono 文件 | 行数 | Koda 对应 | 状态 |
|-------------|------|-----------|------|
| `src/types.ts` | 295 | `koda/ai/types.py` | ✅ |
| `src/models.ts` | 77 | `koda/ai/models_utils.py` | ✅ |
| `src/utils/event-stream.ts` | 87 | `koda/ai/event_stream.py` | ✅ |
| `src/utils/overflow.ts` | 121 | - | ❌ |
| `src/utils/json-parse.ts` | ~100 | (内置 json) | ⚠️ |
| `src/utils/sanitize-unicode.ts` | ~50 | - | ❌ |
| `src/utils/http-proxy.ts` | ~100 | - | ❌ |
| `src/providers/anthropic.ts` | ~800 | `koda/ai/providers/anthropic_provider_v2.py` | ✅ |
| `src/providers/openai-completions.ts` | ~600 | `koda/ai/providers/openai_provider_v2.py` | ✅ |
| `src/providers/openai-responses.ts` | ~700 | `koda/ai/providers/openai_responses.py` | ✅ |
| `src/providers/azure-openai-responses.ts` | ~400 | `koda/ai/providers/azure_provider.py` | ✅ |
| `src/providers/google.ts` | ~600 | `koda/ai/providers/google_provider.py` | ✅ |
| `src/providers/amazon-bedrock.ts` | ~600 | `koda/ai/providers/bedrock_provider.py` | ✅ |
| `src/utils/oauth/*.ts` | ~1000 | `koda/ai/oauth.py` | ✅ |

### packages/agent

| Pi Mono 文件 | 行数 | Koda 对应 | 状态 |
|-------------|------|-----------|------|
| `src/types.ts` | 194 | `koda/agent/types.py` | ✅ |
| `src/agent-loop.ts` | ~400 | `koda/agent/loop.py` | ✅ |
| `src/agent.ts` | ~100 | `koda/agent/agent.py` | ✅ |
| `src/proxy.ts` | 340 | - | ❌ |

### packages/coding-agent

| Pi Mono 文件 | 行数 | Koda 对应 | 状态 |
|-------------|------|-----------|------|
| `src/core/resolve-config-value.ts` | 64 | `koda/coding/config_resolver.py` | ⚠️ |
| `src/core/model-registry.ts` | ~500 | `koda/ai/registry.py` | ⚠️ |
| `src/core/session-manager.ts` | ~1500 | `koda/coding/session_manager.py` | ⚠️ |
| `src/core/compaction/*.ts` | ~800 | `koda/mes/compaction*.py` | ✅ |
| `src/core/tools/*.ts` | ~2000 | `koda/coding/tools/*.py` | ✅ |
| `src/core/settings-manager.ts` | ~500 | - | ❌ |

### packages/mom

| Pi Mono 文件 | 行数 | Koda 对应 | 状态 |
|-------------|------|-----------|------|
| `src/agent.ts` | ~400 | - | ❌ |
| `src/context.ts` | ~200 | - | ❌ |
| `src/sandbox.ts` | ~200 | `koda/mom/sandbox.py` | ✅ |
| `src/store.ts` | ~150 | `koda/mom/store.py` | ✅ |
| `src/slack.ts` | ~300 | - | ❌ |

---

## 第六部分: 缺失功能清单

### P0 (必须实现)

| 功能 | Pi Mono 文件 | 状态 | 备注 |
|------|-------------|------|------|
| Context Overflow 检测 | `ai/utils/overflow.ts` | ❌ | 16 个正则匹配 provider 错误 |
| Config Value 解析修正 | `coding-agent/resolve-config-value.ts` | ⚠️ | 改为 `!command` 语法 |
| Stream Proxy | `agent/proxy.ts` | ❌ | HTTP 代理流，非多 Agent 协调 |
| Unicode 清理 | `ai/utils/sanitize-unicode.ts` | ❌ | 代理对清理 |

### P1 (应该实现)

| 功能 | Pi Mono 文件 | 状态 | 备注 |
|------|-------------|------|------|
| JSON Schema 验证 | `coding-agent/model-registry.ts` | ❌ | AJV/TypeBox 等效 |
| Settings Manager | `coding-agent/settings-manager.ts` | ❌ | 层级配置 |
| HTTP 代理支持 | `ai/utils/http-proxy.ts` | ❌ | 代理配置 |

### P2 (可选)

| 功能 | Pi Mono 文件 | 状态 | 备注 |
|------|-------------|------|------|
| MOM Agent | `mom/agent.ts` | ❌ | Slack Bot |
| Export HTML | `coding-agent/export-html/` | ❌ | 会话导出 |
| Extensions | `coding-agent/extensions/` | ❌ | 扩展系统 |

---

## 覆盖率统计

| 包 | Pi Mono 总行数 | Koda 实现 | 覆盖率 |
|----|---------------|-----------|--------|
| packages/ai | ~18,000 | ~16,000 | ~89% |
| packages/agent | ~1,000 | ~700 | ~70% |
| packages/coding-agent | ~8,000 | ~5,500 | ~69% |
| packages/mom | ~2,000 | ~800 | ~40% |
| **总计** | **~29,000** | **~23,000** | **~79%** |

---

*文档整合日期: 2026-02-09*  
*合并了: 02_PI_MONO_ANALYSIS.md + 08_PI_MONO_FILE_BY_FILE_ANALYSIS.md*
