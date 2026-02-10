# Gap Analysis & Roadmap

> Detailed gap analysis and implementation roadmap
> Merged from: PI_MONO_100_PERCENT_CHECKLIST.md, IMPLEMENTATION_PROGRESS.md

---

## Gap Summary

| Priority | Items | Effort | Timeline |
|----------|-------|--------|----------|
| 🔴 P0 - Critical | 23 | ~3,500 LOC | 4-5 weeks |
| 🟡 P1 - Important | 8 | ~1,500 LOC | 1-2 weeks |
| 🟢 P2 - Nice to have | 5 | ~1,000 LOC | Optional |
| **Total** | **36** | **~6,000 LOC** | **6 weeks** |

---

## P0 - Critical Gaps

### AI Package (8 items)

#### 1. GitHub Copilot Provider
**Pi Mono**: `packages/ai/src/providers/github-copilot.ts`
**Status**: ❌ Not implemented
**Effort**: ~500 LOC
**Dependencies**: OAuth

**Features**:
- Device code flow authentication
- Special token handling
- Copilot-specific headers
- Model: `gpt-4o-copilot`

**Implementation**:
```python
class GitHubCopilotProvider(BaseProvider):
    api_type = "github-copilot"
    
    async def authenticate_device(self):
        # Device code flow
        pass
```

---

#### 2. Anthropic OAuth
**Pi Mono**: `packages/ai/src/utils/oauth/anthropic.ts`
**Status**: ❌ Not implemented
**Effort**: ~400 LOC

**Features**:
- OAuth 2.0 flow
- Token refresh
- Scope management

---

#### 3. GitHub Copilot OAuth  
**Pi Mono**: `packages/ai/src/utils/oauth/github-copilot.ts`
**Status**: ❌ Not implemented
**Effort**: ~600 LOC

**Features**:
- Device code flow
- Token exchange
- Copilot subscription check

---

#### 4. Claude Code Tool Name Mapping
**Pi Mono**: `packages/ai/src/providers/anthropic.ts:90-120`
**Status**: ❌ Not implemented
**Effort**: ~50 LOC

**Purpose**: Convert tool names to Claude Code canonical casing

```typescript
const claudeCodeTools = [
  "Read", "Write", "Edit", "Bash", "Grep", "Glob",
  "AskUserQuestion", "EnterPlanMode", "ExitPlanMode",
  "KillShell", "NotebookEdit", "Skill", "Task",
  "TaskOutput", "TodoWrite", "WebFetch", "WebSearch"
];
```

---

#### 5. Interleaved Thinking
**Pi Mono**: `packages/ai/src/providers/anthropic.ts:200-250`
**Status**: ❌ Not implemented
**Effort**: ~100 LOC

**Purpose**: Support interleaved thinking and text blocks

---

#### 6-8. SSE Edge Cases
**Pi Mono**: Various tests
**Status**: ⚠️ Partial
**Effort**: ~200 LOC

**Missing**:
- Empty stream handling
- Unicode surrogate handling
- Retry delay edge cases

---

### Agent Package (2 items)

#### 9. AgentProxy
**Pi Mono**: `packages/agent/src/proxy.ts`
**Status**: ❌ Not implemented
**Effort**: ~600 LOC

**Features**:
- Multi-agent coordination
- Agent registration
- Load balancing
- Task routing

```typescript
class AgentProxy {
  registerAgent(name: string, agent: AgentLoop): void;
  delegate(task: string, toAgent?: string): Promise<AssistantMessage>;
}
```

---

#### 10. Task Delegation
**Pi Mono**: `packages/agent/src/proxy.ts:150-300`
**Status**: ❌ Not implemented
**Effort**: ~200 LOC

**Purpose**: Route tasks to appropriate agents

---

### Coding-Agent Package (10 items)

#### 11. ModelRegistry Schema Validation
**Pi Mono**: `packages/coding-agent/src/core/model-registry.ts:100-200`
**Status**: ❌ Not implemented
**Effort**: ~400 LOC

**Purpose**: Validate models.json against schema

**Schema**:
```typescript
const ModelDefinitionSchema = Type.Object({
  id: Type.String({ minLength: 1 }),
  name: Type.Optional(Type.String()),
  api: Type.Optional(Type.String()),
  // ...
});
```

**Python equivalent**: Use `pydantic` or `jsonschema`

---

#### 12. Config Value Resolution
**Pi Mono**: `packages/coding-agent/src/core/resolve-config-value.ts`
**Status**: ❌ Not implemented
**Effort**: ~200 LOC

**Features**:
- Environment variable substitution: `${VAR}`
- Command substitution: `$(command)`

```python
def resolve_config_value(value: str) -> str:
    # Replace ${ENV_VAR}
    # Execute $(shell command)
    pass
```

---

#### 13. Smart Cut Point Detection
**Pi Mono**: `packages/coding-agent/src/core/compaction/utils.ts:50-150`
**Status**: ❌ Not implemented
**Effort**: ~150 LOC

**Purpose**: Find optimal point to compact conversation

```typescript
export function findCutPoint(entries: SessionEntry[]): number {
  // Find turn boundary
  // Prefer after assistant message
  // Keep recent context
}
```

---

#### 14. File Operation Tracking
**Pi Mono**: `packages/coding-agent/src/core/compaction/utils.ts:200-300`
**Status**: ❌ Not implemented
**Effort**: ~150 LOC

**Purpose**: Track file operations for deduplication

---

#### 15. Session Entry Types
**Pi Mono**: `packages/coding-agent/src/core/session-manager.ts:50-150`
**Status**: ⚠️ Partial (3/6 types)
**Effort**: ~200 LOC

**Missing Entry Types**:
- ModelChangeEntry
- ThinkingLevelChangeEntry
- CustomEntry
- FileEntry

---

#### 16. Session Version Migration
**Pi Mono**: `packages/coding-agent/src/core/session-manager.ts:400-500`
**Status**: ❌ Not implemented
**Effort**: ~150 LOC

**Purpose**: Migrate old session formats

```typescript
export function migrateSessionEntries(
  entries: any[],
  fromVersion: number
): SessionEntry[] {
  // Version-specific migrations
}
```

---

#### 17. Hierarchical Settings
**Pi Mono**: `packages/coding-agent/src/core/settings-manager.ts:100-250`
**Status**: ❌ Not implemented
**Effort**: ~300 LOC

**Purpose**: Merge global and project settings

```yaml
# ~/.koda/settings.json (global)
# .koda/settings.json (project)
```

---

#### 18. Settings File Watch
**Pi Mono**: `packages/coding-agent/src/core/settings-manager.ts:300-400`
**Status**: ❌ Not implemented
**Effort**: ~150 LOC

**Purpose**: Auto-reload settings on file change

---

#### 19. Pluggable Edit Operations
**Pi Mono**: `packages/coding-agent/src/core/tools/edit.ts:50-100`
**Status**: ❌ Not implemented
**Effort**: ~100 LOC

**Purpose**: Allow custom file operations (e.g., SSH)

```typescript
export interface EditOperations {
  readFile: (path: string) => Promise<Buffer>;
  writeFile: (path: string, content: string) => Promise<void>;
  access: (path: string) => Promise<void>;
}
```

---

#### 20. Bash Spawn Hooks
**Pi Mono**: `packages/coding-agent/src/core/tools/bash.ts:100-200`
**Status**: ❌ Not implemented
**Effort**: ~150 LOC

**Purpose**: Intercept bash execution (for SSH, etc.)

```typescript
export interface BashSpawnHook {
  beforeSpawn?: (context: BashSpawnContext) => void;
  afterSpawn?: (context: BashSpawnContext, result: any) => void;
}
```

---

### MOM Package (3 items)

#### 21. MOMAgent Class
**Pi Mono**: `packages/mom/src/agent.ts`
**Status**: ❌ Not implemented
**Effort**: ~800 LOC

**Purpose**: Main MOM agent implementation

**Features**:
- Integrate context, store, sandbox
- Event handling
- Tool execution

---

#### 22. Download Functionality
**Pi Mono**: `packages/mom/src/download.ts`
**Status**: ❌ Not implemented
**Effort**: ~300 LOC

**Purpose**: Download files from URLs

---

#### 23. Slack Bot (Optional)
**Pi Mono**: `packages/mom/src/slack.ts`
**Status**: ❌ Not implemented
**Effort**: ~600 LOC

**Purpose**: Slack integration

---

## P1 - Important Gaps

### 24. JSON Schema Validation
**Effort**: ~400 LOC
**Tool**: Pydantic or jsonschema

### 25. Precise Token Counting
**Effort**: ~300 LOC
**Tool**: tiktoken integration

### 26. Advanced Error Classification
**Effort**: ~200 LOC

### 27. Usage Aggregation
**Effort**: ~200 LOC

### 28. Loop Detection
**Effort**: ~150 LOC

### 29. Export HTML
**Effort**: ~500 LOC

### 30-32. Advanced Provider Features
**Effort**: ~500 LOC total

---

## P2 - Nice to Have

### 33-37. Extended Features
- Web UI
- Advanced analytics
- Plugin marketplace
- Cloud sync
- Team collaboration

---

## Implementation Priority

### Week 1: AI Package
1. GitHub Copilot Provider
2. Anthropic OAuth
3. GitHub Copilot OAuth
4. Claude Code tool mapping

### Week 2: AI Package cont.
5. Interleaved thinking
6. SSE edge cases

### Week 3: Agent Package
7. AgentProxy
8. Task delegation

### Week 4: Coding-Agent Package
9. Schema validation
10. Config resolution
11. Smart cut point
12. File operation tracking

### Week 5: Coding-Agent cont.
13. Session entry types
14. Version migration
15. Hierarchical settings
16. File watch
17. Edit operations
18. Bash hooks

### Week 6: MOM Package
19. MOMAgent
20. Download

### Week 7: Polish
21. P1 items
22. Testing
23. Documentation

---

## Success Criteria

### 100% Parity Checklist

- [ ] All P0 items implemented
- [ ] All P1 items implemented (or documented why not)
- [ ] All tests passing
- [ ] Integration tests match Pi Mono behavior
- [ ] Documentation complete

---

*Last Updated: 2026-02-10*
