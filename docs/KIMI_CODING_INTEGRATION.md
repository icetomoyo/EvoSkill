# Kimi For Coding API 集成指南

> 基于 EvoSkill 项目集成经验总结

## 概述

Kimi For Coding 是 Moonshot AI 推出的专门面向编程场景的 AI 服务。与普通 Kimi API 不同，它有严格的客户端验证机制，需要特定的配置才能访问。

**关键区别**：

| 特性 | Kimi For Coding | 普通 Kimi API |
|------|----------------|--------------|
| Endpoint | `https://api.kimi.com/coding/v1` | `https://api.moonshot.cn/v1` |
| API 格式 | OpenAI 兼容 | OpenAI 兼容 |
| 客户端验证 | 严格（需要 User-Agent） | 宽松 |
| 用途 | 编程/代码场景 | 通用对话 |
| 获取方式 | https://www.kimi.com/code | https://platform.moonshot.cn |

---

## User-Agent 版本兼容性

### 已验证的有效版本

截至 **2026-02-07**，以下 User-Agent 版本均已验证有效：

| User-Agent 版本 | 状态 | 推荐度 | 备注 |
|----------------|------|--------|------|
| `KimiCLI/0.77` | ✅ 有效 | ⭐⭐⭐⭐⭐ | 稳定使用，推荐默认使用 |
| `KimiCLI/1.0` | ✅ 有效 | ⭐⭐⭐⭐ | 可用，与 0.77 无显著差异 |
| `KimiCLI/1.5` | ✅ 有效 | ⭐⭐⭐⭐ | 可用 |
| `KimiCLI/1.6` | ✅ 有效 | ⭐⭐⭐⭐ | 最新版本，可用 |

### 版本选择建议

**当前推荐**: 使用 `KimiCLI/0.77`

原因：
1. **稳定性**: 经过长期验证，没有兼容性问题
2. **兼容性**: 所有测试版本都有效，Kimi 服务端不强制要求最新
3. **无需频繁更新**: 可以长期使用，直到服务端明确拒绝

**何时升级到 1.6**:
- 当 `0.77` 返回 403 错误时
- 需要使用 1.6 版本特定的新功能（目前未发现）

### 快速验证版本有效性

```bash
# 测试 0.77（默认）
uv run evoskill chat

# 测试 1.6
$env:KIMI_USER_AGENT_VERSION="1.6"
uv run evoskill chat
```

或运行测试脚本：
```bash
uv run python tests/test_user_agent_versions.py
```

---

## 先决条件

1. **API Key**：从 [https://www.kimi.com/code](https://www.kimi.com/code) 申请
2. **Python 3.8+**
3. **OpenAI SDK**：`pip install openai`（不是 anthropic）

---

## 核心集成步骤

### 步骤 1：明确 API 格式

**❌ 常见误区**：认为 Kimi For Coding 使用 Anthropic 格式（因为它在错误信息中提到 Claude）

**✅ 正确做法**：使用 **OpenAI 兼容格式**

```python
# 正确 - 使用 OpenAI 客户端
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-kimi-your-key",
    base_url="https://api.kimi.com/coding/v1"
)

# 错误 - 不要使用 Anthropic
from anthropic import AsyncAnthropic  # ❌
```

---

### 步骤 2：设置特殊 User-Agent

这是最关键的一步！Kimi For Coding 服务器会验证客户端身份。

**注意**: 经测试，`0.77`, `1.0`, `1.5`, `1.6` 版本全部有效。默认推荐使用 `0.77`。

```python
import httpx
from openai import AsyncOpenAI

# 方法 1：通过 default_headers（推荐）
client = AsyncOpenAI(
    api_key="sk-kimi-your-key",
    base_url="https://api.kimi.com/coding/v1",
    default_headers={
        "User-Agent": "KimiCLI/0.77",  # 关键！0.77, 1.0, 1.5, 1.6 均有效
        "Accept": "application/json",
    }
)

# 方法 2：通过自定义 HTTP 客户端
http_client = httpx.AsyncClient(
    headers={"User-Agent": "KimiCLI/0.77"}
)
client = AsyncOpenAI(
    api_key="sk-kimi-your-key",
    base_url="https://api.kimi.com/coding/v1",
    http_client=http_client
)
```

**关键头信息**：
- `User-Agent: KimiCLI/0.77` - 伪装成 Kimi 官方 CLI
- 版本号 `0.77` 是目前测试有效的版本

---

### 步骤 3：正确的请求参数

```python
import asyncio

async def chat_with_kimi():
    client = AsyncOpenAI(
        api_key="sk-kimi-your-key",
        base_url="https://api.kimi.com/coding/v1",
        default_headers={"User-Agent": "KimiCLI/0.77"},
    )
    
    response = await client.chat.completions.create(
        model="k2p5",  # Kimi For Coding 的模型名
        messages=[
            {"role": "user", "content": "你好"}
        ],
        temperature=0.0,
        max_tokens=4096,
        stream=True,  # 支持流式
    )
    
    async for chunk in response:
        # 注意：某些 chunk 可能 choices 为空（心跳包）
        if chunk.choices:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="")

asyncio.run(chat_with_kimi())
```

**模型名称**：
- `k2p5` - Kimi K2.5（当前主要模型）

---

## 完整示例代码

### 基础对话示例

```python
import asyncio
from openai import AsyncOpenAI

class KimiCodingClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.kimi.com/coding/v1",
            default_headers={
                "User-Agent": "KimiCLI/0.77",
                "Accept": "application/json",
            }
        )
    
    async def chat(self, message: str, stream: bool = True):
        response = await self.client.chat.completions.create(
            model="k2p5",
            messages=[{"role": "user", "content": message}],
            temperature=0.0,
            stream=stream,
        )
        
        if stream:
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            yield response.choices[0].message.content

# 使用
async def main():
    kimi = KimiCodingClient("sk-kimi-your-key")
    async for text in kimi.chat("用 Python 写个快速排序"):
        print(text, end="")

asyncio.run(main())
```

### 带工具调用的示例

```python
async def chat_with_tools():
    client = AsyncOpenAI(
        api_key="sk-kimi-your-key",
        base_url="https://api.kimi.com/coding/v1",
        default_headers={"User-Agent": "KimiCLI/0.77"},
    )
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"}
                    },
                    "required": ["city"]
                }
            }
        }
    ]
    
    response = await client.chat.completions.create(
        model="k2p5",
        messages=[{"role": "user", "content": "北京天气如何？"}],
        tools=tools,
        tool_choice="auto",
    )
    
    message = response.choices[0].message
    
    # 检查是否有工具调用
    if message.tool_calls:
        for tool_call in message.tool_calls:
            print(f"调用工具: {tool_call.function.name}")
            print(f"参数: {tool_call.function.arguments}")
    else:
        print(f"回复: {message.content}")
```

---

## 常见错误与解决方案

### 错误 1：403 Forbidden
```
Error code: 403 - {'error': {'message': 'Kimi For Coding is currently only available 
for Coding Agents such as Kimi CLI...', 'type': 'access_terminated_error'}}
```

**原因**：
- 缺少 `User-Agent` 头
- User-Agent 不正确

**解决**：
```python
default_headers={"User-Agent": "KimiCLI/0.77"}
```

---

### 错误 2：401 Unauthorized
```
Error code: 401 - {'error': {'message': 'invalid x-api-key', 'type': 'auth_error'}}
```

**原因**：
- API Key 无效或过期
- 使用了普通 Moonshot API Key（不是 Kimi For Coding Key）

**解决**：
- 从 https://www.kimi.com/code 重新申请
- 确保使用 `KIMI_API_KEY`，不是 `MOONSHOT_API_KEY`

---

### 错误 3：模型不存在
```
Error: model "claude-3-sonnet" not found
```

**原因**：
- 使用了错误的模型名
- 使用了 Anthropic 的模型名

**解决**：
- Kimi For Coding 模型名是 `k2p5`
- 不是 `claude-3-sonnet` 或 `moonshot-v1-8k`

---

### 错误 4：流式响应中断
```
Error: list index out of range
```

**原因**：
- 流式响应中的某些 chunk 可能没有 `choices`
- 心跳包或结束标记

**解决**：
```python
async for chunk in response:
    # 必须检查 choices 是否为空
    if not chunk.choices:
        continue
    
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="")
```

---

## 配置示例

### 配置文件（YAML）

```yaml
# config.yaml
provider: kimi-coding  # 自定义标识，代码中特殊处理
model: k2p5
base_url: https://api.kimi.com/coding/v1
api_key: sk-kimi-your-key  # 或从环境变量读取
temperature: 0.0
max_tokens: 4096

# 可选：自定义 User-Agent 版本（0.77, 1.0, 1.5, 1.6 均有效）
# 默认为 0.77，如需升级可取消注释下一行
# user_agent_version: "1.6"
```

### 环境变量

```bash
# Windows PowerShell
$env:KIMI_API_KEY="sk-kimi-your-key"

# Linux/Mac
export KIMI_API_KEY="sk-kimi-your-key"
```

---

## 最佳实践

### 1. 优雅降级

如果 Kimi For Coding 不可用，提供备选方案：

```python
def create_llm_provider(config):
    try:
        if config.provider == "kimi-coding":
            return KimiCodingProvider(config)
    except Exception as e:
        print(f"Kimi Coding 初始化失败: {e}, 切换到 OpenRouter")
        config.provider = "openai"
        config.base_url = "https://openrouter.ai/api/v1"
        return OpenAIProvider(config)
```

### 2. 隐藏实现细节

用户只需配置 provider，内部自动处理 User-Agent：

```python
class OpenAIProvider:
    def __init__(self, config):
        headers = {"Accept": "application/json"}
        
        # 自动检测 Kimi For Coding
        if config.provider == "kimi-coding" or \
           (config.base_url and "kimi.com/coding" in config.base_url):
            headers["User-Agent"] = "KimiCLI/0.77"
        
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            default_headers=headers,
        )
```

### 3. User-Agent 版本选择

**已验证有效的版本**: `0.77`, `1.0`, `1.5`, `1.6`

**推荐做法**: 
- 默认使用 `0.77`（最稳定）
- 支持通过环境变量切换版本

```python
import os

# 默认版本（稳定）
DEFAULT_VERSION = "0.77"

# 允许用户通过环境变量自定义
version = os.getenv("KIMI_USER_AGENT_VERSION", DEFAULT_VERSION)

headers = {
    "User-Agent": f"KimiCLI/{version}"
}
```

**切换版本测试**:
```bash
# 测试 1.6 版本
$env:KIMI_USER_AGENT_VERSION="1.6"
python your_app.py
```

---

## 验证清单

集成完成后，验证以下功能：

- [ ] 简单对话正常
- [ ] 流式响应正常
- [ ] 工具调用正常
- [ ] 多轮对话上下文保持
- [ ] 长时间对话不中断
- [ ] 错误处理优雅

---

## 参考资源

- **Kimi For Coding**: https://www.kimi.com/code
- **OpenAI SDK**: https://github.com/openai/openai-python
- **本指南来源**: EvoSkill 项目集成经验

---

## 更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-02-07 | v1.0 | 初始版本，基于 EvoSkill v0.1.0 集成经验 |
| 2026-02-07 | v1.1 | 添加 User-Agent 版本兼容性测试结果（0.77, 1.0, 1.5, 1.6 全部有效） |

---

**注意**：Kimi For Coding 的验证机制可能随时更新。如果遇到新的错误，请检查 User-Agent 版本是否需要更新。

### 版本有效性快速检查

如果遇到 403 错误，可以运行以下脚本验证版本：

```bash
# 在 EvoSkill 项目中
uv run python tests/test_user_agent_versions.py
```

或手动测试：

```bash
# 测试当前版本
uv run evoskill chat

# 测试 1.6 版本
$env:KIMI_USER_AGENT_VERSION="1.6"
uv run evoskill chat
```
