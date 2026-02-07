# Skill 自我进化系统设计

> EvoSkill 核心特色：AI 自动创建和进化工具能力

## 核心概念

### 什么是 Skill 自我进化？

当用户提出需求时，系统能：
1. **分析需求** - 理解用户想要什么
2. **匹配现有 Skills** - 检查是否已有工具能满足
3. **决策** - 使用现有 / 修改现有 / 创建新 Skill
4. **自动生成** - 创建 SKILL.md + main.py + 测试
5. **验证** - 自动运行测试确保可用
6. **集成** - 立即可用，无需重启

### 进化触发条件

```
用户请求 → 分析需求
    ↓
现有 Skills 能完成？ → 直接使用
    ↓ 否
类似 Skill 存在？ → 修改/扩展
    ↓ 否
创建全新 Skill → 生成代码 → 验证 → 集成
```

## 系统设计

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    SkillEvolutionEngine                  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Analyzer   │→ │   Designer   │→ │   Generator  │  │
│  │   需求分析    │  │   Skill设计   │  │   代码生成    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↓                   ↓                ↓          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Matcher   │  │   Validator  │  │   Integrator │  │
│  │   技能匹配    │  │   自动验证    │  │   系统集成    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 核心类设计

```python
class SkillEvolutionEngine:
    """Skill 进化引擎"""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        skills_dir: Path,
    ):
        self.analyzer = NeedAnalyzer(llm_provider)
        self.matcher = SkillMatcher()
        self.designer = SkillDesigner(llm_provider)
        self.generator = SkillGenerator(llm_provider)
        self.validator = SkillValidator()
        self.integrator = SkillIntegrator(skills_dir)
    
    async def evolve(self, user_request: str) -> EvolutionResult:
        """
        执行进化流程
        
        步骤:
        1. 分析需求
        2. 匹配现有 Skills
        3. 决策并执行
        4. 验证和集成
        """
        pass

@dataclass
class EvolutionResult:
    """进化结果"""
    status: str  # "created", "modified", "reused", "failed"
    skill_name: str
    skill_path: Path
    message: str
    validation_result: Optional[ValidationResult]
```

## 详细流程

### 步骤 1：需求分析 (NeedAnalyzer)

**输入**: 用户自然语言请求
**输出**: 结构化需求描述

```python
@dataclass
class NeedAnalysis:
    """需求分析结果"""
    intent: str           # 用户意图
    domain: str          # 领域（文件操作、网络、数据处理等）
    required_tools: List[str]  # 需要的工具能力
    complexity: str      # 复杂度（simple/medium/complex）
    can_use_existing: bool     # 是否能用现有工具
```

**分析 Prompt**:
```
分析用户的需求，提取以下信息：
1. 用户想做什么？（意图）
2. 属于什么领域？（文件、网络、数据、系统等）
3. 需要什么能力？（读取、写入、计算、搜索等）
4. 复杂度如何？

用户请求: {user_request}

可用 Skills: {existing_skills}

输出格式（JSON）:
{
    "intent": "...",
    "domain": "...",
    "required_tools": ["..."],
    "complexity": "simple|medium|complex",
    "can_use_existing": true|false
}
```

### 步骤 2：Skill 匹配 (SkillMatcher)

**目标**: 找到最匹配的现有 Skill

**匹配策略**:
1. **精确匹配** - 工具名称或描述完全匹配
2. **语义匹配** - 使用 embedding 计算相似度
3. **能力匹配** - 检查工具参数是否能满足需求

```python
class SkillMatcher:
    def find_best_match(
        self,
        need: NeedAnalysis,
        existing_skills: List[Skill],
    ) -> Optional[MatchResult]:
        """
        找到最佳匹配的 Skill
        
        Returns:
            MatchResult 或 None（没有匹配）
        """
        pass
```

### 步骤 3：Skill 设计 (SkillDesigner)

当需要创建新 Skill 时，设计其结构：

```python
@dataclass
class SkillDesign:
    """Skill 设计"""
    name: str                    # Skill 名称
    description: str            # 描述
    version: str                # 版本
    tools: List[ToolDesign]     # 工具列表
    dependencies: List[str]     # 依赖包
    examples: List[Example]     # 使用示例

@dataclass
class ToolDesign:
    """工具设计"""
    name: str
    description: str
    parameters: Dict[str, ParameterSchema]
    returns: str
    errors: List[str]
```

**设计 Prompt**:
```
根据用户需求设计一个 Skill。

需求: {user_request}
领域: {domain}

设计一个 Python 函数，要求：
1. 函数名称简洁明了
2. 参数设计合理
3. 有完整的错误处理
4. 包含文档字符串

输出格式（JSON）:
{
    "name": "skill_name",
    "description": "...",
    "tools": [
        {
            "name": "tool_name",
            "description": "...",
            "parameters": {...}
        }
    ]
}
```

### 步骤 4：代码生成 (SkillGenerator)

生成完整的 Skill 文件：

**生成文件结构**:
```
skills/
└── {skill_name}/
    ├── SKILL.md           # Skill 元数据和说明
    ├── main.py            # 主要实现
    └── tests/
        └── test_main.py   # 单元测试
```

**SKILL.md 模板**:
```markdown
# {skill_name}

## 描述
{description}

## 版本
{version}

## 工具

### {tool_name}
{tool_description}

**参数**:
- `param1` (string, required): 参数说明
- `param2` (int, optional): 参数说明

**返回值**:
{returns_description}

**错误处理**:
- Error 1: 说明
- Error 2: 说明

## 示例

### 示例 1: 基本用法
```python
result = {tool_name}(arg1="value")
```

## 依赖
{dependencies}
```

**main.py 模板**:
```python
"""
{skill_description}
"""
import asyncio
from typing import Optional, Dict, Any


async def {tool_name}(
    {parameters}
) -> Dict[str, Any]:
    """
    {tool_description}
    
    Args:
        {param_docs}
    
    Returns:
        {return_doc}
    
    Raises:
        {error_docs}
    """
    try:
        # 实现逻辑
        {implementation}
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# 注册信息
SKILL_NAME = "{skill_name}"
SKILL_VERSION = "{version}"
SKILL_TOOLS = [
    {
        "name": "{tool_name}",
        "description": "{tool_description}",
        "handler": {tool_name},
    }
]
```

### 步骤 5：自动验证 (SkillValidator)

```python
class SkillValidator:
    """Skill 验证器"""
    
    async def validate(self, skill_path: Path) -> ValidationResult:
        """
        验证 Skill 是否可用
        
        检查项:
        1. 文件结构完整
        2. 语法正确（可导入）
        3. 单元测试通过
        4. 工具可调用
        """
        pass

@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    test_results: List[TestResult]
```

### 步骤 6：系统集成 (SkillIntegrator)

```python
class SkillIntegrator:
    """Skill 集成器"""
    
    def integrate(self, skill_path: Path) -> bool:
        """
        将 Skill 集成到系统中
        
        步骤:
        1. 加载 Skill
        2. 注册工具到 Session
        3. 添加到可用 Skills 列表
        """
        pass
```

## 用户交互流程

### 场景 1：创建新 Skill

```
用户: 创建一个工具，能查询当前天气

AI: 检测到需求：查询天气
    现有 Skills 无法满足
    正在创建 weather 技能...
    
    [生成代码]
    ✓ SKILL.md 创建完成
    ✓ main.py 创建完成
    ✓ test_main.py 创建完成
    
    [自动验证]
    ✓ 语法检查通过
    ✓ 单元测试通过
    
    [集成]
    ✓ weather 技能已激活
    
    weather 技能创建完成！
    现在你可以使用：查询北京的天气
```

### 场景 2：修改现有 Skill

```
用户: 天气工具能不能查询未来 7 天的预报？

AI: 检测到 weather 技能已存在
    正在添加 forecast 工具...
    
    [修改代码]
    ✓ 添加 get_forecast 函数
    ✓ 更新 SKILL.md
    
    [验证]
    ✓ 测试通过
    
    weather 技能已更新！
    现在支持：查询天气 和 7 天预报
```

### 场景 3：使用现有 Skill

```
用户: 帮我读取 README.md

AI: 使用 read_file 工具（已存在）
    [执行工具]
    ...
```

## 实现计划

### 阶段 1：基础框架（第 1 天）
- [ ] 创建 `SkillEvolutionEngine` 类
- [ ] 实现 `NeedAnalyzer`
- [ ] 实现 `SkillMatcher`

### 阶段 2：生成能力（第 2-3 天）
- [ ] 实现 `SkillDesigner`
- [ ] 实现 `SkillGenerator`
- [ ] 完善 Prompts

### 阶段 3：验证与集成（第 4 天）
- [ ] 实现 `SkillValidator`
- [ ] 实现 `SkillIntegrator`
- [ ] 无重启加载

### 阶段 4：CLI 集成（第 5 天）
- [ ] `/create` 命令完善
- [ ] 进化过程可视化
- [ ] 测试和修复

## 关键技术点

### 1. 提示词工程
- 需要高质量的 prompts 来生成可用代码
- 使用 few-shot 示例
- 迭代优化 prompts

### 2. 代码生成质量
- 生成的代码必须有错误处理
- 必须有类型注解
- 必须有文档字符串

### 3. 安全考虑
- 验证生成的代码（沙箱执行）
- 限制 Skill 的权限
- 用户确认机制

### 4. 版本管理
- Skill 版本控制
- 回滚机制
- 依赖管理

## 成功标准

- [ ] 用户能用自然语言描述创建 Skill
- [ ] 生成的 Skill 无需手动修改即可使用
- [ ] Skill 创建后立即可用（无需重启）
- [ ] 能够修改/扩展现有 Skills
- [ ] 自动验证通过率 > 80%

---

**下一步**: 开始实现 `SkillEvolutionEngine` 基础框架
