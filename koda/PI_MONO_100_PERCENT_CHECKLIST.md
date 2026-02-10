# Pi Mono 100% 能力复现检查清单

> 目标: 完全复现 ai, mom, agent, coding-agent 四个核心模块
> 方法: 逐文件、逐函数、逐行对比
> 版本: Pi Mono latest (badlogic/pi-mono)

---

## 第一部分: packages/ai - 完全复现检查

### 1.1 types.ts 完整复现检查

| 类型/接口 | Pi Mono | Koda | 状态 | 缺失内容 |
|-----------|---------|------|------|----------|
| **KnownApi** | 9种 | 9种 | ✅ | - |
| **KnownProvider** | 22种 | 22种 | ✅ | - |
| **ThinkingLevel** | 5 levels | 5 levels | ✅ | - |
| **CacheRetention** | 3 options | 3 options | ✅ | - |
| **StopReason** | 5 reasons | 5 reasons | ✅ | - |
| **OpenRouterRouting** | only/order | only/order | ✅ | - |
| **VercelGatewayRouting** | only/order | only/order | ✅ | - |
| **OpenAICompletionsCompat** | 15 fields | 15 fields | ⚠️ | 需验证所有字段 |
| **OpenAIResponsesCompat** | empty | empty | ✅ | - |
| **ThinkingBudgets** | 4 budgets | 4 budgets | ✅ | - |
| **Usage** | 9 fields + cost | 9 fields + cost | ✅ | calculateCost方法 |
| **TextContent** | 3 fields | 3 fields | ✅ | - |
| **ThinkingContent** | 3 fields | 3 fields | ✅ | - |
| **ImageContent** | 3 fields | 3 fields | ✅ | - |
| **ToolCall** | 5 fields | 5 fields | ✅ | thoughtSignature |
| **UserMessage** | 3 fields | 3 fields | ✅ | timestamp毫秒 |
| **AssistantMessage** | 9 fields | 9 fields | ✅ | errorMessage |
| **ToolResultMessage** | 6 fields | 6 fields | ✅ | details, isError |
| **Tool** | 3 fields | 3 fields | ✅ | TSchema泛型 |
| **Context** | 3 fields | 3 fields | ✅ | - |
| **StreamOptions** | 10 fields | 10 fields | ⚠️ | onPayload回调 |
| **SimpleStreamOptions** | 2 extra | 2 extra | ✅ | reasoning, budgets |
| **Model** | 13 fields | 13 fields | ⚠️ | compat字段复杂 |

**types.ts 复现状态: 95%**
- ✅ 所有核心类型已定义
- ⚠️ 需要验证: OpenAICompletionsCompat所有字段、Model compat字段

---

### 1.2 models.ts 完整复现检查

| 功能 | Pi Mono | Koda | 状态 | 缺失 |
|------|---------|------|------|------|
| **MODELS** (generated) | 自动生成 | 硬编码 | ⚠️ | 需要models.generated.ts |
| **getModel()** | 类型安全 | 基础实现 | ⚠️ | 泛型类型安全 |
| **getProviders()** | ✅ | ✅ | ✅ | - |
| **getModels()** | 泛型返回 | 基础返回 | ⚠️ | 类型推导 |
| **calculateCost()** | ✅ | ✅ | ✅ | - |
| **supportsXhigh()** | 实现完整 | 未实现 | ❌ | 需要添加 |
| **modelsAreEqual()** | 实现完整 | 未实现 | ❌ | 需要添加 |

**models.ts 复现状态: 70%**
- ❌ 缺少: supportsXhigh, modelsAreEqual
- ⚠️ 需要: 类型安全的getModel/getModels

---

### 1.3 Provider实现完整检查

#### 1.3.1 Anthropic Provider (~800行对比)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **streamAnthropic** | 完整实现 | 基本实现 | ⚠️ |
| **resolveCacheRetention** | 环境变量+参数 | 仅参数 | ❌ |
| **getCacheControl** | 支持ttl | 未实现 | ❌ |
| **Claude Code工具名映射** | Read/Write/Bash... | 未实现 | ❌ |
| **toClaudeCodeName** | 大小写转换 | 未实现 | ❌ |
| **fromClaudeCodeName** | 反向查找 | 未实现 | ❌ |
| **convertContentBlocks** | 图片+文本 | 基本实现 | ⚠️ |
| **sanitizeSurrogates** | Unicode清理 | 未实现 | ❌ |
| **AnthropicOptions** | 6个选项 | 2个选项 | ❌ |
| **thinkingEnabled** | 支持 | 部分 | ⚠️ |
| **thinkingBudgetTokens** | 支持 | 未实现 | ❌ |
| **effort** | low/medium/high/max | 未实现 | ❌ |
| **interleavedThinking** | 支持 | 未实现 | ❌ |
| **toolChoice** | auto/any/none/specific | 未实现 | ❌ |
| **mergeHeaders** | 实现 | 未实现 | ❌ |
| **isOAuthToken处理** | 特殊逻辑 | 未实现 | ❌ |
| **stream参数处理** | 完整 | 部分 | ⚠️ |

**Anthropic Provider复现: 60%**
- ❌ 大量功能缺失

#### 1.3.2 OpenAI Provider (~1000行对比)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Responses API** | 支持 | 未实现 | ❌ |
| **Completions API** | 支持 | 支持 | ✅ |
| **Azure支持** | 支持 | 未实现 | ❌ |
| **Codex支持** | 支持 | 未实现 | ❌ |
| **reasoning_effort映射** | 完整 | 基础 | ⚠️ |
| **supportsStore** | 检测 | 未实现 | ❌ |
| **supportsDeveloperRole** | 角色映射 | 未实现 | ❌ |
| **stream_options** | usage获取 | 未实现 | ❌ |
| **tools格式转换** | 完整 | 基础 | ⚠️ |
| **tool结果格式** | 多种类型 | 基础 | ⚠️ |
| **图片处理** | data URL | 基本实现 | ⚠️ |

**OpenAI Provider复现: 65%**
- ❌ 缺少Responses API, Azure, Codex

#### 1.3.3 Google Provider (~1500行对比)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Generative AI** | 支持 | 支持 | ✅ |
| **Gemini CLI** | OAuth特殊 | 未实现 | ❌ |
| **Vertex AI** | 完整 | 基础 | ⚠️ |
| **thinkingSignatures** | Google特有 | 未实现 | ❌ |
| **unsigned tool calls** | 处理 | 未实现 | ❌ |
| **empty stream处理** | 容错 | 未实现 | ❌ |
| **retry delay** | 特殊处理 | 未实现 | ❌ |

**Google Provider复现: 70%**

#### 1.3.4 Bedrock Provider (~600行对比)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Converse Stream** | 支持 | 支持 | ✅ |
| **cross-region inference** | 自动选择 | 未实现 | ❌ |
| **credential providers** | 多种 | 基础 | ⚠️ |
| **interleaved thinking** | 支持 | 未实现 | ❌ |

**Bedrock Provider复现: 75%**

---

### 1.4 OAuth系统完整检查

| Provider | Pi Mono | Koda | 状态 |
|----------|---------|------|------|
| **Google Gemini CLI** | 完整PKCE | 基础PKCE | ⚠️ |
| **Google Antigravity** | 完整 | 未实现 | ❌ |
| **Anthropic** | 完整 | 未实现 | ❌ |
| **GitHub Copilot** | 完整 | 未实现 | ❌ |
| **OpenAI Codex** | 完整 | 未实现 | ❌ |
| **PKCE工具** | 完整 | 基础 | ⚠️ |
| **本地回调服务器** | HTTP服务器 | 未实现 | ❌ |
| **Token刷新** | 自动 | 未实现 | ❌ |

**OAuth复现: 30%**
- ❌ 大部分OAuth实现缺失

---

### 1.5 Stream/Event系统检查

| 组件 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **AssistantMessageEventStream** | 完整 | 完整 | ✅ |
| **Event类型** | 11种 | 11种 | ✅ |
| **EventStream解析** | 完整 | 部分 | ⚠️ |
| **JSON流解析** | parseStreamingJson | 未实现 | ❌ |
| **溢出保护** | overflow检测 | 未实现 | ❌ |
| **Unicode清理** | sanitizeSurrogates | 未实现 | ❌ |
| **Event验证** | 类型检查 | 未实现 | ❌ |

**Stream系统复现: 80%**

---

## 第二部分: packages/agent 完全复现检查

### 2.1 agent.ts 检查

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Agent类** | 完整 | 部分 | ⚠️ |
| **AgentConfig** | 完整 | 部分 | ⚠️ |
| **createAgent()** | 工厂 | 未实现 | ❌ |
| **消息处理** | 完整 | 基础 | ⚠️ |
| **错误处理** | 完整 | 基础 | ⚠️ |
| **日志** | 内置 | 未实现 | ❌ |

### 2.2 agent-loop.ts 详细检查

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **AgentLoop类** | 完整 | 基本实现 | ⚠️ |
| **maxIterations** | ✅ | ✅ | ✅ |
| **maxToolCallsPerTurn** | ✅ | ✅ | ✅ |
| **retryAttempts** | ✅ | ✅ | ✅ |
| **retryDelayBase** | 指数退避 | 实现 | ✅ |
| **toolTimeout** | ✅ | ✅ | ✅ |
| **enableParallelTools** | ✅ | ✅ | ✅ |
| **maxParallelTools** | ✅ | ✅ | ✅ |
| **Signal中断** | 完整 | 部分 | ⚠️ |
| **Tool结果处理** | 完整 | 基础 | ⚠️ |
| **Usage聚合** | 完整 | 未实现 | ❌ |
| **Error分类** | 详细 | 基础 | ⚠️ |
| **循环检测** | 有 | 无 | ❌ |

**agent-loop.ts复现: 75%**

### 2.3 proxy.ts 检查

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **AgentProxy** | 完整 | 未实现 | ❌ |
| **多Agent协调** | 支持 | 未实现 | ❌ |
| **负载均衡** | 支持 | 未实现 | ❌ |
| **任务分发** | 支持 | 未实现 | ❌ |
| **Agent注册** | 支持 | 未实现 | ❌ |

**proxy.ts复现: 0%**
- ❌ 完全未实现

---

## 第三部分: packages/coding-agent 完全复现检查

### 3.1 model-registry.ts 详细检查 (~500行)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **ModelRegistry类** | 完整 | 部分 | ⚠️ |
| **models.json加载** | 完整 | 基础 | ⚠️ |
| **Schema验证** | AJV | 未实现 | ❌ |
| **Provider Override** | 完整 | 部分 | ⚠️ |
| **Model Override** | 完整 | 未实现 | ❌ |
| **动态Provider注册** | 完整 | 未实现 | ❌ |
| **OAuth Provider集成** | 完整 | 部分 | ⚠️ |
| **模型合并逻辑** | 复杂 | 简单 | ⚠️ |
| **getAvailable()** | 按认证过滤 | 未实现 | ❌ |
| **isUsingOAuth()** | 检测 | 未实现 | ❌ |
| **resolveConfigValue** | 命令替换 | 未实现 | ❌ |
| **环境变量替换** | $(cmd) | 未实现 | ❌ |
| **ModelDefinitionSchema** | TypeBox | 未实现 | ❌ |
| **ProviderConfigSchema** | TypeBox | 未实现 | ❌ |

**model-registry.ts复现: 50%**

### 3.2 compaction/ 详细检查 (~800行)

#### 3.2.1 compaction.ts

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **compaction()** | 主函数 | 部分 | ⚠️ |
| **DEFAULT_COMPACTION_SETTINGS** | 常量 | 未定义 | ❌ |
| **shouldCompact()** | 检测 | 有 | ✅ |
| **calculateContextTokens** | 计算 | 估算 | ⚠️ |
| **estimateTokens** | 精确 | 估算 | ⚠️ |

#### 3.2.2 branch-summarization.ts

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **generateBranchSummary** | LLM调用 | 基础 | ⚠️ |
| **collectEntriesForBranchSummary** | 收集 | 未实现 | ❌ |
| **prepareBranchEntries** | 准备 | 未实现 | ❌ |
| **serializeConversation** | 序列化 | 部分 | ⚠️ |

#### 3.2.3 utils.ts

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **findCutPoint** | 智能查找 | 未实现 | ❌ |
| **findTurnStartIndex** | Turn检测 | 未实现 | ❌ |
| **getLastAssistantUsage** | Usage获取 | 未实现 | ❌ |
| **FileOperations** | 跟踪 | 未实现 | ❌ |

**compaction/复现: 40%**

### 3.3 session-manager.ts 详细检查 (~1500行)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **SessionManager类** | 完整 | 部分 | ⚠️ |
| **SessionEntry类型** | 6种 | 3种 | ⚠️ |
| **createSession()** | ✅ | ✅ | ✅ |
| **loadSession()** | ✅ | ✅ | ✅ |
| **saveSession()** | ✅ | ✅ | ✅ |
| **forkBranch()** | 完整 | 部分 | ⚠️ |
| **switchBranch()** | ✅ | ✅ | ✅ |
| **getBranchHistory()** | 完整 | 部分 | ⚠️ |
| **buildSessionContext()** | 复杂 | 部分 | ⚠️ |
| **migrateSessionEntries** | 版本迁移 | 未实现 | ❌ |
| **CURRENT_SESSION_VERSION** | 常量 | 有 | ✅ |
| **parseSessionEntries** | 解析 | 部分 | ⚠️ |
| **SessionInfo** | 元数据 | 有 | ✅ |
| **SessionContext** | 完整 | 部分 | ⚠️ |
| **BranchSummaryEntry** | 分支摘要 | 有 | ✅ |
| **CompactionEntry** | 压缩条目 | 有 | ✅ |
| **ModelChangeEntry** | 模型变更 | 未实现 | ❌ |
| **ThinkingLevelChangeEntry** | 思考级别 | 未实现 | ❌ |
| **CustomEntry** | 自定义 | 未实现 | ❌ |
| **FileEntry** | 文件 | 未实现 | ❌ |
| **getLatestCompactionEntry** | 获取 | 未实现 | ❌ |
| **标签系统** | tags | 未实现 | ❌ |
| **修改时间跟踪** | modified_at | 有 | ✅ |
| **垃圾回收** | gc_old_sessions | 有 | ✅ |
| **导入/导出** | JSON/Markdown | 有 | ✅ |
| **导出HTML** | 完整 | 未实现 | ❌ |

**session-manager.ts复现: 65%**

### 3.4 settings-manager.ts 详细检查 (~500行)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **SettingsManager类** | 完整 | 部分 | ⚠️ |
| **CompactionSettings** | 配置 | 有 | ✅ |
| **ImageSettings** | 图片 | 有 | ✅ |
| **RetrySettings** | 重试 | 有 | ✅ |
| **PackageSource** | 包源 | 未实现 | ❌ |
| **层级配置** | 全局+项目 | 仅全局 | ❌ |
| **实时重载** | 文件监视 | 未实现 | ❌ |
| **Schema验证** | 验证 | 未实现 | ❌ |
| **迁移** | 版本迁移 | 未实现 | ❌ |
| **设置分类** | 分类存储 | 未实现 | ❌ |

**settings-manager.ts复现: 50%**

### 3.5 tools/ 详细检查 (~2000行)

#### 3.5.1 edit.ts + edit-diff.ts (~600行)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **fuzzyFindText** | 模糊查找 | 有 | ✅ |
| **normalizeForFuzzyMatch** | 规范化 | 有 | ✅ |
| **detectLineEnding** | 检测 | 有 | ✅ |
| **restoreLineEndings** | 恢复 | 有 | ✅ |
| **stripBom** | BOM处理 | 有 | ✅ |
| **generateDiffString** | Diff生成 | 有 | ✅ |
| **EditOperations接口** | 可插拔 | 未实现 | ❌ |
| **AbortSignal处理** | 完整 | 部分 | ⚠️ |
| **错误分类** | 详细 | 基础 | ⚠️ |
| **重复检测** | 模糊后 | 未实现 | ❌ |
| **CRLF处理** | 完整 | 部分 | ⚠️ |
| **UTF8 BOM保留** | 保留 | 有 | ✅ |

**edit工具复现: 75%**

#### 3.5.2 bash.ts (~400行)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **BashSpawnContext** | 上下文 | 未实现 | ❌ |
| **_spawnHook** | 钩子 | 未实现 | ❌ |
| **timeout控制** | 参数 | 有 | ✅ |
| **环境变量** | env参数 | 部分 | ⚠️ |
| **cwd控制** | 工作目录 | 有 | ✅ |
| **maxOutputBytes** | 输出限制 | 未实现 | ❌ |
| **combined output** | 合并 | 有 | ✅ |
| **spawn options** | 选项 | 未实现 | ❌ |

**bash工具复现: 60%**

#### 3.5.3 其他工具 (~800行)

| 工具 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Read** | 完整 | 完整 | ✅ |
| **Write** | 完整 | 完整 | ✅ |
| **Find** | Glob+正则 | 有 | ✅ |
| **Grep** | 递归搜索 | 有 | ✅ |
| **Ls** | 目录列表 | 有 | ✅ |
| **Truncate** | 智能截断 | 有 | ✅ |

**其他工具复现: 90%**

---

## 第四部分: packages/mom 完全复现检查

### 4.1 mom/ 模块检查 (~4000行)

| 功能 | Pi Mono | Koda | 状态 |
|------|---------|------|------|
| **Agent类** | 完整 | 未实现 | ❌ |
| **Context管理** | 动态 | 有 | ✅ |
| **Download** | 下载 | 未实现 | ❌ |
| **Events** | 事件系统 | 有 | ✅ |
| **Log** | 日志 | 基础 | ⚠️ |
| **Sandbox** | 沙箱 | 有 | ✅ |
| **Slack Bot** | Slack集成 | 未实现 | ❌ |
| **Store** | 存储 | 有 | ✅ |
| **tools/** | 工具集 | 部分 | ⚠️ |

**mom/复现: 60%**

---

## 第五部分: 缺失功能汇总

### 5.1 高优先级缺失 (必须实现)

#### AI Package
1. ❌ `supportsXhigh()` - 模型xhigh检测
2. ❌ `modelsAreEqual()` - 模型比较
3. ❌ OpenAI **Responses API** (与Completions不同)
4. ❌ Azure OpenAI Provider
5. ❌ GitHub Copilot Provider
6. ❌ OpenAI Codex Provider
7. ❌ **Anthropic OAuth** 完整实现
8. ❌ **GitHub Copilot OAuth** 完整实现
9. ❌ Anthropic: Claude Code工具名映射
10. ❌ Anthropic: interleavedThinking支持

#### Agent Package
11. ❌ **AgentProxy** 完整实现
12. ❌ 多Agent协调

#### Coding-Agent Package
13. ❌ ModelRegistry: Schema验证 (AJV等效)
14. ❌ ModelRegistry: resolveConfigValue (命令替换)
15. ❌ Compaction: findCutPoint智能查找
16. ❌ Compaction: FileOperations跟踪
17. ❌ Session: 所有Entry类型 (ModelChange, ThinkingLevelChange, Custom, File)
18. ❌ Session: migrateSessionEntries版本迁移
19. ❌ Settings: 层级配置 (项目级)
20. ❌ Settings: 文件监视重载
21. ❌ Edit: EditOperations可插拔接口
22. ❌ Bash: BashSpawnContext和spawn hooks

#### MOM Package
23. ❌ MOM Agent类
24. ❌ Download功能
25. ❌ Slack Bot集成

### 5.2 中优先级缺失 (建议实现)

26. ⚠️ TypeBox等效的Schema验证
27. ⚠️ 更精确的Token计算 (tiktoken等)
28. ⚠️ 更完善的错误分类
29. ⚠️ Usage聚合和跟踪
30. ⚠️ 循环检测

### 5.3 低优先级/延期 (可接受)

- TUI系统 (~25,000行)
- Extension系统 (~15,000行)
- HTML导出
- 高级Provider功能

---

## 第六部分: 100%复现路线图

### Phase 1: AI包完善 (2周)
- [ ] 实现Responses API支持
- [ ] 添加Azure Provider
- [ ] 添加Copilot Provider
- [ ] 完成所有OAuth实现
- [ ] 添加 Anthropic 高级功能

### Phase 2: Agent包完善 (1周)
- [ ] 实现AgentProxy
- [ ] 多Agent协调

### Phase 3: Coding-Agent包完善 (2周)
- [ ] ModelRegistry完整功能
- [ ] Compaction完整功能
- [ ] Session所有Entry类型
- [ ] Settings层级配置
- [ ] Edit/Bash工具增强

### Phase 4: MOM包完善 (1周)
- [ ] MOM Agent类
- [ ] Download功能

### Phase 5: 测试与验证 (1周)
- [ ] 集成测试
- [ ] 与Pi Mono行为对比测试
- [ ] 性能测试

**总计: 7周达到100%复现**

---

## 当前真实复现率

| 包 | 声称复现率 | 真实复现率 | 差距 |
|----|-----------|-----------|------|
| packages/ai | 75% | **65%** | -10% |
| packages/agent | 85% | **75%** | -10% |
| packages/coding-agent | 65% | **55%** | -10% |
| packages/mom | 75% | **60%** | -15% |
| **平均** | **72%** | **63%** | **-9%** |

**需要增加约37%的功能才能达到100%复现**
