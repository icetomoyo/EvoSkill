# EvoSkill 集成设计方案

> 连接 EvoSkill Core 与 Koda，实现完整闭环

---

## 一、集成目标

### 1.1 核心目标

实现 **EvoSkill Core + Koda** 的无缝集成：

```
用户输入 → EvoSkill Session → 调用 Koda Agent → 工具执行 → 结果返回
                        ↓
              触发 Skill 进化（如果需要）
                        ↓
              生成/更新 Skill → 立即可用
```

### 1.2 具体目标

1. **查询**: 用户能查看当前可用的 Skills
2. **使用**: 用户能使用现有 Skills 完成任务
3. **创建**: 系统能根据需求自动生成新 Skill
4. **进化**: Skill 能根据使用反馈自我改进

---

## 二、集成架构

### 2.1 集成点设计

```
┌─────────────────────────────────────────────────────────────┐
│                    EvoSkill Core                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Session    │  │   Evolution  │  │   Skills     │      │
│  │   会话管理    │  │   进化引擎    │  │   管理器      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          │  调用           │  生成           │  注册
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      Koda                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Agent V2    │  │   Tools      │  │  Validator   │      │
│  │  执行引擎     │  │   工具集      │  │  验证系统     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 关键接口定义

#### 接口 1: EvoSkill → Koda 调用

```python
# evoskill/coding_agent/koda_adapter.py

class KodaAdapter:
    """
    EvoSkill 与 Koda 的适配器
    
    职责:
    1. 将 EvoSkill Session 转换为 Koda Agent 调用
    2. 转换消息格式
    3. 管理 Koda Agent 生命周期
    """
    
    def __init__(self, workspace: Path, llm_config: dict):
        self.workspace = workspace
        self.llm = self._create_llm(llm_config)
        self.agent = None
    
    async def execute_task(
        self,
        task: str,
        context: Optional[List[Message]] = None
    ) -> ExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务描述
            context: 上下文消息
            
        Returns:
            ExecutionResult: 执行结果
        """
        # 创建或复用 Agent
        if not self.agent:
            self.agent = AgentV2(workspace=self.workspace, llm=self.llm)
        
        # 执行
        return await self.agent.execute(task)
```

#### 接口 2: Skill 注册到 EvoSkill

```python
# evoskill/skills/loader.py

class SkillLoader:
    """扩展 SkillLoader，支持热加载"""
    
    def register_skill(self, skill: Skill) -> None:
        """
        注册新 Skill（热加载）
        
        不需要重启即可使用
        """
        self._skills[skill.name] = skill
        
        # 通知 Session 有新 Skill 可用
        self._notify_sessions(skill)
    
    def unregister_skill(self, skill_name: str) -> None:
        """卸载 Skill"""
        if skill_name in self._skills:
            del self._skills[skill_name]
```

#### 接口 3: 进化触发

```python
# evoskill/evolution/engine.py

class SkillEvolutionEngine:
    """扩展进化引擎，与 EvoSkill 集成"""
    
    async def evolve_from_session(
        self,
        session: AgentSession,
        user_request: str
    ) -> EvolutionResult:
        """
        基于会话上下文触发进化
        
        1. 分析会话历史，理解完整需求
        2. 检查现有 Skills
        3. 决策并执行进化
        4. 注册新 Skill 到 EvoSkill
        """
        # 获取会话上下文
        context = session.get_context()
        
        # 分析需求
        analysis = await self.analyzer.analyze(user_request, context)
        
        # 检查现有 Skills
        existing_skills = self.skill_loader.list_skills()
        match = self.matcher.find_best_match(analysis, existing_skills)
        
        if match and match.confidence > 0.9:
            # 使用现有 Skill
            return EvolutionResult(
                status="reused",
                skill_name=match.skill.name
            )
        
        # 创建新 Skill
        return await self._create_skill(analysis)
```

---

## 三、数据流设计

### 3.1 标准使用流程

```
用户: 帮我读取 README.md 的内容

┌─────────────────────────────────────────────────────────────┐
│ Step 1: 会话处理                                              │
│ ─────────────────                                           │
│ Session 接收输入 → 添加到消息历史                              │
│                                                           │
│ 系统提示词: "你有以下工具可用: read_file, write_file..."        │
│ 历史消息: [...]                                            │
│ 当前输入: "帮我读取 README.md 的内容"                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: LLM 决策                                              │
│ ─────────────────                                           │
│ LLM 分析: 用户要读取文件 → 需要调用 read_file                   │
│                                                           │
│ 输出工具调用:                                               │
│ {                                                          │
│   "tool": "read_file",                                     │
│   "args": {"file_path": "README.md"}                       │
│ }                                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 工具执行 (通过 Koda)                                   │
│ ─────────────────                                           │
│ KodaAdapter 调用 read_file 工具                               │
│ Koda 执行并返回结果                                          │
│                                                           │
│ 结果: "# EvoSkill\n\n智能对话系统..."                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 结果返回                                              │
│ ─────────────────                                           │
│ LLM 整合结果 → 返回给用户                                     │
│                                                           │
│ 输出: "README.md 的内容是: # EvoSkill..."                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Skill 创建流程

```
用户: 创建一个工具，能查询当前时间

┌─────────────────────────────────────────────────────────────┐
│ Step 1: 需求分析                                              │
│ ─────────────────                                           │
│ NeedAnalyzer 分析:                                           │
│ - 意图: 查询当前时间                                          │
│ - 领域: 系统工具                                              │
│ - 复杂度: simple                                             │
│ - 现有 Skills: 无匹配                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Skill 设计                                            │
│ ─────────────────                                           │
│ SkillDesigner 输出:                                          │
│ - name: "time_tool"                                         │
│ - tools: [{"name": "get_current_time", ...}]                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 代码生成                                              │
│ ─────────────────                                           │
│ SkillGenerator 生成:                                         │
│ - skills/time_tool/SKILL.md                                 │
│ - skills/time_tool/main.py                                  │
│ - skills/time_tool/tests/test_main.py                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 验证                                                  │
│ ─────────────────                                           │
│ SkillValidator 检查:                                         │
│ ✓ 语法正确                                                   │
│ ✓ 测试通过                                                   │
│ ✓ 可调用                                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 集成                                                  │
│ ─────────────────                                           │
│ SkillIntegrator:                                             │
│ - 加载 Skill                                                │
│ - 注册到 SkillLoader（热加载）                                 │
│ - 通知 Session 新 Skill 可用                                  │
│                                                           │
│ 用户立即可用: "查询当前时间" → 调用 get_current_time()         │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、关键实现细节

### 4.1 消息格式转换

```python
# evoskill/core/types.py <-> koda/core/types.py

def evoskill_to_koda_message(msg: EvoSkillMessage) -> KodaMessage:
    """转换消息格式"""
    return KodaMessage(
        role=msg.role,
        content=msg.content,
        tool_calls=[convert_tool_call(tc) for tc in msg.tool_calls] if msg.tool_calls else None
    )

def koda_to_evoskill_result(result: KodaExecutionResult) -> EvoSkillToolResult:
    """转换执行结果"""
    return EvoSkillToolResult(
        tool_name=result.tool_name,
        output=result.output,
        error=result.error,
        artifacts=result.artifacts
    )
```

### 4.2 工具注册

```python
# 自动将 Koda 工具注册到 EvoSkill

KODA_TO_EVOSKILL_TOOLS = {
    "read_file": ReadFileTool,
    "write_file": WriteFileTool,
    "edit_file": EditFileTool,
    "bash": BashTool,
    "grep": GrepTool,
    "find": FindTool,
    "ls": LsTool,
}

def register_koda_tools(skill_loader: SkillLoader):
    """将 Koda 工具注册为 EvoSkill Skills"""
    for tool_name, tool_class in KODA_TO_EVOSKILL_TOOLS.items():
        skill = Skill(
            name=tool_name,
            description=tool_class.description,
            tools=[tool_class]
        )
        skill_loader.register_skill(skill)
```

### 4.3 上下文传递

```python
# 会话上下文传递给 Koda Agent

class AgentSession:
    async def prompt(self, user_input: str) -> AsyncIterator[Event]:
        # 1. 添加用户消息到历史
        self.messages.append(UserMessage(content=user_input))
        
        # 2. 构建 Koda 可用的上下文
        koda_context = self._build_koda_context()
        
        # 3. 调用 Koda Adapter
        result = await self.koda_adapter.execute_task(
            task=user_input,
            context=koda_context
        )
        
        # 4. 处理结果
        if result.success:
            yield MessageEvent(content=result.output)
        else:
            # 触发进化？
            if self._should_evolve(result):
                evolution_result = await self._trigger_evolution(user_input)
                yield EvolutionEvent(result=evolution_result)
```

---

## 五、闭环演示设计

### 5.1 演示场景: 时间工具进化

**目标**: 展示完整的 "查询 → 创建 → 使用 → 进化" 闭环

#### 阶段 1: 查询现有 Skills

```
用户: 有哪些工具可用？

AI: 当前可用的 Skills:
     - read_file: 读取文件内容
     - write_file: 写入文件
     - edit_file: 编辑文件
     - bash: 执行命令
     - grep: 文本搜索
     - find: 文件查找
     - ls: 目录列表
     
     [还没有时间相关工具]
```

#### 阶段 2: 创建新 Skill

```
用户: 帮我创建一个查询当前时间的工具

AI: 检测到需求：查询当前时间
    现有 Skills 无法满足
    正在创建 time_tool...
    
    [Analyzer] 分析需求 ✓
    [Designer] 设计 Skill ✓
    [Generator] 生成代码 ✓
    [Validator] 验证 ✓
    [Integrator] 集成 ✓
    
    time_tool 已创建并激活！
    
    可用命令：
    - 查询当前时间
    - 获取当前时间
    - 现在几点了
```

#### 阶段 3: 使用新 Skill

```
用户: 现在几点了？

AI: [调用 time_tool.get_current_time()]
    当前时间：2026-02-09 14:30:25
```

#### 阶段 4: Skill 进化

```
用户: 时间工具能不能显示 UTC 时间？

AI: 检测到 time_tool 功能扩展需求
    正在添加 UTC 支持...
    
    [修改代码]
    ✓ 添加 timezone 参数
    ✓ 更新 SKILL.md
    ✓ 更新测试
    
    time_tool 已进化！
    现在支持：
    - get_current_time() - 本地时间
    - get_current_time(timezone="UTC") - UTC 时间
    
用户: UTC 时间是多少？

AI: [调用 time_tool.get_current_time(timezone="UTC")]
    UTC 时间：2026-02-09 06:30:25
```

---

## 六、实施计划

### 阶段 1: 基础集成 (Day 1-2)

- [ ] 完善 `KodaAdapter` 实现
- [ ] 实现消息格式转换
- [ ] 连接 Session → Koda
- [ ] 基础工具调用测试

### 阶段 2: Skill 系统完善 (Day 3-4)

- [ ] 完善 `SkillLoader` 热加载
- [ ] 实现 Skill 注册/卸载
- [ ] Koda 工具自动注册
- [ ] Skill 查询接口

### 阶段 3: 进化引擎集成 (Day 5-7)

- [ ] 完善 `SkillEvolutionEngine`
- [ ] 实现 Analyzer → Generator 流程
- [ ] 集成 Validator
- [ ] 实现 Integrator 热加载

### 阶段 4: 闭环演示 (Day 8-10)

- [ ] 实现时间工具演示
- [ ] 测试完整流程
- [ ] 优化交互体验
- [ ] 文档和演示脚本

---

## 七、验收标准

### 7.1 功能验收

- [ ] 用户能查询所有可用 Skills
- [ ] 用户能使用现有 Skills 完成任务
- [ ] 系统能根据自然语言描述创建新 Skill
- [ ] 新 Skill 立即可用（无需重启）
- [ ] 系统能根据反馈进化现有 Skills

### 7.2 性能验收

- [ ] Skill 创建时间 < 30 秒
- [ ] 工具调用延迟 < 1 秒
- [ ] 进化过程流畅，有进度提示

### 7.3 质量验收

- [ ] 生成的 Skill 代码通过验证
- [ ] 生成的 Skill 无需手动修改即可使用
- [ ] 测试覆盖率 > 80%

---

**下一步**: 开始实施阶段 1 —— 基础集成
