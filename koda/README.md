# Koda Documentation

> Pi Mono Compatible AI Coding Agent Framework
> Version: 0.5.0

## Documentation Index

| Document | Description | Size |
|----------|-------------|------|
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture and design | ~15KB |
| [02_PI_MONO_ANALYSIS.md](02_PI_MONO_ANALYSIS.md) | Complete Pi Mono module analysis | ~26KB |
| [03_IMPLEMENTATION_STATUS.md](03_IMPLEMENTATION_STATUS.md) | Current implementation status | ~8KB |
| [04_GAP_ANALYSIS.md](04_GAP_ANALYSIS.md) | Gap analysis and roadmap | ~10KB |
| [05_API_REFERENCE.md](05_API_REFERENCE.md) | API reference | ~12KB |

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

## Module Overview

```
koda/
├── ai/          # LLM Provider Interface (70% complete)
├── agent/       # Agent Framework (75% complete)
├── coding/      # Coding Agent (55% complete)
├── mes/         # Message Optimization (70% complete)
└── mom/         # Model-Optimized Messages (60% complete)
```

## Status Summary

| Package | Completion | Status |
|---------|------------|--------|
| packages/ai | 70% | 🟡 In Progress |
| packages/agent | 75% | 🟡 In Progress |
| packages/coding-agent | 55% | 🔴 Needs Work |
| packages/mom | 60% | 🟡 In Progress |
| **Total** | **68%** | 🟢 Improving |

## Links

- [GitHub Repository](https://github.com/icetomoyo/EvoSkill)
- [Pi Mono Reference](https://github.com/badlogic/pi-mono)
