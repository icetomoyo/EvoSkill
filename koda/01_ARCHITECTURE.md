# Koda Architecture

> System architecture and design patterns
> Merged from: DESIGN_ROADMAP.md, IMPLEMENTATION_STATUS.md

---

## 1. System Overview

Koda is a Python implementation of Pi Mono's AI coding agent framework, providing:

- **Unified LLM Interface**: Support for 20+ providers
- **Agent Framework**: Loop-based agent with tool execution
- **Session Management**: Tree-based conversation history
- **Coding Tools**: File operations, search, editing
- **MOM Integration**: Model-optimized message handling

## 2. Module Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Application                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Agent Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Agent Loop  │  │   Proxy     │  │   Tools     │         │
│  │             │  │  (Multi)    │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Session Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Session   │  │   Branch    │  │ Compaction  │         │
│  │   Manager   │  │   Manager   │  │   Engine    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    AI Layer                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Providers  │  │   Models    │  │    OAuth    │         │
│  │  (20+)      │  │  Registry   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 3. Data Flow

```
User Input
    │
    ▼
┌──────────────┐
│ Context      │
│ Builder      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Agent Loop   │◄──────┐
└──────┬───────┘       │
       │               │
       ▼               │
┌──────────────┐       │
│ LLM Provider │       │
└──────┬───────┘       │
       │               │
       ▼               │
┌──────────────┐       │
│ Response     │       │
│ Parser       │       │
└──────┬───────┘       │
       │               │
       ├──── Tool ─────┘
       │    Call
       ▼
┌──────────────┐
│ Tool         │
│ Execution    │
└──────┬───────┘
       │
       ▼
   Output
```

## 4. Core Components

### 4.1 AI Module (`koda.ai`)

**Purpose**: Unified LLM interface

**Key Classes**:
- `BaseProvider`: Abstract base for all providers
- `ModelRegistry`: Model discovery and metadata
- `AssistantMessageEventStream`: Streaming infrastructure

**Providers**:
| Provider | Status | Features |
|----------|--------|----------|
| OpenAI (Completions) | ✅ | Full |
| OpenAI (Responses) | ✅ | Full |
| Anthropic | ✅ | Full |
| Google | ✅ | Full |
| Azure OpenAI | ✅ | Full |
| Bedrock | ✅ | Full |
| GitHub Copilot | ❌ | Missing |

### 4.2 Agent Module (`koda.agent`)

**Purpose**: Agent execution loop

**Key Classes**:
- `AgentLoop`: Main execution loop
- `AgentLoopConfig`: Configuration
- `AgentTool`: Tool wrapper

**Features**:
- ✅ Max iteration protection
- ✅ Retry with exponential backoff
- ✅ Parallel tool execution
- ✅ AbortSignal support
- ❌ AgentProxy (multi-agent)

### 4.3 Coding Module (`koda.coding`)

**Purpose**: Coding agent functionality

**Key Classes**:
- `SessionManager`: Conversation management
- `AuthStorage`: Secure credential storage
- `ModelRegistry`: Extended model management
- `SettingsManager`: Configuration

**Tools**:
| Tool | Status | Features |
|------|--------|----------|
| Read | ✅ | Full |
| Write | ✅ | Full |
| Edit | ⚠️ | Basic fuzzy |
| Bash | ⚠️ | Basic |
| Grep | ✅ | Full |
| Find | ✅ | Full |
| Ls | ✅ | Full |

### 4.4 MOM Module (`koda.mom`)

**Purpose**: Model-optimized messages

**Key Classes**:
- `ContextManager`: Dynamic context
- `Store`: Persistent storage
- `Sandbox`: Isolated execution

**Features**:
- ✅ Context management
- ✅ Auto-compaction
- ✅ Persistent storage
- ✅ Sandbox
- ❌ MOMAgent class
- ❌ Download

## 5. Design Patterns

### 5.1 Provider Pattern

```python
class BaseProvider(ABC):
    @abstractmethod
    async def stream(self, model, context, options) -> AssistantMessageEventStream:
        pass
    
    @abstractmethod
    def calculate_cost(self, model, usage) -> float:
        pass
```

### 5.2 Event-Driven Architecture

```python
class AssistantMessageEventStream:
    async def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        # Yield events as they arrive
        
    def on_event(self, callback: Callable) -> None:
        # Register event handler
```

### 5.3 Tool Interface

```python
class AgentTool:
    name: str
    description: str
    parameters: dict
    execute: Callable[..., Any]
```

## 6. Configuration

### 6.1 Environment Variables

```bash
# Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Azure
AZURE_OPENAI_ENDPOINT=https://...openai.azure.com
AZURE_OPENAI_API_KEY=...

# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### 6.2 Settings File

```yaml
# ~/.koda/settings.json
{
  "compaction": {
    "max_tokens": 128000,
    "trigger_ratio": 0.8
  },
  "images": {
    "max_width": 2048,
    "max_height": 2048
  },
  "retry": {
    "max_attempts": 3,
    "base_delay": 1.0
  }
}
```

## 7. Extension Points

### 7.1 Custom Provider

```python
from koda.ai import BaseProvider

class MyProvider(BaseProvider):
    @property
    def api_type(self) -> str:
        return "my-api"
    
    async def stream(self, model, context, options):
        # Implementation
        pass
```

### 7.2 Custom Tool

```python
def my_tool(query: str) -> str:
    return f"Result: {query}"

tool = AgentTool(
    name="my_tool",
    description="Does something",
    parameters={"type": "object", "properties": {...}},
    execute=my_tool
)
```

## 8. Performance Considerations

### 8.1 Streaming

- Use async generators for memory efficiency
- Process chunks as they arrive
- Backpressure handling

### 8.2 Caching

- Model metadata caching
- Session state persistence
- Token usage tracking

### 8.3 Concurrency

- Parallel tool execution
- Connection pooling
- Rate limit handling

## 9. Security

### 9.1 Credential Storage

- API Keys: System keyring
- OAuth Tokens: Encrypted file storage
- No credentials in code

### 9.2 Sandboxing

- Isolated execution environment
- Resource limits
- Network restrictions

### 9.3 Input Validation

- JSON Schema validation
- Path traversal protection
- Command injection prevention

## 10. Future Architecture

### 10.1 Planned Components

- **TUI**: Terminal UI (deferred)
- **Extension System**: Plugin architecture (deferred)
- **Web UI**: Browser interface (future)

### 10.2 Scalability

- Horizontal scaling for multi-agent
- Distributed session storage
- Load balancing

---

*Last Updated: 2026-02-10*
