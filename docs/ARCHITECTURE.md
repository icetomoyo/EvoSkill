# EvoSkill 系统架构设计

> 基于 Pi Agent、OpenClaw、Goose 等开源项目的深度调研

## 1. 设计哲学

### 核心原则
1. **嵌入优先**: 设计为可被任何应用集成的 Agent 引擎
2. **渐进增强**: 从简单工具调用到自动 Skill 生成
3. **开放标准**: 采用 Anthropic Agent Skill 规范
4. **语言无关**: 核心 Python，支持多语言 Skill

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           应用层 (Application Layer)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   CLI 工具    │  │   Web 服务   │  │   IDE 插件   │  │   消息机器人      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ SDK / API / RPC
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                           EvoSkill 核心引擎                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Agent 会话管理器                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │   对话状态    │  │   上下文压缩  │  │      会话持久化          │  │   │
│  │  │   管理       │  │   (Compaction)│  │     (JSONL)             │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                        Agent 执行循环 (Agent Loop)                     │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │   意图理解    │→│   计划生成    │→│   工具执行    │→│   结果整合  │ │ │
│  │  │  (Intent)    │  │   (Plan)     │  │  (Execute)   │  │  (Synthesize)│ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                        工具与 Skill 系统                              │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │ │
│  │  │   内置工具集      │  │   Skill 加载器    │  │    Skill 运行时       │ │ │
│  │  │ (文件/网络/代码)  │  │  (动态发现/加载)  │  │   (沙箱执行)          │ │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐ │
│  │                        Skill 进化引擎 (Skill Evolution)               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │   需求分析    │→│   Skill 设计  │→│   代码生成    │→│   自动测试  │ │ │
│  │  │ (Analyzer)   │  │  (Designer)  │  │ (Generator)  │  │  (Tester)  │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              基础设施层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   LLM 接口    │  │   向量存储    │  │   文件系统    │  │     配置管理      │ │
│  │  (多Provider) │  │  (ChromaDB)  │  │   (工作区)    │  │   (YAML/JSON)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 Agent 会话管理器 (Session Manager)

**设计参考**: Pi Agent 的 Session 管理

```python
class AgentSession:
    """
    Agent 会话核心类
    
    职责:
    1. 维护对话历史 (messages)
    2. 管理上下文压缩 (compaction)
    3. 持久化存储 (JSONL)
    4. 支持会话分支 (branching)
    """
    
    def __init__(self, session_id: str, workspace: Path):
        self.session_id = session_id
        self.workspace = workspace
        self.messages: List[Message] = []
        self.metadata: SessionMetadata
        
    async def prompt(self, user_input: str) -> AsyncIterator[Event]:
        """处理用户输入，返回事件流"""
        pass
        
    async def compact(self) -> CompactionResult:
        """上下文压缩"""
        pass
        
    def branch(self, entry_id: str) -> "AgentSession":
        """从指定历史点创建分支"""
        pass
```

**关键特性**:
- **JSONL 持久化**: 每行一个消息，支持追加写入
- **树状结构**: 通过 `parent_id` 支持分支
- **自动压缩**: Token 数超过阈值时自动总结

### 3.2 Agent 执行循环 (Agent Loop)

**设计参考**: Claude Code + Pi Agent

```
┌─────────────────────────────────────────────────────────┐
│                     Agent Loop                          │
├─────────────────────────────────────────────────────────┤
│  1. 接收用户输入                                         │
│     ↓                                                   │
│  2. 构建上下文 (系统提示词 + 历史消息 + 可用工具)          │
│     ↓                                                   │
│  3. 调用 LLM (streaming)                                │
│     ↓                                                   │
│  4. 解析响应                                            │
│     ├── 如果是文本 → 直接返回用户                       │
│     └── 如果是工具调用 → 执行步骤 5                     │
│     ↓                                                   │
│  5. 执行工具调用                                         │
│     ├── 查找工具                                        │
│     ├── 验证参数                                        │
│     ├── 执行 (可能涉及权限确认)                          │
│     └── 获取结果                                        │
│     ↓                                                   │
│  6. 将工具结果加入上下文                                  │
│     ↓                                                   │
│  7. 回到步骤 3 (继续循环直到获得最终响应)                  │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Skill 系统

**设计参考**: Anthropic Agent Skill 标准 + OpenClaw Skills

#### Skill 目录结构
```
skill-name/
├── SKILL.md              # Skill 定义文件 (YAML frontmatter + Markdown)
├── main.py               # 实现代码 (Python/TypeScript/...)
├── requirements.txt      # 依赖
└── tests/                # 测试用例
    └── test_main.py
```

#### SKILL.md 格式
```markdown
---
name: weather-query
description: 查询指定城市的天气信息
version: 1.0.0
author: evoskill
tools:
  - name: get_weather
    description: 获取城市天气
    parameters:
      city:
        type: string
        description: 城市名称
        required: true
---

# Weather Query Skill

## 使用场景

当用户询问天气时使用此 Skill。

## 示例

User: "北京今天天气怎么样？"
→ 调用 get_weather(city="北京")
```

#### Skill 加载器
```python
class SkillLoader:
    """
    Skill 动态加载器
    
    支持:
    1. 从本地目录加载
    2. 从 GitHub/远程 URL 加载
    3. 热更新 (无需重启)
    """
    
    def load_skill(self, path: Path) -> Skill:
        """加载单个 Skill"""
        pass
        
    def discover_skills(self, directory: Path) -> List[Skill]:
        """发现目录下所有 Skills"""
        pass
        
    def reload_skill(self, skill_name: str) -> Skill:
        """热重载指定 Skill"""
        pass
```

### 3.4 Skill 进化引擎

**核心能力**: 自动识别需求缺口 → 设计 Skill → 生成代码 → 测试验证

```python
class SkillEvolutionEngine:
    """
    Skill 进化引擎
    
    触发条件:
    1. 用户明确请求: "帮我创建一个能...的 Skill"
    2. 自动识别: LLM 判断现有 Skills 无法满足需求
    """
    
    async def analyze_need(self, context: ConversationContext) -> NeedAnalysis:
        """
        分析需求
        
        输出:
        - 核心功能点
        - 技术可行性
        - 与现有 Skills 的关系
        """
        pass
        
    async def design_skill(self, analysis: NeedAnalysis) -> SkillDesign:
        """
        设计 Skill
        
        输出:
        - Skill 名称和描述
        - 工具列表和参数
        - 实现方案
        """
        pass
        
    async def generate_code(self, design: SkillDesign) -> GeneratedSkill:
        """
        生成代码
        
        输出:
        - SKILL.md
        - 实现代码
        - 测试用例
        """
        pass
        
    async def validate_skill(self, skill: GeneratedSkill) -> ValidationResult:
        """
        验证 Skill
        
        - 语法检查
        - 单元测试
        - 集成测试 (模拟调用)
        """
        pass
        
    async def deploy_skill(self, skill: GeneratedSkill) -> DeployResult:
        """
        部署 Skill
        
        - 保存到 Skills 目录
        - 注册到 Skill 仓库
        - 通知用户
        """
        pass
```

---

## 4. 数据模型

### 4.1 消息类型

```python
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Message:
    """基础消息类"""
    id: str
    role: Literal["user", "assistant", "system", "tool"]
    timestamp: datetime
    parent_id: Optional[str] = None  # 支持分支

@dataclass
class UserMessage(Message):
    content: str
    attachments: List[Attachment] = None

@dataclass
class AssistantMessage(Message):
    content: List[ContentBlock]  # 文本/思考/工具调用
    model: str
    usage: TokenUsage

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ToolResultMessage(Message):
    tool_call_id: str
    tool_name: str
    content: List[ContentBlock]
    is_error: bool = False
```

### 4.2 Skill 定义

```python
@dataclass
class Skill:
    """Skill 定义"""
    name: str
    description: str
    version: str
    author: str
    tools: List[ToolDefinition]
    metadata: SkillMetadata
    source_path: Path
    
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, ParameterSchema]
    handler: Callable  # 实际执行函数
```

---

## 5. 事件流设计

参考 Pi Agent 的 Event Stream:

```python
class EventType(Enum):
    # 生命周期事件
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    
    # 消息事件
    MESSAGE_START = "message_start"
    MESSAGE_UPDATE = "message_update"  # 流式更新
    MESSAGE_END = "message_end"
    
    # 工具事件
    TOOL_EXECUTION_START = "tool_execution_start"
    TOOL_EXECUTION_UPDATE = "tool_execution_update"  # 流式输出
    TOOL_EXECUTION_END = "tool_execution_end"
    
    # Skill 事件
    SKILL_CREATED = "skill_created"
    SKILL_UPDATED = "skill_updated"
    
    # 系统事件
    AUTO_COMPACTION_START = "auto_compaction_start"
    AUTO_COMPACTION_END = "auto_compaction_end"
```

---

## 6. LLM 接口抽象

支持多 Provider:

```python
class LLMProvider(ABC):
    """LLM 提供商抽象接口"""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[LLMResponse]:
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI / 兼容 OpenAI API 的提供商"""
    pass

class AnthropicProvider(LLMProvider):
    """Anthropic Claude"""
    pass
```

---

## 7. 安全设计

### 7.1 工具执行沙箱

```python
class ToolSandbox:
    """
    工具执行沙箱
    
    限制:
    1. 文件系统访问限制 (chroot/工作区)
    2. 网络访问白名单
    3. 执行超时
    4. 资源限制 (CPU/内存)
    """
    
    def execute(self, tool: Tool, args: Dict) -> ToolResult:
        # 在受限环境中执行
        pass
```

### 7.2 权限控制

```python
class PermissionPolicy:
    """
    权限策略
    
    级别:
    - SAFE: 安全操作，直接执行
    - NORMAL: 普通操作，记录日志
    - DANGEROUS: 危险操作，需用户确认
    - FORBIDDEN: 禁止执行
    """
    pass
```

---

## 8. 扩展点

| 扩展点 | 说明 | 示例 |
|--------|------|------|
| LLM Provider | 自定义大模型后端 | 接入本地部署的模型 |
| Tool | 自定义工具 | 接入内部系统 API |
| Skill Source | 自定义 Skill 来源 | 企业内部 Skill 仓库 |
| Event Handler | 自定义事件处理 | 日志记录、监控告警 |
| Session Store | 自定义会话存储 | 数据库存储 |

---

## 9. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 生态丰富，AI/ML 友好 |
| 异步框架 | asyncio | 标准库，生态成熟 |
| LLM 客户端 | openai / anthropic SDK | 官方 SDK |
| 配置管理 | Pydantic Settings | 类型安全，环境变量支持 |
| 日志 | structlog | 结构化日志 |
| 测试 | pytest | 生态标准 |
| CLI | typer | 类型友好的 CLI 框架 |
| 向量存储 | ChromaDB (可选) | 轻量，本地优先 |

---

## 10. 演进路线

### Phase 1: 核心引擎 (MVP)
- [x] Agent Loop 基础实现
- [x] 基础工具集 (文件、代码、网络)
- [x] 会话管理
- [x] CLI 界面

### Phase 2: Skill 系统
- [x] Skill 加载器
- [x] 内置 Skills
- [x] Skill 文档规范

### Phase 3: 自我进化
- [x] 需求分析引擎
- [x] Skill 自动生成
- [x] 自动测试验证

### Phase 4: 生产就绪
- [ ] 多模态支持
- [ ] 分布式部署
- [ ] 监控与可观测性
- [ ] Skill 市场

---

## 参考项目

- [Pi Agent](https://github.com/can1357/oh-my-pi) - Agent 核心架构
- [OpenClaw](https://github.com/openclaw/openclaw) - 消息渠道集成
- [Goose](https://github.com/block/goose) - MCP 协议、工具生态
- [Aider](https://github.com/Aider-AI/aider) - 代码编辑、RepoMap
