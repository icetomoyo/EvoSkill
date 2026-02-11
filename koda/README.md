# Koda Documentation

> Pi Mono Compatible AI Coding Agent Framework
> Version: 0.5.0

---

## Documentation Index

| Document | Description | Status |
|----------|-------------|--------|
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture and design | Current |
| [02_PI_MONO_ANALYSIS.md](02_PI_MONO_ANALYSIS.md) | Complete Pi Mono module analysis | Current |
| [03_IMPLEMENTATION_STATUS.md](03_IMPLEMENTATION_STATUS.md) | Implementation status | Current |
| [04_GAP_ANALYSIS.md](04_GAP_ANALYSIS.md) | **Detailed gap analysis & file comparison** | **Updated 2026-02-10** |
| [05_API_REFERENCE.md](05_API_REFERENCE.md) | API reference | Current |

---

## Quick Start

```python
from koda.ai import get_provider_registry
from koda.agent.loop import AgentLoop, AgentLoopConfig
from koda.coding.session_manager import SessionManager

# 1. Setup provider
provider = get_provider_registry().create("openai-v2")

# 2. Create agent
tools = [...]
config = AgentLoopConfig(max_iterations=50)
agent = AgentLoop(provider, model, tools, config)

# 3. Run
response = await agent.run(context)
```

---

## Module Overview

```
koda/
├── ai/          # LLM Provider Interface (85% complete)
├── agent/       # Agent Framework (70% complete)
├── coding/      # Coding Agent (69% complete)
├── mes/         # Message Optimization (70% complete)
└── mom/         # Model-Optimized Messages (40% complete)
```

---

## Status Summary

| Package | Completion | Status |
|---------|------------|--------|
| packages/ai | 85% | 🟡 In Progress |
| packages/agent | 70% | 🟡 In Progress |
| packages/coding-agent | 69% | 🟡 In Progress |
| packages/mom | 40% | 🔴 Needs Work |
| **Total** | **~79%** | 🟢 Improving |

---

## Recent Updates (2026-02-09)

### ✅ Completed
- **Claude Code Tool Name Mapping** - Full implementation with 15/15 tests passing
- **File-by-file code review** - Analyzed all pi-mono source files

### 🔧 Corrections
- **`agent/proxy.ts`** - Was incorrectly implemented as multi-agent coordination; actually **stream proxy for HTTP routing**
- **`resolve-config-value.ts`** - Was using `$(command)` syntax; correct syntax is **`!command`**
- **`overflow.ts`** - Is **error detection** (regex matching), not token management

### 📝 Documentation
- Merged and updated analysis documents
- Reduced document count from 8 to 5
- Clarified actual vs perceived functionality

---

## Next Steps

See [04_GAP_ANALYSIS.md](04_GAP_ANALYSIS.md) for detailed roadmap.

### Week 1: Critical Fixes
1. Fix config value syntax (`!command`)
2. Implement context overflow detection
3. Implement stream proxy (correctly)

### Week 2: Core Features
4. Unicode sanitization
5. Streaming JSON parser
6. HTTP proxy support

---

## Links

- [GitHub Repository](https://github.com/icetomoyo/EvoSkill)
- [Pi Mono Reference](https://github.com/badlogic/pi-mono)

---

*Last Updated: 2026-02-09*
