# Pi Coding Agent 能力审计清单

## 1. 核心架构对比

### 1.1 Agent 主类

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 状态管理 | AgentState (系统提示词、模型、工具、消息) | AgentConfig + TreeSession | ✅ |
| 事件订阅 | subscribe() 方法 | 暂缺，需添加 | ❌ |
| 流式处理 | agentLoop() 生成器 | execute_stream() | ✅ |
| 工具调用 | pendingToolCalls Set | 暂缺，需添加 | ❌ |
| Steering 队列 | steeringQueue | 暂缺，需添加 | ❌ |
| Follow-up 队列 | followUpQueue | 暂缺，需添加 | ❌ |
| 会话ID | sessionId | session_id | ✅ |
| 中止控制 | AbortController | 暂缺，需添加 | ❌ |

### 1.2 Agent 执行循环

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 上下文转换 | convertToLlm() | 直接传递 | ⚠️ |
| Steering 处理 | 中断当前工具链 | 暂不支持 | ❌ |
| 工具调用执行 | 并行执行所有工具 | 顺序执行 | ⚠️ |
| 流式事件 | text_delta, thinking_delta, tool_call | 简化版本 | ⚠️ |
| Turn 管理 | turn_start, turn_end | 暂缺 | ❌ |
| 错误处理 | 详细的错误事件 | 基础错误处理 | ⚠️ |

## 2. 工具系统对比

### 2.1 Read 工具

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 基本读取 | ✅ | FileTool.read | ✅ |
| offset/limit | ✅ 支持 | ❌ 暂不支持 | ❌ |
| 图片读取 | ✅ 自动调整大小 | ❌ 不支持 | ❌ |
| 截断处理 | ✅ 头部截断 | ❌ 简单读取 | ❌ |
| BOM 处理 | ✅ 处理 UTF-8 BOM | ❌ 未处理 | ❌ |
| 继续提示 | ✅ "Use offset=X to continue" | ❌ 无提示 | ❌ |

### 2.2 Write 工具

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 基本写入 | ✅ | FileTool.write | ✅ |
| 自动创建父目录 | ✅ | ✅ | ✅ |
| 覆盖确认 | ❌ 直接覆盖 | 直接覆盖 | ✅ |
| 写入反馈 | ✅ "Wrote X bytes" | 无反馈 | ❌ |

### 2.3 Edit 工具

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 精确文本替换 | ✅ 模糊匹配+精确替换 | ❌ 未实现 | ❌ |
| 换行符处理 | ✅ 检测并保留 | ❌ 未处理 | ❌ |
| BOM 保留 | ✅ 检测并保留 | ❌ 未处理 | ❌ |
| 重复匹配检测 | ✅ 检测多个匹配 | ❌ 未实现 | ❌ |
| Diff 生成 | ✅ 生成变更对比 | ❌ 未实现 | ❌ |
| 失败反馈 | ✅ 详细错误信息 | ❌ 未实现 | ❌ |

### 2.4 Bash 工具

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 基本执行 | ✅ | ShellTool.execute | ✅ |
| 超时支持 | ✅ | ✅ | ✅ |
| 流式输出 | ✅ onUpdate 回调 | ❌ 仅返回结果 | ❌ |
| 尾部截断 | ✅ 保留最后50KB | ❌ 无截断 | ❌ |
| 临时文件 | ✅ 大输出写入文件 | ❌ 未实现 | ❌ |
| 滚动缓冲区 | ✅ 内存中保留最近数据 | ❌ 未实现 | ❌ |
| 退出码处理 | ✅ 详细处理 | 基础处理 | ⚠️ |
| 环境变量 | ✅ 支持自定义 env | 暂不支持 | ❌ |

### 2.5 额外工具（Pi 特有）

| 工具 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| Grep | ✅ | SearchTool.search_text | ✅ |
| Find | ✅ | SearchTool.find_files | ✅ |
| Ls | ✅ | FileTool.list | ✅ |

### 2.6 截断处理

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 默认限制 | 50KB / 2000行 | 无限制 | ❌ |
| 头部截断 | ✅ truncateHead | ❌ 未实现 | ❌ |
| 尾部截断 | ✅ truncateTail | ❌ 未实现 | ❌ |
| 首行超长处理 | ✅ 特殊处理 | ❌ 未实现 | ❌ |
| 截断提示 | ✅ 详细提示 | ❌ 无提示 | ❌ |

## 3. 树状会话对比

### 3.1 数据结构

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| ID 格式 | 8-char hex | 8-char hex | ✅ |
| Parent ID | ✅ parentId | ✅ parent_id | ✅ |
| 时间戳 | ✅ ISO 格式 | ✅ ISO 格式 | ✅ |
| 条目类型 | 多种类型（message/compaction/label等） | 仅 message/node | ⚠️ |
| JSONL 存储 | ✅ 每行独立 | ✅ 类似实现 | ✅ |

### 3.2 Pi 特有条目类型（Koda 暂缺）

| 类型 | 用途 | Koda 状态 |
|------|------|-----------|
| ThinkingLevelChangeEntry | 思考级别变更 | ❌ 未实现 |
| ModelChangeEntry | 模型切换 | ❌ 未实现 |
| CompactionEntry | 上下文压缩 | ❌ 未实现 |
| BranchSummaryEntry | 分支摘要 | ❌ 未实现（重要）|
| CustomEntry | 扩展自定义数据 | ❌ 未实现 |
| LabelEntry | 用户标签 | ❌ 未实现 |

### 3.3 树导航

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| getBranch() | ✅ 根到叶子路径 | ✅ get_path_to_root | ✅ |
| getTree() | ✅ 完整树结构 | ✅ get_tree_visualization | ✅ |
| getChildren() | ✅ 获取子节点 | ❌ 未实现 | ❌ |
| branch() | ✅ 在指定点创建分支 | ✅ create_branch | ✅ |
| createBranchedSession() | ✅ 提取到新文件 | ❌ 未实现 | ❌ |

### 3.4 分支摘要

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 自动生成摘要 | ✅ navigateTree 时生成 | ❌ 未实现 | ❌ |
| 自定义指令 | ✅ 支持 customInstructions | ❌ 未实现 | ❌ |
| 摘要存储 | ✅ BranchSummaryEntry | ❌ 未实现 | ❌ |

## 4. 扩展系统对比

### 4.1 扩展 API

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| on() 事件订阅 | ✅ | ❌ 未实现 | ❌ |
| registerTool() | ✅ | ✅ load_extension | ✅ |
| getActiveTools() | ✅ | ❌ 未实现 | ❌ |
| setActiveTools() | ✅ | ❌ 未实现 | ❌ |
| registerCommand() | ✅ /commands | ❌ 未实现 | ❌ |
| registerShortcut() | ✅ 键盘快捷键 | ❌ 未实现 | ❌ |
| registerFlag() | ✅ CLI 标志 | ❌ 未实现 | ❌ |
| sendMessage() | ✅ 消息注入 | ❌ 未实现 | ❌ |
| appendEntry() | ✅ 持久化状态 | ✅ (session级别) | ⚠️ |
| setSessionName() | ✅ | ❌ 未实现 | ❌ |
| setLabel() | ✅ 用户标签 | ❌ 未实现 | ❌ |
| setModel() | ✅ | ❌ 未实现 | ❌ |
| setThinkingLevel() | ✅ | ❌ 未实现 | ❌ |
| exec() | ✅ 执行命令 | ❌ 未实现 | ❌ |
| events EventBus | ✅ 扩展间通信 | ❌ 未实现 | ❌ |

### 4.2 扩展上下文

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| UI 交互 | ✅ notify/confirm/select/input | ❌ 未实现 | ❌ |
| TUI 组件 | ✅ setWidget/setFooter等 | ❌ 未实现 | ❌ |
| hasUI 标志 | ✅ | ❌ 未实现 | ❌ |
| 会话管理 | ✅ ReadonlySessionManager | ⚠️ 部分实现 | ⚠️ |
| 模型注册表 | ✅ ModelRegistry | ❌ 未实现 | ❌ |
| abort() | ✅ | ❌ 未实现 | ❌ |
| compact() | ✅ 触发压缩 | ❌ 未实现 | ❌ |
| getContextUsage() | ✅ | ❌ 未实现 | ❌ |
| getSystemPrompt() | ✅ | ❌ 未实现 | ❌ |

### 4.3 扩展加载

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| TypeScript 支持 | ✅ jiti | ⚠️ Python 直接加载 | ⚠️ |
| 全局扩展目录 | ✅ ~/.pi/extensions | ❌ 未实现 | ❌ |
| 项目本地扩展 | ✅ ./.pi/extensions | ✅ 临时目录 | ⚠️ |
| npm 包扩展 | ✅ | ❌ 未实现 | ❌ |
| 错误处理 | ✅ 记录但不中断 | ✅ 异常抛出 | ⚠️ |
| 热重载 | ✅ /reload 命令 | ✅ hot_reload | ✅ |

## 5. 系统提示词对比

### 5.1 构建器

| 特性 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| buildSystemPrompt() | ✅ 动态构建 | ❌ 硬编码 | ❌ |
| 自定义提示词 | ✅ customPrompt | ❌ 未实现 | ❌ |
| 选中工具过滤 | ✅ selectedTools | ❌ 未实现 | ❌ |
| 追加内容 | ✅ appendSystemPrompt | ❌ 未实现 | ❌ |
| 上下文文件 | ✅ contextFiles (AGENTS.md) | ❌ 未实现 | ❌ |
| Skills 支持 | ✅ | ⚠️ 部分实现 | ⚠️ |
| 日期时间 | ✅ | ⚠️ 部分实现 | ⚠️ |
| 工作目录 | ✅ | ✅ | ✅ |

### 5.2 提示词内容

| 内容 | Pi Coding Agent | Koda V2 | 状态 |
|------|----------------|---------|------|
| 工具描述 | ✅ 动态生成 | ❌ 硬编码 | ❌ |
| 使用指南 | ✅ 根据工具动态生成 | ❌ 未实现 | ❌ |
| Pi 文档引用 | ✅ 文档内省 | ❌ 不适用 | N/A |
| 项目上下文 | ✅ AGENTS.md | ❌ 未实现 | ❌ |
| Skills 注入 | ✅ 格式化注入 | ⚠️ 部分实现 | ⚠️ |

## 6. 缺失功能总结

### 高优先级（必须实现）

1. **Edit 工具** - Pi 的核心工具，精确文本替换
2. **截断处理** - 50KB/2000行限制 + 头部/尾部截断
3. **分支摘要** - 切换分支时自动生成摘要
4. **系统提示词构建器** - 动态构建，支持上下文文件
5. **事件系统** - on() 订阅，支持扩展拦截

### 中优先级（重要功能）

6. **Steering 队列** - 中断当前工具链
7. **Bash 流式输出** - onUpdate 回调 + 尾部截断
8. **扩展上下文 API** - UI 交互、模型控制等
9. **Compaction** - 上下文压缩
10. **标签系统** - setLabel/getLabel

### 低优先级（增强功能）

11. **图片处理** - 读取和调整图片大小
12. **命令注册** - /command 系统
13. **快捷键** - 键盘快捷键绑定
14. **标志注册** - CLI 标志
15. **模型注册表** - 动态模型管理

## 7. 实现建议

### 立即实现（本周）

1. EditTool - 精确文本替换，参考 Pi 的模糊匹配+精确替换算法
2. Truncation - 头部/尾部截断，50KB/2000行限制
3. SystemPromptBuilder - 动态构建提示词

### 短期实现（本月）

4. EventSystem - 事件订阅和拦截
5. BranchSummary - 切换分支时自动生成摘要
6. BashTool 流式输出 - onUpdate 回调

### 中期实现（下月）

7. ExtensionContext API - UI 交互、模型控制
8. Compaction - 上下文压缩
9. LabelSystem - 用户标签

## 8. 核心差异总结

### Pi Coding Agent 优势
- 极简但完整的工具集（特别是 Edit 工具）
- 精细的截断处理
- 强大的扩展系统（事件驱动）
- 成熟的树状会话管理
- 完善的系统提示词构建

### Koda V2 优势
- 自验证循环（Pi 没有）
- 模块化设计（Planner/Executor/Validator/Reflector）
- Python 生态（Pi 是 TypeScript）
- EvoSkill 集成

### 需要融合的点
Koda 需要吸收 Pi 的：
1. Edit 工具实现
2. 截断处理策略
3. 系统提示词构建器
4. 事件系统
5. 分支摘要

同时保持 Koda 的：
1. 自验证能力
2. 模块化架构
3. Python 实现
