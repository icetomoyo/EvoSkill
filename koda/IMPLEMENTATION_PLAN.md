# Koda Pi-Mono 完全对标实施计划

**创建日期**: 2026-02-12
**Pi-Mono 参考版本**: main 分支 (commit: latest)
**目标**: 完全对标复现 Pi-Mono 功能（**排除 Slack Bot 集成部分**）

---

## 🎯 项目目标

将 Pi-Mono (TypeScript) 的核心功能完整移植到 Python，提供：
- ✅ 完整的 AI Provider 抽象层
- ✅ 强大的 Agent 框架
- ✅ 功能完整的 Coding Agent
- ✅ Mom 模块核心功能（非 Slack Bot）

**排除范围**: `slack.ts` 及与 Slack API 直接集成的部分

---

## 📊 当前真实完成度

| 模块 | 完成度 | 文件覆盖率 | 代码行数估算 | 状态 |
|------|--------|-----------|------------|------|
| **AI** | **90%** | 40/44 文件 | ~8000/10000 行 | ✅ 核心完整 |
| **Agent** | **75%** | 6/10 功能 | ~1500/4000 行 | ⚠️ 缺关键特性 |
| **Coding** | **70%** | 68/108 文件 | ~15000/25000 行 | ⚠️ 缺扩展系统 |
| **Mom** | **10%** | 3/16 文件 | ~250/2500 行 | 🔴 大部分缺失 |
| **总体** | **65%** | **117/178 文件** | **~25K/42K 行** | ⚠️ 需要大量工作 |

---

## 📋 详细缺失功能清单

### 1️⃣ AI 模块 (koda/ai/) - 90% 完成

#### ✅ 已完成 (40个文件)
- [x] 核心类型 (`types.py`)
- [x] 事件流 (`event_stream.py`)
- [x] 所有 9 个 Provider
- [x] 所有 5 个 OAuth Provider
- [x] 消息转换 (`transform_messages.py`)
- [x] Unicode 清理 (`sanitize_unicode.py`)
- [x] 溢出检测 (`overflow.py`)

#### ❌ 缺失功能

**P0 - 高优先级 (阻塞)**
- [ ] **完整模型数据库** (`models/generated.py`)
  - Pi-mono: 301KB 的 `models.generated.ts`，包含 300+ 模型定义
  - Koda: 硬编码约 70 个模型
  - **工作量**: 2-3天
  - **任务**:
    - 解析 Pi-mono 的 `models.generated.ts`
    - 转换为 Python 字典结构
    - 添加模型成本、上下文窗口等元数据
    - 补充 2025-2026 年新模型 (GPT-5.x, Claude Opus 4.6, Gemini 3)

- [ ] **Partial JSON 流式解析**
  - Pi-mono 使用 `partial-json` npm 包
  - Koda 的 `json_parse.py` 只有基础实现
  - **工作量**: 1-2天
  - **任务**:
    - 集成 Python partial JSON 解析库
    - 或实现等效的流式 JSON 解析器
    - 处理深度嵌套的不完整对象和数组

**P1 - 中优先级 (影响体验)**
- [ ] **工具验证增强** (`validation.py`)
  - Pi-mono 使用 AJV 进行 Schema 验证和类型强制
  - Koda 只有基础验证
  - **工作量**: 1天
  - **任务**:
    - 增强 `typebox_helpers.py` 的验证器
    - 实现类型强制转换 (coercion)
    - 添加工具参数验证

- [ ] **完整 CLI OAuth 流程** (`cli.py`)
  - Pi-mono: `npx @mariozechner/pi-ai login`
  - Koda: 基础 CLI 存在但不完整
  - **工作量**: 1天
  - **任务**:
    - 实现完整的登录流程
    - 添加设备码认证
    - Token 存储和刷新

**P2 - 低优先级 (增强)**
- [ ] **HTTP 代理支持** (`http_proxy.py`)
  - 已存在但功能不完整
  - **工作量**: 0.5天

---

### 2️⃣ Agent 模块 (koda/agent/) - 75% 完成

#### ✅ 已完成 (6个核心功能)
- [x] Agent 核心类 (`agent.py`)
- [x] 基础事件循环 (`loop.py`)
- [x] 流代理 (`stream_proxy.py`)
- [x] 并行执行 (`parallel.py`)
- [x] 消息队列 (`queue.py`)
- [x] 工具注册表 (`tools.py`)

#### ❌ 缺失功能

**P0 - 关键特性 (阻塞 Agent 完整功能)**

- [ ] **`agentLoopContinue()` 函数** (`loop.py`)
  - **功能**: 从现有 context 继续执行，不添加新消息
  - **Pi-mono**: `agentLoopContinue(context, config)`
  - **Koda**: 完全缺失
  - **工作量**: 1天
  - **实现要点**:
    - 复用现有 context
    - 跳过添加用户消息步骤
    - 直接进入 LLM 调用

- [ ] **Steering 消息集成** (`loop.py`)
  - **功能**: 在工具执行期间检查并应用 steering 消息
  - **Pi-mono**: 每个工具调用后检查 `getSteeringMessages()`
  - **Koda**: 完全缺失
  - **工作量**: 2天
  - **实现要点**:
    - 工具调用后检查 steering 队列
    - 如果有 steering，跳过剩余工具调用
    - 将 steering 消息注入 context

- [ ] **Follow-up 消息外层循环** (`loop.py`)
  - **功能**: Agent 在有 follow-up 消息时继续执行
  - **Pi-mono**: 外层 while 循环检查 `getFollowUpMessages()`
  - **Koda**: 完全缺失
  - **工作量**: 1天
  - **实现要点**:
    - Agent.run() 外层添加 follow-up 循环
    - 检查 follow-up 队列
    - 自动继续执行直到队列为空

- [ ] **`convertToLlm` 转换层** (`loop.py` 或新文件)
  - **功能**: LLM 调用前的消息转换/过滤
  - **Pi-mono**: `transformContext` 选项包含 `convertToLlm`
  - **Koda**: 完全缺失
  - **工作量**: 2天
  - **实现要点**:
    - 消息类型转换
    - 过滤不支持的消息类型
    - Provider 特定的格式化

- [ ] **`transformContext` 预处理** (`loop.py`)
  - **功能**: Context 修剪和优化
  - **Pi-mono**: `transformContext` 回调
  - **Koda**: 完全缺失
  - **工作量**: 1天
  - **实现要点**:
    - Context token 计数
    - 智能修剪旧消息
    - 保留关键上下文

**P1 - 重要特性 (影响 API 完整性)**

- [ ] **AgentMessage 联合类型** (`types.py`)
  - **功能**: 支持自定义消息类型
  - **Pi-mono**: 使用 TypeScript 声明合并
  - **Koda**: 缺失
  - **工作量**: 0.5天
  - **实现要点**:
    - 定义消息类型注册机制
    - 支持第三方扩展

- [ ] **动态 API Key 解析** (`agent.py`)
  - **功能**: `getApiKey` 回调支持
  - **Pi-mono**: 每个 provider 可配置 `getApiKey`
  - **Koda**: 硬编码 API key
  - **工作量**: 1天

- [ ] **Session ID 管理** (`agent.py`)
  - **功能**: 基于会话的缓存
  - **Pi-mono**: `sessionId` getter/setter
  - **Koda**: 缺失
  - **工作量**: 1天

- [ ] **Thinking budgets 配置** (`types.py`)
  - **功能**: Token 预算自定义
  - **Pi-mono**: `thinkingBudgets` 选项
  - **Koda**: 缺失
  - **工作量**: 0.5天

- [ ] **`prompt()` 方法增强** (`agent.py`)
  - **功能**: 接受 `AgentMessage[]` 或图片
  - **Pi-mono**: `prompt(AgentMessage[] | string, images?)`
  - **Koda**: 只接受 string
  - **工作量**: 1天

- [ ] **`waitForIdle()` 方法** (`agent.py`)
  - **功能**: Promise 风格的空闲等待
  - **Pi-mono**: `agent.waitForIdle()`
  - **Koda**: 缺失
  - **工作量**: 1天

- [ ] **Pending tool calls 状态跟踪** (`agent.py`)
  - **功能**: 跟踪正在执行的工具调用
  - **Pi-mono**: `pendingToolCalls: Set<string>`
  - **Koda**: 缺失
  - **工作量**: 0.5天

---

### 3️⃣ Coding 模块 (koda/coding/) - 70% 完成

#### ✅ 已完成 (68个文件)
- [x] 会话管理 (`session_manager.py`)
- [x] 会话压缩 (`core/compaction/`)
- [x] 所有基础工具 (`tools/`)
- [x] CLI 选择器 (`cli/`)
- [x] 事件总线 (`core/event_bus.py`)
- [x] 诊断工具 (`core/diagnostics.py`)
- [x] 技能系统 (`skills.py`)
- [x] Slash 命令 (`slash_commands.py`)

#### ❌ 缺失功能

**P0 - 核心文件 (阻塞)**

- [ ] **config.ts** → `config.py`
  - **功能**: 全局配置模块
  - **工作量**: 1天
  - **内容**: 配置加载、验证、默认值

- [ ] **main.ts** → `main.py`
  - **功能**: 主入口点
  - **工作量**: 1天
  - **内容**: CLI 启动、参数解析

- [ ] **core/defaults.ts** → `core/defaults.py`
  - **功能**: 默认值定义
  - **工作量**: 0.5天

- [ ] **core/exec.ts** → `core/exec.py`
  - **功能**: 执行工具
  - **工作量**: 1天

**P1 - 扩展系统 (重要功能)**

- [ ] **core/extensions/loader.ts** → `extensions/loader.py`
  - **功能**: 扩展加载器
  - **Pi-mono**: 155 行，动态加载扩展模块
  - **工作量**: 2天
  - **实现要点**:
    - 扫描扩展目录
    - 动态导入 Python 模块
    - 验证扩展元数据
    - 注册扩展 hooks

- [ ] **core/extensions/runner.ts** → `extensions/runner.py`
  - **功能**: 扩展运行器
  - **Pi-mono**: 280 行，执行扩展逻辑
  - **工作量**: 2天
  - **实现要点**:
    - 调用扩展生命周期方法
    - 错误隔离
    - 超时控制

- [ ] **core/extensions/types.ts** → `extensions/types.py`
  - **功能**: 扩展类型定义
  - **Pi-mono**: 42KB，完整的扩展 API 定义
  - **工作量**: 2天
  - **内容**:
    - Extension 接口
    - Hook 类型
    - Context 类型
    - 配置 Schema

- [ ] **core/extensions/wrapper.ts** → `extensions/wrapper.py`
  - **功能**: 扩展包装器
  - **工作量**: 1天

**P2 - 工具增强**

- [ ] **core/tools/path-utils.ts** → `tools/path_utils.py`
  - **功能**: 路径处理工具
  - **工作量**: 0.5天

**P3 - 工具类 (辅助)**

- [ ] **utils/changelog.ts** → `utils/changelog.py`
  - **功能**: 变更日志工具
  - **工作量**: 0.5天

- [ ] **utils/mime.ts** → `utils/mime.py`
  - **功能**: MIME 类型检测
  - **工作量**: 0.5天

- [ ] **utils/photon.ts** → `utils/photon.py`
  - **功能**: 图片处理 (Photon 库集成)
  - **工作量**: 1天

- [ ] **utils/sleep.ts** → `utils/sleep.py`
  - **功能**: 睡眠工具
  - **工作量**: 0.1天 (简单)

- [ ] **utils/tools-manager.ts** → `utils/tools_manager.py`
  - **功能**: 工具管理器
  - **工作量**: 1天

**P4 - TUI 组件 (35个文件，平台特定)**

⚠️ **注意**: 这些是 React/Ink 组件，需要用 Python TUI 框架重写

**建议**: 使用 **Textual** 或 **Rich** + **Prompt Toolkit** 框架

- [ ] **Interactive 模式组件** (35个组件)
  - **工作量**: 10-15天 (需要完全重写)
  - **文件列表**:
    - `modes/interactive/components/armin.ts`
    - `modes/interactive/components/assistant-message.ts`
    - `modes/interactive/components/bash-execution.ts`
    - `modes/interactive/components/bordered-loader.ts`
    - `modes/interactive/components/branch-summary-message.ts`
    - `modes/interactive/components/compaction-summary-message.ts`
    - `modes/interactive/components/config-selector.ts`
    - `modes/interactive/components/countdown-timer.ts`
    - `modes/interactive/components/custom-editor.ts`
    - `modes/interactive/components/custom-message.ts`
    - `modes/interactive/components/daxnuts.ts`
    - `modes/interactive/components/diff.ts`
    - `modes/interactive/components/dynamic-border.ts`
    - `modes/interactive/components/extension-editor.ts`
    - `modes/interactive/components/extension-input.ts`
    - `modes/interactive/components/extension-selector.ts`
    - `modes/interactive/components/footer.ts`
    - `modes/interactive/components/keybinding-hints.ts`
    - `modes/interactive/components/login-dialog.ts`
    - `modes/interactive/components/model-selector.ts`
    - `modes/interactive/components/oauth-selector.ts`
    - `modes/interactive/components/scoped-models-selector.ts`
    - `modes/interactive/components/session-selector-search.ts`
    - `modes/interactive/components/session-selector.ts`
    - `modes/interactive/components/settings-selector.ts`
    - `modes/interactive/components/show-images-selector.ts`
    - `modes/interactive/components/skill-invocation-message.ts`
    - `modes/interactive/components/theme-selector.ts`
    - `modes/interactive/components/thinking-selector.ts`
    - `modes/interactive/components/tool-execution.ts`
    - `modes/interactive/components/tree-selector.ts`
    - `modes/interactive/components/user-message-selector.ts`
    - `modes/interactive/components/user-message.ts`
    - `modes/interactive/components/visual-truncate.ts`
    - `modes/interactive/theme/theme.ts`

---

### 4️⃣ Mom 模块 (koda/mom/) - 10% 完成 ⚠️ **最大缺口**

#### ✅ 已完成 (3个基础文件)
- [x] 基础 ContextManager (`context.py` - 72行)
- [x] 基础 Sandbox (`sandbox.py` - 118行)
- [x] 基础 Store (`store.py` - 62行)

#### ❌ 缺失功能

**P0 - 核心模块 (非 Slack Bot，独立功能)**

- [ ] **agent.ts** → `agent.py` (885行)
  - **功能**: Agent 运行器，与 Agent/AgentSession 完整集成
  - **工作量**: 5天
  - **内容**:
    - `getOrCreateRunner()` - 每个 channel 的缓存 runner
    - `createRunner()` - 完整 AgentSession 设置
    - 系统提示构建
    - 内存管理 (workspace + channel MEMORY.md)
    - 技能加载
    - 事件处理
    - 图片附件处理
    - 使用追踪和成本报告
    - Silent 完成支持 (`[SILENT]` marker)

- [ ] **events.ts** → `events.py` (384行)
  - **功能**: 事件调度系统
  - **工作量**: 3天
  - **内容**:
    - 三种事件类型: immediate, one-shot, periodic
    - EventsWatcher (文件系统监控)
    - Cron 调度 (使用 croniter 库)
    - 去抖和重试逻辑
    - 自动清理已触发事件

- [ ] **log.ts** → `log.py` (272行)
  - **功能**: 结构化控制台日志
  - **工作量**: 2天
  - **内容**:
    - LogContext (channel/user 信息)
    - 工具执行日志 (start/success/error)
    - 响应流日志
    - 下载日志
    - 使用摘要日志
    - Backfill 日志
    - 彩色格式化 (使用 rich 或 colorama)

- [ ] **main.ts** → `main.py` (323行)
  - **功能**: CLI 入口点
  - **工作量**: 2天
  - **内容**:
    - 参数解析 (--sandbox, --download, working directory)
    - Channel 状态管理
    - Handler 实现 (isRunning, handleStop, handleEvent)
    - Events watcher 生命周期
  - **注意**: 排除 Slack 集成部分

- [ ] **download.ts** → `download.py` (118行)
  - **功能**: Channel 历史下载工具
  - **工作量**: 1天
  - **内容**:
    - 下载完整 channel 历史
    - 获取线程回复
    - 格式化消息 (带时间戳)
  - **注意**: 可作为独立工具，不依赖 Slack Bot

**P1 - Mom 专用工具集 (5个工具)**

- [ ] **tools/index.ts** → `tools/__init__.py` (20行)
  - **功能**: 工具注册表
  - **工作量**: 0.5天

- [ ] **tools/attach.ts** → `tools/attach.py` (48行)
  - **功能**: 文件附件
  - **工作量**: 1天
  - **Schema**: label, path, title (optional)
  - **实现**: Upload 函数注入模式

- [ ] **tools/bash.ts** → `tools/bash.py` (98行)
  - **功能**: Bash 命令执行
  - **工作量**: 1天
  - **特性**:
    - 输出截断 (2000行 / 50KB 限制)
    - 临时文件保存完整输出
    - 超时支持
    - Abort signal 支持

- [ ] **tools/edit.ts** → `tools/edit.py` (166行)
  - **功能**: 精确文件编辑
  - **工作量**: 1天
  - **特性**:
    - 精确文本匹配
    - 单次出现强制
    - 统一 diff 生成
    - Shell 转义

- [ ] **tools/read.ts** → `tools/read.py` (160行)
  - **功能**: 文件读取 (支持图片)
  - **工作量**: 1天
  - **特性**:
    - 图片文件检测 (jpg, png, gif, webp)
    - 图片 Base64 编码
    - 行偏移/限制支持
    - 头部截断 (保留开头)
    - 行数感知

- [ ] **tools/truncate.ts** → `tools/truncate.py` (237行)
  - **功能**: 共享截断工具
  - **工作量**: 1天
  - **特性**:
    - `truncateHead()` - 用于文件读取
    - `truncateTail()` - 用于 bash 输出
    - 行和字节限制 (独立)
    - UTF-8 安全截断
    - 部分行处理

- [ ] **tools/write.ts** → `tools/write.py` (46行)
  - **功能**: 文件写入
  - **工作量**: 0.5天
  - **特性**:
    - 自动创建父目录
    - 特殊字符 Shell 转义

**P2 - 现有文件增强**

- [ ] **context.py 增强**
  - **缺失功能**:
    - `syncLogToSessionManager()` - 同步 log.jsonl 到 SessionManager
    - `LogMessage` 接口用于日志解析
    - `MomSettingsManager` 类
    - `MomCompactionSettings` 接口
    - `MomRetrySettings` 接口
    - `MomSettings` 接口 (provider/model/thinking)
  - **工作量**: 2天

- [ ] **sandbox.py 增强**
  - **缺失功能**:
    - `SandboxConfig` 类型 (host/docker)
    - `parseSandboxArg()` - CLI 解析
    - `validateSandbox()` - Docker 验证
    - `Executor` 接口
    - `HostExecutor` 类
    - `DockerExecutor` 类
    - `killProcessTree()` - 进程树终止
    - `shellEscape()` - Shell 转义
  - **工作量**: 3天

- [ ] **store.py 增强**
  - **缺失功能**:
    - `Attachment` 接口
    - `LoggedMessage` 接口
    - `getChannelDir()` - channel 目录管理
    - `generateLocalFilename()` - 附件命名
    - `processAttachments()` - 附件队列
    - `logMessage()` - JSONL 日志去重
    - `logBotResponse()` - bot 消息日志
    - `getLastTimestamp()` - 日志尾部读取
    - `processDownloadQueue()` - 异步下载
    - `downloadAttachment()` - 认证获取
  - **工作量**: 3天

---

## 🎯 实施路线图

### Phase 1: 核心功能补全 (4-5周)

#### Week 1-2: Agent 关键特性 + AI 模型数据库
- Day 1-3: `agentLoopContinue()` + Steering/Follow-up 消息循环
- Day 4-5: `convertToLlm` + `transformContext`
- Day 6-7: 完整模型数据库生成
- Day 8-10: Partial JSON 解析器

#### Week 3-4: Mom 核心模块
- Day 1-5: `mom/agent.py` (885行)
- Day 6-8: `mom/events.py` + `mom/log.py`
- Day 9-10: `mom/download.py` + `mom/main.py` (排除 Slack 部分)

#### Week 5: Coding 核心文件 + Mom 工具
- Day 1-2: `config.py` + `main.py` + `defaults.py`
- Day 3-4: `core/exec.py`
- Day 5-7: Mom 工具集 (5个工具)

### Phase 2: 扩展系统 (2-3周)

#### Week 6-7: 扩展加载和运行
- Day 1-2: `extensions/types.py` (42KB)
- Day 3-4: `extensions/loader.py`
- Day 5-6: `extensions/runner.py`
- Day 7: `extensions/wrapper.py`

#### Week 8: Agent 完整 API
- Day 1-2: AgentMessage 联合类型 + 动态 API Key
- Day 3-4: Session ID + Thinking budgets
- Day 5-6: `prompt()` 增强 + `waitForIdle()`
- Day 7: Pending tool calls 跟踪

### Phase 3: 增强和优化 (2-3周)

#### Week 9: 工具类 + AI 增强
- Day 1-2: 工具验证增强
- Day 3-4: 完整 CLI OAuth 流程
- Day 5-7: 工具类 (changelog, mime, photon, sleep, tools-manager)

#### Week 10-11: Mom 增强 + 现有文件完善
- Day 1-3: `sandbox.py` 增强 (Docker 支持)
- Day 4-6: `store.py` 增强 (附件处理)
- Day 7-10: `context.py` 增强 (设置管理)

### Phase 4: TUI 和最终打磨 (3-4周，可选)

#### Week 12-15: TUI 组件 (Python 版本)
- **决策**: 选择 TUI 框架 (Textual vs Rich+PromptToolkit)
- **实现**: 35个组件的 Python 等价物
- **注意**: 这是平台特定的，可以根据需求选择性实现

---

## 📈 成功指标

### 代码覆盖率目标

| 模块 | 当前 | Phase 1 后 | Phase 2 后 | 最终 |
|------|------|-----------|-----------|------|
| AI | 90% | 95% | 98% | 100% |
| Agent | 75% | 95% | 100% | 100% |
| Coding | 70% | 80% | 90% | 95% |
| Mom | 10% | 70% | 85% | 95% |
| **总体** | **65%** | **85%** | **93%** | **97%** |

### 功能完整性目标

- ✅ 所有核心 API 可用
- ✅ 所有测试通过 (>95%)
- ✅ 文档完整
- ✅ 性能与 Pi-mono 相当

---

## 🚦 风险和依赖

### 高风险
1. **TUI 组件移植** - 需要 Python 框架选型和重写
2. **扩展系统** - Python 动态导入与 TS 不同
3. **Partial JSON** - 可能需要实现自定义解析器

### 中风险
1. **Mom agent** - 与 Agent 模块深度集成
2. **Docker 支持** - 需要 Docker SDK for Python
3. **性能优化** - Python vs TypeScript 性能差异

### 外部依赖
1. **croniter** - Cron 调度
2. **Docker SDK** - Docker 执行
3. **Textual/Rich** - TUI 框架
4. **partial-json** - 需要找 Python 等价物或实现

---

## 📝 开发规范

### 代码风格
- 使用 Black 格式化
- 类型注解必需 (Python 3.10+)
- 文档字符串使用 Google Style
- 单元测试覆盖率 >80%

### Git 提交规范
```
feat(module): 添加新功能
fix(module): 修复bug
docs: 文档更新
test: 测试相关
refactor: 重构
chore: 杂项
```

### 测试要求
- 每个新功能必须有测试
- 集成测试覆盖主要流程
- Mock 外部 API 调用

---

## 🔗 参考资源

- **Pi-Mono 仓库**: https://github.com/pi-mono/pi-mono
- **本地 Pi-Mono**: `/Users/icetomoyo/Works/GitHub/pi-mono`
- **Koda 仓库**: `/Users/icetomoyo/Works/GitHub/EvoSkill/koda`

---

## 📅 里程碑

- **M1 (Week 5)**: Agent 关键特性和 Mom 核心完成
- **M2 (Week 8)**: 扩展系统完成，Agent API 完整
- **M3 (Week 11)**: 所有核心功能完成
- **M4 (Week 15)**: TUI 和最终打磨完成 (可选)

---

**文档维护者**: @icetomoyo
**最后更新**: 2026-02-12
**版本**: v1.0
