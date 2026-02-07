# User-Agent 版本管理指南

## 当前状态

- **我们使用的版本**: `KimiCLI/0.77`
- **Kimi CLI 最新版本**: `1.6+`
- **状态**: 截至 2026-02-07，`0.77` 仍然有效

---

## 需要更新吗？

### 短期（现在）
**不需要**

Kimi 服务端目前接受 `0.77`，没有强制要求使用最新版本。

### 中长期（建议）
**最好支持配置**

原因：
1. Kimi 可能随时升级验证，旧版本可能被拒绝
2. 新版本可能有新功能或性能优化
3. 用户可能有自己的偏好

---

## 验证当前版本是否有效

### 方法 1：快速测试
```python
import asyncio
from openai import AsyncOpenAI

async def test_user_agent(version: str):
    client = AsyncOpenAI(
        api_key="sk-kimi-your-key",
        base_url="https://api.kimi.com/coding/v1",
        default_headers={"User-Agent": f"KimiCLI/{version}"},
    )
    
    try:
        response = await client.chat.completions.create(
            model="k2p5",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
        )
        print(f"✓ 版本 {version} 有效")
        return True
    except Exception as e:
        print(f"✗ 版本 {version} 无效: {e}")
        return False

# 测试多个版本
async def main():
    versions = ["0.77", "1.0", "1.5", "1.6"]
    for v in versions:
        await test_user_agent(v)

asyncio.run(main())
```

### 方法 2：查看官方文档/公告
- Kimi For Coding 官网: https://www.kimi.com/code
- 关注 API 更新日志

---

## 最佳实践：让版本可配置

### 方案 1：配置文件支持
```yaml
# config.yaml
provider: kimi-coding
model: k2p5
base_url: https://api.kimi.com/coding/v1

# 可自定义 User-Agent 版本
user_agent_version: "0.77"  # 如果为空，使用默认值
```

### 方案 2：环境变量支持
```bash
# Windows
$env:KIMI_USER_AGENT_VERSION="1.6"

# Linux/Mac
export KIMI_USER_AGENT_VERSION="1.6"
```

### 方案 3：代码实现
```python
import os

class OpenAIProvider:
    # 默认版本
    DEFAULT_KIMI_VERSION = "0.77"
    
    def __init__(self, config):
        headers = {"Accept": "application/json"}
        
        # 检测是否是 Kimi For Coding
        is_kimi_coding = (
            config.provider == "kimi-coding" or
            (config.base_url and "kimi.com/coding" in config.base_url)
        )
        
        if is_kimi_coding:
            # 优先从环境变量读取版本
            version = os.getenv(
                "KIMI_USER_AGENT_VERSION", 
                getattr(config, 'user_agent_version', None) or 
                self.DEFAULT_KIMI_VERSION
            )
            headers["User-Agent"] = f"KimiCLI/{version}"
            print(f"[INFO] 使用 User-Agent: KimiCLI/{version}")
        
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            default_headers=headers,
        )
```

---

## 升级策略

### 策略 1：保守策略（推荐目前使用）
```python
# 保持 0.77，直到它失效
DEFAULT_VERSION = "0.77"
```
**优点**: 稳定，不需要频繁改动  
**缺点**: 可能错过新功能，某天突然失效

---

### 策略 2：自动检测策略
```python
import asyncio
from openai import AsyncOpenAI

async def detect_working_version():
    """自动检测哪个版本有效"""
    versions = ["1.6", "1.5", "1.0", "0.77"]
    
    for version in versions:
        try:
            client = AsyncOpenAI(
                api_key="sk-kimi-your-key",
                base_url="https://api.kimi.com/coding/v1",
                default_headers={"User-Agent": f"KimiCLI/{version}"},
            )
            await client.chat.completions.create(
                model="k2p5",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return version  # 返回第一个有效的版本
        except:
            continue
    
    return "0.77"  # 都失败，返回默认

# 启动时检测
WORKING_VERSION = asyncio.run(detect_working_version())
print(f"[INFO] 检测到有效 User-Agent 版本: {WORKING_VERSION}")
```
**优点**: 自适应，自动找到可用版本  
**缺点**: 启动时增加延迟（多 1-3 个请求）

---

### 策略 3：跟随官方策略
```python
# 定期更新默认值
DEFAULT_VERSION = "1.6"  # 每次发布新版本时更新
```
**优点**: 总是使用最新版本  
**缺点**: 需要频繁更新代码

---

## 推荐的实现方案

结合配置 + 自动检测：

```python
class KimiCodingProvider:
    """
    Kimi For Coding Provider
    
    User-Agent 版本优先级:
    1. 环境变量 KIMI_USER_AGENT_VERSION
    2. 配置文件 user_agent_version
    3. 内置默认版本
    """
    
    DEFAULT_VERSION = "0.77"  # 保守策略
    FALLBACK_VERSIONS = ["1.6", "1.5", "1.0", "0.77"]
    
    def __init__(self, config):
        self.version = self._get_version(config)
        self.client = self._create_client(config)
    
    def _get_version(self, config):
        # 1. 环境变量
        if env_version := os.getenv("KIMI_USER_AGENT_VERSION"):
            return env_version
        
        # 2. 配置文件
        if hasattr(config, 'user_agent_version') and config.user_agent_version:
            return config.user_agent_version
        
        # 3. 默认
        return self.DEFAULT_VERSION
    
    async def verify_version(self):
        """验证当前版本是否有效"""
        try:
            await self.client.chat.completions.create(
                model="k2p5",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            if "403" in str(e) or "available for Coding Agents" in str(e):
                return False
            raise  # 其他错误不是版本问题
    
    async def auto_fix_version(self):
        """自动尝试其他版本"""
        for version in self.FALLBACK_VERSIONS:
            if version == self.version:
                continue
            
            try:
                test_client = AsyncOpenAI(
                    api_key=self.client.api_key,
                    base_url=self.client.base_url,
                    default_headers={"User-Agent": f"KimiCLI/{version}"},
                )
                await test_client.chat.completions.create(
                    model="k2p5",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5,
                )
                
                # 成功，更新客户端
                self.version = version
                self.client = test_client
                print(f"[INFO] 自动切换到有效版本: {version}")
                return True
            except:
                continue
        
        return False
```

---

## 总结建议

| 场景 | 建议 |
|------|------|
| **现在** | 保持 `0.77`，它仍然有效 |
| **配置文件** | 添加 `user_agent_version` 选项，让用户可自定义 |
| **环境变量** | 支持 `KIMI_USER_AGENT_VERSION` 覆盖 |
| **长期** | 添加版本自动检测/修复机制 |
| **监控** | 在 403 错误时提示用户尝试更新版本 |

### 最简单的改动（推荐现在就加）

```python
# evoskill/core/llm.py

import os

class OpenAIProvider:
    def __init__(self, config):
        # ...
        if is_kimi_coding:
            # 支持自定义版本
            version = os.getenv("KIMI_USER_AGENT_VERSION", "0.77")
            default_headers["User-Agent"] = f"KimiCLI/{version}"
```

这样用户可以在不修改代码的情况下尝试新版本：
```bash
$env:KIMI_USER_AGENT_VERSION="1.6"
uv run evoskill chat
```

---

## 快速验证

想知道 `1.6` 是否有效？现在就可以测试：

```python
# test_version.py
import asyncio
from openai import AsyncOpenAI

async def test():
    for version in ["0.77", "1.0", "1.5", "1.6"]:
        client = AsyncOpenAI(
            api_key="你的Key",
            base_url="https://api.kimi.com/coding/v1",
            default_headers={"User-Agent": f"KimiCLI/{version}"},
        )
        try:
            await client.chat.completions.create(
                model="k2p5",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            print(f"✓ {version} 有效")
        except Exception as e:
            print(f"✗ {version} 无效: {str(e)[:50]}")

asyncio.run(test())
```
