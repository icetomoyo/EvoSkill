# EvoSkill Coding Agent 设计文档

## 架构概览

Coding Agent 是一个自主的软件开发代理，模拟人类开发者的完整开发流程。

```
┌─────────────────────────────────────────────────────────────┐
│                    Coding Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: SkillDesign (需求)                                  │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Planner   │───▶│    Coder    │───▶│   Tester    │     │
│  │   (规划)    │    │   (编码)    │    │   (测试)    │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                                 │           │
│                    ┌─────────────┐             │           │
│                    │  Reflector  │◀────────────┘           │
│                    │  (反思修复) │                          │
│                    └──────┬──────┘                          │
│                           │                                │
│                           └──────────────┐                 │
│                                          ▼                 │
│                                    ┌─────────────┐         │
│                                    │   测试通过? │         │
│                                    └──────┬──────┘         │
│                                           │                │
│            ┌──────────────────────────────┴──────────────┐│
│            │ 否 (继续迭代)                              │是│
│            ▼                                             │  │
│       (最多3轮)                                          ▼  │
│                                                 ┌─────────┐│
│                                                 │ Output  ││
│                                                 │ 交付    ││
│                                                 └─────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Planner (技术规划)
**职责**: 分析需求并制定技术实现方案

**输入**: 
- SkillDesign (工具设计)

**输出**:
- 需求分析
- 技术方案
- 推荐的 API 和服务
- 实现步骤
- 风险提示

**Prompt 示例**:
```
你是一位经验丰富的 Python 开发者。
请为以下 Skill 制定技术实现方案...
返回 JSON 格式: {analysis, approach, apis, dependencies, steps, risks}
```

### 2. Coder (代码生成)
**职责**: 根据规划编写完整可运行的代码

**生成内容**:
- `main.py` - 主程序代码
- `SKILL.md` - 文档和配置指南
- `tests/test_main.py` - 单元测试

**关键要求**:
- 使用 Python 标准库优先
- 外部 API 从环境变量读取 Key
- 完整的错误处理
- 标准返回格式: `{"success": bool, "result": any}` 或 `{"success": false, "error": str}`

### 3. Tester (测试验证)
**职责**: 自动检查代码质量

**检查项**:
1. **语法检查** - AST 解析
2. **元数据检查** - SKILL_NAME, SKILL_TOOLS 等
3. **函数完整性** - 工具函数是否存在
4. **错误处理** - try/except 检查
5. **API Key 处理** - 环境变量读取

**输出**: 
```python
{
    "passed": bool,
    "errors": ["错误列表"],
    "warnings": ["警告列表"]
}
```

### 4. Reflector (反思修复)
**职责**: 分析测试失败原因并修复代码

**工作流程**:
1. 接收测试错误和警告
2. 分析根本原因
3. 生成修复后的代码
4. 重新提交测试

**Prompt 示例**:
```
请修复以下 Python 代码中的问题...

错误:
- 语法错误: ...
- 缺少错误处理

请直接返回修复后的完整 main.py 代码。
```

## 迭代机制

Coding Agent 使用 **测试驱动修复** 循环:

```
初始代码 → 测试 → 发现问题 → 反思修复 → 测试 → ... → 通过/超时
```

**配置**:
- `max_iterations = 3` - 最大反思迭代次数
- 超时后即使未通过也返回最佳版本

## API 发现集成

Coding Agent 集成 `ApiDiscovery` 模块，为 Skill 推荐合适的公共 API:

| 类别 | 推荐 API | 免费额度 |
|------|---------|---------|
| Weather | OpenWeatherMap | 1000次/天 |
| Weather | 和风天气 | 1000次/天 |
| Search | Bing Search | 1000次/月 |
| Translate | Google Translate | 50万字符/月 |
| News | NewsAPI | 100次/天 |

**生成的配置指南包括**:
- 注册链接
- API Key 获取步骤
- 环境变量配置命令
- 免费额度说明

## 与旧 Generator 对比

| 特性 | 旧 Generator | Coding Agent |
|------|-------------|--------------|
| 代码生成 | 硬编码模板 | LLM 智能生成 |
| 错误处理 | 固定模式 | 上下文感知 |
| API 推荐 | 无 | 智能推荐 + 配置指南 |
| 代码质量 | 不可变 | 可迭代优化 |
| 测试验证 | 简单语法检查 | 多维度验证 |
| 自我修复 | 无 | 自动反思修复 |
| 灵活性 | 低 | 高 |

## 使用示例

```python
from evoskill.coding_agent import CodingAgent
from evoskill.evolution.designer import SkillDesign, ToolDesign

# 创建 Agent
agent = CodingAgent(llm_provider)

# 定义 Skill
design = SkillDesign(
    name="weather_query",
    description="查询天气",
    tools=[
        ToolDesign(
            name="get_weather",
            description="获取城市天气",
            parameters={"city": ParameterSchema(...)},
            ...
        )
    ]
)

# 开发
result = await agent.develop(design)

# 使用结果
print(result.main_py)      # 生成的代码
print(result.skill_md)     # 生成的文档
print(result.iterations)   # 迭代次数
```

## 未来扩展

1. **Code Reviewer** - 添加代码审查环节
2. **Security Scanner** - 安全检查
3. **Performance Optimizer** - 性能优化建议
4. **Documentation Generator** - 自动生成 API 文档
5. **Multi-language Support** - 支持其他编程语言
