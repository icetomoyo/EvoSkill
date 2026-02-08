# Koda 架构设计

## 概述

Koda (KOding Agent) 是一个自主编程代理框架，对标 Pi Agent、Devin 等代码生成框架�?

核心设计理念�?*像人类开发者一样思考和编码**

```
需�?�?规划 �?编码 �?测试 �?反�?�?修复 �?交付
```

## 架构�?

```
┌─────────────────────────────────────────────────────────────────────────�?
�?                               Koda                                      �?
├─────────────────────────────────────────────────────────────────────────�?
�?                                                                         �?
�? ┌─────────────────────────────────────────────────────────────────�?   �?
�? �?                       KodaAgent (Orchestrator)                  �?   �?
�? �? ┌──────────�? ┌──────────�? ┌──────────�? ┌──────────�?        �?   �?
�? �? �? Planner │→�?Executor │→�?Validator│→�?Reflector�?        �?   �?
�? �? �?         �? �?         �? �?         �? �?         �?        �?   �?
�? �? �?- Analyze�? �?- Generate�?�?- Syntax �? �?- Review �?        �?   �?
�? �? �?- Plan   �? �?- Execute �?�?- Check  �? �?- Fix    �?        �?   �?
�? �? �?- APIs   �? �?- Create  �?�?- Score  �? �?- Improve�?        �?   �?
�? �? └──────────�? └──────────�? └──────────�? └──────────�?        �?   �?
�? �?                                                                 �?   �?
�? �? Iteration Loop (max 3 rounds)                                   �?   �?
�? └─────────────────────────────────────────────────────────────────�?   �?
�?                                                                         �?
�? ┌─────────────────────────────────────────────────────────────────�?   �?
�? �?                           Core Types                            �?   �?
�? �?                                                                 �?   �?
�? �? �?Task        - 编程任务定义                                    �?   �?
�? �? �?Plan        - 执行计划                                        �?   �?
�? �? �?Step        - 执行步骤                                        �?   �?
�? �? �?CodeArtifact   - 代码产物                                     �?   �?
�? �? �?ExecutionResult - 执行结果                                    �?   �?
�? �? �?ReflectionResult- 反思结�?                                   �?   �?
�? �? �?ValidationReport- 验证报告                                    �?   �?
�? └─────────────────────────────────────────────────────────────────�?   �?
�?                                                                         �?
�? ┌─────────────────────────────────────────────────────────────────�?   �?
�? �?                         Adapters                                �?   �?
�? �?                                                                 �?   �?
�? �? �?BaseLLMAdapter - LLM 适配器基�?                             �?   �?
�? �? �?OpenAIAdapter  - OpenAI 适配�?(TODO)                        �?   �?
�? �? �?ClaudeAdapter  - Claude 适配�?(TODO)                        �?   �?
�? └─────────────────────────────────────────────────────────────────�?   �?
�?                                                                         �?
�? ┌─────────────────────────────────────────────────────────────────�?   �?
�? �?                          Tools                                  �?   �?
�? �?                                                                 �?   �?
�? �? �?FileTool    - 文件操作                                        �?   �?
�? �? �?SearchTool  - 网络搜索 (TODO)                                 �?   �?
�? �? �?TestTool    - 测试执行 (TODO)                                 �?   �?
�? └─────────────────────────────────────────────────────────────────�?   �?
�?                                                                         �?
└─────────────────────────────────────────────────────────────────────────�?
```

## 核心组件

### 1. PiAgent

**职责**: 协调整个开发流�?

**工作流程**:
```
execute(task)
  �?
plan = planner.create_plan(task)
  �?
for iteration in max_iterations:
    result = executor.execute(plan, task)
    report = validator.validate(result)
    
    if report.passed:
        return success
    
    reflection = reflector.reflect(result, report)
    if reflection.can_fix:
        plan = update_plan(plan, reflection)
  �?
return best_result
```

### 2. Planner

**职责**: 需求分析和技术规�?

**输入**: Task
**输出**: Plan

**关键方法**:
- `analyze_task()` - 需求分�?
- `discover_apis()` - API 发现
- `generate_steps()` - 生成执行步骤

### 3. Executor

**职责**: 代码生成

**输入**: Plan, Task
**输出**: ExecutionResult (包含 CodeArtifact 列表)

**生成产物**:
- `main.py` - 主程�?
- `README.md` - 文档
- `test_main.py` - 测试

### 4. Validator

**职责**: 代码质量验证

**检查项**:
- Syntax - 语法正确�?
- Structure - 代码结构完整�?
- Imports - 导入语句
- Error Handling - 错误处理
- Documentation - 文档字符�?

**输出**: ValidationReport (含分�?0-100)

### 5. Reflector

**职责**: 代码审查和改�?

**功能**:
- Static Analysis - 静态代码分�?
- LLM Review - LLM 深度审查
- Auto Fix - 自动生成修复代码

## �?EvoSkill 集成

```
EvoSkill
  └── SkillEvolutionEngine
        └── SkillGenerator
              └── PiCodingAdapter
                    └── PiAgent (from koda)
```

**集成�?*:
- `PiCodingAdapter` �?EvoSkill �?`SkillDesign` 转换�?Pi Coding �?`Task`
- `EvoSkillLLMAdapter` �?EvoSkill �?LLM 适配�?Pi Coding 的接�?
- 生成�?`CodeArtifact` 转换�?EvoSkill 的文件格�?

## 扩展�?

### 添加新的 LLM 适配�?

```python
from koda.adapters.base import BaseLLMAdapter

class ClaudeAdapter(BaseLLMAdapter):
    async def complete(self, prompt: str, **kwargs) -> str:
        # 调用 Claude API
        return response
```

### 添加新的工具

```python
from koda.core.types import ToolDefinition

def my_tool(param: str) -> str:
    return f"Result: {param}"

agent.add_tool(ToolDefinition(
    name="my_tool",
    description="My custom tool",
    parameters={"param": {"type": "string"}},
    handler=my_tool,
))
```

### 自定义验证规�?

```python
class CustomValidator(Validator):
    async def _check_custom(self, code: str) -> Dict[str, Any]:
        # 自定义检查逻辑
        return {"name": "custom", "type": "info", "message": "OK"}
```

## 对标 Pi Agent

| 特�?| Pi Agent | Koda (本项�? |
|------|----------|-------------------|
| 架构 | Planner-Executor-Validator | 相同 |
| 代码迭代 | 支持 | 支持 (max 3 rounds) |
| API 发现 | 支持 | 支持 (内置 10+ APIs) |
| 多语言 | 支持 | 当前�?Python |
| LLM 支持 | OpenAI | 任何 (Adapter 模式) |
| 工具系统 | 支持 | 基础支持 |
| 部署 | 云服�?| 本地/嵌入 |

## 未来规划

1. **更多 LLM 支持** - Claude、Gemini、本地模�?
2. **多语言生成** - JavaScript、Go、Rust
3. **高级工具** - 数据库、Web 框架集成
4. **代码解释�?* - 执行生成的代码进行验�?
5. **协作模式** - �?Agent 协作开�?
