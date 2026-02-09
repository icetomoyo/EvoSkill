# EvoSkill 设计文档总结

> 完整梳理系统架构、集成方案与演进路线

---

## 一、系统架构总览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  CLI / Web   │  │   API 服务   │  │   IDE 插件           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    EvoSkill Core (高层编排)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  IntegratedSession - 集成会话 (Session + Koda)           │   │
│  │  - /skills        - 查询可用 Skills                      │   │
│  │  - /create        - 创建新 Skill                         │   │
│  │  - /evolve        - 进化现有 Skill                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SkillEvolutionEngine - Skill 进化引擎                   │   │
│  │  - Analyzer   - 需求分析                                 │   │
│  │  - Designer   - Skill 设计                               │   │
│  │  - Generator  - 代码生成                                 │   │
│  │  - Validator  - 自动验证                                 │   │
│  │  - Integrator - 系统集成                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       Koda (底层执行)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Agent V2    │  │   7 Tools    │  │  Validation System   │  │
│  │  - Execute   │  │  (Pi compat) │  │  - Validator         │  │
│  │  - Validate  │  │              │  │  - Reflector         │  │
│  │  - Reflect   │  │              │  │  - Auto-fix          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件关系

```
User Input
    │
    ▼
IntegratedSession.prompt()
    │
    ├── /commands ────────► SkillRegistry
    │   (/skills, /create, /evolve)
    │
    ├── Code Tasks ───────► KodaAdapterV2 ───────► Agent V2
    │   (read/write/edit/...)                         │
    │                                                 ▼
    │                                            7 Tools
    │
    └── Evolution ────────► SkillEvolutionEngine
        (auto skill creation)
```

---

## 二、关键设计决策

### 2.1 为什么采用双层架构？

**EvoSkill Core + Koda**

| 优势 | 说明 |
|------|------|
| **关注点分离** | EvoSkill 负责业务逻辑，Koda 负责代码执行 |
| **独立使用** | Koda 可单独作为 Coding Agent |
| **生态兼容** | 100% Pi Coding Agent 工具兼容 |
| **可测试性** | 每层可独立测试 |

### 2.2 为什么选择 Pi 兼容性？

Pi Agent 是工业级 Coding Agent 的标杆：

- ✅ 工具设计经过生产验证
- ✅ 7 个核心工具覆盖 95% 编码场景
- ✅ 优秀的提示词工程实践
- ✅ 稳定的沙箱执行模型

**EvoSkill 在 Pi 基础上增加**：
- 验证系统 (Validator + Reflector)
- Skill 自我进化能力
- 更灵活的配置选项

### 2.3 验证系统的设计权衡

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Pi 模式 (无验证)** | 简单快速 | 依赖 LLM 自我纠错，弱 LLM 下效果差 |
| **Koda 验证 (强制)** | 质量有保障 | 增加复杂度，可能过度设计 |
| **Koda 验证 (可选)** | 按需启用 | 需要配置管理 |

**决策**: 采用可选验证 (off/static/full 三档)

### 2.4 Skill 进化的触发策略

```
触发条件:
1. 显式触发: 用户说 "创建一个能...的 Skill"
2. 自动识别: LLM 判断现有 Skills 无法满足需求
3. 失败补偿: 任务执行失败时，分析是否需要新 Skill

决策流程:
User Request
    │
    ▼
NeedAnalyzer
    │
    ├── 现有 Skill 可完成? ──► 直接使用
    │
    ├── 类似 Skill 存在? ───► 修改/扩展
    │
    └── 全新需求 ───────────► 创建新 Skill
```

---

## 三、数据流设计

### 3.1 标准执行流程

```
[User] "读取 README.md"
    │
    ▼
[IntegratedSession]
    │
    ├── 1. 添加到消息历史
    │   UserMessage(content="读取 README.md")
    │
    ├── 2. 判断使用 Koda (包含文件操作关键词)
    │
    ├── 3. 调用 KodaAdapterV2.execute()
    │       Task: "读取 README.md"
    │
    ├── 4. Agent V2 规划
    │       Plan: [read_file("README.md")]
    │
    ├── 5. 执行 read_file 工具
    │       Result: "# EvoSkill\n..."
    │
    ├── 6. 验证 (可选)
    │       Validator.check(result)
    │
    └── 7. 返回结果
            AssistantMessage(content="README.md 内容是...")
```

### 3.2 Skill 创建流程

```
[User] "/create 查询天气的工具"
    │
    ▼
[IntegratedSession._create_skill()]
    │
    ├── 1. Analyze
    │   NeedAnalyzer → intent=weather_query
    │
    ├── 2. Check existing
    │   SkillMatcher → no match
    │
    ├── 3. Design
    │   SkillDesigner → weather skill with get_weather()
    │
    ├── 4. Generate
    │   Generator.create_files()
    │   - skills/weather/SKILL.md
    │   - skills/weather/main.py
    │   - skills/weather/tests/test_main.py
    │
    ├── 5. Validate
    │   SkillValidator.run_tests() → passed
    │
    ├── 6. Integrate
    │   SkillIntegrator.register() → hot reload
    │
    └── 7. Response
        "weather skill created and activated!"
```

### 3.3 Skill 进化流程

```
[User] "时间工具能显示 UTC 吗？"
    │
    ▼
[IntegratedSession._evolve_skill()]
    │
    ├── 1. Load existing
    │   time_tool v1.0.0
    │
    ├── 2. Analyze request
    │   Add UTC timezone support
    │
    ├── 3. Modify code
    │   - Add timezone parameter
    │   - Update SKILL.md
    │   - Add tests
    │
    ├── 4. Validate
    │   - Backward compatibility
    │   - Tests pass
    │
    ├── 5. Update
    │   Hot reload → v1.1.0
    │
    └── 6. Response
        "time_tool evolved to v1.1.0!"
```

---

## 四、接口定义

### 4.1 KodaAdapterV2

```python
class KodaAdapterV2:
    """EvoSkill 与 Koda 的适配器"""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        workspace: Path,
    ):
        self.agent = AgentV2(llm, workspace)
    
    async def execute(
        self,
        task: str,
        context: Optional[List[Message]] = None,
    ) -> KodaExecutionResult:
        """执行任务"""
        pass
```

### 4.2 IntegratedSession

```python
class IntegratedSession(AgentSession):
    """集成会话 - 支持 Skill 管理"""
    
    async def prompt(self, user_input: str) -> AsyncIterator[Event]:
        """处理用户输入"""
        # 支持:
        # - 普通对话
        # - /skills, /create, /evolve 命令
        # - 代码任务 (自动使用 Koda)
        pass
    
    def _list_available_skills(self) -> str:
        """列出可用 Skills"""
        pass
    
    async def _create_skill(self, description: str) -> AsyncIterator[Event]:
        """创建新 Skill"""
        pass
    
    async def _evolve_skill(self, name: str, request: str) -> AsyncIterator[Event]:
        """进化现有 Skill"""
        pass
```

### 4.3 SkillEvolutionEngine

```python
class SkillEvolutionEngine:
    """Skill 进化引擎"""
    
    async def analyze(self, request: str) -> NeedAnalysis:
        """分析需求"""
        pass
    
    async def design(self, analysis: NeedAnalysis) -> SkillDesign:
        """设计 Skill"""
        pass
    
    async def generate(self, design: SkillDesign) -> GeneratedSkill:
        """生成代码"""
        pass
    
    async def validate(self, skill: GeneratedSkill) -> ValidationResult:
        """验证 Skill"""
        pass
    
    async def integrate(self, skill: GeneratedSkill) -> Skill:
        """集成到系统"""
        pass
```

---

## 五、文件组织

```
evoskill/
├── core/
│   ├── integrated_session.py    # 集成会话 (新增)
│   ├── session.py               # 基础会话
│   ├── types.py                 # 类型定义
│   ├── llm.py                   # LLM 接口
│   └── events.py                # 事件系统
├── coding_agent/
│   ├── koda_adapter_v2.py       # Koda 适配器 V2 (新增)
│   └── koda_adapter.py          # 旧适配器
├── evolution/
│   ├── engine.py                # 进化引擎
│   ├── analyzer.py              # 需求分析
│   ├── designer.py              # Skill 设计
│   ├── generator.py             # 代码生成
│   ├── validator.py             # 验证器
│   └── integrator.py            # 集成器
└── skills/
    └── loader.py                # Skill 加载器

koda/
├── core/
│   ├── agent_v2.py              # Agent V2 实现
│   ├── validator.py             # 验证器
│   ├── reflector.py             # 反思器
│   └── tools/                   # 7 个 Pi 兼容工具
└── ...

skills/                          # 用户 Skills 目录
└── {skill_name}/
    ├── SKILL.md                 # Skill 定义
    ├── main.py                  # 实现代码
    └── tests/
        └── test_main.py         # 测试

docs/
├── INTEGRATION_DESIGN.md        # 集成设计 (新增)
├── DESIGN_SUMMARY.md            # 本文档
├── ARCHITECTURE.md              # 架构设计
└── SKILL_EVOLUTION_DESIGN.md    # 进化设计
```

---

## 六、状态与进度

### 6.1 已完成 ✅

| 组件 | 状态 | 说明 |
|------|------|------|
| Koda 工具集 | 100% | 7 个 Pi 兼容工具，48 测试通过 |
| Koda 验证系统 | 100% | Validator + Reflector + Manager |
| KodaAdapterV2 | 100% | EvoSkill-Koda 集成适配器 |
| IntegratedSession | 90% | 基础实现完成，需完善测试 |
| 闭环演示 | 100% | 模拟演示验证架构 |

### 6.2 进行中 ⚠️

| 组件 | 状态 | 说明 |
|------|------|------|
| SkillEvolutionEngine | 60% | 核心类定义完成，需实现完整流程 |
| Skill 热加载 | 70% | 基础实现，需完善错误处理 |
| 端到端集成测试 | 30% | 需编写完整测试用例 |

### 6.3 待开始 📋

| 组件 | 优先级 | 说明 |
|------|--------|------|
| Web UI | P1 | 对话界面 + Skill 管理 |
| CLI 完善 | P1 | /skills, /create, /evolve 命令 |
| 上下文压缩 | P2 | 长对话处理 |
| Skill 市场 | P2 | 分享机制 |

---

## 七、使用示例

### 7.1 查询 Skills

```python
session = IntegratedSession(workspace=Path("./workspace"))

async for event in session.prompt("/skills"):
    print(event.data["content"])

# Output:
# Available skills:
#   - read_file: Read file content
#   - write_file: Write file content
#   - time_tool: Query current time
```

### 7.2 使用 Skill

```python
async for event in session.prompt("What time is it?"):
    if event.type == EventType.MESSAGE_END:
        print(event.data["content"])

# Output:
# Current time: 2026-02-09T16:40:21
```

### 7.3 创建 Skill

```python
async for event in session.prompt("/create query weather info"):
    print(event.data)

# Output:
# weather skill created and activated!
# Files generated:
#   - skills/weather/SKILL.md
#   - skills/weather/main.py
#   - skills/weather/tests/test_main.py
```

### 7.4 进化 Skill

```python
async for event in session.prompt("/evolve time_tool add UTC support"):
    print(event.data)

# Output:
# time_tool evolved to v1.1.0!
# New features:
#   - get_current_time(timezone="UTC")
#   - get_utc_time()
```

---

## 八、演进路线

### Phase 1: 基础集成 (当前)
- [x] Koda 工具集完成
- [x] 验证系统集成
- [x] KodaAdapterV2
- [x] IntegratedSession 基础

### Phase 2: Skill 进化 (Next)
- [ ] SkillEvolutionEngine 完整实现
- [ ] 需求分析 → 代码生成 闭环
- [ ] 热加载完善
- [ ] 端到端测试

### Phase 3: 体验优化
- [ ] CLI 命令完善
- [ ] Web UI 原型
- [ ] 上下文压缩
- [ ] 错误处理优化

### Phase 4: 生态建设
- [ ] Skill 市场
- [ ] 文档站点
- [ ] 示例库
- [ ] MCP 协议支持

---

## 九、参考文档

| 文档 | 内容 |
|------|------|
| `docs/INTEGRATION_DESIGN.md` | 详细集成方案 |
| `docs/ARCHITECTURE.md` | 系统架构 |
| `docs/SKILL_EVOLUTION_DESIGN.md` | Skill 进化设计 |
| `docs/PROJECT_STATUS_AND_ROADMAP.md` | 项目状态与路线图 |
| `docs/koda_validation_analysis.md` | 验证系统分析 |

---

## 十、总结

EvoSkill 的核心价值：**让 AI 系统具备自我进化的能力**。

通过 EvoSkill Core + Koda 的双层架构：
1. **底层 (Koda)**: 提供稳定、可靠的代码执行能力
2. **高层 (EvoSkill)**: 提供业务逻辑和 Skill 进化能力

用户可以通过自然语言与系统交互，系统能够：
- 理解需求并自动创建新 Skill
- 根据反馈持续进化现有 Skill
- 越用越聪明，越用越强大

**下一步**: 完善 SkillEvolutionEngine，实现真正的自动 Skill 生成。
