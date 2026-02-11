# Gap Analysis & Roadmap

> Detailed gap analysis and implementation roadmap
> Updated: 2026-02-09

---

## Gap Summary

| Priority | Items | Effort | Timeline |
|----------|-------|--------|----------|
| 🔴 P0 - Critical | 5 | ~800 LOC | 1-2 weeks |
| 🟡 P1 - Important | 6 | ~1,500 LOC | 2-3 weeks |
| 🟢 P2 - Nice to have | 5 | ~2,000 LOC | Optional |
| **Total** | **16** | **~4,300 LOC** | **4-5 weeks** |

**Note**: Gap count reduced after code review corrections (proxy.ts, config syntax, etc.)

---

## P0 - Critical Gaps ✅ COMPLETED

### 1. Context Overflow Detection ✅
**Pi Mono**: `packages/ai/src/utils/overflow.ts` (121 lines)
**Status**: ✅ Implemented
**File**: `koda/ai/overflow.py`
**Lines**: ~120 LOC

**Purpose**: Detect context overflow errors from different providers via regex patterns

```typescript
const OVERFLOW_PATTERNS = [
  /prompt is too long/i,              // Anthropic
  /exceeds the context window/i,      // OpenAI
  /input token count.*exceeds/i,      // Google
  /maximum prompt length is \d+/i,    // xAI
  // ... 16 patterns total
];

function isContextOverflow(message, contextWindow?): boolean
```

**Note**: This is **error detection**, not prevention!

---

### 2. Config Value Resolution Syntax Fix ✅
**Pi Mono**: `packages/coding-agent/src/core/resolve-config-value.ts` (64 lines)
**Status**: ✅ Implemented with `!command` syntax
**File**: `koda/coding/resolve_config_value.py`

**Current (WRONG)**: Using `$(command)` syntax
**Should be**: Using `!command` syntax

```typescript
// CORRECT implementation:
export function resolveConfigValue(config: string): string | undefined {
  if (config.startsWith("!")) {
    return executeCommand(config)  // Execute shell command
  }
  const envValue = process.env[config]
  return envValue || config
}
```

**Action**: Fix `koda/coding/config_resolver.py`

---

### 3. Stream Proxy ✅
**Pi Mono**: `packages/agent/src/proxy.ts` (340 lines)
**Status**: ✅ Implemented
**File**: `koda/agent/stream_proxy.py`

**Purpose**: HTTP proxy for routing LLM calls through a server

**Previous Misunderstanding**: Implemented multi-agent coordination (doesn't exist in pi-mono)
**Actual Function**: Stream proxy for LLM calls

```typescript
interface ProxyStreamOptions extends SimpleStreamOptions {
  authToken: string
  proxyUrl: string
}

export function streamProxy(model, context, options): ProxyMessageEventStream
```

---

### 4. Unicode Sanitization ✅
**Pi Mono**: `packages/ai/src/utils/sanitize-unicode.ts` (~50 lines)
**Status**: ✅ Implemented
**File**: `koda/ai/sanitize_unicode.py`

**Purpose**: Remove orphaned Unicode surrogates

```typescript
function sanitizeSurrogates(text: string): string
```

---

### 5. Streaming JSON Parser ✅
**Pi Mono**: `packages/ai/src/utils/json-parse.ts` (~100 lines)
**Status**: ✅ Implemented
**File**: `koda/ai/json_parse.py`

**Purpose**: Parse incomplete JSON streams

```typescript
function parseStreamingJson(json: string): any | undefined
```

---

## P1 - Important Gaps

### 6. JSON Schema Validation ✅
**Pi Mono**: `packages/coding-agent/src/core/model-registry.ts:100-200`
**Status**: ✅ Implemented using Pydantic
**File**: `koda/coding/model_schema.py`

**Purpose**: Validate models.json against schema

**Python equivalent**: Use `pydantic` or `jsonschema`

---

### 7. Settings Manager ✅
**Pi Mono**: `packages/coding-agent/src/core/settings-manager.ts` (~500 lines)
**Status**: ✅ Implemented
**File**: `koda/coding/settings_manager.py`

**Purpose**: Hierarchical settings (global + project)

```typescript
class SettingsManager {
  // Global: ~/.koda/settings.json
  // Project: .koda/settings.json
  + load(): Settings
  + save(settings, scope): void
  + watch(callback): void
}
```

---

### 8. HTTP Proxy Support ✅
**Pi Mono**: `packages/ai/src/utils/http-proxy.ts` (~100 lines)
**Status**: ✅ Implemented
**File**: `koda/ai/http_proxy.py`

---

### 9. Session Entry Types ✅
**Pi Mono**: `packages/coding-agent/src/core/session-manager.ts:50-150`
**Status**: ✅ All 6 types implemented
**File**: `koda/coding/session_entries.py`

---

### 10. Session Version Migration ✅
**Pi Mono**: `packages/coding-agent/src/core/session-manager.ts:400-500`
**Status**: ✅ Implemented
**File**: `koda/coding/session_migration.py`

---

### 11. Pluggable Edit Operations ✅
**Pi Mono**: `packages/coding-agent/src/core/tools/edit.ts:50-100`
**Status**: ✅ Implemented
**File**: `koda/coding/tools/edit_operations.py`

---

## P2 - Optional

### 12. MOM Agent 🚫 SKIPPED
**Pi Mono**: `packages/mom/src/agent.ts` (~400 lines)
**Status**: 🚫 Intentionally skipped
**Reason**: MOM is a Slack Bot, not core functionality (per user request)

---

### 13. Download Functionality ✅
**Pi Mono**: `packages/mom/src/download.ts` (~300 lines)
**Status**: ✅ Implemented
**File**: `koda/coding/download.py`

---

### 14. Export HTML ✅
**Pi Mono**: `packages/coding-agent/src/core/export-html/` (~1000 lines)
**Status**: ✅ Implemented
**File**: `koda/coding/export_html.py`

---

### 15. Extensions System ✅
**Pi Mono**: `packages/coding-agent/src/extensions/` (~2000 lines)
**Status**: ✅ Core implemented
**Files**: `koda/coding/extensions/*.py`

---

## Completed Items (Recent)

### ✅ Claude Code Tool Name Mapping
**Completed**: 2026-02-09
**File**: `koda/ai/claude_code_mapping.py`

```python
CLAUDE_CODE_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Grep", "Glob",
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode",
    "KillShell", "NotebookEdit", "Skill", "Task",
    "TaskOutput", "TodoWrite", "WebFetch", "WebSearch",
]

def to_claude_code_name(name: str) -> str
# "ask_user" -> "AskUserQuestion"

def from_claude_code_name(name: str, tools=None) -> str
# "AskUserQuestion" -> "ask_user"
```

**Tests**: 15/15 passing

---

### ✅ GitHub Copilot Provider
**Completed**: Earlier
**File**: `koda/ai/github_copilot.py`

---

### ✅ OAuth Implementations
**Completed**: Earlier
**File**: `koda/ai/oauth.py`

---

### ✅ Advanced Compaction
**Completed**: Earlier
**File**: `koda/mes/compaction_advanced.py`

---

## Implementation Priority

### Week 1: Critical Fixes
1. Fix config value syntax (`!command`)
2. Implement context overflow detection
3. Delete incorrect AgentProxy code

### Week 2: Core Features
4. Implement stream proxy
5. Implement unicode sanitization
6. Implement streaming JSON parser

### Week 3: Important Features
7. Settings Manager
8. Session entry types & migration
9. JSON Schema validation

### Week 4+: Optional
10. HTTP proxy support
11. MOM Agent (if needed)
12. Export HTML
13. Extensions system

---

## 详细文件对比 (packages/coding-agent)

### Core - 主要功能

| Pi Mono 文件 | Koda 对应 | 状态 | 缺失功能 |
|-------------|----------|------|----------|
| `model-resolver.ts` | ❌ | ❌ | **缺失**: 模型解析逻辑 |
| `package-manager.ts` | ❌ | ❌ | **缺失**: 扩展包管理 |
| `skills.ts` | ❌ | ❌ | **缺失**: 完整技能系统 |
| `slash-commands.ts` | ❌ | ❌ | **缺失**: /命令支持 |
| `timings.ts` | ❌ | ❌ | **缺失**: 性能计时 |
| `resource-loader.ts` | ❌ | ❌ | **缺失**: 资源加载 |
| `bash-executor.ts` | `coding/tools/shell_tool.py` | ⚠️ | 基础实现，缺少 hooks |

### Utils (全部缺失)

| Pi Mono 文件 | Koda 对应 | 状态 |
|-------------|----------|------|
| `utils/shell.ts` | ❌ | **缺失** |
| `utils/git.ts` | ❌ | **缺失** |
| `utils/clipboard.ts` | ❌ | **缺失** |
| `utils/image-convert.ts` | ❌ | **缺失** |
| `utils/frontmatter.ts` | ❌ | **缺失** |

### Modes (全部缺失)

| Pi Mono 文件 | Koda 对应 | 状态 |
|-------------|----------|------|
| `modes/interactive/*.ts` (~30个) | ❌ | **缺失**: 交互式模式 |
| `modes/print-mode.ts` | ❌ | **缺失** |
| `modes/rpc/*.ts` (3个) | ❌ | **缺失**: RPC模式 |

---

## 诚实的完成度评估

| 包 | 之前声称 | 实际完成度 | 主要缺失 |
|----|---------|-----------|----------|
| packages/ai | 85% | **~75%** | 2 providers, PKCE, transform-messages |
| packages/agent | 70% | **~95%** | 基本完成 |
| packages/coding-agent | 69% | **~50%** | package-manager, skills, utils |
| packages/mom | 40% | **~30%** | 非Slack功能也缺失 |
| **整体** | ~79% | **~60%** | 核心可用，高级功能缺失 |

---

## 建议实现顺序 (剩余)

1. **PKCE** (`oauth/pkce.ts`) - OAuth安全必需
2. **transform-messages** - 跨provider兼容性
3. **simple-options** - Thinking预算
4. **OpenAI Codex Provider** - 新模型
5. **model-resolver** - 动态模型选择
6. **skills** - 技能系统
7. **package-manager** - 扩展生态

---

*Last Updated: 2026-02-10*
*Corrections*: proxy.ts function, config syntax, overflow.ts purpose
*Merged*: 10_DETAILED_FILE_COMPARISON.md
