# EvoSkill 功能测试清单

## 1. 基础对话测试

### 1.1 简单对话
```bash
uv run evoskill chat
```
输入：
- `你好，请介绍一下你自己`
- `1+1等于几？`
- `用Python写一个斐波那契数列函数`

**预期结果**：
- [ ] 能正常回复，没有报错
- [ ] 回复内容合理
- [ ] 没有 `list index out of range` 错误

### 1.2 多轮对话
```
You: 你好
AI: 回复...
You: 刚才我说了什么？
```

**预期结果**：
- [ ] AI 能记住上下文，回答"你好"

---

## 2. 工具调用测试

### 2.1 文件读取
```
You: 请读取 README.md 文件的内容
```

**预期结果**：
- [ ] 看到 `▶ 使用工具: read_file`
- [ ] 返回文件内容
- [ ] 没有权限错误

### 2.2 目录浏览
```
You: 列出当前目录的文件
```

**预期结果**：
- [ ] 调用 `list_dir` 工具
- [ ] 显示文件列表

### 2.3 代码搜索
```
You: 搜索项目中所有包含 "class AgentSession" 的文件
```

**预期结果**：
- [ ] 调用 `search_files` 工具
- [ ] 返回匹配的文件和行号

### 2.4 命令执行
```
You: 执行命令 "python --version"
```

**预期结果**：
- [ ] 询问是否确认执行（如果 require_confirmation: true）
- [ ] 执行后返回 Python 版本

---

## 3. 代码编辑测试

### 3.1 查看代码
```
You: 查看 evoskill/core/session.py 的前 50 行
```

**预期结果**：
- [ ] 显示代码内容
- [ ] 有行号标注

### 3.2 编辑代码
```
You: 在 evoskill/core/types.py 中添加一个新类 TestClass
```

**预期结果**：
- [ ] AI 使用 `edit_code` 或 `write_file` 工具
- [ ] 文件被正确修改
- [ ] 可以手动验证文件内容

---

## 4. 配置测试

### 4.1 切换 Provider
编辑配置文件，测试不同提供商：

```yaml
# Kimi For Coding
provider: kimi-coding
model: k2p5
base_url: https://api.kimi.com/coding/v1
```

```yaml
# OpenRouter
provider: openai
model: moonshot/kimi-k2.5
base_url: https://openrouter.ai/api/v1
```

**预期结果**：
- [ ] 每种配置都能正常对话
- [ ] 没有 401/403 认证错误

### 4.2 环境变量测试
```bash
# Windows PowerShell
$env:KIMI_API_KEY="sk-xxxx"
uv run evoskill chat
```

**预期结果**：
- [ ] 不从配置文件读取 key，使用环境变量

---

## 5. Skill 系统测试

### 5.1 创建新 Skill
```
You: /create calculator
AI: 询问 Skill 用途...
You: 创建一个计算器工具，支持加减乘除
```

**预期结果**：
- [ ] 生成 Skill 文件在 `.evoskill/skills/calculator/`
- [ ] 包含 SKILL.md 和 main.py
- [ ] Skill 可以被加载和调用

### 5.2 使用自定义 Skill
```
You: 使用 calculator 计算 123 + 456
```

**预期结果**：
- [ ] 调用 calculator skill
- [ ] 返回正确结果 579

---

## 6. 边界情况测试

### 6.1 大文件处理
```
You: 读取 uv.lock 文件（大文件）
```

**预期结果**：
- [ ] 能读取，不会内存溢出
- [ ] 如果文件太大，应该分段返回

### 6.2 特殊字符
```
You: 创建一个包含中文、emoji 🎉、特殊符号 @#$% 的文件
```

**预期结果**：
- [ ] 文件内容正确，不乱码

### 6.3 空输入
```
You: （直接回车，不输入内容）
```

**预期结果**：
- [ ] 优雅处理，不崩溃

---

## 7. 命令测试

### 7.1 帮助命令
```
You: /help
```

**预期结果**：
- [ ] 显示可用命令列表

### 7.2 Skills 命令
```
You: /skills
```

**预期结果**：
- [ ] 显示已加载的 Skills

### 7.3 清空历史
```
You: /clear
You: 我刚才说了什么？
```

**预期结果**：
- [ ] AI 回答"这是对话的开始"或类似

### 7.4 退出
```
You: /exit
```

**预期结果**：
- [ ] 程序正常退出，无报错

---

## 8. 性能测试

### 8.1 长对话
连续对话 20+ 轮，观察：
- [ ] 响应时间是否变慢
- [ ] 内存占用是否增长
- [ ] 上下文是否正确维护

### 8.2 并发工具调用
```
You: 同时读取 README.md 和 LICENSE 文件
```

**预期结果**：
- [ ] 两个工具都执行成功

---

## 9. 错误处理测试

### 9.1 无效命令
```
You: /invalid_command
```

**预期结果**：
- [ ] 提示未知命令，不崩溃

### 9.2 无效文件路径
```
You: 读取 /etc/passwd（系统文件，应该被拒绝）
```

**预期结果**：
- [ ] 工具返回错误，提示权限问题

### 9.3 网络错误
断开网络后：
```
You: 访问 https://example.com
```

**预期结果**：
- [ ] 优雅提示网络错误

---

## 10. 记录测试结果

完成测试后，记录以下信息：

```markdown
## 测试日期: 2026-02-07
## 测试环境: Windows 11, Python 3.12.9
## 模型: kimi-coding/k2p5

### 通过的测试:
- 基础对话 ✅
- 文件读取 ✅
- ...

### 失败的测试:
- Skill 创建 ❌ (错误信息: ...)
- ...

### 发现的问题:
1. ...
2. ...
```
