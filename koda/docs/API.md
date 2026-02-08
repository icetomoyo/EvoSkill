# Koda API 参考

## Core Components

### KodaAgent

主代理类，协调所有组件。

```python
class KodaAgent:
    def __init__(
        self,
        llm: BaseLLMAdapter,
        config: Optional[AgentConfig] = None,
        tools: Optional[List] = None,
        verbose: bool = False,
    )
    
    async def execute(self, task: Task) -> TaskResult
    async def execute_stream(self, task: Task) -> AsyncIterator[Dict[str, Any]]
    def add_tool(self, tool: Any) -> None
```

### Task

任务定义。

```python
@dataclass
class Task:
    description: str
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    language: str = "python"
    max_iterations: int = 3
    timeout_seconds: int = 120
    
    def to_prompt(self) -> str
```

### TaskResult

任务执行结果。

```python
@dataclass
class TaskResult:
    task: Task
    success: bool
    status: TaskStatus
    artifacts: List[CodeArtifact]
    plan: Optional[Plan]
    iterations: int
    execution_history: List[ExecutionResult]
    reflection_history: List[ReflectionResult]
    total_time_ms: int
    
    def get_main_code(self) -> Optional[str]
    def to_dict(self) -> Dict[str, Any]
```

## Tools

### ShellTool

```python
class ShellTool:
    def __init__(
        self,
        working_dir: Optional[Path] = None,
        timeout: int = 60,
        allowed_commands: Optional[List[str]] = None,
        blocked_commands: Optional[List[str]] = None,
    )
    
    async def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ShellResult
    
    async def execute_many(
        self,
        commands: List[str],
        stop_on_error: bool = True,
    ) -> List[ShellResult]
```

### FileTool

```python
class FileTool:
    def __init__(self, base_path: Path)
    
    async def read(self, path: str, encoding: str = 'utf-8') -> str
    async def write(self, path: str, content: str, encoding: str = 'utf-8') -> None
    async def append(self, path: str, content: str) -> None
    async def delete(self, path: str) -> None
    async def exists(self, path: str) -> bool
    async def list(self, path: str = ".", pattern: str = "*") -> List[FileInfo]
    async def mkdir(self, path: str, parents: bool = True) -> None
    async def copy(self, src: str, dst: str) -> None
    async def move(self, src: str, dst: str) -> None
    async def get_info(self, path: str) -> FileInfo
```

### SearchTool

```python
class SearchTool:
    def __init__(self, base_path: Path)
    
    async def search_text(
        self,
        query: str,
        pattern: str = "*",
        context_lines: int = 2,
    ) -> List[SearchResult]
    
    async def search_regex(
        self,
        pattern: str,
        file_pattern: str = "*",
        context_lines: int = 2,
    ) -> List[SearchResult]
    
    async def find_files(
        self,
        pattern: str,
        exclude_dirs: Optional[List[str]] = None,
    ) -> List[str]
    
    async def grep_code(
        self,
        symbol: str,
        language: str = "python",
    ) -> List[SearchResult]
```

### APITool

```python
class APITool:
    def __init__(self, timeout: int = 30)
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> APIResponse
    
    async def get(url, headers=None, params=None) -> APIResponse
    async def post(url, headers=None, data=None, json_data=None) -> APIResponse
    async def put(url, headers=None, data=None, json_data=None) -> APIResponse
    async def delete(url, headers=None) -> APIResponse
    async def download(url: str, dest_path: str) -> bool
```

### GitTool

```python
class GitTool:
    def __init__(self, repo_path: Path)
    
    async def status(self) -> GitResult
    async def add(self, files: str = ".") -> GitResult
    async def commit(self, message: str) -> GitResult
    async def push(self, remote: str = "origin", branch: str = "") -> GitResult
    async def pull(self, remote: str = "origin", branch: str = "") -> GitResult
    async def branch(self, branch_name: Optional[str] = None) -> GitResult
    async def checkout(self, branch_or_commit: str) -> GitResult
    async def log(self, n: int = 10) -> GitResult
    async def diff(self, staged: bool = False) -> GitResult
    async def clone(self, url: str, dest: Optional[str] = None) -> GitResult
    async def init(self) -> GitResult
```

## Configuration

### KodaConfig

```python
@dataclass
class KodaConfig:
    version: str = "0.1.0"
    workspace: str = "./workspace"
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "KodaConfig"
    def save(self, path: Path) -> None
    @classmethod
    def from_env(cls) -> "KodaConfig"
    def to_dict(self) -> Dict[str, Any]
```

### LLMConfig

```python
@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str = ""
    api_base: str = ""
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60
```

## Types

### CodeArtifact

```python
@dataclass
class CodeArtifact:
    filename: str
    content: str
    language: str = "python"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    artifacts: List[CodeArtifact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### ReflectionResult

```python
@dataclass
class ReflectionResult:
    has_issues: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    improved_code: Optional[str] = None
    
    @property
    def needs_fix(self) -> bool
```

### ValidationReport

```python
@dataclass
class ValidationReport:
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0
```

## Adapters

### BaseLLMAdapter

```python
class BaseLLMAdapter(ABC):
    def __init__(self, **config)
    
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str
    
    def get_name(self) -> str
```

## Context

### ContextManager

```python
class ContextManager:
    def __init__(self, workspace_path: Path)
    
    async def create_session(self, session_id: Optional[str] = None) -> SessionContext
    async def load_session(self, session_id: str) -> Optional[SessionContext]
    async def save_session(self) -> None
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None
    
    async def get_conversation_history(self, limit: int = 50) -> List[Message]
    
    async def load_project(self, project_path: Path) -> ProjectContext
    
    async def add_artifact(
        self,
        artifact_type: str,
        name: str,
        content: str,
    ) -> None
    
    async def get_project_summary(self) -> str
    async def clear_history(self) -> None
```

## CLI

```bash
koda init [--workspace PATH]
koda generate <task> [--output PATH]
koda validate [--file PATH]
koda config [--show] [--init]
```

## Constants

### TaskStatus

```python
class TaskStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"
```

### StepStatus

```python
class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
```
