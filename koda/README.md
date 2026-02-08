# Koda (KOding Agent)

> An autonomous coding agent framework for Python

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Koda is an autonomous coding agent framework that generates, validates, and improves code through an iterative process inspired by human software development workflows.

Formerly known as **Pi Coding**.

## Features

- 🤖 **Autonomous Coding** - Plans, codes, validates, and reflects automatically
- 🧩 **Modular Architecture** - Planner, Executor, Reflector, Validator components
- 🔧 **Rich Toolset** - Shell, File, Search, Git, API tools included
- 🌐 **API Discovery** - Automatically recommends and configures public APIs
- 🧪 **Self-Testing** - Validates code quality and fixes issues iteratively
- 🔌 **Multi-LLM Support** - Adapter pattern for any LLM provider
- 📦 **Easy Integration** - Drop-in Skill generator for EvoSkill

## Quick Start

### Installation

```bash
pip install koda
```

Or from source:

```bash
git clone https://github.com/yourusername/koda.git
cd koda
pip install -e .
```

### Basic Usage

```python
import asyncio
from koda import KodaAgent, Task
from koda.adapters.openai_adapter import OpenAIAdapter

# Initialize LLM
llm = OpenAIAdapter(api_key="your-api-key")

# Create agent
agent = KodaAgent(llm=llm, verbose=True)

# Define task
task = Task(
    description="Create a weather query tool",
    requirements=[
        "Use OpenWeatherMap API",
        "Handle errors gracefully",
        "Return JSON format",
    ],
)

# Execute
async def main():
    result = await agent.execute(task)
    
    if result.success:
        print("Generated code:")
        print(result.get_main_code())
    else:
        print(f"Failed: {result.error_message}")

asyncio.run(main())
```

### CLI Usage

```bash
# Initialize workspace
koda init --workspace ./my_project

# Generate code
koda generate "Create a REST API client"

# Validate code
koda validate --file main.py

# View config
koda config --show
```

## Architecture

```
KodaAgent
├── Planner (Task planning & API discovery)
├── Executor (Code generation)
├── Validator (Quality checks)
└── Reflector (Review & fix)
```

## Tools Included

| Tool | Purpose | Status |
|------|---------|--------|
| `ShellTool` | Execute shell commands | ✅ |
| `FileTool` | File operations | ✅ |
| `SearchTool` | Code/text search | ✅ |
| `GitTool` | Version control | ✅ |
| `APITool` | HTTP requests | ✅ |

## Documentation

- [Tutorial](./docs/TUTORIAL.md) - Step-by-step guide
- [API Reference](./docs/API.md) - Complete API documentation
- [Architecture](./docs/ARCHITECTURE.md) - Design details
- [Design Doc](./docs/DESIGN.md) - Feature roadmap

## Comparison with Other Agents

| Feature | Koda | Devin | AutoGPT | Pi Agent |
|---------|------|-------|---------|----------|
| **Focus** | Coding | Coding | General | Companion |
| **Open Source** | ✅ | ❌ | ✅ | ❌ |
| **Code Execution** | ✅ (planned) | ✅ | ✅ | ❌ |
| **Sandbox** | 🔄 | ✅ | ✅ | ❌ |
| **Tools** | Rich | Rich | Rich | Limited |
| **Pricing** | Free | Paid | Free | Freemium |

## Configuration

Create `.koda.yaml`:

```yaml
llm:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

agent:
  max_iterations: 3
  enable_reflection: true
  verbose: true

security:
  enable_sandbox: true
  allow_network: false
```

Or use environment variables:

```bash
export KODA_LLM_PROVIDER=openai
export KODA_LLM_MODEL=gpt-4
export KODA_LLM_API_KEY=your-key
```

## Roadmap

### Phase 1: Core (Current)
- ✅ Basic architecture
- ✅ Planner/Executor/Validator/Reflector
- ✅ Tool system

### Phase 2: Tools (v0.2)
- 🔄 Sandbox execution
- 🔄 Code interpreter
- 🔄 Browser automation

### Phase 3: Intelligence (v0.3)
- 🔄 Context memory
- 🔄 Knowledge base
- 🔄 Multi-agent collaboration

### Phase 4: Ecosystem (v0.4)
- 🔄 IDE plugins
- 🔄 API service
- 🔄 Community tools

## Contributing

Contributions are welcome! Areas for contribution:

- Additional LLM adapters (Claude, Gemini, etc.)
- More tools (Database, Docker, Cloud)
- IDE integrations
- Documentation improvements

See [Contributing Guide](./CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](./LICENSE) file.

## Acknowledgements

- Inspired by [Devin](https://www.cognition-labs.com/introducing-devin) by Cognition Labs
- Architecture influenced by [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
- Formerly named "Pi Coding"

---

<p align="center">
Made with ❤️ by the EvoSkill Team
</p>
