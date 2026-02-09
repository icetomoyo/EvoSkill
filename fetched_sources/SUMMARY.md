# Pi-Mono Repository Source Code Summary

This document provides a comprehensive summary of the source files fetched from the `badlogic/pi-mono` repository for feature parity analysis.

## Repository Structure

```
pi-mono/
├── packages/
│   ├── ai/                    # @mariozechner/pi-ai - Unified LLM API
│   │   └── src/
│   ├── coding-agent/          # @mariozechner/pi-coding-agent - Coding agent CLI
│   │   └── src/
│   └── agent-core/            # @mariozechner/pi-agent-core - Core agent abstractions
│       └── src/
```

---

## 1. Pi-AI Package (`packages/ai/src/`)

### Core Types (`types.ts`)

**Key Interfaces:**

#### Message Types
- `UserMessage`: Contains `role: "user"`, `content: string | (TextContent | ImageContent)[]`, `timestamp`
- `AssistantMessage`: Contains `role: "assistant"`, content blocks (text/thinking/toolCall), usage stats, stop reason
- `ToolResultMessage`: Contains `role: "toolResult"`, `toolCallId`, `toolName`, content (supports images!)

#### Content Block Types
```typescript
interface TextContent {
  type: "text";
  text: string;
  textSignature?: string;  // For replay contexts
}

interface ThinkingContent {
  type: "thinking";
  thinking: string;
  thinkingSignature?: string;  // Provider-specific signature
}

interface ImageContent {
  type: "image";
  data: string;        // base64 encoded
  mimeType: string;    // image/jpeg, image/png, image/gif, image/webp
}

interface ToolCall {
  type: "toolCall";
  id: string;
  name: string;
  arguments: Record<string, any>;
  thoughtSignature?: string;  // Google-specific for reasoning replay
}
```

#### Usage & Cost Tracking
```typescript
interface Usage {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  totalTokens: number;
  cost: {
    input: number;      // $/million tokens
    output: number;
    cacheRead: number;
    cacheWrite: number;
    total: number;
  };
}
```

#### Model Definition
```typescript
interface Model<TApi extends Api> {
  id: string;
  name: string;
  api: TApi;
  provider: Provider;
  baseUrl: string;
  reasoning: boolean;
  input: ("text" | "image")[];  // Supported input modalities
  cost: { input, output, cacheRead, cacheWrite };
  contextWindow: number;
  maxTokens: number;
  headers?: Record<string, string>;
  compat?: OpenAICompletionsCompat | OpenAIResponsesCompat;
}
```

#### Supported APIs
- `openai-completions` - OpenAI-compatible chat completions
- `openai-responses` - OpenAI Responses API
- `azure-openai-responses` - Azure OpenAI
- `openai-codex-responses` - OpenAI Codex
- `anthropic-messages` - Anthropic Messages API
- `bedrock-converse-stream` - AWS Bedrock
- `google-generative-ai` - Google Gemini API
- `google-gemini-cli` - Google Gemini CLI
- `google-vertex` - Google Vertex AI

#### Supported Providers
amazon-bedrock, anthropic, google, google-gemini-cli, google-antigravity, google-vertex, openai, azure-openai-responses, openai-codex, github-copilot, xai, groq, cerebras, openrouter, vercel-ai-gateway, zai, mistral, minimax, minimax-cn, huggingface, opencode, kimi-coding

#### Streaming Event Types
```typescript
type AssistantMessageEvent =
  | { type: "start"; partial: AssistantMessage }
  | { type: "text_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "text_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "text_end"; contentIndex: number; content: string; partial: AssistantMessage }
  | { type: "thinking_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "thinking_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "thinking_end"; contentIndex: number; content: string; partial: AssistantMessage }
  | { type: "toolcall_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "toolcall_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "toolcall_end"; contentIndex: number; toolCall: ToolCall; partial: AssistantMessage }
  | { type: "done"; reason: StopReason; message: AssistantMessage }
  | { type: "error"; reason: StopReason; error: AssistantMessage };
```

#### OpenAI Compatibility Settings
```typescript
interface OpenAICompletionsCompat {
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

---

## 2. Provider Implementations

### 2.1 OpenAI Completions (`providers/openai-completions.ts`)

**Key Features:**
- Supports multiple OpenAI-compatible endpoints (OpenAI, Azure, GitHub Copilot, Groq, etc.)
- Auto-detects provider capabilities from baseUrl
- Handles tool call ID normalization (Mistral requires 9 alphanumeric chars)
- Supports reasoning content in `reasoning_content`, `reasoning`, `reasoning_text` fields
- GitHub Copilot-specific headers (`X-Initiator`, `Openai-Intent`, `Copilot-Vision-Request`)
- Converts thinking blocks to text for Mistral
- Handles pipe-separated tool call IDs from OpenAI Responses API

**Compatibility Detection:**
```typescript
function detectCompat(model: Model): Required<OpenAICompletionsCompat> {
  // Detects provider from URL or explicit provider field
  // Sets flags for: store, developer role, reasoning effort, 
  // max tokens field, tool result name, assistant after tool result,
  // thinking as text, Mistral tool IDs, thinking format
}
```

### 2.2 Anthropic Messages (`providers/anthropic.ts`)

**Key Features:**
- Supports both API keys and OAuth tokens (`sk-ant-oat` prefix)
- OAuth mode mimics Claude Code headers exactly
- Adaptive thinking support for Opus 4.6+ (effort-based)
- Budget-based thinking for older models
- Tool call ID normalization to match Anthropic pattern (max 64 chars)
- Claude Code tool name canonicalization
- Interleaved thinking beta feature support
- Prompt caching with `cache_control: { type: "ephemeral" }`

**OAuth Stealth Mode:**
```typescript
const defaultHeaders = {
  accept: "application/json",
  "anthropic-dangerous-direct-browser-access": "true",
  "anthropic-beta": `claude-code-20250219,oauth-2025-04-20,...`,
  "user-agent": `claude-cli/${claudeCodeVersion} (external, cli)`,
  "x-app": "cli",
};
```

### 2.3 Google Generative AI (`providers/google.ts`)

**Key Features:**
- Uses `@google/genai` SDK
- Supports Gemini 3.x thinking levels (LOW, MEDIUM, HIGH)
- Supports Gemini 2.5 Pro/Flash budget-based thinking
- Thought signature handling for multi-turn reasoning replay
- Unique tool call ID generation (combines name, timestamp, counter)

**Thinking Level Mapping:**
```typescript
function getGemini3ThinkingLevel(effort: ClampedThinkingLevel, model: Model): GoogleThinkingLevel {
  // Gemini 3 Pro: minimal/low -> LOW, medium/high -> HIGH
  // Gemini 3 Flash: minimal -> MINIMAL, low -> LOW, medium -> MEDIUM, high -> HIGH
}
```

**Default Budgets:**
- Gemini 2.5 Pro: minimal=128, low=2048, medium=8192, high=32768
- Gemini 2.5 Flash: minimal=128, low=2048, medium=8192, high=24576

### 2.4 Google Shared Utils (`providers/google-shared.ts`)

**Key Functions:**
- `isThinkingPart(part)`: Determines if a part is thinking content (checks `thought: true`)
- `retainThoughtSignature()`: Preserves thought signatures during streaming
- `convertMessages()`: Converts internal messages to Gemini Content format
- `convertTools()`: Converts tools to Gemini function declarations
- `requiresToolCallId()`: Checks if model needs explicit tool call IDs (Claude, GPT-OSS)

**Message Conversion:**
- Handles text, image, thinking, and tool call blocks
- Supports multimodal function responses for Gemini 3
- Preserves thought signatures for same provider/model replay
- Converts unsigned function calls to text for Gemini 3 cross-provider

### 2.5 AWS Bedrock (`providers/amazon-bedrock.ts`)

**Key Features:**
- Uses `@aws-sdk/client-bedrock-runtime`
- Supports proxy configuration via `HTTP_PROXY`/`HTTPS_PROXY`
- HTTP/1.1 fallback via `AWS_BEDROCK_FORCE_HTTP1`
- Skip auth mode via `AWS_BEDROCK_SKIP_AUTH`
- Prompt caching for Claude 3.5 Haiku, 3.7 Sonnet, 4.x models
- Adaptive thinking for Opus 4.6+
- Budget-based thinking for other Claude models
- Interleaved thinking beta support
- Claude-only thinking signatures

**Credential Sources:**
- `AWS_PROFILE` - named profile
- `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` - IAM keys
- `AWS_BEARER_TOKEN_BEDROCK` - Bedrock API keys
- `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` - ECS task roles
- `AWS_WEB_IDENTITY_TOKEN_FILE` - IRSA

---

## 3. Core Utilities

### 3.1 Event Stream (`utils/event-stream.ts`)

**Generic Event Stream Class:**
```typescript
class EventStream<T, R> implements AsyncIterable<T> {
  private queue: T[] = [];
  private waiting: Array<(value: IteratorResult<T>) => void> = [];
  private done = false;
  
  push(event: T): void;
  end(result?: R): void;
  result(): Promise<R>;
  [Symbol.asyncIterator](): AsyncIterator<T>;
}
```

**Assistant Message Event Stream:**
```typescript
class AssistantMessageEventStream extends EventStream<AssistantMessageEvent, AssistantMessage> {
  constructor() {
    super(
      (event) => event.type === "done" || event.type === "error",
      (event) => event.type === "done" ? event.message : event.error
    );
  }
}
```

### 3.2 JSON Parsing (`utils/json-parse.ts`)

**Streaming JSON Parser:**
```typescript
export function parseStreamingJson<T = any>(partialJson: string | undefined): T {
  // 1. Try standard JSON.parse (fastest for complete JSON)
  // 2. Try partial-json library for incomplete JSON
  // 3. Return empty object if all parsing fails
}
```

### 3.3 Validation (`utils/validation.ts`)

**Tool Call Validation:**
```typescript
export function validateToolCall(tools: Tool[], toolCall: ToolCall): any {
  // Finds tool by name
  // Validates arguments against TypeBox schema using AJV
  // Returns coerced arguments or throws validation error
}
```

**Notes:**
- Skips validation in browser extension environment (CSP restrictions)
- AJV requires 'unsafe-eval' CSP which Manifest V3 doesn't allow

### 3.4 Transform Messages (`providers/transform-messages.ts`)

**Key Features:**
- Normalizes tool call IDs for cross-provider compatibility
- Transforms thinking blocks based on same-model check
- Handles orphaned tool calls (inserts synthetic error results)
- Skips errored/aborted assistant messages
- Preserves thought signatures for same provider/model replay

**Same Model Check:**
```typescript
const isSameModel =
  assistantMsg.provider === model.provider &&
  assistantMsg.api === model.api &&
  assistantMsg.model === model.id;
```

### 3.5 Simple Options (`providers/simple-options.ts`)

```typescript
export function buildBaseOptions(model: Model, options?: SimpleStreamOptions, apiKey?: string): StreamOptions;
export function clampReasoning(effort: ThinkingLevel | undefined): Exclude<ThinkingLevel, "xhigh"> | undefined;
export function adjustMaxTokensForThinking(
  baseMaxTokens: number,
  modelMaxTokens: number,
  reasoningLevel: ThinkingLevel,
  customBudgets?: ThinkingBudgets
): { maxTokens: number; thinkingBudget: number };
```

**Default Thinking Budgets:**
- minimal: 1024
- low: 2048
- medium: 8192
- high: 16384

---

## 4. Pi-Coding-Agent Package

### 4.1 SDK (`core/sdk.ts`)

**Main Entry Point:**
```typescript
export async function createAgentSession(options: CreateAgentSessionOptions = {}): Promise<CreateAgentSessionResult> {
  // 1. Setup directories and managers
  // 2. Load or restore session
  // 3. Find/restore model (with fallback)
  // 4. Restore thinking level
  // 5. Create Agent with convertToLlm wrapper
  // 6. Create AgentSession
  // 7. Return session + extensions
}
```

**Options:**
```typescript
interface CreateAgentSessionOptions {
  cwd?: string;
  agentDir?: string;
  authStorage?: AuthStorage;
  modelRegistry?: ModelRegistry;
  model?: Model<any>;
  thinkingLevel?: ThinkingLevel;
  scopedModels?: Array<{ model: Model; thinkingLevel: ThinkingLevel }>;
  tools?: Tool[];
  customTools?: ToolDefinition[];
  resourceLoader?: ResourceLoader;
  sessionManager?: SessionManager;
  settingsManager?: SettingsManager;
}
```

**Image Blocking Support:**
```typescript
const convertToLlmWithBlockImages = (messages: AgentMessage[]): Message[] => {
  // Filters out ImageContent if blockImages setting is enabled
  // Replaces with text placeholder "Image reading is disabled."
  // Deduplicates consecutive placeholders
};
```

### 4.2 Messages (`core/messages.ts`)

**Custom Message Types:**
```typescript
interface BashExecutionMessage {
  role: "bashExecution";
  command: string;
  output: string;
  exitCode: number | undefined;
  cancelled: boolean;
  truncated: boolean;
  fullOutputPath?: string;
  timestamp: number;
  excludeFromContext?: boolean;  // For !! prefix
}

interface CustomMessage<TDetails = any> {
  role: "custom";
  customType: string;
  content: string | (TextContent | ImageContent)[];
  display: boolean;
  details?: TDetails;
  timestamp: number;
}

interface BranchSummaryMessage {
  role: "branchSummary";
  summary: string;
  fromId: string;
  timestamp: number;
}

interface CompactionSummaryMessage {
  role: "compactionSummary";
  summary: string;
  tokensBefore: number;
  timestamp: number;
}
```

**convertToLlm Function:**
Converts AgentMessages (including custom types) to LLM-compatible Messages:
- `bashExecution` -> user message with command output
- `custom` -> user message with content
- `branchSummary` -> user message with summary prefix/suffix
- `compactionSummary` -> user message with compaction summary

### 4.3 Session Manager (`core/session-manager.ts`)

**Entry Types:**
```typescript
type SessionEntry =
  | SessionMessageEntry      // Regular message
  | ThinkingLevelChangeEntry // Thinking level change
  | ModelChangeEntry         // Model/provider change
  | CompactionEntry          // Compaction summary
  | BranchSummaryEntry       // Branch summary
  | CustomEntry              // Extension-specific data
  | CustomMessageEntry       // Extension message in LLM context
  | LabelEntry               // User-defined bookmark
  | SessionInfoEntry;        // Session metadata
```

**Session Context:**
```typescript
interface SessionContext {
  messages: AgentMessage[];
  thinkingLevel: string;
  model: { provider: string; modelId: string } | null;
}
```

**Version Migration:**
- V1 -> V2: Adds id/parentId tree structure
- V2 -> V3: Renames hookMessage role to custom

### 4.4 Tools

#### 4.4.1 Read Tool (`core/tools/read.ts`)

**Features:**
- Reads text files with offset/limit pagination
- Reads and auto-resizes images
- Truncation handling with actionable notices
- First line exceeds limit detection

**Image Handling:**
```typescript
if (mimeType) {
  // Read as image
  const buffer = await ops.readFile(absolutePath);
  const base64 = buffer.toString("base64");
  
  if (autoResizeImages) {
    const resized = await resizeImage({ type: "image", data: base64, mimeType });
    // Include dimension note for coordinate mapping
  }
}
```

**Truncation Notices:**
- Line-based: `[Showing lines X-Y of Z. Use offset=N to continue.]`
- Byte-based: `[Showing lines X-Y of Z (30KB limit). Use offset=N to continue.]`
- Single line too large: `[Line N is X, exceeds 30KB limit. Use bash: sed -n 'Np' file | head -c 30720]`

#### 4.4.2 Bash Tool (`core/tools/bash.ts`)

**Features:**
- Execute bash commands with streaming output
- Timeout support
- Process tree killing on abort
- Output truncation to rolling buffer
- Temp file for full output

**Truncation:**
- Default: 500 lines or 30KB (whichever hit first)
- Saves full output to temp file when truncated
- Provides actionable notice with line range

**Spawn Configuration:**
```typescript
const { shell, args } = getShellConfig();  // Platform-specific
const child = spawn(shell, [...args, command], {
  cwd,
  detached: true,
  env: getShellEnv(),
  stdio: ["ignore", "pipe", "pipe"],
});
```

#### 4.4.3 Write Tool (`core/tools/write.ts`)

**Features:**
- Write content to file (creates or overwrites)
- Auto-creates parent directories
- Abort signal handling

#### 4.4.4 Edit Tool (`core/tools/edit.ts`)

**Features:**
- Replace exact text in file
- Fuzzy matching fallback for whitespace tolerance
- BOM preservation
- Line ending preservation (auto-detect and restore)
- Unified diff generation
- First changed line tracking

**Fuzzy Matching:**
```typescript
function fuzzyFindText(content: string, oldText: string): FuzzyMatchResult {
  // 1. Try exact match
  // 2. Try normalized match (ignore whitespace differences)
  // 3. Return match position and length
}
```

### 4.5 Image Utilities

#### 4.5.1 Image Resize (`utils/image-resize.ts`)

**Features:**
- Uses Photon (Rust/WASM) for image processing
- Resizes to fit within max dimensions (default 2000x2000)
- Compresses to stay under max bytes (default 4.5MB)
- Tries both PNG and JPEG, picks smaller
- Progressive quality reduction if needed
- Progressive dimension reduction if needed

**Strategy:**
1. Resize to maxWidth/maxHeight using Lanczos3
2. Try both PNG and JPEG formats, pick smaller
3. If still too large, try JPEG with decreasing quality (85, 70, 55, 40)
4. If still too large, progressively reduce dimensions (1.0, 0.75, 0.5, 0.35, 0.25)

**Interface:**
```typescript
interface ImageResizeOptions {
  maxWidth?: number;      // Default: 2000
  maxHeight?: number;     // Default: 2000
  maxBytes?: number;      // Default: 4.5MB
  jpegQuality?: number;   // Default: 80
}

interface ResizedImage {
  data: string;           // base64
  mimeType: string;
  originalWidth: number;
  originalHeight: number;
  width: number;
  height: number;
  wasResized: boolean;
}
```

#### 4.5.2 MIME Detection (`utils/mime.ts`)

**Features:**
- Uses `file-type` library for detection
- Sniffs first 4100 bytes
- Returns supported image MIME type or null

**Supported Types:**
- image/jpeg
- image/png
- image/gif
- image/webp

---

## 5. Key Design Patterns

### 5.1 Provider Abstraction

All providers implement:
```typescript
interface ApiProvider<TApi extends Api, TOptions extends StreamOptions> {
  api: TApi;
  stream: StreamFunction<TApi, TOptions>;
  streamSimple: StreamFunction<TApi, SimpleStreamOptions>;
}
```

Registration via:
```typescript
registerApiProvider({
  api: "anthropic-messages",
  stream: streamAnthropic,
  streamSimple: streamSimpleAnthropic,
});
```

### 5.2 Message Transformation Pipeline

1. **transformMessages()**: Cross-provider compatibility
   - Normalizes tool call IDs
   - Transforms thinking blocks (keep for same model, convert to text for different)
   - Handles orphaned tool calls
   - Skips errored/aborted messages

2. **Provider-specific convertMessages()**: API format conversion
   - Converts to provider's native message format
   - Handles images, thinking, tool calls
   - Adds cache control markers

### 5.3 Streaming Architecture

- Event-based streaming with `AssistantMessageEventStream`
- Async iteration support
- Partial message building during stream
- Usage tracking and cost calculation
- Error handling with partial results

### 5.4 Tool System

- TypeBox for JSON Schema generation
- AJV for validation (except browser extensions)
- Pluggable operations for remote execution (SSH)
- Abort signal support throughout
- Streaming updates for long-running operations

### 5.5 Session Persistence

- Line-delimited JSON (NDJSON) format
- Tree structure with id/parentId
- Version migration support
- Branching and compaction support
- Extension-customizable entries

---

## 6. Notable Implementation Details

### 6.1 GitHub Copilot Support

Special headers for Copilot:
```typescript
headers["X-Initiator"] = isAgentCall ? "agent" : "user";
headers["Openai-Intent"] = "conversation-edits";
if (hasImages) {
  headers["Copilot-Vision-Request"] = "true";
}
```

### 6.2 Tool Call ID Normalization

Different providers have different ID requirements:
- **OpenAI**: max 40 chars ( Responses API can be 450+ with special chars)
- **Anthropic**: max 64 chars, alphanumeric + underscore/hyphen only
- **Mistral**: exactly 9 alphanumeric chars

### 6.3 OAuth Token Support (Anthropic)

OAuth tokens start with `sk-ant-oat` and use different auth mechanism:
```typescript
const client = new Anthropic({
  apiKey: null,
  authToken: apiKey,  // OAuth token
  baseURL: model.baseUrl,
  defaultHeaders: { /* Claude Code headers */ },
});
```

### 6.4 Image Handling Strategy

1. Detect MIME type from file header (file-type library)
2. Read and base64 encode
3. Auto-resize if enabled (Photon WASM)
   - Target max 2000x2000
   - Target max 4.5MB
   - Try PNG and JPEG, pick smaller
4. Include dimension note for coordinate mapping

### 6.5 Truncation Strategy

**Text Files:**
- Head truncation for context (keep end of file)
- Line and byte limits
- Actionable continuation notices

**Bash Output:**
- Tail truncation (keep end of output)
- Rolling buffer during execution
- Temp file for full output

---

## 7. Files Summary

### Fetched Files:

**Pi-AI Core:**
- `types.ts` - Core type definitions
- `stream.ts` - Main streaming API
- `api-registry.ts` - Provider registration
- `models.ts` - Model registry and cost calculation
- `env-api-keys.ts` - Environment variable API key resolution

**Pi-AI Providers:**
- `providers/openai-completions.ts` - OpenAI-compatible providers
- `providers/anthropic.ts` - Anthropic Messages API
- `providers/google.ts` - Google Generative AI
- `providers/google-shared.ts` - Shared Google utilities
- `providers/amazon-bedrock.ts` - AWS Bedrock
- `providers/transform-messages.ts` - Cross-provider message transformation
- `providers/simple-options.ts` - Stream options builders
- `providers/register-builtins.ts` - Provider registration

**Pi-AI Utils:**
- `utils/event-stream.ts` - Event streaming infrastructure
- `utils/json-parse.ts` - Streaming JSON parsing
- `utils/validation.ts` - Tool call validation

**Pi-Coding-Agent Core:**
- `core/sdk.ts` - Main SDK entry point
- `core/messages.ts` - Custom message types and conversion
- `core/session-manager.ts` - Session persistence
- `core/agent-session.ts` - Agent session management (partial)

**Pi-Coding-Agent Tools:**
- `core/tools/index.ts` - Tool exports and factories
- `core/tools/read.ts` - File reading with image support
- `core/tools/bash.ts` - Bash execution
- `core/tools/write.ts` - File writing
- `core/tools/edit.ts` - File editing with fuzzy matching

**Pi-Coding-Agent Utils:**
- `utils/image-resize.ts` - Image resizing with Photon
- `utils/mime.ts` - MIME type detection

---

## 8. Dependencies Summary

**Key Production Dependencies:**
- `@anthropic-ai/sdk` - Anthropic API client
- `@aws-sdk/client-bedrock-runtime` - AWS Bedrock
- `@google/genai` - Google Generative AI
- `openai` - OpenAI API client
- `@sinclair/typebox` - JSON Schema generation
- `ajv` + `ajv-formats` - JSON Schema validation
- `partial-json` - Incomplete JSON parsing
- `@silvia-odwyer/photon-node` - Image processing (WASM)
- `file-type` - MIME type detection
- `chalk` - Terminal colors
- `marked` - Markdown parsing
- `diff` - Diff generation
- `glob` + `ignore` + `minimatch` - File matching

---

This summary provides the complete implementation details needed for 100% feature parity with the pi-mono repository's pi-ai and pi-coding-agent packages.
