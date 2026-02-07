# 上下文压缩系统设计（Context Compaction）

> 基于 Pi Agent 论文的实现

## 问题背景

当对话历史超过 `max_context_tokens` 时：
- ❌ 简单截断：丢失重要信息
- ❌ 直接报错：用户体验差
- ✅ Pi Agent 方案：智能压缩，保留关键信息

## 核心概念

### 触发条件（Pi Agent 设计）

```
触发阈值 = max_context_tokens × 80%

当上下文 token 数 ≥ 触发阈值时，启动压缩
```

**示例**:
- `max_context_tokens = 80000`
- 触发阈值 = 64000 tokens
- 当对话达到 64000 tokens 时压缩

### 压缩策略

Pi Agent 的核心思想：
1. **保留系统提示**（System Prompt）- 总是完整保留
2. **保留工具定义** - 压缩后仍需知道可用工具
3. **生成对话摘要** - 用 LLM 总结历史对话
4. **保留最近 N 轮** - 保留最近 2-3 轮完整对话

### 压缩前后对比

**压缩前**（假设 70k tokens）:
```
[System Prompt]          ~2k tokens
[Tool Definitions]       ~3k tokens
[User: 你好]             ~0.1k
[Assistant: 回复...]     ~0.5k
[User: 帮我读文件]       ~0.2k
[Assistant: 使用工具...] ~1k
... (100+ 轮对话)        ~63k tokens
```

**压缩后**（~10k tokens）:
```
[System Prompt]          ~2k tokens (保留)
[Tool Definitions]       ~3k tokens (保留)
[Summary: 之前对话中，用户让我读取了 README.md，创建了 test.py 文件，
         询问了项目结构...]  ~3k tokens (生成)
[User: 刚才的文件在哪？]   ~0.5k (最近对话保留)
[Assistant: 在 test.py]    ~0.5k (最近对话保留)
[User: 帮我修改它]        ~0.5k (当前输入)
```

## 系统设计

### 类结构

```python
class ContextCompactor:
    """上下文压缩器"""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        max_tokens: int = 80000,
        trigger_ratio: float = 0.8,
        keep_recent_rounds: int = 2,
    ):
        self.llm = llm_provider
        self.max_tokens = max_tokens
        self.trigger_threshold = int(max_tokens * trigger_ratio)
        self.keep_recent = keep_recent_rounds
    
    def should_compact(self, messages: List[Message]) -> bool:
        """检查是否需要压缩"""
        current_tokens = estimate_tokens(messages)
        return current_tokens >= self.trigger_threshold
    
    async def compact(
        self,
        messages: List[Message],
        system_prompt: str,
        tools: List[ToolDefinition],
    ) -> CompactResult:
        """执行压缩"""
        # 1. 分离需要保留的部分
        # 2. 生成摘要
        # 3. 组装新的消息列表
        pass

@dataclass
class CompactResult:
    """压缩结果"""
    new_messages: List[Message]
    summary: str
    original_token_count: int
    new_token_count: int
    compacted_count: int  # 压缩了多少轮对话
```

### 压缩流程

```
┌─────────────────────────────────────────┐
│  1. 检查 Token 数                         │
│     if tokens < threshold: 无需压缩        │
└──────────────────┬──────────────────────┘
                   │ 是
                   ▼
┌─────────────────────────────────────────┐
│  2. 分离消息                              │
│     - 系统提示 (system)                   │
│     - 工具定义 (tools)                    │
│     - 历史对话 (history)                  │
│     - 最近 N 轮 (recent)                  │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  3. 生成摘要                              │
│     使用 LLM 总结历史对话的关键信息          │
│     Prompt: "请总结以下对话..."            │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  4. 组装新上下文                          │
│     [System] + [Tools] + [Summary] +      │
│     [Recent N rounds] + [Current]         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  5. 返回结果                              │
│     包含统计信息：压缩前/后 token 数        │
└─────────────────────────────────────────┘
```

## 关键实现细节

### Token 估算

不需要精确计算，使用近似值：

```python
def estimate_tokens(text: str) -> int:
    """估算 token 数（近似）"""
    # 中文：1 字 ≈ 1.5 tokens
    # 英文：1 词 ≈ 1.3 tokens
    # 简单近似：字符数 / 2
    return len(text) // 2

def estimate_messages_tokens(messages: List[Message]) -> int:
    """估算消息列表的 token 数"""
    total = 0
    for msg in messages:
        # 消息格式开销 ~4 tokens
        total += 4
        # 内容 token
        if isinstance(msg.content, str):
            total += estimate_tokens(msg.content)
        else:
            for block in msg.content:
                if hasattr(block, 'text'):
                    total += estimate_tokens(block.text)
    return total
```

### 摘要生成 Prompt

```python
SUMMARY_PROMPT = """请总结以下对话历史的关键信息。

要求：
1. 保留用户的意图和请求
2. 保留重要的文件操作（读取/修改了哪些文件）
3. 保留关键的决策和结果
4. 简洁，不超过 500 字
5. 使用第三人称："用户要求...", "AI 完成了..."

对话历史：
{conversation_history}

请生成摘要："""
```

### 用户确认

压缩前询问用户（可配置）：

```python
if config.require_confirmation:
    confirmation = await ask_user(
        f"上下文即将达到上限 ({current_tokens}/{max_tokens} tokens)。\n"
        f"建议压缩对话历史，保留关键信息。\n"
        f"是否同意压缩？"
    )
    if not confirmation:
        # 用户拒绝，可能选择其他策略
        return
```

## 配置选项

```yaml
# config.yaml

# 上下文压缩配置
context_compaction:
  enabled: true                    # 是否启用
  max_context_tokens: 80000        # 最大上下文 token 数
  trigger_ratio: 0.8               # 触发压缩的比例（0-1）
  keep_recent_rounds: 2            # 保留最近 N 轮完整对话
  require_confirmation: true       # 压缩前是否询问用户
  summary_max_length: 1000         # 摘要最大长度（字符）
```

## 与现有系统集成

### 修改 Session 类

```python
class AgentSession:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.compactor = ContextCompactor(
            llm_provider=self._llm_provider,
            max_tokens=config.max_context_tokens,
        )
    
    async def prompt(self, user_input: str):
        # 添加消息前检查是否需要压缩
        if self.compactor.should_compact(self.messages):
            await self._compact_context()
        
        # ... 正常流程 ...
    
    async def _compact_context(self):
        """执行上下文压缩"""
        result = await self.compactor.compact(
            messages=self.messages,
            system_prompt=self.system_prompt,
            tools=list(self._tools.values()),
        )
        
        # 替换消息列表
        self.messages = result.new_messages
        
        # 通知用户
        self.events.emit(EventType.CONTEXT_COMPACTED, {
            "original_tokens": result.original_token_count,
            "new_tokens": result.new_token_count,
            "summary": result.summary,
        })
```

### 事件通知

```python
class EventType:
    # ... 现有事件 ...
    CONTEXT_COMPACTED = "context_compacted"  # 上下文已压缩
    
class CompactContextEvent:
    original_tokens: int
    new_tokens: int
    saved_ratio: float  # 节省比例
    summary: str
```

## 边界情况处理

### 情况 1：摘要也超过限制

```python
if estimate_tokens(summary) > max_summary_tokens:
    # 进一步截断摘要
    summary = summary[:max_summary_tokens]
```

### 情况 2：用户拒绝压缩

```python
# 提供替代方案：
# 1. 删除最旧的消息
# 2. 启动新会话
# 3. 报错并要求用户手动处理
```

### 情况 3：压缩后仍然超限

```python
# 递归压缩，保留更少的历史
# 或者启动新会话
```

## 测试策略

### 单元测试

```python
async def test_compact_logic():
    """测试压缩逻辑"""
    # 构造大量消息
    messages = [create_message(f"内容{i}") for i in range(100)]
    
    compactor = ContextCompactor(...)
    result = await compactor.compact(messages, ...)
    
    assert result.new_token_count < result.original_token_count
    assert len(result.new_messages) < len(messages)
```

### 集成测试

```python
async def test_session_auto_compact():
    """测试 Session 自动触发压缩"""
    session = AgentSession(
        max_context_tokens=1000,  # 设置很小以触发压缩
    )
    
    # 发送大量消息
    for i in range(50):
        await session.prompt(f"测试消息 {i}")
    
    # 验证压缩被触发
    assert session.compaction_count > 0
```

## 实现步骤

1. **创建 `ContextCompactor` 类** (2 小时)
   - Token 估算
   - 压缩逻辑

2. **集成到 `AgentSession`** (1 小时)
   - 触发检查
   - 执行压缩

3. **添加配置支持** (30 分钟)
   - 配置模型
   - 配置文件更新

4. **UI/事件通知** (1 小时)
   - 压缩提示
   - 统计信息展示

5. **测试** (1 小时)
   - 单元测试
   - 手动测试

**总计**: 约 6 小时工作量

## 下一步

确认设计后，我将开始实现：
1. `evoskill/core/context.py` - ContextCompactor 类
2. 修改 `evoskill/core/session.py` - 集成压缩逻辑
3. 添加配置选项
4. 编写测试

请确认设计，或提出修改意见！
