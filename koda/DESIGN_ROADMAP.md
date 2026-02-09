# Koda Core Packages - 设计路线图

> 目标: 完全对标 Pi Mono 的 ai/agent/coding-agent/mom 四个核心包
> 策略: 先实现核心功能，TUI 延后
> 版本: v0.2.0 -> v0.5.0

---

## 第一阶段: AI 包完善 (v0.2.0)

### 1.1 类型系统完善

```python
# koda/ai/types.py - 新增完整类型

from typing import Literal, TypedDict, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

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
    AMAZON_BEDROCK = "amazon-bedrock"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    GOOGLE_VERTEX = "google-vertex"
    OPENAI = "openai"
    AZURE_OPENAI = "azure-openai-responses"
    OPENAI_CODEX = "openai-codex"
    GITHUB_COPILOT = "github-copilot"
    XAI = "xai"
    GROQ = "groq"
    CEREBRAS = "cerebras"
    OPENROUTER = "openrouter"
    MISTRAL = "mistral"
    KIMI_CODING = "kimi-coding"

class ThinkingLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"

class CacheRetention(Enum):
    NONE = "none"
    SHORT = "short"
    LONG = "long"

class StopReason(Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "toolUse"
    ERROR = "error"
    ABORTED = "aborted"

@dataclass
class Usage:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost_input: float = 0.0
    cost_output: float = 0.0
    cost_cache_read: float = 0.0
    cost_cache_write: float = 0.0
    cost_total: float = 0.0

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
    mime_type: str = ""  # image/jpeg, image/png

@dataclass
class ToolCall:
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: dict = None
    thought_signature: Optional[str] = None

Content = Union[TextContent, ThinkingContent, ImageContent, ToolCall]

@dataclass
class UserMessage:
    role: Literal["user"] = "user"
    content: Union[str, List[Union[TextContent, ImageContent]]] = None
    timestamp: int = 0

@dataclass
class AssistantMessage:
    role: Literal["assistant"] = "assistant"
    content: List[Content] = None
    api: str = ""
    provider: str = ""
    model: str = ""
    usage: Usage = None
    stop_reason: StopReason = StopReason.STOP
    error_message: Optional[str] = None
    timestamp: int = 0

@dataclass
class ToolResultMessage:
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: List[Union[TextContent, ImageContent]] = None
    details: Optional[dict] = None
    is_error: bool = False
    timestamp: int = 0

Message = Union[UserMessage, AssistantMessage, ToolResultMessage]

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema

@dataclass
class Context:
    system_prompt: Optional[str] = None
    messages: List[Message] = None
    tools: Optional[List[Tool]] = None
```

### 1.2 事件流系统

```python
# koda/ai/event_stream.py

from typing import Callable, AsyncIterator, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

class EventType(Enum):
    START = "start"
    TEXT_START = "text_start"
    TEXT_DELTA = "text_delta"
    TEXT_END = "text_end"
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_END = "thinking_end"
    TOOLCALL_START = "toolcall_start"
    TOOLCALL_DELTA = "toolcall_delta"
    TOOLCALL_END = "toolcall_end"
    DONE = "done"
    ERROR = "error"

@dataclass
class AssistantMessageEvent:
    type: EventType
    partial: Optional[AssistantMessage] = None
    content_index: Optional[int] = None
    delta: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    reason: Optional[StopReason] = None
    error: Optional[Exception] = None

class AssistantMessageEventStream:
    """
    等效于 Pi Mono 的 AssistantMessageEventStream
    支持异步迭代和回调
    """
    
    def __init__(self):
        self._queue: asyncio.Queue[AssistantMessageEvent] = asyncio.Queue()
        self._closed = False
        self._callbacks: List[Callable[[AssistantMessageEvent], None]] = []
    
    def push(self, event: AssistantMessageEvent) -> None:
        """推送事件到流"""
        if self._closed:
            return
        self._queue.put_nowait(event)
        for callback in self._callbacks:
            callback(event)
    
    async def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        """异步迭代事件"""
        while True:
            event = await self._queue.get()
            yield event
            if event.type in (EventType.DONE, EventType.ERROR):
                break
    
    def on_event(self, callback: Callable[[AssistantMessageEvent], None]) -> None:
        """注册事件回调"""
        self._callbacks.append(callback)
    
    def close(self) -> None:
        """关闭流"""
        self._closed = True
```

### 1.3 Provider 接口标准化

```python
# koda/ai/provider_base.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class StreamOptions:
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    signal: Optional[Any] = None  # AbortSignal
    api_key: Optional[str] = None
    cache_retention: str = "short"  # none/short/long
    session_id: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    max_retry_delay_ms: int = 60000

@dataclass
class SimpleStreamOptions(StreamOptions):
    reasoning: Optional[str] = None  # thinking level
    thinking_budgets: Optional[Dict[str, int]] = None

class BaseProvider(ABC):
    """
    标准化 Provider 接口
    所有 Provider 必须实现
    """
    
    @property
    @abstractmethod
    def api_type(self) -> str:
        """返回 API 类型，如 'openai-completions', 'anthropic-messages'"""
        pass
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """返回 Provider ID，如 'openai', 'anthropic'"""
        pass
    
    @abstractmethod
    async def stream(
        self,
        model: ModelInfo,
        context: Context,
        options: Optional[StreamOptions] = None
    ) -> AssistantMessageEventStream:
        """
        流式生成响应
        必须返回 AssistantMessageEventStream
        """
        pass
    
    @abstractmethod
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> float:
        """计算请求成本"""
        pass
    
    @abstractmethod
    def supports_thinking_level(self, level: ThinkingLevel) -> bool:
        """检查是否支持特定思考级别"""
        pass
```

### 1.4 新增 Provider 实现

需要实现:
- [ ] **GoogleProvider** - Google Generative AI + Gemini CLI + Vertex
- [ ] **AzureOpenAIProvider** - Azure OpenAI Responses
- [ ] **BedrockProvider** - Amazon Bedrock Converse Stream
- [ ] **GitHubCopilotProvider** - Copilot OAuth + API

---

## 第二阶段: Agent 包完善 (v0.3.0)

### 2.1 Agent Loop 增强

```python
# koda/agent/loop.py

@dataclass
class AgentLoopConfig:
    max_iterations: int = 50
    max_tool_calls_per_turn: int = 32
    retry_attempts: int = 3
    retry_delay_base: float = 1.0  # 指数退避基数
    tool_timeout: float = 600.0  # 10分钟
    enable_parallel_tools: bool = True

class AgentLoop:
    """
    等效于 Pi Mono 的 Agent Loop
    支持错误重试、并发控制、最大迭代限制
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        model: ModelInfo,
        tools: List[AgentTool],
        config: Optional[AgentLoopConfig] = None
    ):
        self.provider = provider
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.config = config or AgentLoopConfig()
        self.iteration_count = 0
        self.tool_call_count = 0
    
    async def run(
        self,
        context: Context,
        on_event: Optional[Callable[[AgentEvent], None]] = None
    ) -> AssistantMessage:
        """
        运行 Agent Loop 直到完成
        
        特性:
        - 最大迭代限制保护
        - 工具错误重试
        - 并发工具执行
        - 优雅错误处理
        """
        pass
    
    async def _execute_tool_with_retry(
        self,
        tool_call: ToolCall,
        signal: Optional[Any] = None
    ) -> ToolResultMessage:
        """带重试的工具执行"""
        pass
    
    async def _execute_tools_parallel(
        self,
        tool_calls: List[ToolCall],
        signal: Optional[Any] = None
    ) -> List[ToolResultMessage]:
        """并行执行工具"""
        pass
```

### 2.2 Agent Proxy

```python
# koda/agent/proxy.py

class AgentProxy:
    """
    Agent 代理模式
    支持多 Agent 协调和负载均衡
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentLoop] = {}
        self.routing_strategy: str = "round_robin"
    
    def register_agent(self, name: str, agent: AgentLoop) -> None:
        """注册子 Agent"""
        pass
    
    async def delegate(
        self,
        task: str,
        to_agent: Optional[str] = None
    ) -> AssistantMessage:
        """委派任务给特定 Agent 或自动选择"""
        pass
```

---

## 第三阶段: Coding-Agent 包完善 (v0.4.0)

### 3.1 Auth Storage 系统

```python
# koda/coding/auth_storage.py

from dataclasses import dataclass
from typing import Literal, Optional
from pathlib import Path
import keyring

@dataclass
class ApiKeyCredential:
    type: Literal["apiKey"] = "apiKey"
    key: str = ""
    provider: str = ""

@dataclass
class OAuthCredential:
    type: Literal["oauth"] = "oauth"
    provider: str = ""
    access_token: str = ""
    refresh_token: str = ""
    expires_at: int = 0  # timestamp
    scopes: List[str] = None

Credential = Union[ApiKeyCredential, OAuthCredential]

class AuthStorage:
    """
    安全凭据存储
    - API Key: 系统 keyring
    - OAuth: 加密文件存储 + keyring
    - 自动 Token 刷新
    """
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self._fallback_resolver: Optional[Callable[[str], Optional[str]]] = None
    
    def get(self, provider: str) -> Optional[Credential]:
        """获取凭据"""
        pass
    
    def set(self, provider: str, credential: Credential) -> None:
        """存储凭据"""
        pass
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """获取 API Key (自动处理 OAuth 降级)"""
        pass
    
    async def refresh_oauth(self, provider: str) -> bool:
        """刷新 OAuth Token"""
        pass
    
    def set_fallback_resolver(self, resolver: Callable[[str], Optional[str]]) -> None:
        """设置备用解析器 (用于 models.json 配置)"""
        pass
```

### 3.2 OAuth 实现

```python
# koda/coding/oauth/

# google_oauth.py
class GoogleOAuth:
    """Google OAuth PKCE 流程"""
    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    
    async def start_flow(self, scopes: List[str]) -> str:
        """启动 OAuth 流程，返回授权 URL"""
        pass
    
    async def handle_callback(self, code: str, verifier: str) -> OAuthCredential:
        """处理回调，获取 token"""
        pass

# anthropic_oauth.py
class AnthropicOAuth:
    """Anthropic OAuth"""
    pass

# github_copilot_oauth.py
class GitHubCopilotOAuth:
    """GitHub Copilot OAuth"""
    pass
```

### 3.3 Model Registry 增强

```python
# koda/coding/model_registry.py

class CodingModelRegistry(ModelRegistry):
    """
    增强版 Model Registry
    支持自定义 models.json 配置
    """
    
    def __init__(
        self,
        auth_storage: AuthStorage,
        models_json_path: Optional[Path] = None
    ):
        super().__init__()
        self.auth_storage = auth_storage
        self.models_json_path = models_json_path
        self._load_error: Optional[str] = None
        self._custom_provider_keys: Dict[str, str] = {}
        self._registered_providers: Dict[str, ProviderConfig] = {}
    
    def load_custom_models(self, path: Path) -> CustomModelsResult:
        """
        从 models.json 加载自定义模型
        
        支持:
        - 自定义 Provider 定义
        - 模型覆盖
        - 环境变量替换
        - 命令替换 $(cmd)
        """
        pass
    
    def register_provider(
        self,
        provider_name: str,
        config: ProviderConfigInput
    ) -> None:
        """
        动态注册 Provider (用于 Extensions)
        
        config 包含:
        - baseUrl: API 端点
        - apiKey: API 密钥
        - api: API 类型
        - streamSimple: 自定义流函数
        - headers: 自定义头部
        - oauth: OAuth 配置
        - models: 模型定义列表
        """
        pass
    
    def get_available(self) -> List[ModelInfo]:
        """获取有认证配置的可用模型"""
        pass
    
    def is_using_oauth(self, model: ModelInfo) -> bool:
        """检查模型是否使用 OAuth"""
        pass
```

### 3.4 Compaction 系统增强

```python
# koda/coding/compaction/enhanced.py

@dataclass
class CompactionSettings:
    """Compaction 配置"""
    max_tokens: int = 128000
    reserve_tokens: int = 4000
    trigger_ratio: float = 0.8
    enable_branch_summary: bool = True
    enable_file_deduplication: bool = True
    preserve_recent_turns: int = 2

class EnhancedCompactor(MessageCompactor):
    """
    增强版 Compaction 系统
    等效于 Pi Mono 的完整 compaction
    """
    
    def __init__(self, settings: Optional[CompactionSettings] = None):
        super().__init__()
        self.settings = settings or CompactionSettings()
    
    def should_compact(self, entries: List[SessionEntry]) -> bool:
        """
        判断是否需要压缩
        基于 token 数量和触发比例
        """
        pass
    
    def find_cut_point(self, entries: List[SessionEntry]) -> int:
        """
        查找最佳切割点
        优先在 turn 边界切割
        """
        pass
    
    def collect_entries_for_branch_summary(
        self,
        entries: List[SessionEntry],
        cut_point: int
    ) -> CollectEntriesResult:
        """
        收集需要摘要的分支条目
        处理文件操作去重
        """
        pass
    
    async def generate_branch_summary(
        self,
        entries: List[SessionEntry],
        provider: BaseProvider,
        model: ModelInfo
    ) -> BranchSummaryResult:
        """
        使用 LLM 生成分支摘要
        """
        pass
    
    def serialize_conversation(
        self,
        entries: List[SessionEntry],
        include_summaries: bool = True
    ) -> List[Message]:
        """
        序列化会话为消息列表
        包含摘要信息
        """
        pass
```

### 3.5 Session Manager 完整实现

```python
# koda/coding/session_manager.py

from enum import Enum, auto
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

class EntryType(Enum):
    MESSAGE = auto()
    COMPACTION = auto()
    MODEL_CHANGE = auto()
    THINKING_LEVEL_CHANGE = auto()
    CUSTOM = auto()
    FILE = auto()

@dataclass
class SessionEntryBase:
    id: str
    type: EntryType
    timestamp: int
    branch_id: str = "main"
    parent_id: Optional[str] = None

@dataclass
class SessionMessageEntry(SessionEntryBase):
    role: str
    content: Any
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None
    usage: Optional[Usage] = None

@dataclass
class CompactionEntry(SessionEntryBase):
    summary: str
    original_count: int
    compacted_count: int
    tokens_saved: int

@dataclass
class BranchSummaryEntry:
    branch_id: str
    summary: str
    entry_count: int
    file_operations: List[str] = field(default_factory=list)

@dataclass
class SessionContext:
    id: str
    name: str
    created_at: int
    modified_at: int
    current_branch: str = "main"
    entries: List[SessionEntry] = field(default_factory=list)
    branch_summaries: Dict[str, BranchSummaryEntry] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SessionManager:
    """
    完整 Session Manager
    等效于 Pi Mono 的 SessionManager
    
    特性:
    - 树形分支导航
    - 会话持久化
    - 导入/导出
    - 标签系统
    - 垃圾回收
    """
    
    CURRENT_VERSION = 1
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.sessions: Dict[str, SessionContext] = {}
        self.current_session: Optional[SessionContext] = None
    
    def create_session(self, name: Optional[str] = None) -> SessionContext:
        """创建新会话"""
        pass
    
    def load_session(self, session_id: str) -> Optional[SessionContext]:
        """加载会话"""
        pass
    
    def save_session(self, session: SessionContext) -> None:
        """保存会话到磁盘"""
        pass
    
    def fork_branch(
        self,
        session: SessionContext,
        from_entry_id: str,
        new_branch_name: str
    ) -> str:
        """
        从指定条目创建新分支
        等效于 Pi Mono 的分支功能
        """
        pass
    
    def switch_branch(self, session: SessionContext, branch_id: str) -> bool:
        """切换到指定分支"""
        pass
    
    def get_branch_history(
        self,
        session: SessionContext,
        branch_id: str
    ) -> List[SessionEntry]:
        """获取分支的完整历史"""
        pass
    
    def build_context(
        self,
        session: SessionContext,
        max_tokens: int = 128000
    ) -> Context:
        """
        构建 LLM 上下文
        包含分支摘要处理
        """
        pass
    
    def migrate_entries(
        self,
        entries: List[dict],
        from_version: int
    ) -> List[SessionEntry]:
        """迁移旧版本会话条目"""
        pass
    
    def export_session(
        self,
        session: SessionContext,
        format: str = "json"
    ) -> str:
        """
        导出会话
        支持: json, markdown, html
        """
        pass
    
    def import_session(self, data: str, format: str = "json") -> SessionContext:
        """导入会话"""
        pass
    
    def list_sessions(
        self,
        tag: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionInfo]:
        """列会话，支持标签过滤"""
        pass
    
    def delete_session(self, session_id: str, permanent: bool = False) -> None:
        """删除会话（或移至回收站）"""
        pass
    
    def gc_old_sessions(self, max_age_days: int = 30) -> int:
        """清理旧会话，返回清理数量"""
        pass
```

### 3.6 Settings Manager 完整实现

```python
# koda/coding/settings_manager.py

@dataclass
class CompactionSettings:
    max_tokens: int = 128000
    reserve_tokens: int = 4000
    trigger_ratio: float = 0.8
    strategy: str = "smart"

@dataclass
class ImageSettings:
    max_width: int = 2048
    max_height: int = 2048
    quality: int = 85
    format: str = "jpeg"

@dataclass
class RetrySettings:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0

@dataclass
class PackageSource:
    name: str
    url: str
    auth_token: Optional[str] = None

@dataclass
class Settings:
    """完整 Settings 结构"""
    # 版本
    version: int = 1
    
    # Compaction 设置
    compaction: CompactionSettings = field(default_factory=CompactionSettings)
    
    # 图片处理
    images: ImageSettings = field(default_factory=ImageSettings)
    
    # 重试设置
    retry: RetrySettings = field(default_factory=RetrySettings)
    
    # 包源 (用于 extensions)
    package_sources: List[PackageSource] = field(default_factory=list)
    
    # Provider 配置
    provider_overrides: Dict[str, dict] = field(default_factory=dict)
    
    # 主题
    theme: str = "dark"
    
    # 行为
    require_confirmation: bool = True
    auto_compact: bool = True
    thinking_level: str = "medium"

class SettingsManager:
    """
    完整 Settings Manager
    
    特性:
    - 层级配置 (全局 + 项目级)
    - 实时重载 (文件监视)
    - Schema 验证
    - 迁移支持
    """
    
    def __init__(
        self,
        global_path: Path,
        project_path: Optional[Path] = None
    ):
        self.global_path = global_path
        self.project_path = project_path
        self._global_settings: Optional[Settings] = None
        self._project_settings: Optional[Settings] = None
        self._watchers: List[Any] = []
        self._on_change_callbacks: List[Callable[[], None]] = []
    
    def load(self) -> Settings:
        """加载设置（合并全局和项目）"""
        pass
    
    def save(self, settings: Settings, scope: str = "global") -> None:
        """保存设置"""
        pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取设置值（支持点号路径）"""
        pass
    
    def set(self, key: str, value: Any, scope: str = "global") -> None:
        """设置值"""
        pass
    
    def watch(self, callback: Callable[[], None]) -> None:
        """监视设置变化"""
        pass
    
    def migrate(self, from_version: int) -> Settings:
        """迁移旧版本设置"""
        pass
```

### 3.7 工具增强

#### Edit Tool 增强 (模糊匹配)

```python
# koda/coding/tools/edit_enhanced.py

def normalize_for_fuzzy_match(text: str) -> str:
    """
    规范化文本用于模糊匹配
    - 智能引号 -> ASCII 引号
    - 破折号变体 -> ASCII 破折号
    - 不间断空格 -> 普通空格
    """
    # 智能引号
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    # 破折号
    text = text.replace('—', '-').replace('–', '-')
    # 空格
    text = text.replace('\xa0', ' ')
    return text

def fuzzy_find_text(
    content: str,
    old_text: str,
    context_lines: int = 2
) -> FuzzyMatchResult:
    """
    模糊查找文本
    
    策略:
    1. 精确匹配
    2. 忽略空白差异
    3. 规范化后的匹配
    4. 行级模糊匹配
    """
    pass

@dataclass
class EditResult:
    success: bool
    diff: str
    first_changed_line: Optional[int] = None
    error: Optional[str] = None

class EnhancedEditTool:
    """
    增强版 Edit Tool
    等效于 Pi Mono 的 edit.ts + edit-diff.ts
    
    特性:
    - 模糊匹配 (智能引号、破折号、空格)
    - BOM 处理
    - 行尾保持 (CRLF/LF)
    - 统一 diff 生成
    - AbortSignal 支持
    """
    
    async def execute(
        self,
        path: str,
        old_text: str,
        new_text: str,
        signal: Optional[Any] = None
    ) -> EditResult:
        pass
```

#### Bash Tool 增强

```python
# koda/coding/tools/bash_enhanced.py

@dataclass
class BashSpawnContext:
    """Bash 执行上下文"""
    cwd: str
    env: Dict[str, str]
    timeout: float
    max_output_bytes: int

@dataclass  
class BashSpawnHook:
    """可插拔的 spawn 钩子"""
    before_spawn: Optional[Callable[[BashSpawnContext], None]] = None
    after_spawn: Optional[Callable[[BashSpawnContext, Any], None]] = None

@dataclass
class BashResult:
    stdout: str
    stderr: str
    exit_code: int
    combined_output: str  # stdout + stderr 交错
    execution_time_ms: int

class EnhancedBashTool:
    """
    增强版 Bash Tool
    
    特性:
    - 超时控制
    - 输出限制
    - 环境变量注入
    - Spawn 钩子 (用于 SSH 等)
    - 组合输出
    """
    
    def __init__(
        self,
        cwd: str,
        spawn_hook: Optional[BashSpawnHook] = None
    ):
        self.cwd = cwd
        self.spawn_hook = spawn_hook
    
    async def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        max_output_bytes: int = 10240,
        signal: Optional[Any] = None
    ) -> BashResult:
        pass
```

---

## 第四阶段: MOM 包完善 (v0.5.0)

### 4.1 Context 管理

```python
# koda/mom/context.py

class ContextManager:
    """
    动态上下文管理
    等效于 Pi Mono 的 context.ts
    """
    
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self._context: List[Message] = []
        self._metadata: Dict[str, Any] = {}
    
    def add(self, message: Message) -> None:
        """添加消息，自动管理上下文窗口"""
        pass
    
    def get_context(self) -> Context:
        """获取当前上下文"""
        pass
    
    def clear(self) -> None:
        """清空上下文"""
        pass
```

### 4.2 Store 系统

```python
# koda/mom/store.py

class Store:
    """
    持久化存储
    等效于 Pi Mono 的 store.ts
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def get(self, key: str) -> Optional[Any]:
        pass
    
    def set(self, key: str, value: Any) -> None:
        pass
    
    def delete(self, key: str) -> None:
        pass
    
    def list(self, prefix: str = "") -> List[str]:
        pass
```

### 4.3 Sandbox

```python
# koda/mom/sandbox.py

class Sandbox:
    """
    沙箱环境
    等效于 Pi Mono 的 sandbox.ts
    
    特性:
    - 文件系统隔离
    - 网络限制
    - 资源限制
    """
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
    
    async def execute(
        self,
        command: List[str],
        timeout: float = 60.0
    ) -> dict:
        pass
```

---

## 实现优先级

### Sprint 1: 基础类型和事件流 (1 周)
- [ ] 完善 types.py (所有类型定义)
- [ ] 实现 event_stream.py
- [ ] 重构 Provider 基类

### Sprint 2: 核心 Provider 实现 (1 周)
- [ ] Google Provider (Gemini)
- [ ] Azure OpenAI Provider
- [ ] Bedrock Provider

### Sprint 3: Agent 和 Auth (1 周)
- [ ] Agent Loop 增强
- [ ] Auth Storage
- [ ] OAuth 实现 (Google/Anthropic)

### Sprint 4: Session 和 Compaction (1 周)
- [ ] Session Manager 完整实现
- [ ] 增强 Compaction
- [ ] Settings Manager

### Sprint 5: 工具增强 (1 周)
- [ ] Edit Tool (模糊匹配)
- [ ] Bash Tool (超时/钩子)
- [ ] 工具测试

### Sprint 6: MOM 和集成 (1 周)
- [ ] Context Manager
- [ ] Store
- [ ] Sandbox 基础
- [ ] 端到端测试

---

## 验收标准

每个 Sprint 完成后，对比 Pi Mono 对应功能：
1. **API 兼容**: 方法签名等效
2. **功能对等**: 核心功能完整
3. **测试覆盖**: 单元测试 > 80%
4. **文档完整**: 每个模块有 README
