# Koda vs Pi Mono - Detailed Feature Comparison

> Generated: 2026-02-09
> Pi Mono Reference: badlogic/pi-mono (packages/ai, packages/mom, packages/agent, packages/coding-agent)

## Summary

| Package | Pi Mono Lines | Koda Status | Coverage |
|---------|---------------|-------------|----------|
| packages/ai | ~32,000 | Partial | ~30% |
| packages/mom | ~4,000 | Partial | ~40% |
| packages/agent | ~3,000 | Partial | ~50% |
| packages/coding-agent | ~66,000 | Minimal | ~15% |
| **Total** | **~105,000** | | **~20%** |

---

## 1. packages/ai - LLM Provider Interface

### 1.1 Model Registry ❌ MISSING
**Pi Mono:** `packages/ai/src/models.ts`, `packages/ai/src/models.generated.ts`

Features:
- Automatic model discovery from providers
- Model capability detection (vision, tools, streaming, etc.)
- Model metadata (context window, pricing, etc.)
- Generated model list from provider APIs

**Koda Gap:** No model registry - only hardcoded model lists in providers.

### 1.2 OAuth Authentication ❌ MISSING
**Pi Mono:** `packages/ai/src/utils/oauth/`

Providers:
- `google-gemini-cli.ts` - Google OAuth
- `anthropic.ts` - Anthropic OAuth
- `github-copilot.ts` - GitHub Copilot OAuth
- `openai-codex.ts` - OpenAI OAuth
- `pkce.ts` - PKCE flow utilities

**Koda Gap:** Only API key authentication, no OAuth support.

### 1.3 Providers ⚠️ PARTIAL
| Provider | Pi Mono | Koda | Status |
|----------|---------|------|--------|
| OpenAI | ✅ | ✅ | Basic support |
| Anthropic | ✅ | ✅ | Basic support |
| Google Gemini | ✅ | ❌ | **MISSING** |
| Google Vertex | ✅ | ❌ | **MISSING** |
| Azure OpenAI | ✅ | ❌ | **MISSING** |
| Amazon Bedrock | ✅ | ❌ | **MISSING** |
| GitHub Copilot | ✅ | ❌ | **MISSING** |

### 1.4 API Registry ❌ MISSING
**Pi Mono:** `packages/ai/src/api-registry.ts`
- Dynamic provider registration
- Provider discovery
- API key management

### 1.5 Streaming Support ⚠️ PARTIAL
**Pi Mono:** `packages/ai/src/stream.ts`
- Full streaming with event stream parsing
- Tool call streaming
- Content filtering

**Koda Gap:** Basic streaming only, no advanced features.

### 1.6 Token Counting ✅ IMPLEMENTED
**Koda:** `koda/ai/tokenizer.py`
- Tiktoken support for OpenAI models
- Estimate fallback for other models

### 1.7 Message Transformation ❌ MISSING
**Pi Mono:** `packages/ai/src/providers/transform-messages.ts`
- Converting between provider message formats
- Image handling
- Tool result normalization

---

## 2. packages/mom - Model-Optimized Messages

### 2.1 Context Management ❌ MISSING
**Pi Mono:** `packages/mom/src/context.ts`
- Dynamic context window management
- Smart truncation strategies

**Koda Status:** Basic `HistoryManager` exists but limited.

### 2.2 Event System ✅ IMPLEMENTED
**Koda:** `koda/agent/events.py`
- Event bus with pub/sub

### 2.3 Sandbox ❌ MISSING
**Pi Mono:** `packages/mom/src/sandbox.ts`
- Isolated execution environment
- Security boundaries

### 2.4 Slack Integration ❌ MISSING
**Pi Mono:** `packages/mom/src/slack.ts`
- Slack bot interface
- Message handling

### 2.5 Store ❌ MISSING
**Pi Mono:** `packages/mom/src/store.ts`
- Persistent storage
- Data migration

### 2.6 Tools ⚠️ PARTIAL
| Tool | Pi Mono | Koda | Status |
|------|---------|------|--------|
| bash | ✅ | ✅ | Basic |
| read | ✅ | ✅ | Basic |
| write | ✅ | ✅ | Basic |
| edit | ✅ | ✅ | Partial |
| truncate | ✅ | ✅ | Basic |
| attach | ✅ | ❌ | **MISSING** |

---

## 3. packages/agent - Agent Core

### 3.1 Agent Loop ⚠️ PARTIAL
**Pi Mono:** `packages/agent/src/agent-loop.ts`
- Message loop with tool execution
- Error handling
- Retry logic

**Koda:** Basic agent in `koda/agent/agent.py`

### 3.2 Agent Proxy ❌ MISSING
**Pi Mono:** `packages/agent/src/proxy.ts`
- Agent delegation
- Multi-agent coordination

### 3.3 Agent Types ✅ IMPLEMENTED
Basic types defined.

---

## 4. packages/coding-agent - Full Coding Agent

### 4.1 CLI ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/cli.ts`, `packages/coding-agent/src/cli/`

Features:
- Argument parsing
- Config selector
- File processor
- Session picker
- Model lister

### 4.2 Core Components

#### 4.2.1 Agent Session ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/agent-session.ts`
- Session lifecycle management
- State persistence
- Branch management
- Message tree navigation

#### 4.2.2 Auth Storage ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/auth-storage.ts`
- Secure credential storage
- Token refresh
- Multi-provider auth

#### 4.2.3 Bash Executor ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/bash-executor.ts`
- Shell execution
- Environment management
- Output streaming
- Timeout handling

#### 4.2.4 Compaction ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/compaction/`

Files:
- `compaction.ts` - Main compaction logic
- `branch-summarization.ts` - Summarize conversation branches
- `utils.ts` - Compaction utilities

Features:
- Automatic context window management
- Conversation summarization
- Branch pruning
- Smart retention

#### 4.2.5 Event Bus ✅ IMPLEMENTED
**Koda:** `koda/agent/events.py`

#### 4.2.6 Export HTML ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/export-html/`
- Session export to HTML
- ANSI to HTML conversion
- Syntax highlighting

#### 4.2.7 Extensions System ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/extensions/`

Files:
- `index.ts` - Extension exports
- `loader.ts` - Extension loading
- `runner.ts` - Extension execution
- `types.ts` - Extension types
- `wrapper.ts` - Extension wrapper

Features:
- Third-party extensions
- Extension marketplace
- Runtime extension loading
- TypeScript-based extensions

**Koda Gap:** No extension system.

#### 4.2.8 Footer Data Provider ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/footer-data-provider.ts`
- Status bar information
- Dynamic updates

#### 4.2.9 Keybindings ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/keybindings.ts`
- Keyboard shortcuts
- Custom key mapping

#### 4.2.10 Messages ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/messages.ts`
- Message formatting
- Content types

#### 4.2.11 Model Registry ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/model-registry.ts`
- Model discovery
- Scoped models
- Model metadata

#### 4.2.12 Model Resolver ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/model-resolver.ts`
- Model selection logic
- Fallback handling

#### 4.2.13 Package Manager ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/package-manager.ts`
- Extension package management
- Dependency resolution
- npm-like functionality

#### 4.2.14 Prompt Templates ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/prompt-templates.ts`
- Dynamic prompts
- Template variables

#### 4.2.15 Resource Loader ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/resource-loader.ts`
- External resource loading
- Cache management

#### 4.2.16 SDK ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/sdk.ts`
- Programmatic API
- Custom agent creation

#### 4.2.17 Session Manager ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/session-manager.ts`
- Session CRUD
- Tree navigation
- Search
- Import/export

#### 4.2.18 Settings Manager ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/settings-manager.ts`

**Koda:** Basic `Settings` class in `koda/coding/settings.py`

#### 4.2.19 Skills System ⚠️ PARTIAL
**Pi Mono:** `packages/coding-agent/src/core/skills.ts`

**Koda:** EvoSkill has skills system, integration needed.

#### 4.2.20 Slash Commands ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/slash-commands.ts`
- Built-in commands
- Custom commands

#### 4.2.21 System Prompt ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/system-prompt.ts`
- Dynamic system prompts
- Context injection

#### 4.2.22 Timings ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/core/timings.ts`
- Performance tracking
- Request timing

#### 4.2.23 Tools ⚠️ PARTIAL
| Tool | Pi Mono | Koda | Notes |
|------|---------|------|-------|
| bash | ✅ | ✅ | Basic |
| edit | ✅ | ✅ | Needs diff mode |
| edit-diff | ✅ | ❌ | **MISSING** |
| find | ✅ | ✅ | Basic |
| grep | ✅ | ✅ | Basic |
| ls | ✅ | ✅ | Basic |
| read | ✅ | ✅ | Basic |
| truncate | ✅ | ✅ | Basic |
| write | ✅ | ✅ | Basic |

### 4.3 Interactive Mode (TUI) ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/modes/interactive/`

Components (66+ files):
- `interactive-mode.ts` - Main TUI
- `components/` - UI components
  - Model selector
  - Session selector
  - Theme selector
  - Settings selector
  - Tool execution display
  - Diff viewer
  - Footer
  - And many more...
- `theme/` - Color themes

**Koda Gap:** No TUI - command line only.

### 4.4 Print Mode ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/modes/print-mode.ts`
- Non-interactive output

### 4.5 RPC Mode ❌ MISSING
**Pi Mono:** `packages/coding-agent/src/modes/rpc/`
- RPC client/server
- External integration

---

## 5. Critical Missing Features (Priority Order)

### P0 - Essential for MVP
1. **Model Registry** - Dynamic model discovery and metadata
2. **Compaction** - Context window management with summarization
3. **Session Management** - Persistent sessions with tree navigation
4. **Settings Manager** - Full settings persistence and management
5. **Edit-Diff Tool** - Structured file editing with diffs

### P1 - Important for Usability
6. **TUI (Interactive Mode)** - Terminal UI for better UX
7. **OAuth Authentication** - Login with Google, Anthropic, etc.
8. **Extension System** - Plugin architecture
9. **Additional Providers** - Gemini, Azure, Bedrock
10. **Export HTML** - Session export functionality

### P2 - Nice to Have
11. **Package Manager** - Extension marketplace
12. **Slack Integration** - Chat bot
13. **Sandbox** - Isolated execution
14. **RPC Mode** - External integration
15. **More Tools** - attach, custom tools

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure (1-2 weeks)
- [ ] Model Registry with model discovery
- [ ] Compaction system with summarization
- [ ] Enhanced Session Manager with tree support
- [ ] Complete Settings Manager

### Phase 2: Tool Enhancements (1 week)
- [ ] Edit-Diff tool implementation
- [ ] Enhanced Bash executor
- [ ] Tool result formatting

### Phase 3: Authentication (3-5 days)
- [ ] OAuth flow for Google/Anthropic
- [ ] Secure token storage
- [ ] Auth UI

### Phase 4: TUI (2-3 weeks)
- [ ] Terminal UI framework
- [ ] Interactive components
- [ ] Theme system

### Phase 5: Extensions (1-2 weeks)
- [ ] Extension loading system
- [ ] Extension API
- [ ] Package manager basics

---

## 7. Files Breakdown

### Pi Mono packages/ai (32k lines)
```
src/
├── index.ts              # Exports
├── cli.ts                # CLI interface
├── models.ts             # Model definitions (~1000 lines)
├── models.generated.ts   # Auto-generated models
├── api-registry.ts       # Provider registry
├── env-api-keys.ts       # API key management
├── stream.ts             # Streaming support
├── types.ts              # Core types
├── providers/            # Provider implementations (~15k lines)
│   ├── anthropic.ts
│   ├── openai-*.ts       # Multiple OpenAI variants
│   ├── google*.ts        # Google providers
│   ├── amazon-bedrock.ts
│   └── ...
└── utils/                # Utilities (~10k lines)
    ├── oauth/            # OAuth implementations
    ├── event-stream.ts
    └── ...
test/                     # Tests (~6k lines)
```

### Pi Mono packages/coding-agent (66k lines)
```
src/
├── cli/                  # CLI handling (~2k lines)
├── core/                 # Core functionality (~25k lines)
│   ├── agent-session.ts
│   ├── compaction/
│   ├── extensions/
│   ├── export-html/
│   ├── session-manager.ts
│   ├── settings-manager.ts
│   └── tools/
├── modes/                # Operating modes (~25k lines)
│   ├── interactive/      # TUI components
│   ├── print-mode.ts
│   └── rpc/
└── utils/                # Utilities (~5k lines)
```

---

## 8. Conclusion

Koda currently implements approximately **20%** of Pi Mono's functionality. The core gaps are:

1. **No TUI** - Biggest UX difference
2. **Limited compaction** - No summarization
3. **No model registry** - Hardcoded models only
4. **No OAuth** - API keys only
5. **No extension system** - Closed architecture
6. **Basic session management** - No tree navigation

To achieve full Pi Mono parity, significant work is needed, particularly in:
- Interactive TUI (~25k lines in Pi)
- Compaction system
- Extension architecture
- OAuth authentication
- Additional LLM providers
