# Pi-Mono 组件分析 - 值得在 Koda 中实现的模块

> 分析 badlogic/pi-mono 的 packages，找出值得移植的组件

---

## 一、Pi-Mono 包结构

```
packages/
├── ai/              # LLM 工具包 (@mariozechner/pi-ai)
├── agent/           # Agent 框架 (@mariozechner/pi-agent)
├── coding-agent/    # Pi Coding Agent (已对标)
├── mom/             # 消息格式 (@mariozechner/pi-mom)
├── pods/            # 进程管理 (@mariozechner/pi-pods)
├── tui/             # 终端 UI (@mariozechner/pi-tui)
└── web-ui/          # Web UI (未来考虑)
```

---

## 二、逐个分析

### 1. packages/ai - LLM 工具包 ⭐⭐⭐⭐⭐

**功能**: 统一的 LLM 接口，支持多提供商

**支持提供商**:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini/Vertex)
- Azure OpenAI
- Amazon Bedrock
- Mistral, Groq, Cerebras, xAI
- OpenRouter, Vercel AI Gateway
- **Kimi For Coding** ✅
- 自定义 Provider

**核心功能**:
- 流式响应 (streaming)
- 工具调用标准化
- Token 计算
- 上下文管理
- 图片/多模态支持

**Koda 实现价值**: ⭐⭐⭐⭐⭐ (最高)
- 统一 LLM 接口
- 自动提供商检测
- 模型列表管理

---

### 2. packages/agent - Agent 框架 ⭐⭐⭐⭐⭐

**功能**: 基础 Agent 抽象

**核心组件**:
- Agent 生命周期管理
- 消息队列
- 工具注册与调用
- 事件系统
- Session 管理

**Koda 现状**: 已有简化版，可对比增强

**值得借鉴**:
- 更完善的事件系统
- 消息队列机制
- Agent 状态管理

**Koda 实现价值**: ⭐⭐⭐⭐

---

### 3. packages/mom - 消息格式 ⭐⭐⭐⭐

**功能**: Model-Optimized Messages

**核心设计**:
- 标准化消息格式
- 工具调用/结果格式
- Token 优化编码
- 压缩/解压

**特点**:
- 比 OpenAI format 更高效
- 支持嵌套工具调用
- 内置成本计算

**Koda 实现价值**: ⭐⭐⭐⭐
- 优化 Token 使用
- 标准化接口

---

### 4. packages/pods - 进程管理 ⭐⭐⭐

**功能**: 沙箱进程管理

**核心功能**:
- 隔离进程执行
- 资源限制 (CPU/内存)
- 超时控制
- 安全沙箱

**使用场景**:
- 不受信任的代码执行
- 后台任务
- 长时间运行任务

**Koda 实现价值**: ⭐⭐⭐
- 增强安全性
- 但会增加复杂度

---

### 5. packages/tui - 终端 UI ⭐⭐⭐⭐

**功能**: 终端用户界面组件

**核心组件**:
- 编辑器 (Editor)
- 消息显示
- 快捷键系统
- 主题支持
- 滚动/分页

**特点**:
- React-like 组件模型
- 键盘导航
- 自定义主题

**Koda 实现价值**: ⭐⭐⭐⭐
- CLI 体验提升
- 但可以用简单版

---

### 6. packages/web-ui ⭐⭐

**功能**: Web 界面

**Koda 定位**: CLI 优先，Web 为可选
**实现优先级**: 低

---

## 三、推荐移植优先级

### P0 - 核心必须

| 组件 | 模块 | 说明 |
|------|------|------|
| **ai** | `koda/llm/` | 统一 LLM 接口，支持 15+ 提供商 |
| **mom** | `koda/messages/` | 标准化消息格式，Token 优化 |

### P1 - 重要增强

| 组件 | 模块 | 说明 |
|------|------|------|
| **agent** | `koda/core/agent.py` 增强 | 事件系统、消息队列 |
| **tui** | `koda/tui/` | 终端 UI 组件（简化版） |

### P2 - 安全增强

| 组件 | 模块 | 说明 |
|------|------|------|
| **pods** | `koda/sandbox/` | 沙箱执行（可选） |

### P3 - 未来考虑

| 组件 | 说明 |
|------|------|
| **web-ui** | Web 界面（大工程） |

---

## 四、具体实现建议

### 4.1 LLM 统一接口 (packages/ai)

```python
# koda/llm/provider.py
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages, **kwargs) -> AsyncIterator[Message]:
        pass
    
    @abstractmethod
    async def get_models(self) -> List[Model]:
        pass

# 实现
class OpenAIProvider(LLMProvider): ...
class AnthropicProvider(LLMProvider): ...
class KimiProvider(LLMProvider): ...
class OpenRouterProvider(LLMProvider): ...
# ... 15+ 提供商
```

**价值**:
- 用户无需关心底层 API 差异
- 自动选择最优模型
- 统一错误处理

### 4.2 消息格式 (packages/mom)

```python
# koda/messages/format.py
class Message:
    role: str  # user/assistant/tool/system
    content: Union[str, List[ContentBlock]]
    tool_calls: Optional[List[ToolCall]]
    
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    
# Token 优化
class TokenOptimizer:
    def optimize(messages: List[Message]) -> List[Message]:
        # 移除冗余，压缩历史
        pass
```

**价值**:
- 减少 Token 消耗
- 统一格式转换

### 4.3 事件系统 (packages/agent)

```python
# koda/core/events.py
class EventBus:
    def on(self, event: str, handler: Callable): ...
    def emit(self, event: str, data: Any): ...

# 事件类型
class AgentEvent(Enum):
    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
```

**价值**:
- 更好的可观测性
- 支持扩展

### 4.4 沙箱 (packages/pods) - 可选

```python
# koda/sandbox/pod.py
class Pod:
    """隔离执行环境"""
    
    async def execute(self, command: str, timeout: int = 60) -> Result:
        # 在隔离环境中执行
        pass
```

**价值**:
- 安全性
- 资源控制

---

## 五、实施建议

### 阶段 1: LLM 统一接口 (1-2 周)
- 实现 Provider 抽象
- 支持 OpenAI, Anthropic, Kimi
- 模型自动发现

### 阶段 2: 消息优化 (1 周)
- 实现 MOM 格式
- Token 优化
- 上下文压缩

### 阶段 3: 事件系统 (3-5 天)
- Agent 事件重构
- 更好的流式输出

### 阶段 4: TUI (可选, 1-2 周)
- 简化版终端 UI
- 语法高亮
- 快捷键

---

## 六、总结

| 组件 | 优先级 | 工作量 | 价值 |
|------|--------|--------|------|
| **ai (LLM)** | P0 | 大 | ⭐⭐⭐⭐⭐ |
| **mom (消息)** | P0 | 中 | ⭐⭐⭐⭐ |
| **agent (事件)** | P1 | 中 | ⭐⭐⭐⭐ |
| **tui (UI)** | P1 | 大 | ⭐⭐⭐ |
| **pods (沙箱)** | P2 | 大 | ⭐⭐⭐ |
| **web-ui** | P3 | 很大 | ⭐⭐ |

**建议**: 优先实现 **ai** 和 **mom**，这是最大价值所在。
