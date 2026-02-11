# Koda 实现规格文档

## 1. 模型数据库实现规格

### 1.1 文件结构
```
koda/ai/models/
├── __init__.py
├── generated.py          # 模型定义数据
├── registry.py           # 注册表实现
└── costs.py              # 成本计算
```

### 1.2 generated.py 内容结构

包含以下Provider的模型:
- amazon-bedrock (15+ 模型)
- anthropic (8+ 模型)
- azure-openai (5+ 模型)
- google (10+ 模型)
- openai (15+ 模型)
- 其他Provider

每个模型包含:
- id, name, provider, api
- base_url, reasoning, input
- cost (input, output, cache_read, cache_write)
- context_window, max_tokens

### 1.3 实现要点

- 使用字典存储模型数据
- 提供get_model()快速查询
- 支持按条件过滤

---

## 2. AI CLI实现规格

### 2.1 文件位置
`koda/ai/cli.py`

### 2.2 命令规格

```python
# login命令
async def login_command(provider: Optional[str] = None):
    """OAuth登录流程"""
    # 1. 如果没有指定provider，交互式选择
    # 2. 获取OAuth provider实例
    # 3. 启动OAuth流程
    # 4. 保存凭证到~/.koda/auth.json

# list命令  
async def list_command():
    """列出可用providers"""
    # 显示所有OAuth providers及其状态

# models命令
async def models_command(provider: Optional[str] = None):
    """列出可用模型"""
    # 从模型数据库查询并显示
```

### 2.3 凭证存储格式

```json
{
  "anthropic": {
    "type": "oauth",
    "access_token": "sk-ant-...",
    "refresh_token": null,
    "expires_at": null
  }
}
```

---

## 3. OAuth类型规格

### 3.1 文件位置
`koda/ai/providers/oauth/types.py`

### 3.2 类型定义

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

class OAuthProviderId(str, Enum):
    ANTHROPIC = "anthropic"
    GITHUB_COPILOT = "github-copilot"
    GOOGLE_ANTIGRAVITY = "google-antigravity"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    OPENAI_CODEX = "openai-codex"

@dataclass
class OAuthCredentials:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None  # Unix timestamp

@dataclass
class AuthPrompt:
    message: str
    placeholder: Optional[str] = None

@dataclass
class AuthInfo:
    url: str
    instructions: Optional[str] = None

# 回调类型
AuthCallback = Callable[[AuthInfo], None]
PromptCallback = Callable[[AuthPrompt], Awaitable[str]]
ProgressCallback = Callable[[str], None]

@dataclass
class OAuthProviderConfig:
    client_id: str
    auth_url: str
    token_url: str
    scopes: list[str]
    prompt_handler: Optional[PromptCallback] = None
```

---

## 4. 会话压缩规格

### 4.1 文件结构
```
koda/coding/core/compaction/
├── __init__.py
├── base.py               # 基础接口
├── branch.py             # 分支摘要
├── session.py            # 会话压缩
└── utils.py              # 工具函数
```

### 4.2 核心算法

1. **Token计算**: 使用tiktoken或估计
2. **消息重要性评分**: 
   - 用户消息: 高
   - 助手消息(含工具): 高
   - 系统消息: 最高
   - 普通助手消息: 中
3. **压缩策略**:
   - 保留最近N条
   - 摘要早期消息
   - 删除冗余消息

### 4.3 接口定义

```python
@dataclass
class CompactionStrategy:
    max_tokens: int
    preserve_recent: int = 10
    enable_summarization: bool = True

class SessionCompactor:
    def __init__(self, strategy: CompactionStrategy):
        self.strategy = strategy
    
    async def compact(self, messages: List[Message]) -> CompactionResult:
        # 实现压缩逻辑
        pass
    
    async def summarize(self, messages: List[Message]) -> str:
        # 生成摘要
        pass
```

---

## 5. CLI选择器规格

### 5.1 依赖
```
pip install questionary
```

### 5.2 实现要点

- 使用questionary实现交互式选择
- 支持搜索过滤
- 支持键盘导航
- 美观的格式化输出

### 5.3 选择器类型

```python
class ConfigSelector:
    async def select_config(self, configs: List[Config]) -> Optional[Config]
    async def select_model(self, models: List[ModelInfo]) -> Optional[ModelInfo]

class SessionPicker:
    async def pick_session(self, sessions: List[Session]) -> Optional[Session]
    async def multi_select(self, sessions: List[Session]) -> List[Session]

class FileProcessor:
    async def process_files(self, paths: List[str]) -> ProcessedFiles
```

---

## 6. 事件总线规格

### 6.1 文件位置
`koda/coding/core/event_bus.py`

### 6.2 实现

```python
from typing import Callable, Any
from dataclasses import dataclass
import asyncio

@dataclass
class Event:
    type: str
    data: Any
    source: Optional[str] = None

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
    
    def on(self, event_type: str, handler: Callable):
        """订阅事件"""
        pass
    
    def emit(self, event: Event):
        """发布事件"""
        pass
    
    def off(self, event_type: str, handler: Callable):
        """取消订阅"""
        pass
```

---

## 7. 实现优先级

| 优先级 | 功能 | 依赖 | 预计时间 |
|--------|------|------|----------|
| P0 | 模型数据库 | 无 | 2h |
| P0 | OAuth类型 | 无 | 30min |
| P0 | AI CLI | OAuth类型 | 1h |
| P1 | Anthropic OAuth | OAuth类型 | 1h |
| P1 | GitHub Copilot OAuth | OAuth类型 | 1h |
| P1 | 会话压缩 | 模型数据库 | 2h |
| P2 | CLI选择器 | 无 | 2h |
| P2 | 事件总线 | 无 | 1h |
| P2 | 诊断工具 | 事件总线 | 1h |

---

*规格版本: 1.0*
*日期: 2026-02-11*
