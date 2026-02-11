# Koda Implementation Action Plan

> 基于详细审计的补全计划
> 创建时间: 2026-02-10

---

## 📋 缺失文件清单 (共11个)

### Phase 10: 关键缺失 (3个文件) - Priority: 🔴 High

#### 1. `koda/ai/env_api_keys.py`
**对应**: `packages/ai/src/env-api-keys.ts` (~100 lines)
**功能**: 从环境变量读取API Keys
**重要性**: 🔴 High
**预计时间**: 1-2小时
**依赖**: 无

**功能要点**:
- 读取 `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` 等标准环境变量
- 支持自定义前缀
- 提供默认值和验证

---

#### 2. `koda/ai/providers/register_builtins.py`
**对应**: `packages/ai/src/providers/register-builtins.ts` (~200 lines)
**功能**: 自动注册所有内置providers
**重要性**: 🔴 High
**预计时间**: 2-3小时
**依赖**: 所有providers已实现

**功能要点**:
- 自动发现并注册所有内置provider类
- Provider优先级管理
- 动态加载机制

---

#### 3. `koda/ai/utils/typebox_helpers.py`
**对应**: `packages/ai/src/utils/typebox-helpers.ts` (~200 lines)
**功能**: JSON Schema完整验证
**重要性**: 🔴 High
**预计时间**: 3-4小时
**依赖**: `json_schema.py` 已存在

**功能要点**:
- 完整的JSON Schema验证
- TypeBox风格的类型构造
- 错误信息格式化

---

### Phase 11: OAuth扩展 (3个文件) - Priority: 🟡 Medium

#### 4. `koda/ai/oauth/google_antigravity.py`
**对应**: `packages/ai/src/utils/oauth/google-antigravity.ts`
**功能**: Google Antigravity OAuth流程
**重要性**: 🟡 Medium
**预计时间**: 3-4小时
**依赖**: OAuth基础结构

---

#### 5. `koda/ai/oauth/google_gemini_cli.py`
**对应**: `packages/ai/src/utils/oauth/google-gemini-cli.ts`
**功能**: Gemini CLI OAuth流程
**重要性**: 🟡 Medium
**预计时间**: 3-4小时
**依赖**: OAuth基础结构

---

#### 6. `koda/ai/oauth/openai_codex_oauth.py`
**对应**: `packages/ai/src/utils/oauth/openai-codex.ts`
**功能**: OpenAI Codex OAuth流程
**重要性**: 🟡 Medium
**预计时间**: 3-4小时
**依赖**: OAuth基础结构

---

### Phase 12: Provider共享代码 (2个文件) - Priority: 🟢 Low

#### 7. `koda/ai/providers/openai_shared.py`
**对应**: `packages/ai/src/providers/openai-responses-shared.ts` (~300 lines)
**功能**: OpenAI Responses共享代码
**重要性**: 🟢 Low (代码复用)
**预计时间**: 2小时
**依赖**: 无

---

#### 8. `koda/ai/providers/google_shared.py`
**对应**: `packages/ai/src/providers/google-shared.ts` (~400 lines)
**功能**: Google Provider共享代码
**重要性**: 🟢 Low (代码复用)
**预计时间**: 2小时
**依赖**: 无

---

### Phase 13: 重构优化 (3个文件) - Priority: 🟢 Optional

#### 9. 重构 `koda/ai/oauth.py` 为目录结构
**当前**: 单文件 (~600 lines)
**目标**: `koda/ai/oauth/` 目录
    - `__init__.py`
    - `base.py`
    - `google.py`
    - `anthropic.py`
    - `github_copilot.py`
    - `pkce.py`
**重要性**: 🟢 Optional
**预计时间**: 半天
**依赖**: 无

---

#### 10. 重构 `koda/coding/tools/edit_*.py` 合并
**当前**: 4个文件
**目标**: 统一Edit工具
**重要性**: 🟢 Optional
**预计时间**: 半天
**依赖**: 无

---

#### 11. 完善 `koda/coding/modes/interactive.py`
**当前**: 简化版
**目标**: 完整Interactive模式
**重要性**: 🟢 Optional
**预计时间**: 1-2天
**依赖**: 无

---

## 📊 时间估算

| Phase | 文件数 | 预计时间 | 优先级 |
|-------|--------|----------|--------|
| Phase 10 | 3 | 6-9小时 | 🔴 High |
| Phase 11 | 3 | 9-12小时 | 🟡 Medium |
| Phase 12 | 2 | 4小时 | 🟢 Low |
| Phase 13 | 3 | 2-3天 | 🟢 Optional |
| **总计** | **11** | **2-4天** | - |

---

## 🎯 推荐执行顺序

### Week 1: 关键功能补全 (Phase 10)

**Day 1-2**:
- [ ] 实现 `env_api_keys.py`
- [ ] 实现 `register_builtins.py`
- [ ] 更新 `__init__.py` 导出

**Day 3-4**:
- [ ] 实现 `typebox_helpers.py`
- [ ] 测试验证
- [ ] 文档更新

### Week 2: OAuth扩展 (Phase 11)

**Day 1-2**:
- [ ] 实现 `google_antigravity.py`
- [ ] 实现 `google_gemini_cli.py`

**Day 3-4**:
- [ ] 实现 `openai_codex_oauth.py`
- [ ] 测试验证

### Week 3: 代码优化 (Phase 12-13)

**Day 1-2**:
- [ ] 实现共享代码文件
- [ ] 重构OAuth目录

**Day 3-5**:
- [ ] 重构Edit工具
- [ ] 完善Interactive模式 (可选)

---

## ✅ 验收标准

### Phase 10 验收

- [ ] `env_api_keys.py` 能正确读取环境变量
- [ ] `register_builtins.py` 自动注册所有providers
- [ ] `typebox_helpers.py` 通过所有schema测试

### Phase 11 验收

- [ ] 所有OAuth provider能独立完成认证流程
- [ ] 支持token刷新
- [ ] 错误处理完善

### Phase 12 验收

- [ ] 代码复用率提升
- [ ] 无重复代码
- [ ] 所有测试通过

---

## 📈 完成度预测

| 阶段 | 当前 | Phase 10 | Phase 11 | Phase 12 | 最终 |
|------|------|----------|----------|----------|------|
| 完成度 | 96.9% | 98% | 99% | 99.5% | 99.9% |

---

## 🚀 立即开始

准备好后，请告诉我：
1. "开始Phase 10" - 实现关键缺失文件
2. "开始Phase 11" - 实现OAuth扩展
3. "开始Phase 12" - 实现共享代码
4. "开始Phase 13" - 重构优化

或者指定具体文件：
- "实现 env_api_keys.py"
- "实现 register_builtins.py"
- 等等

---

*计划创建时间: 2026-02-10*
*基于审计: 07_COMPREHENSIVE_AUDIT.md*
