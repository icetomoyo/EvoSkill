# Koda 设计路线图 - 100% Pi-Mono 复刻计划

## 文档信息
- **版本**: 1.0
- **日期**: 2026-02-11
- **目标**: 实现与 Pi-Mono 100% 功能对等

---

## 1. 架构概览

### 1.1 模块结构

```
koda/
├── ai/                          # AI Provider 模块
│   ├── __init__.py             # 统一导出
│   ├── cli.py                  # 【新增】AI包CLI入口
│   ├── models/                 # 【新增】模型数据库
│   │   ├── __init__.py
│   │   ├── generated.py        # 自动生成的模型定义
│   │   ├── registry.py         # 模型注册表
│   │   └── costs.py            # 成本计算
│   ├── providers/              # Provider实现
│   │   ├── oauth/              # OAuth模块
│   │   │   ├── types.py        # 【新增】OAuth类型定义
│   │   │   ├── anthropic.py    # 【新增】Anthropic OAuth
│   │   │   └── github_copilot.py # 【新增】GitHub Copilot OAuth
│   └── ...
├── agent/                       # Agent模块
├── coding/                      # Coding Agent模块
│   ├── cli/                     # CLI组件
│   │   ├── config_selector.py  # 【新增】配置选择器
│   │   ├── file_processor.py   # 【新增】文件处理器
│   │   ├── list_models.py      # 【新增】模型列表
│   │   └── session_picker.py   # 【新增】会话选择器
│   ├── core/                    # 核心功能
│   │   ├── compaction/         # 【新增/完善】压缩模块
│   │   │   ├── __init__.py
│   │   │   ├── branch.py       # 分支摘要
│   │   │   ├── session.py      # 会话压缩
│   │   │   └── utils.py        # 工具函数
│   │   ├── diagnostics.py      # 【新增】诊断工具
│   │   ├── event_bus.py        # 【新增】事件总线
│   │   └── model_registry.py   # 【新增】模型注册表
│   └── ...
├── mes/                         # 消息处理模块 (与compaction整合)
└── mom/                         # Mom模块
```

### 1.2 设计原则

1. **Pythonic**: 利用Python语言特性，保持代码简洁
2. **类型安全**: 使用Python 3.10+类型注解
3. **异步优先**: 所有IO操作使用async/await
4. **模块化**: 保持清晰的模块边界
5. **向后兼容**: 不破坏现有API

---

## 2. 详细设计

### 2.1 模型数据库 (ai/models/)

#### 2.1.1 数据模型

```python
@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    provider: str
    api: str
    base_url: str
    reasoning: bool
    input: List[str]  # ["text", "image"]
    cost: ModelCost
    context_window: int
    max_tokens: int
    supports_thinking: bool = False
    supports_vision: bool = False
    supports_tools: bool = True

@dataclass
class ModelCost:
    """模型成本 (每百万tokens)"""
    input: float
    output: float
    cache_read: float = 0.0
    cache_write: float = 0.0
```

#### 2.1.2 注册表接口

```python
class ModelRegistry:
    """模型注册表"""
    
    def get_model(self, provider: str, model_id: str) -> Optional[ModelInfo]
    def get_models(self, provider: str) -> List[ModelInfo]
    def get_providers(self) -> List[str]
    def filter_models(self, **criteria) -> List[ModelInfo]
    def calculate_cost(self, model: ModelInfo, usage: Usage) -> CostBreakdown
```

### 2.2 AI包CLI (ai/cli.py)

#### 2.2.1 命令结构

```
koda-ai <command> [options]

Commands:
  login [provider]    登录到OAuth provider
  list               列出可用providers
  models             列出可用模型
  config             配置管理
```

#### 2.2.2 实现要点

- 使用 `argparse` 构建CLI
- 支持交互式provider选择
- 凭证存储到JSON文件
- 统一OAuth流程

### 2.3 OAuth模块完善

#### 2.3.1 类型定义 (oauth/types.py)

```python
class OAuthProviderId(Enum):
    ANTHROPIC = "anthropic"
    GITHUB_COPILOT = "github-copilot"
    GOOGLE_ANTIGRAVITY = "google-antigravity"
    GOOGLE_GEMINI_CLI = "google-gemini-cli"
    OPENAI_CODEX = "openai-codex"

@dataclass
class OAuthCredentials:
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[int]
    
@dataclass
class AuthPrompt:
    message: str
    placeholder: Optional[str]
```

#### 2.3.2 Provider实现

每个OAuth Provider需要实现:
- `login()`: 启动OAuth流程
- `refresh()`: 刷新token
- `logout()`: 清除凭证

### 2.4 会话压缩 (coding/core/compaction/)

#### 2.4.1 核心概念

- **分支摘要**: 为会话分支生成摘要
- **会话压缩**: 压缩历史消息保留上下文
- **智能截断**: 基于重要性的消息截断

#### 2.4.2 实现接口

```python
class SessionCompactor:
    """会话压缩器"""
    
    def compact(self, messages: List[Message], 
                target_tokens: int) -> CompactionResult
    def summarize_branch(self, messages: List[Message]) -> str
    def calculate_tokens(self, messages: List[Message]) -> int

@dataclass
class CompactionResult:
    messages: List[Message]
    summary: Optional[str]
    tokens_saved: int
```

### 2.5 CLI选择器

使用 `questionary` 或 `inquirer` 库实现交互式TUI:

```python
class ConfigSelector:
    """配置选择器"""
    def select(self) -> Config

class SessionPicker:
    """会话选择器"""
    def pick(self, sessions: List[Session]) -> Optional[Session]
    
class ModelLister:
    """模型列表"""
    def list_models(self, provider: Optional[str] = None)
```

---

## 3. 实现计划

### Phase 1: 基础设施 (Day 1)
- [ ] 创建目录结构
- [ ] 实现模型数据库 (generated.py)
- [ ] 实现模型注册表

### Phase 2: OAuth完善 (Day 1-2)
- [ ] OAuth类型定义
- [ ] Anthropic OAuth
- [ ] GitHub Copilot OAuth
- [ ] 更新现有OAuth实现

### Phase 3: AI包CLI (Day 2)
- [ ] CLI框架
- [ ] login命令
- [ ] list命令
- [ ] models命令

### Phase 4: 会话压缩 (Day 2-3)
- [ ] 压缩核心算法
- [ ] 分支摘要
- [ ] 与mes模块整合

### Phase 5: CLI选择器 (Day 3)
- [ ] 配置选择器
- [ ] 会话选择器
- [ ] 模型列表

### Phase 6: 其他功能 (Day 3-4)
- [ ] 事件总线
- [ ] 诊断工具
- [ ] 工具管理器

### Phase 7: 整合测试 (Day 4)
- [ ] 更新__init__.py
- [ ] 编写测试
- [ ] 运行验证

---

## 4. 兼容性说明

### 4.1 API兼容性

- 保持现有API不变
- 新增功能使用独立模块
- 提供迁移指南

### 4.2 配置兼容性

- 支持Pi-Mono配置格式
- 提供配置转换工具

---

## 5. 测试策略

### 5.1 单元测试

每个模块独立测试:
- 模型数据库查询
- OAuth流程
- 压缩算法

### 5.2 集成测试

- CLI端到端测试
- Provider集成测试
- 会话流程测试

---

*最后更新: 2026-02-11*
