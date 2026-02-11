# Koda - Pi-Mono Python Implementation

Koda 是 [Pi-Mono](https://github.com/pi-mono/pi-mono) 的 Python 实现，提供 AI Agent、Coding Agent 和 Mom (Slack Bot) 功能。

## 项目状态

| 模块 | 完成度 | 状态 |
|------|--------|------|
| AI Core | 85% | 核心Provider、模型数据库、OAuth ✅ |
| Agent | 90% | 核心Agent、事件循环、并行处理 ✅ |
| Coding | 75% | 工具、会话、压缩、CLI ✅ |
| Mom | 40% | 基础功能，Slack Bot待实现 ⏳ |

**总体完成度: 80%**

## 快速开始

```python
# 使用AI模型
from koda.ai.models import get_model, calculate_cost

model = get_model('openai', 'gpt-4o')
cost = calculate_cost(model, Usage(input=1000, output=500))

# 使用Coding工具
from koda.coding.tools import FileTool, ShellTool

file_tool = FileTool()
content = await file_tool.read("README.md")
```

## 模块说明

### koda.ai - AI Provider模块
- **models/** - 模型数据库（70+模型，9个Provider）
- **providers/** - Provider实现（OpenAI、Anthropic、Google等）
- **providers/oauth/** - OAuth认证
- **cli.py** - AI CLI工具

### koda.agent - Agent模块
- **agent.py** - Agent核心
- **loop.py** - 事件循环
- **parallel.py** - 并行执行
- **events.py** - 事件系统

### koda.coding - Coding Agent模块
- **core/** - 核心功能（事件总线、诊断、压缩）
- **tools/** - 工具集（文件、编辑、Shell、搜索）
- **cli/** - CLI选择器（配置、会话、模型）
- **modes/** - 运行模式（交互、打印、RPC）

### koda.mom - Mom模块（Slack Bot）
- **store.py** - 存储
- **context.py** - 上下文
- **sandbox.py** - 沙箱
- ⚠️ Slack Bot功能待实现

### koda.mes - 消息处理
- 消息压缩、历史管理、格式化

## 与Pi-Mono的差异

| 方面 | Pi-Mono (TS) | Koda (Python) |
|------|--------------|---------------|
| 模型定义 | `models.generated.ts` | `ai/models/generated.py` |
| OAuth位置 | `ai/utils/oauth/` | `ai/providers/oauth/` |
| 压缩功能 | `core/compaction/` | `mes/` + `core/compaction/` |
| 编辑工具 | 单文件 | 多文件拆分 |

## 文档

- [ARCHITECTURE.md](ARCHITECTURE.md) - 架构设计
- [PI_MONO_PARITY.md](PI_MONO_PARITY.md) - Pi-Mono对比和完成度
- [API_REFERENCE.md](API_REFERENCE.md) - API参考

## 待实现功能

### P0 (关键)
- [ ] Mom Slack Bot (`mom/agent.py`, `mom/slack.py`)
- [ ] Coding SDK完整接口 (`coding/sdk.py`)

### P1 (重要)
- [ ] 扩展加载器 (`extensions/loader.py`)
- [ ] 诊断系统完善
- [ ] TUI交互组件

### P2 (可选)
- [ ] HTML导出完整版
- [ ] 图片剪贴板
- [ ] 各种辅助工具

## 开发

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 使用AI CLI
python -m koda.ai.cli login
python -m koda.ai.cli models
```

## License

MIT
