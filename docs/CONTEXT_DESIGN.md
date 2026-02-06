# EvoSkill 上下文管理设计

> 参考 OpenClaw/Pi Agent 的实现

---

## OpenClaw 的设计分析

### 1. 核心洞察

**OpenClaw 不暴露复杂的压缩配置给用户**，而是：

```
用户配置: 最大上下文窗口 (如 200000 tokens)
         ↓
系统行为: 自动监测 → 接近上限时自动压缩 → 保持性能
```

### 2. OpenClaw 的压缩机制

```typescript
// 自动压缩触发
auto_compaction_start  // 开始压缩事件
auto_compaction_end    // 完成压缩事件

// 压缩策略
- Adaptive token budgeting  // 自适应 token 预算
- Tool failure summaries    // 工具失败摘要  
- File operation summaries  // 文件操作摘要
```

### 3. Context Pruning（剪枝）

```typescript
// Cache-TTL 基础剪枝
contextPruning: {
  mode: "cache-ttl" | "off"
}
```

### 4. History Limiting（历史限制）

```typescript
// 基于对话类型的历史限制
limitHistoryTurns(DM vs Group)
```

---

## 当前 EvoSkill 设计的反思

### ❌ 当前设计（复杂）

```yaml
# 用户需要理解两个概念
auto_compact: true          # 是否开启
compact_threshold: 8000     # 触发阈值（token 数）
```

**问题**:
1. 用户不知道应该设置多少阈值
2. 需要理解"压缩"的技术概念
3. 两个参数相互关联，容易配置错误

### ✅ 新设计（简化）

```yaml
# 只配置最大上下文
max_context_tokens: 80000   # 最大上下文 token 数
```

**行为**:
- 当上下文接近上限（如 80%）时，自动触发压缩
- 用户无需关心"是否开启"、"阈值是多少"
- 系统内部管理压缩策略

---

## 新配置设计

### 简化后的配置

```yaml
# ============================================
# LLM 配置
# ============================================

provider: openai
model: gpt-4o-mini
base_url: https://api.moonshot.cn/v1
# api_key 建议用环境变量

# ============================================
# 上下文配置 (简化!)
# ============================================

# max_context_tokens: 最大上下文 token 数
#   - 达到此值时自动触发压缩
#   - 建议设置为模型上下文窗口的 80-90%
#   - 例如: gpt-4o (128k) 可设为 100000
max_context_tokens: 80000

# ============================================
# 安全配置
# ============================================

# require_confirmation: 危险操作前是否询问确认
require_confirmation: true
```

### 对比

| 配置项 | 旧设计 | 新设计 |
|--------|--------|--------|
| 自动压缩开关 | `auto_compact: true` | 移除（始终开启） |
| 压缩阈值 | `compact_threshold: 8000` | 移除（内部管理） |
| 最大上下文 | 无 | `max_context_tokens: 80000` |

---

## 实现细节

### 压缩策略（内部实现）

```python
class ContextManager:
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.compact_threshold = int(max_tokens * 0.8)  # 80% 触发
    
    async def add_message(self, message: Message):
        current_tokens = self.estimate_tokens()
        
        if current_tokens > self.compact_threshold:
            # 自动压缩
            await self.compact_context()
        
        self.messages.append(message)
    
    async def compact_context(self):
        """压缩策略"""
        # 1. 保留系统提示词
        # 2. 总结早期对话（保留关键信息）
        # 3. 保留最近 N 轮完整对话
        # 4. 保留文件修改记录
        pass
```

### Token 估算

```python
def estimate_tokens(messages: List[Message]) -> int:
    """
    估算 token 数
    简单估算: 1 token ≈ 4 字符 (英文) 或 1-2 字符 (中文)
    """
    total_chars = sum(len(m.content) for m in messages)
    return int(total_chars / 4)
```

---

## 迁移指南

### 从旧配置迁移

```yaml
# 旧配置
auto_compact: true
compact_threshold: 8000

# 新配置
max_context_tokens: 10000  # 约等于旧 threshold / 0.8
```

---

## 结论

**设计理念**: 让用户关注"想要多少上下文"，而非"如何管理压缩"

- **简单**: 一个参数控制
- **智能**: 系统自动在合适时机压缩
- **安全**: 始终保留关键信息
