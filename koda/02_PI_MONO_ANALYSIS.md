# Pi Mono 完整模块分析 & Koda 对标补全指南

> 分析日期: 2026-02-10
> 分析范围: packages/ai, packages/agent, packages/mom, packages/coding-agent
> 目标: 100% 功能复现

---

## 目录结构总览

```
pi-mono/
├── packages/
│   ├── ai/              # ~32,000 lines - LLM Provider Interface
│   ├── agent/           # ~3,000 lines - Agent Core
│   ├── mom/             # ~4,000 lines - Model-Optimized Messages
│   ├── coding-agent/    # ~66,000 lines - Full Coding Agent
│   └── tui/             # ~8,000 lines - Terminal UI (Deferred)
```

---

## 第一部分: packages/ai 详细分析

### 1.1 文件结构

```
packages/ai/src/
├── index.ts                 # 导出所有公共API
├── types.ts                 # ~800 lines - 核心类型定义
├── models.ts                # ~200 lines - 模型注册和工具
├── api-registry.ts          # ~300 lines - Provider注册
├── env-api-keys.ts          # ~100 lines - 环境变量API Key
├── stream.ts                # ~400 lines - 流处理
├── cli.ts                   # ~500 lines - CLI接口
│
├── providers/               # ~15,000 lines
│   ├── anthropic.ts         # ~800 lines - Anthropic Messages API
│   ├── openai-completions.ts    # ~600 lines
│   ├── openai-responses.ts      # ~700 lines
│   ├── openai-responses-shared.ts   # ~300 lines
│   ├── azure-openai-responses.ts    # ~400 lines
│   ├── openai-codex-responses.ts    # ~300 lines
│   ├── google.ts            # ~600 lines
│   ├── google-gemini-cli.ts # ~500 lines
│   ├── google-shared.ts     # ~400 lines
│   ├── google-vertex.ts     # ~300 lines
│   ├── amazon-bedrock.ts    # ~600 lines
│   ├── register-builtins.ts # ~200 lines
│   ├── simple-options.ts    # ~300 lines
│   └── transform-messages.ts    # ~400 lines
│
├── utils/                   # ~10,000 lines
│   ├── oauth/               # ~4,000 lines
│   │   ├── index.ts
│   │   ├── anthropic.ts
│   │   ├── github-copilot.ts
│   │   ├── google-antigravity.ts
│   │   ├── google-gemini-cli.ts
│   │   ├── openai-codex.ts
│   │   ├── pkce.ts
│   │   └── types.ts
│   ├── event-stream.ts      # ~600 lines
│   ├── json-parse.ts        # ~300 lines
│   ├── overflow.ts          # ~200 lines
│   ├── sanitize-unicode.ts  # ~100 lines
│   ├── http-proxy.ts        # ~300 lines
│   ├── typebox-helpers.ts   # ~200 lines
│   └── validation.ts        # ~400 lines
│
└── test/                    # ~6,000 lines
```

### 1.2 核心类型详解 (types.ts)

#### 1.2.1 基础枚举

```typescript
// KnownApi - 支持的API类型
export type KnownApi =
  | "openai-completions"
  | "openai-responses"
  | "azure-openai-responses"
  | "openai-codex-responses"
  | "anthropic-messages"
  | "bedrock-converse-stream"
  | "google-generative-ai"
  | "google-gemini-cli"
  | "google-vertex";

// KnownProvider - 已知Provider列表 (22个)
export type KnownProvider =
  | "amazon-bedrock"
  | "anthropic"
  | "google"
  | "google-gemini-cli"
  | "google-antigravity"
  | "google-vertex"
  | "openai"
  | "azure-openai-responses"
  | "openai-codex"
  | "github-copilot"
  | "xai"
  | "groq"
  | "cerebras"
  | "openrouter"
  | "vercel-ai-gateway"
  | "zai"
  | "mistral"
  | "minimax"
  | "minimax-cn"
  | "huggingface"
  | "opencode"
  | "kimi-coding";

// ThinkingLevel - 思考级别
export type ThinkingLevel = "minimal" | "low" | "medium" | "high" | "xhigh";

// CacheRetention - 缓存保留策略
export type CacheRetention = "none" | "short" | "long";

// StopReason - 停止原因
export type StopReason = "stop" | "length" | "toolUse" | "error" | "aborted";
```

#### 1.2.2 内容类型

```typescript
// TextContent - 文本内容
export interface TextContent {
  type: "text";
  text: string;
  textSignature?: string;  // OpenAI: message ID
}

// ThinkingContent - 思考内容 (reasoning)
export interface ThinkingContent {
  type: "thinking";
  thinking: string;
  thinkingSignature?: string;  // OpenAI: reasoning item ID
}

// ImageContent - 图片内容
export interface ImageContent {
  type: "image";
  data: string;        // base64 encoded
  mimeType: string;    // "image/jpeg", "image/png", etc.
}

// ToolCall - 工具调用
export interface ToolCall {
  type: "toolCall";
  id: string;
  name: string;
  arguments: Record<string, any>;
  thoughtSignature?: string;  // Google-specific
}
```

#### 1.2.3 消息类型

```typescript
// UserMessage - 用户消息
export interface UserMessage {
  role: "user";
  content: string | (TextContent | ImageContent)[];
  timestamp: number;  // Unix timestamp in milliseconds
}

// AssistantMessage - 助手消息
export interface AssistantMessage {
  role: "assistant";
  content: (TextContent | ThinkingContent | ToolCall)[];
  api: Api;
  provider: Provider;
  model: string;
  usage: Usage;
  stopReason: StopReason;
  errorMessage?: string;
  timestamp: number;
}

// ToolResultMessage - 工具结果
export interface ToolResultMessage<TDetails = any> {
  role: "toolResult";
  toolCallId: string;
  toolName: string;
  content: (TextContent | ImageContent)[];
  details?: TDetails;
  isError: boolean;
  timestamp: number;
}
```

#### 1.2.4 Usage 和成本

```typescript
export interface Usage {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  totalTokens: number;
  cost: {
    input: number;
    output: number;
    cacheRead: number;
    cacheWrite: number;
    total: number;
  };
}
```

#### 1.2.5 模型定义

```typescript
export interface Model<TApi extends Api> {
  id: string;
  name: string;
  api: TApi;
  provider: Provider;
  baseUrl: string;
  reasoning: boolean;
  input: ("text" | "image")[];
  cost: {
    input: number;      // $/million tokens
    output: number;
    cacheRead: number;
    cacheWrite: number;
  };
  contextWindow: number;
  maxTokens: number;
  headers?: Record<string, string>;
  compat?: TApi extends "openai-completions" ? OpenAICompletionsCompat :
          TApi extends "openai-responses" ? OpenAIResponsesCompat :
          never;
}
```

#### 1.2.6 流选项

```typescript
// 基础流选项
export interface StreamOptions {
  temperature?: number;
  maxTokens?: number;
  signal?: AbortSignal;
  apiKey?: string;
  cacheRetention?: CacheRetention;
  sessionId?: string;
  onPayload?: (payload: unknown) => void;
  headers?: Record<string, string>;
  maxRetryDelayMs?: number;
}

// 简化流选项
export interface SimpleStreamOptions extends StreamOptions {
  reasoning?: ThinkingLevel;
  thinkingBudgets?: ThinkingBudgets;
}
```

#### 1.2.7 OpenAI兼容设置

```typescript
export interface OpenAICompletionsCompat {
  supportsStore?: boolean;
  supportsDeveloperRole?: boolean;
  supportsReasoningEffort?: boolean;
  supportsUsageInStreaming?: boolean;
  maxTokensField?: "max_completion_tokens" | "max_tokens";
  requiresToolResultName?: boolean;
  requiresAssistantAfterToolResult?: boolean;
  requiresThinkingAsText?: boolean;
  requiresMistralToolIds?: boolean;
  thinkingFormat?: "openai" | "zai" | "qwen";
  openRouterRouting?: OpenRouterRouting;
  vercelGatewayRouting?: VercelGatewayRouting;
  supportsStrictMode?: boolean;
}
```

### 1.3 Provider 接口详解

#### 1.3.1 基础Provider接口

```typescript
export interface ApiProvider<TApi extends Api> {
  api: TApi;
  stream: StreamFunction<TApi>;
  streamSimple?: SimpleStreamFunction<TApi>;
}

export type StreamFunction<TApi extends Api> = (
  model: Model<TApi>,
  context: Context,
  options?: StreamOptions,
) => AssistantMessageEventStream;
```

#### 1.3.2 Anthropic Provider 详解

**核心函数**: `streamAnthropic`

**关键特性**:
1. **Cache Control**
   - `resolveCacheRetention`: 处理环境变量 `PI_CACHE_RETENTION`
   - `getCacheControl`: 返回 `{ type: "ephemeral", ttl?: "1h" }`

2. **Claude Code 兼容性**
   ```typescript
   const claudeCodeTools = [
     "Read", "Write", "Edit", "Bash", "Grep", "Glob",
     "AskUserQuestion", "EnterPlanMode", "ExitPlanMode",
     "KillShell", "NotebookEdit", "Skill", "Task",
     "TaskOutput", "TodoWrite", "WebFetch", "WebSearch"
   ];
   // 自动转换工具名大小写
   const toClaudeCodeName = (name: string) => ccToolLookup.get(name.toLowerCase()) ?? name;
   ```

3. **AnthropicOptions**
   ```typescript
   export interface AnthropicOptions extends StreamOptions {
     thinkingEnabled?: boolean;        // 启用扩展思考
     thinkingBudgetTokens?: number;    // 旧模型的思考token预算
     effort?: AnthropicEffort;         // Opus 4.6+: low/medium/high/max
     interleavedThinking?: boolean;    // 交错思考
     toolChoice?: "auto" | "any" | "none" | { type: "tool"; name: string };
   }
   ```

4. **内容块转换**
   - 文本 -> Anthropic text block
   - 图片 -> Anthropic image block (base64)
   - 自动添加图片的placeholder文本

5. **事件处理**
   - `message_start`: 捕获初始token使用
   - `content_block_start`: 文本/思考/工具调用开始
   - `content_block_delta`: 内容增量
   - `content_block_stop`: 内容块结束
   - `message_delta`: 消息更新
   - `message_stop`: 消息完成

#### 1.3.3 OpenAI Providers 详解

**Completions API** (`openai-completions.ts`):
- 标准Chat Completion接口
- 工具调用通过 `tools` 和 `tool_choice`
- 支持 function calling

**Responses API** (`openai-responses.ts`):
- 不同端点: `/v1/responses`
- 输入格式: `input` 数组
- 支持 `store` 参数
- `stream_options: { include_usage: true }`
- 输出项类型: `message`, `reasoning`, `function_call`
- 事件类型:
  - `response.created`
  - `response.output_item.added`
  - `response.output_text.delta`
  - `response.function_call_arguments.delta`
  - `response.output_item.done`
  - `response.completed`

**Azure OpenAI** (`azure-openai-responses.ts`):
- 端点格式: `https://{resource}.openai.azure.com/openai/deployments/{deployment}`
- 认证: `api-key` header 或 Azure AD Bearer token
- API版本参数: `api-version=2024-10-21`

#### 1.3.4 Google Provider 详解

**Generative AI** (`google.ts`):
- 端点: `generativelanguage.googleapis.com/v1beta`
- 认证: API Key in URL
- 内容格式: `contents` 数组
- 系统提示: `systemInstruction`
- 工具: `functionDeclarations`

**Gemini CLI** (`google-gemini-cli.ts`):
- OAuth认证流程
- 特殊的token处理

**Vertex AI** (`google-vertex.ts`):
- 端点: `{region}-aiplatform.googleapis.com`
- 需要GCP项目ID和区域
- 认证: GCP access token

**特殊处理**:
- `thoughtSignature`: Google特有的思考签名
- 空流处理
- 重试延迟

#### 1.3.5 Bedrock Provider 详解

**核心**: `bedrock-converse-stream.ts`

**特性**:
- AWS SDK集成
- 跨区域推理
- `converse_stream` API调用
- 内容格式转换

### 1.4 OAuth 系统详解

#### 1.4.1 OAuth Provider 接口

```typescript
export interface OAuthProviderInterface {
  id: string;
  name: string;
  authorizationEndpoint: string;
  tokenEndpoint: string;
  scopes: string[];
  modifyModels?: (models: Model<Api>[], cred: OAuthCredential) => Model<Api>[];
}
```

#### 1.4.2 PKCE 流程

```typescript
// 生成PKCE参数
export interface PKCEChallenge {
  codeChallenge: string;
  codeVerifier: string;
}

export function generatePKCEChallenge(): PKCEChallenge {
  const verifier = generateCodeVerifier();
  const challenge = generateCodeChallenge(verifier);
  return { codeChallenge: challenge, codeVerifier: verifier };
}
```

#### 1.4.3 各Provider OAuth

**Google**:
- Gemini CLI OAuth
- Antigravity OAuth
- PKCE流程
- 本地回调服务器

**Anthropic**:
- OAuth flow
- Token刷新

**GitHub Copilot**:
- 特殊的OAuth流程
- Device code flow

---

## 第二部分: packages/agent 详细分析

### 2.1 文件结构

```
packages/agent/src/
├── index.ts         # 导出
├── agent.ts         # Agent类定义
├── agent-loop.ts    # Agent主循环
├── proxy.ts         # Agent代理
└── types.ts         # 类型定义
```

### 2.2 Agent Loop 详解

#### 2.2.1 核心接口

```typescript
export interface AgentLoopConfig {
  maxIterations: number;
  maxToolCallsPerTurn: number;
  retryAttempts: number;
  retryDelayBase: number;
  toolTimeout: number;
  enableParallelTools: boolean;
  maxParallelTools: number;
}

export interface AgentLoop {
  run(
    context: Context,
    onEvent?: (event: AgentEvent) => void,
    signal?: AbortSignal
  ): Promise<AssistantMessage>;
}
```

#### 2.2.2 执行流程

```
1. 检查迭代次数限制
2. 调用LLM获取响应
3. 检查停止原因:
   - STOP: 完成
   - LENGTH: token限制
   - TOOL_USE: 执行工具
4. 执行工具调用:
   - 串行或并行
   - 错误重试
5. 添加结果到上下文
6. 循环
```

#### 2.2.3 工具执行

```typescript
// 串行执行
for (const toolCall of toolCalls) {
  const result = await executeToolWithRetry(toolCall, signal);
}

// 并行执行
const results = await Promise.all(
  toolCalls.map(tc => executeToolWithRetry(tc, signal))
);
```

#### 2.2.4 错误处理

- 指数退避重试
- 超时控制
- 错误分类
- AbortSignal取消

### 2.3 Agent Proxy 详解

#### 2.3.1 多Agent协调

```typescript
export interface AgentProxy {
  registerAgent(name: string, agent: AgentLoop): void;
  delegate(task: string, toAgent?: string): Promise<AssistantMessage>;
}
```

#### 2.3.2 任务委派

- 负载均衡
- 任务路由
- Agent发现

---

## 第三部分: packages/coding-agent 详细分析

### 3.1 文件结构

```
packages/coding-agent/src/
├── index.ts
├── main.ts
├── cli.ts
├── cli/
│   ├── args.ts
│   ├── config-selector.ts
│   ├── file-processor.ts
│   ├── list-models.ts
│   └── session-picker.ts
├── config.ts
├── core/
│   ├── agent-session.ts       # ~2000 lines
│   ├── auth-storage.ts        # ~400 lines
│   ├── bash-executor.ts       # ~400 lines
│   ├── compaction/            # ~800 lines
│   │   ├── index.ts
│   │   ├── compaction.ts
│   │   ├── branch-summarization.ts
│   │   └── utils.ts
│   ├── event-bus.ts           # ~300 lines
│   ├── export-html/           # ~1000 lines
│   ├── extensions/            # ~2000 lines
│   ├── footer-data-provider.ts
│   ├── index.ts
│   ├── keybindings.ts
│   ├── messages.ts
│   ├── model-registry.ts      # ~500 lines
│   ├── model-resolver.ts
│   ├── package-manager.ts     # ~600 lines
│   ├── prompt-templates.ts
│   ├── resolve-config-value.ts
│   ├── resource-loader.ts
│   ├── sdk.ts
│   ├── session-manager.ts     # ~1500 lines
│   ├── settings-manager.ts    # ~500 lines
│   ├── skills.ts              # ~600 lines
│   ├── slash-commands.ts
│   ├── system-prompt.ts
│   ├── timings.ts
│   └── tools/                 # ~2000 lines
│       ├── index.ts
│       ├── bash.ts
│       ├── edit.ts
│       ├── edit-diff.ts
│       ├── find.ts
│       ├── grep.ts
│       ├── ls.ts
│       ├── path-utils.ts
│       ├── read.ts
│       ├── truncate.ts
│       └── write.ts
├── modes/
│   ├── index.ts
│   ├── interactive/           # ~15000 lines (TUI)
│   ├── print-mode.ts
│   └── rpc/
└── utils/
```

### 3.2 Model Registry 详解

#### 3.2.1 功能

```typescript
export class ModelRegistry {
  // 加载自定义模型
  loadCustomModels(path: string): CustomModelsResult;
  
  // Schema验证 (AJV)
  validateConfig(config: ModelsConfig): void;
  
  // Provider覆盖
  applyProviderOverrides(models: Model[]): Model[];
  
  // Model覆盖
  applyModelOverride(model: Model, override: ModelOverride): Model;
  
  // 动态注册
  registerProvider(name: string, config: ProviderConfigInput): void;
  
  // 获取可用模型
  getAvailable(): Model[];  // 有认证的
  
  // 检查OAuth
  isUsingOAuth(model: Model): boolean;
}
```

#### 3.2.2 models.json 格式

```json
{
  "providers": {
    "openai": {
      "baseUrl": "...",
      "apiKey": "${OPENAI_API_KEY}",
      "models": [...],
      "modelOverrides": {
        "gpt-4o": { "maxTokens": 8192 }
      }
    }
  }
}
```

#### 3.2.3 配置值解析

```typescript
// 环境变量: ${VAR}
// 命令替换: $(command)
export function resolveConfigValue(value: string): string {
  // 替换 ${ENV_VAR}
  // 执行 $(shell command)
}
```

### 3.3 Session Manager 详解

#### 3.3.1 会话结构

```typescript
export interface SessionContext {
  id: string;
  name: string;
  createdAt: number;
  modifiedAt: number;
  currentBranch: string;
  entries: SessionEntry[];
  branchSummaries: Record<string, BranchSummaryEntry>;
  metadata: Record<string, any>;
}

export type SessionEntry =
  | SessionMessageEntry
  | CompactionEntry
  | ModelChangeEntry
  | ThinkingLevelChangeEntry
  | CustomEntry
  | FileEntry;
```

#### 3.3.2 分支管理

```typescript
// 创建分支
forkBranch(fromEntryId: string, newBranchName: string): string;

// 切换分支
switchBranch(branchId: string): boolean;

// 获取分支历史
getBranchHistory(branchId: string): SessionEntry[];
```

#### 3.3.3 版本迁移

```typescript
// 从旧版本迁移
migrateSessionEntries(entries: any[], fromVersion: number): SessionEntry[];

// CURRENT_SESSION_VERSION = 1
```

### 3.4 Compaction 详解

#### 3.4.1 核心功能

```typescript
export interface CompactionResult {
  shouldCompact: boolean;
  cutPoint: number;
  summary: string;
  entriesToSummarize: SessionEntry[];
}

// 检测是否需要压缩
export function shouldCompact(entries: SessionEntry[], maxTokens: number): boolean;

// 查找最佳切分点
export function findCutPoint(entries: SessionEntry[]): number;

// 收集需要摘要的条目
export function collectEntriesForBranchSummary(
  entries: SessionEntry[],
  cutPoint: number
): CollectEntriesResult;

// 生成分支摘要
export async function generateBranchSummary(
  entries: SessionEntry[],
  provider: Provider,
  model: Model
): Promise<string>;

// 文件操作去重
export function deduplicateFileOperations(entries: SessionEntry[]): SessionEntry[];
```

### 3.5 Tools 详解

#### 3.5.1 Edit Tool 高级功能

```typescript
// 模糊匹配
export function fuzzyFindText(
  content: string,
  oldText: string
): FuzzyMatchResult;

// 规范化
export function normalizeForFuzzyMatch(text: string): string;
// - 智能引号 -> ASCII
// - 破折号变体 -> ASCII
// - 不间断空格 -> 普通空格

// 行尾处理
export function detectLineEnding(content: string): '\n' | '\r\n';
export function restoreLineEndings(content: string, ending: string): string;

// BOM处理
export function stripBom(content: string): { bom: string; text: string };

// Diff生成
export function generateDiffString(
  original: string,
  modified: string
): { diff: string; firstChangedLine?: number };

// 可插拔操作
export interface EditOperations {
  readFile: (path: string) => Promise<Buffer>;
  writeFile: (path: string, content: string) => Promise<void>;
  access: (path: string) => Promise<void>;
}
```

#### 3.5.2 Bash Tool 高级功能

```typescript
export interface BashSpawnContext {
  cwd: string;
  env: Record<string, string>;
  timeout: number;
  maxOutputBytes: number;
}

export interface BashSpawnHook {
  beforeSpawn?: (context: BashSpawnContext) => void;
  afterSpawn?: (context: BashSpawnContext, result: any) => void;
}

export interface BashToolOptions {
  spawnHook?: BashSpawnHook;
}
```

### 3.6 Settings Manager 详解

```typescript
export interface Settings {
  // Compaction
  compaction: {
    maxTokens: number;
    reserveTokens: number;
    triggerRatio: number;
  };
  
  // Images
  images: {
    maxWidth: number;
    maxHeight: number;
    quality: number;
    format: string;
  };
  
  // Retry
  retry: {
    maxAttempts: number;
    baseDelay: number;
    maxDelay: number;
  };
  
  // Package sources for extensions
  packageSources: PackageSource[];
}

// 层级配置
export class SettingsManager {
  // 全局配置: ~/.koda/settings.json
  // 项目配置: .koda/settings.json
  
  load(): Settings;  // 合并全局和项目
  save(settings: Settings, scope: 'global' | 'project'): void;
  
  // 文件监视
  watch(callback: () => void): void;
}
```

---

## 第四部分: packages/mom 详细分析

### 4.1 文件结构

```
packages/mom/src/
├── index.ts
├── agent.ts         # MOM Agent
├── context.ts       # 上下文管理
├── download.ts      # 文件下载
├── events.ts        # 事件系统
├── log.ts           # 日志
├── main.ts          # 入口
├── sandbox.ts       # 沙箱
├── slack.ts         # Slack集成
├── store.ts         # 存储
└── tools/
    ├── attach.ts
    ├── bash.ts
    ├── edit.ts
    ├── index.ts
    ├── read.ts
    ├── truncate.ts
    └── write.ts
```

### 4.2 MOM Agent

```typescript
export class MOMAgent {
  // 主要Agent类
  // 集成context, store, sandbox
  // 处理事件流
}
```

### 4.3 Context 管理

```typescript
export class ContextManager {
  // 动态上下文窗口管理
  // 自动compact
}
```

### 4.4 Sandbox

```typescript
export interface Sandbox {
  // 隔离执行环境
  execute(command: string[], options: SandboxOptions): Promise<SandboxResult>;
}
```

### 4.5 Store

```typescript
export interface Store {
  // 持久化存储
  get(key: string): Promise<any>;
  set(key: string, value: any): Promise<void>;
}
```

---

## 第五部分: Koda 对标补全计划

### 5.1 packages/ai 补全

#### 必补 (P0)
1. ✅ `supportsXhigh()` - 已实现 (koda/ai/models_utils.py)
2. ✅ `modelsAreEqual()` - 已实现 (koda/ai/models_utils.py)
3. ✅ OpenAI Responses API - 已实现 (koda/ai/providers/openai_responses.py)
4. ✅ Azure OpenAI Provider - 已实现 (koda/ai/providers/azure_provider.py)
5. ✅ GitHub Copilot Provider - 已实现 (koda/ai/github_copilot.py)
6. ❌ Anthropic: Claude Code工具名映射
7. ❌ Anthropic: interleaved thinking
8. ✅ Anthropic OAuth - 已实现 (koda/ai/oauth.py)
9. ✅ GitHub Copilot OAuth - 已实现 (koda/ai/oauth.py)

#### 可选 (P1)
10. ❌ JSON Schema验证 (TypeBox)
11. ⚠️ Token计算 - 基础实现完成，可优化

### 5.2 packages/agent 补全

#### 必补 (P0)
1. ✅ AgentProxy - 已实现 (koda/agent/proxy.py)
2. ✅ 多Agent协调 - 已实现 (AgentProxy)
3. ✅ 任务委派 - 已实现 (AgentProxy.delegate)

### 5.3 packages/coding-agent 补全

#### 必补 (P0)
1. ❌ ModelRegistry: Schema验证 (AJV/TypeBox)
2. ❌ ModelRegistry: 命令替换 $(cmd)
3. ✅ Compaction: findCutPoint - 已实现 (koda/mes/compaction_advanced.py)
4. ✅ Compaction: FileOperations跟踪 - 已实现 (koda/mes/compaction_advanced.py)
5. ✅ Session: 所有Entry类型 - 已实现 (koda/mes/compaction_advanced.py)
6. ❌ Session: 版本迁移
7. ❌ Settings: 层级配置 (全局/项目)
8. ❌ Settings: 文件监视
9. ✅ Edit: EditOperations接口 - 已实现 (koda/coding/tools/edit_operations.py)
10. ❌ Bash: BashSpawnHook

#### 可选 (P1)
11. ❌ Export HTML

### 5.4 packages/mom 补全

#### 必补 (P0)
1. ❌ MOMAgent类
2. ❌ Download功能

#### 可选 (P1)
3. ❌ Slack Bot

---

## 第六部分: 其他文件覆盖情况

### 6.1 packages/ai/utils/ 文件

| Pi Mono 文件 | Koda 对应 | 状态 | 说明 |
|--------------|-----------|------|------|
| `utils/oauth/*.ts` | `koda/ai/oauth.py` | ✅ | OAuth完整实现 |
| `utils/event-stream.ts` | `koda/ai/event_stream.py` | ✅ | SSE事件流解析 |
| `utils/json-parse.ts` | 内置json模块 | ✅ | Python标准库 |
| `utils/overflow.ts` | 未实现 | ❌ | Token溢出处理 |
| `utils/sanitize-unicode.ts` | 未实现 | ❌ | Unicode净化 |
| `utils/http-proxy.ts` | 未实现 | ❌ | HTTP代理支持 |
| `utils/typebox-helpers.ts` | 未实现 | ❌ | JSON Schema验证 |
| `utils/validation.ts` | 部分实现 | ⚠️ | 基础验证 |

### 6.2 packages/coding-agent/core/ 其他文件

| Pi Mono 文件 | Koda 对应 | 状态 | 说明 |
|--------------|-----------|------|------|
| `core/auth-storage.ts` | `koda/mom/store.py` | ⚠️ | 基础存储实现 |
| `core/bash-executor.ts` | `koda/coding/tools/shell_tool.py` | ✅ | Shell执行 |
| `core/event-bus.ts` | `koda/agent/events.py` | ✅ | 事件系统 |
| `core/export-html/` | 未实现 | ❌ | HTML导出 |
| `core/extensions/` | 未实现 | ❌ | 扩展系统 |
| `core/skills.ts` | `evoskill/skills/` | ⚠️ | 技能系统 |
| `core/settings-manager.ts` | 未实现 | ❌ | 层级设置 |
| `core/system-prompt.ts` | `koda/core/prompts.py` | ✅ | 系统提示词 |

### 6.3 packages/coding-agent/tools/ 文件

| Pi Mono 文件 | Koda 对应 | 状态 | 说明 |
|--------------|-----------|------|------|
| `tools/bash.ts` | `koda/coding/tools/shell_tool.py` | ✅ | Bash工具 |
| `tools/edit.ts` | `koda/coding/tools/edit_*.py` | ✅ | Edit工具系列 |
| `tools/read.ts` | `koda/coding/tools/file_tool.py` | ✅ | 文件读取 |
| `tools/write.ts` | `koda/coding/tools/file_tool.py` | ✅ | 文件写入 |
| `tools/grep.ts` | `koda/coding/tools/grep_tool.py` | ✅ | Grep工具 |
| `tools/find.ts` | `koda/coding/tools/find_tool.py` | ✅ | Find工具 |
| `tools/ls.ts` | `koda/coding/tools/ls_tool.py` | ✅ | 目录列表 |

### 6.4 覆盖率统计

| 包 | 总文件数 | 已实现 | 覆盖率 |
|----|---------|--------|--------|
| packages/ai | ~30 | ~25 | ~83% |
| packages/agent | ~5 | ~5 | 100% |
| packages/coding-agent | ~40 | ~25 | ~63% |
| packages/mom | ~10 | ~8 | 80% |
| packages/tui | ~20 | 0 | 0% (Deferred) |
| **总计** | **~105** | **~63** | **~60%** |

---

## 第七部分: 文档整理合并计划

### 现有文档

```
koda/
├── PI_MONO_COMPARISON.md           # 早期对比 (13KB)
├── PI_MONO_DETAILED_COMPARISON.md  # 详细对比 (18KB)
├── PI_MONO_100_PERCENT_CHECKLIST.md # 100%检查清单 (18KB)
├── 100_PERCENT_PARITY_STATUS.md     # 状态报告 (5KB)
├── IMPLEMENTATION_PROGRESS.md        # 进度追踪 (5KB)
├── IMPLEMENTATION_STATUS.md          # 早期状态 (5KB)
└── DESIGN_ROADMAP.md                 # 设计路线图 (29KB)
```

### 合并方案

**新文档结构**:

```
koda/docs/
├── 01_ARCHITECTURE.md           # 架构设计 (合并DESIGN_ROADMAP)
├── 02_PI_MONO_ANALYSIS.md       # Pi Mono完整分析 (本文件)
├── 03_IMPLEMENTATION_STATUS.md  # 实现状态 (合并状态文档)
├── 04_GAP_ANALYSIS.md           # 差距分析
├── 05_ROADMAP.md                # 路线图
└── api/
    ├── ai.md
    ├── agent.md
    ├── coding.md
    └── mom.md
```

### 需要合并的内容

1. **DESIGN_ROADMAP.md** → 01_ARCHITECTURE.md
2. **PI_MONO_* 对比文件** → 02_PI_MONO_ANALYSIS.md
3. **状态文件** → 03_IMPLEMENTATION_STATUS.md
4. **差距分析** → 04_GAP_ANALYSIS.md
5. **剩余路线图** → 05_ROADMAP.md

---

## 附录: 快速参考

### Pi Mono 核心文件对应

| Pi Mono | Koda | 状态 | 备注 |
|---------|------|------|------|
| `ai/types.ts` | `koda/ai/types.py` | ✅ | 完整实现 |
| `ai/models.ts` | `koda/ai/models_utils.py` | ✅ | 完整实现 |
| `ai/stream.ts` | `koda/ai/event_stream.py` | ✅ | 完整实现 |
| `ai/providers/anthropic.ts` | `koda/ai/providers/anthropic_provider_v2.py` | ✅ | 完整实现 |
| `ai/providers/openai-completions.ts` | `koda/ai/providers/openai_provider_v2.py` | ✅ | 完整实现 |
| `ai/providers/openai-responses.ts` | `koda/ai/providers/openai_responses.py` | ✅ | 完整实现 |
| `ai/providers/azure-openai-responses.ts` | `koda/ai/providers/azure_provider.py` | ✅ | 完整实现 |
| `ai/providers/google.ts` | `koda/ai/providers/google_provider.py` | ✅ | 完整实现 |
| `ai/providers/bedrock.ts` | `koda/ai/providers/bedrock_provider.py` | ✅ | 完整实现 |
| `ai/providers/github-copilot.ts` | `koda/ai/github_copilot.py` | ✅ | 完整实现 |
| `ai/utils/oauth/*.ts` | `koda/ai/oauth.py` | ✅ | 支持Google/Anthropic/GitHub |
| `agent/agent-loop.ts` | `koda/agent/loop.py` | ✅ | 完整实现 |
| `agent/proxy.ts` | `koda/agent/proxy.py` | ✅ | 完整实现 |
| `coding-agent/session-manager.ts` | `koda/coding/session_manager.py` | ⚠️ | 基础实现 |
| `coding-agent/model-registry.ts` | `koda/ai/registry.py` | ⚠️ | 基础实现，无Schema验证 |
| `coding-agent/compaction/*.ts` | `koda/mes/compaction.py` | ✅ | 基础实现 |
| `coding-agent/compaction/branch-summarization.ts` | `koda/mes/compaction_advanced.py` | ✅ | 完整实现 |
| `coding-agent/tools/edit-diff.ts` | `koda/coding/tools/edit_diff_tool.py` | ✅ | 完整实现 |
| `coding-agent/tools/edit.ts` | `koda/coding/tools/edit_enhanced.py` | ✅ | 完整实现 |
| `coding-agent/tools/edit-operations.ts` | `koda/coding/tools/edit_operations.py` | ✅ | 完整实现 |
| `mom/agent.ts` | N/A | ❌ | 未实现 |
| `mom/sandbox.ts` | `koda/mom/sandbox.py` | ✅ | 完整实现 |
| `mom/store.ts` | `koda/mom/store.py` | ✅ | 完整实现 |
