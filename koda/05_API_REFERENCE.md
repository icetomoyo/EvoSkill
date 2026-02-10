# API Reference

> Complete API reference for Koda

---

## koda.ai

### Types

#### Enums

```python
class KnownApi(Enum):
    OPENAI_COMPLETIONS = "openai-completions"
    OPENAI_RESPONSES = "openai-responses"
    AZURE_OPENAI_RESPONSES = "azure-openai-responses"
    OPENAI_CODEX_RESPONSES = "openai-codex-responses"
    ANTHROPIC_MESSAGES = "anthropic-messages"
    BEDROCK_CONVERSE_STREAM = "bedrock-converse-stream"
    GOOGLE_GENERATIVE_AI = "google-generative-ai"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    GOOGLE_VERTEX = "google-vertex"

class KnownProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AMAZON_BEDROCK = "amazon-bedrock"
    AZURE_OPENAI = "azure-openai-responses"
    # ... (22 total)

class ThinkingLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"

class StopReason(Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "toolUse"
    ERROR = "error"
    ABORTED = "aborted"
```

#### Content Types

```python
@dataclass
class TextContent:
    type: Literal["text"] = "text"
    text: str = ""
    text_signature: Optional[str] = None

@dataclass
class ThinkingContent:
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    thinking_signature: Optional[str] = None

@dataclass
class ImageContent:
    type: Literal["image"] = "image"
    data: str = ""  # base64
    mime_type: str = ""

@dataclass
class ToolCall:
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
```

#### Message Types

```python
@dataclass
class UserMessage:
    role: Literal["user"] = "user"
    content: Union[str, List[Union[TextContent, ImageContent]]] = ""
    timestamp: int = 0

@dataclass
class AssistantMessage:
    role: Literal["assistant"] = "assistant"
    content: List[Content] = field(default_factory=list)
    api: str = ""
    provider: str = ""
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_reason: StopReason = StopReason.STOP
    error_message: Optional[str] = None
    timestamp: int = 0

@dataclass
class ToolResultMessage:
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: List[Union[TextContent, ImageContent]] = field(default_factory=list)
    is_error: bool = False
    timestamp: int = 0
```

### Providers

#### BaseProvider

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def api_type(self) -> str: ...
    
    @property
    @abstractmethod
    def provider_id(self) -> str: ...
    
    @abstractmethod
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream: ...
    
    @abstractmethod
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float: ...
    
    async def complete(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessage: ...
```

#### Provider Registry

```python
# Get global registry
from koda.ai import get_provider_registry

registry = get_provider_registry()

# Register provider
registry.register("my-provider", MyProvider)

# Create instance
provider = registry.create("openai-v2", ProviderConfig(api_key="..."))
```

### Event Stream

```python
# Create stream
stream = AssistantMessageEventStream()

# Consume events
async for event in stream:
    if event.type == EventType.TEXT_DELTA:
        print(event.delta, end="")
    elif event.type == EventType.DONE:
        break

# Or collect full message
message = await stream.collect()
```

---

## koda.agent

### AgentLoop

```python
from koda.agent.loop import AgentLoop, AgentLoopConfig, AgentTool

# Configuration
config = AgentLoopConfig(
    max_iterations=50,
    max_tool_calls_per_turn=32,
    retry_attempts=3,
    retry_delay_base=1.0,
    tool_timeout=600.0,
    enable_parallel_tools=True,
    max_parallel_tools=8
)

# Create tools
tools = [
    AgentTool(
        name="read_file",
        description="Read a file",
        parameters={"type": "object", "properties": {...}},
        execute=read_file
    )
]

# Create agent
agent = AgentLoop(provider, model, tools, config)

# Run
response = await agent.run(context, on_event=handler, signal=abort_signal)
```

### Agent Events

```python
class AgentEventType(Enum):
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"

@dataclass
class AgentEvent:
    type: AgentEventType
    data: Dict[str, Any]
    timestamp: int
```

---

## koda.coding

### SessionManager

```python
from koda.coding.session_manager import SessionManager

# Create manager
session_mgr = SessionManager(Path.home() / ".koda" / "sessions")

# Create session
session = session_mgr.create_session("My Project")

# Add entry
session_mgr.add_entry(session, message_entry)

# Fork branch
branch_id = session_mgr.fork_branch(session, "entry_id", "feature-branch")

# Save
session_mgr.save_session(session)

# Load
loaded = session_mgr.load_session(session.id)

# Export
markdown = session_mgr.export_session(session, "markdown")
```

### AuthStorage

```python
from koda.coding.auth_storage import AuthStorage, ApiKeyCredential, OAuthCredential

# Create storage
auth = AuthStorage(Path.home() / ".koda")

# Store API key
auth.set("openai", ApiKeyCredential(
    type="apiKey",
    key="sk-...",
    provider="openai"
))

# Store OAuth
auth.set("google", OAuthCredential(
    type="oauth",
    provider="google",
    access_token="...",
    refresh_token="...",
    expires_at=1234567890
))

# Get API key
api_key = auth.get_api_key("openai")
```

---

## koda.mom

### ContextManager

```python
from koda.mom.context import ContextManager

# Create
context_mgr = ContextManager(max_tokens=128000)

# Add message
context_mgr.add(message)

# Get context
context = context_mgr.get_context(system_prompt="...", tools=[...])

# Clear
context_mgr.clear()
```

### Store

```python
from koda.mom.store import Store

# Create
store = Store(Path.home() / ".koda" / "store.json")

# Set
store.set("key", "value")
store.set("nested", {"data": True})

# Get
value = store.get("key")

# List
keys = store.list("prefix")
```

### Sandbox

```python
from koda.mom.sandbox import Sandbox

# Create temp sandbox
async with Sandbox() as sandbox:
    # Write file
    sandbox.write_file("test.txt", "Hello")
    
    # Execute
    result = await sandbox.execute(
        ["cat", "test.txt"],
        timeout=60.0
    )
    
    print(result["stdout"])  # "Hello"
    print(result["exit_code"])  # 0
```

---

## Utilities

### Model Helpers

```python
from koda.ai.models_utils import (
    supports_xhigh,
    models_are_equal,
    calculate_cost,
    resolve_model_alias
)

# Check xhigh support
if supports_xhigh(model):
    print("Model supports xhigh thinking")

# Compare models
if models_are_equal(model_a, model_b):
    print("Same model")

# Calculate cost
cost = calculate_cost(model, usage)
print(f"Cost: ${cost:.4f}")

# Resolve alias
model_id = resolve_model_alias("gpt4")  # "gpt-4o"
```

### Token Counting

```python
from koda.ai.tokenizer import Tokenizer

tokenizer = Tokenizer(model="gpt-4")

# Count text
count = tokenizer.count("Hello world")

# Count messages
count = tokenizer.count_messages(messages)

# Truncate
truncated = tokenizer.truncate_to_limit(messages, max_tokens=4000)
```

---

## Examples

### Complete Workflow

```python
import asyncio
from pathlib import Path

from koda.ai import get_provider_registry, ModelInfo, Context
from koda.agent.loop import AgentLoop, AgentLoopConfig, AgentTool
from koda.coding.session_manager import SessionManager
from koda.coding.auth_storage import AuthStorage, ApiKeyCredential

async def main():
    # 1. Setup auth
    auth = AuthStorage(Path.home() / ".koda")
    auth.set("openai", ApiKeyCredential(
        type="apiKey",
        key="sk-...",
        provider="openai"
    ))
    
    # 2. Create provider
    registry = get_provider_registry()
    from koda.ai.provider_base import ProviderConfig
    provider = registry.create("openai-v2", ProviderConfig(
        api_key="sk-..."
    ))
    
    # 3. Create model info
    model = ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url="https://api.openai.com/v1",
        cost={"input": 2.5, "output": 10.0, "cache_read": 0, "cache_write": 0},
        context_window=128000,
        max_tokens=16384
    )
    
    # 4. Create tools
    async def read_file(path: str) -> str:
        return Path(path).read_text()
    
    tools = [
        AgentTool(
            name="read",
            description="Read file contents",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            },
            execute=read_file
        )
    ]
    
    # 5. Create agent
    config = AgentLoopConfig(
        max_iterations=50,
        enable_parallel_tools=True
    )
    agent = AgentLoop(provider, model, tools, config)
    
    # 6. Create session
    session_mgr = SessionManager(Path.home() / ".koda" / "sessions")
    session = session_mgr.create_session("My Task")
    
    # 7. Run agent
    from koda.ai.types import UserMessage
    context = Context(
        system_prompt="You are a helpful assistant.",
        messages=[UserMessage(content="Read /tmp/test.txt")],
        tools=tools
    )
    
    def on_event(event):
        print(f"Event: {event.type}")
    
    response = await agent.run(context, on_event=on_event)
    print(f"Response: {response.content}")
    
    # 8. Save session
    session_mgr.save_session(session)

if __name__ == "__main__":
    asyncio.run(main())
```

---

*Last Updated: 2026-02-10*
