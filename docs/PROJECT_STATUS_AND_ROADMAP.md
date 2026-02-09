# EvoSkill 项目状态与路线图

**最后更新**: 2026-02-09

---

## 一、项目概览

### 1.1 项目定位

EvoSkill 是一个**具备自我进化能力的智能对话系统**，核心差异化能力：

1. **会造工具的 AI** —— 能从对话中感知需求，自动生成新 Skill
2. **多层架构设计** —— EvoSkill (高层编排) + Koda (底层执行)
3. **100% Pi Coding Agent 兼容** —— 工具层完全兼容，可无缝切换

### 1.2 代码规模

```
总代码量: ~20,000 行 Python

模块分布:
├── EvoSkill Core    8,014 lines (40.7%)  - 会话、进化引擎、CLI
├── Koda             8,429 lines (42.7%)  - Pi-compatible 工具集 + 验证系统
├── Tests            2,629 lines (13.3%)  - 单元测试、集成测试
└── Examples           653 lines ( 3.3%)  - 示例 Skills
```

### 1.3 当前状态

| 模块 | 状态 | 测试覆盖 |
|------|------|----------|
| Koda 工具集 | ✅ 完成 | 48 passed, 1 skipped |
| Pi 兼容性 | ✅ 100% | 功能对齐完成 |
| 验证系统 | ✅ 完成 | Validator + Reflector + Manager |
| EvoSkill Core | ⚠️ 进行中 | 会话管理基础完成 |
| Skill 进化引擎 | ⚠️ 原型 | 核心类已定义 |
| CLI 界面 | ⚠️ 基础 | 入口已实现 |

---

## 二、架构梳理

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  应用层                                                          │
│  ├── CLI (evoskill/cli/main.py)                                 │
│  └── Web UI (TODO)                                              │
├─────────────────────────────────────────────────────────────────┤
│  EvoSkill Core (高层编排)                                         │
│  ├── Session    - 对话会话管理                                    │
│  ├── Evolution  - Skill 进化引擎 (分析/设计/生成/验证)              │
│  └── Skills     - Skill 加载与调度                                │
├─────────────────────────────────────────────────────────────────┤
│  Koda (底层执行) - Pi Coding Agent 兼容                          │
│  ├── Tools      - 文件/编辑/命令/搜索工具 (100% Pi 兼容)           │
│  ├── Validator  - 代码质量验证 (Koda 特有)                        │
│  ├── Reflector  - AI 代码分析 (Koda 特有)                         │
│  └── Truncation - 内容截断处理                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件详情

#### Koda (已完成 ✅)

```
koda/
├── core/
│   ├── truncation.py    - 内容截断 (272 lines)
│   ├── validator.py     - 代码验证 (130 lines)
│   ├── reflector.py     - 代码反思 (200 lines)
│   ├── agent_v2.py      - Agent V2 实现 (503 lines)
│   └── types.py         - 类型定义
├── tools/
│   ├── read.py          - 文件读取 (Pi 兼容)
│   ├── write.py         - 文件写入 (Pi 兼容)
│   ├── edit.py          - 文本编辑 (Pi 兼容)
│   ├── bash.py          - 命令执行 (Pi 兼容)
│   ├── grep.py          - 文本搜索 (Pi 兼容)
│   ├── find.py          - 文件查找 (Pi 兼容)
│   └── ls.py            - 目录列表 (Pi 兼容)
└── docs/
    └── VALIDATION_STATUS.md
```

**Koda 特点**:
- 工具层与 Pi Coding Agent 100% 功能对齐
- 额外提供验证系统（Validator + Reflector）
- 可独立使用，也可被 EvoSkill 调用

#### EvoSkill Core (进行中 ⚠️)

```
evoskill/
├── core/
│   ├── session.py       - Agent 会话管理 (基础实现)
│   ├── context.py       - 上下文管理
│   ├── context_compactor.py - 上下文压缩
│   ├── llm.py           - LLM 接口
│   ├── types.py         - 类型定义
│   └── events.py        - 事件系统
├── evolution/           - Skill 进化引擎 (核心！)
│   ├── engine.py        - 进化主引擎
│   ├── analyzer.py      - 需求分析
│   ├── designer.py      - 架构设计
│   ├── generator.py     - 代码生成
│   ├── validator.py     - Skill 验证
│   ├── integrator.py    - 集成部署
│   ├── matcher.py       - 需求匹配
│   └── api_discovery.py - API 发现
├── skills/
│   ├── loader.py        - Skill 加载器
│   ├── builtin.py       - 内置工具
│   └── git_skill/       - Git Skill 示例
└── cli/
    └── main.py          - CLI 入口
```

**EvoSkill 核心差异化**: Skill 进化引擎 —— 能自动感知需求并生成新 Skill

---

## 三、已完成工作

### 3.1 Koda V2 (100% 完成)

- [x] 7 个 Pi-compatible 工具实现
- [x] 验证系统 (Validator + Reflector + ValidationManager)
- [x] 48 个单元测试全部通过
- [x] 完整功能对比文档

### 3.2 EvoSkill 基础

- [x] 项目架构设计
- [x] 核心类型定义
- [x] 配置管理系统
- [x] LLM 接口封装
- [x] CLI 入口

---

## 四、下一步工作计划

### 4.1 近期目标 (2-4 周)

#### 优先级 P0: EvoSkill Core 完成

1. **Session 系统完善**
   - 状态: 基础实现存在，需完善消息历史管理
   - 任务:
     - [ ] 完整的消息序列化/反序列化
     - [ ] 会话持久化到磁盘
     - [ ] 多会话管理

2. **Koda 与 EvoSkill 集成**
   - 状态: 有 koda_adapter.py，需完善
   - 任务:
     - [ ] EvoSkill Session 调用 Koda Agent
     - [ ] 工具注册机制
     - [ ] 消息格式转换

3. **内置 Skills 完善**
   - 状态: 有 git_skill 示例，需扩展
   - 任务:
     - [ ] 文件操作 Skill
     - [ ] 网络请求 Skill
     - [ ] 代码搜索 Skill

#### 优先级 P1: Skill 进化引擎 V1

1. **需求分析器 (analyzer.py)**
   - 从对话中提取潜在 Skill 需求
   - 需求形式化描述

2. **Skill 生成器 (generator.py)**
   - 基于需求生成 Skill 代码
   - 生成测试用例

3. **验证与部署 (validator.py + integrator.py)**
   - 自动测试生成的 Skill
   - 部署到 Skills 目录

4. **闭环演示**
   - 一个完整的 "需求 → Skill → 使用" 演示

### 4.2 中期目标 (1-3 月)

#### 优先级 P2: 体验优化

1. **Web UI**
   - 对话界面
   - Skill 管理面板
   - 进化过程可视化

2. **上下文管理优化**
   - 智能上下文压缩
   - 长对话处理

3. **Skill 市场**
   - Skill 分享机制
   - 社区 Skills 导入

#### 优先级 P3: 高级功能

1. **多模态支持**
   - 图片理解
   - 文档处理

2. **团队协作**
   - 共享 Skills
   - 权限管理

3. **MCP 协议支持**
   - 与 Goose 等工具互通

### 4.3 远期目标 (3-6 月)

1. **自主进化** —— Skill 能自我改进
2. **跨项目学习** —— 从多个项目中学习通用能力
3. **企业级部署** —— 私有化、安全合规

---

## 五、设计决策记录

### 5.1 Koda 验证系统是否多余？

**决策**: 保留，但改为可选配置

**理由**:
- Pi 的假设（LLM 自我纠错）只在强 LLM + 简单任务下成立
- 验证系统只占用 5% 代码量，但提供显式质量保障
- 让用户按需选择 (off/static/full)

### 5.2 为什么采用双层架构？

```
EvoSkill (高层) + Koda (底层)
```

**理由**:
1. **关注点分离**: EvoSkill 负责业务逻辑，Koda 负责代码执行
2. **可独立使用**: Koda 可以单独作为 Coding Agent 使用
3. **兼容生态**: Pi 兼容的工具生态可以直接复用

### 5.3 Skill 进化的触发策略

**方案 A**: 用户显式触发 ("帮我创建一个 Skill")
**方案 B**: AI 主动提议 ("检测到您经常做 X，是否创建 Skill？")
**方案 C**: 自动学习 (静默生成，用户无感知)

**当前选择**: 从 A → B → C 渐进

---

## 六、风险与挑战

### 6.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 生成代码质量不稳定 | 高 | 多层验证 + 用户确认 |
| 上下文长度限制 | 中 | 智能压缩 + 分层摘要 |
| 复杂项目理解困难 | 中 | RepoMap + 符号索引 |

### 6.2 产品风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Skill 进化不可控 | 高 | 人工审核 + 版本回滚 |
| 用户学习成本高 | 中 | 渐进式引导 + 优秀示例 |
| 与现有工具竞争 | 低 | 差异化（自我进化） |

---

## 七、成功指标

### 7.1 技术指标

- [ ] Koda 测试覆盖率 > 90%
- [ ] EvoSkill Core 测试覆盖率 > 80%
- [ ] 端到端演示可用

### 7.2 产品指标

- [ ] 完成一个 "需求 → Skill" 闭环 < 5 分钟
- [ ] Skill 生成成功率 > 70%
- [ ] 用户满意度 > 4.0/5.0

---

## 八、参考资源

### 8.1 设计文档

- `docs/ARCHITECTURE.md` - 系统架构
- `docs/SKILL_EVOLUTION_DESIGN.md` - 进化引擎设计
- `docs/CODING_AGENT_DESIGN.md` - Coding Agent 设计
- `docs/CONTEXT_DESIGN.md` - 上下文管理
- `docs/koda_validation_analysis.md` - 验证系统分析

### 8.2 参考项目

| 项目 | 学习点 | 状态 |
|------|--------|------|
| [Pi Agent](https://github.com/can1357/oh-my-pi) | 工具设计 | 已兼容 |
| [Aider](https://github.com/Aider-AI/aider) | 代码编辑 | 参考中 |
| [Goose](https://github.com/block/goose) | MCP 协议 | 待集成 |
| [OpenClaw](https://github.com/openclaw/openclaw) | Skill 系统 | 参考中 |

---

## 九、总结

EvoSkill 项目已完成底层基础设施（Koda），正在建设上层业务逻辑（EvoSkill Core + 进化引擎）。

**当前阶段**: 从 "能用的工具" 向 "会造工具的系统" 演进。

**下一步关键里程碑**:
1. 完成 EvoSkill Core 与 Koda 的集成
2. 实现第一个完整的 Skill 进化闭环演示
3. 发布 v0.3.0-alpha 版本
