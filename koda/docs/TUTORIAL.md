# Koda 教程 - 从入门到进阶

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [基础使用](#基础使用)
4. [工具使用](#工具使用)
5. [高级功能](#高级功能)
6. [最佳实践](#最佳实践)

## 快速开始

### 安装

```bash
# 从源码安装
git clone https://github.com/evoskill/koda.git
cd koda
pip install -e .

# 验证安装
koda --version
```

### 第一个程序

```python
import asyncio
from koda import KodaAgent, Task

# 创建 Mock LLM（实际使用时替换为真实 LLM）
class SimpleLLM:
    async def complete(self, prompt: str, **kwargs) -> str:
        # 这里应该调用真实 LLM API
        return 'print("Hello from Koda!")'

async def main():
    # 创建 Agent
    agent = KodaAgent(llm=SimpleLLM(), verbose=True)
    
    # 定义任务
    task = Task(
        description="Create a hello world program",
        requirements=["Print 'Hello World'", "Use Python"],
    )
    
    # 执行任务
    result = await agent.execute(task)
    
    # 查看结果
    if result.success:
        print("Generated code:")
        print(result.get_main_code())

asyncio.run(main())
```

## 核心概念

### KodaAgent

KodaAgent 是框架的核心，协调所有组件完成代码生成任务。

```python
from koda import KodaAgent, AgentConfig

# 自定义配置
config = AgentConfig(
    max_iterations=5,
    enable_reflection=True,
    verbose=True,
)

agent = KodaAgent(
    llm=llm_adapter,
    config=config,
)
```

### Task

Task 定义要完成的编程任务。

```python
from koda import Task

task = Task(
    description="Create a web scraper",
    requirements=[
        "Fetch web page content",
        "Parse HTML with BeautifulSoup",
        "Extract all links",
        "Save to JSON file",
    ],
    constraints=[
        "Handle HTTP errors",
        "Respect robots.txt",
    ],
)
```

### Tools

工具扩展 Agent 的能力。

```python
from koda.tools.implementations.shell_tool import ShellTool
from koda.tools.implementations.file_tool import FileTool

# 添加工具
agent.add_tool(ShellTool())
agent.add_tool(FileTool("/workspace"))
```

## 基础使用

### 代码生成

```python
result = await agent.execute(task)

if result.success:
    # 获取生成的代码
    code = result.get_main_code()
    
    # 获取所有产物
    for artifact in result.artifacts:
        print(f"{artifact.filename}: {len(artifact.content)} chars")
```

### 流式输出

```python
async for event in agent.execute_stream(task):
    phase = event["phase"]
    status = event["status"]
    
    if phase == "plan":
        print("Planning...")
    elif phase == "execute":
        print(f"Executing iteration {event.get('iteration')}")
    elif phase == "complete":
        print("Done!")
```

### 上下文管理

```python
from koda.core.context import ContextManager

# 创建上下文管理器
ctx = ContextManager("./workspace")

# 加载项目
await ctx.load_project("./my_project")

# 添加对话
await ctx.add_message("user", "Create a weather tool")
await ctx.add_message("assistant", "I'll create that for you")

# 获取历史
history = await ctx.get_conversation_history()
```

## 工具使用

### ShellTool - 执行命令

```python
from koda.tools.implementations.shell_tool import ShellTool

shell = ShellTool(
    working_dir="/workspace",
    timeout=60,
)

# 执行命令
result = await shell.execute("ls -la")
print(result.stdout)

# 批量执行
results = await shell.execute_many([
    "pip install requests",
    "python main.py",
], stop_on_error=True)
```

### FileTool - 文件操作

```python
from koda.tools.implementations.file_tool import FileTool

file_tool = FileTool("/workspace")

# 读写文件
content = await file_tool.read("main.py")
await file_tool.write("test.py", "print('test')")

# 列出文件
files = await file_tool.list(".", pattern="*.py")
for file in files:
    print(f"{file.name} ({file.size} bytes)")
```

### SearchTool - 代码搜索

```python
from koda.tools.implementations.search_tool import SearchTool

search = SearchTool("/workspace")

# 文本搜索
results = await search.search_text("TODO", "*.py")
for r in results:
    print(f"{r.file}:{r.line}: {r.content}")

# 正则搜索
results = await search.search_regex(r"def\s+\w+", "*.py")

# 符号搜索
results = await search.grep_code("my_function", "python")
```

### APITool - HTTP 请求

```python
from koda.tools.implementations.api_tool import APITool

api = APITool(timeout=30)

# GET 请求
result = await api.get("https://api.example.com/data")
print(result.body)

# POST 请求
result = await api.post(
    "https://api.example.com/submit",
    json_data={"key": "value"},
)
```

### GitTool - 版本控制

```python
from koda.tools.implementations.git_tool import GitTool

git = GitTool("/workspace/my_project")

# 基本操作
await git.status()
await git.add(".")
await git.commit("Update code")
await git.push()

# 分支操作
await git.branch("feature/new-tool")
await git.checkout("feature/new-tool")
```

## 高级功能

### 自定义 LLM 适配器

```python
from koda.adapters.base import BaseLLMAdapter

class MyLLMAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
    
    async def complete(self, prompt: str, **kwargs) -> str:
        # 调用你的 LLM API
        response = await call_your_llm(prompt, self.api_key)
        return response
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # 实现对话模式
        pass

# 使用
agent = KodaAgent(llm=MyLLMAdapter("your-api-key"))
```

### 配置管理

```python
from koda.config import KodaConfig, LLMConfig

# 加载配置
config = KodaConfig.load(".koda.yaml")

# 或从环境变量
config = KodaConfig.from_env()

# 修改配置
config.llm.model = "gpt-4"
config.agent.max_iterations = 5

# 保存
config.save(".koda.yaml")
```

### 自定义验证器

```python
from koda.core.validator import Validator

class MyValidator(Validator):
    async def _check_custom(self, code: str) -> Dict[str, Any]:
        # 自定义检查
        if "bad_pattern" in code:
            return {
                "name": "custom",
                "type": "error",
                "message": "Found bad pattern",
                "passed": False,
            }
        return {"name": "custom", "type": "info", "message": "OK", "passed": True}
```

## 最佳实践

### 1. 任务描述要清晰

```python
# 好的描述
task = Task(
    description="Create a REST API client for OpenWeatherMap",
    requirements=[
        "Support current weather endpoint",
        "Handle API key authentication",
        "Parse JSON response",
        "Include error handling for 404/401",
    ],
)

# 不好的描述
task = Task(description="Make a weather app")  # 太模糊
```

### 2. 使用约束限制范围

```python
task = Task(
    description="...",
    constraints=[
        "Use only standard library",
        "Max 100 lines of code",
        "No external dependencies",
    ],
)
```

### 3. 安全检查

```python
from koda.config import SecurityConfig

security = SecurityConfig(
    allow_shell=True,
    blocked_commands=["rm -rf /", "dd"],
    max_execution_time=60,
)
```

### 4. 错误处理

```python
result = await agent.execute(task)

if not result.success:
    print(f"Failed after {result.iterations} iterations")
    print(f"Error: {result.error_message}")
    
    # 查看执行历史
    for exec_result in result.execution_history:
        print(f"Exit code: {exec_result.exit_code}")
```

### 5. 保存重要结果

```python
# 保存生成的代码
for artifact in result.artifacts:
    with open(artifact.filename, 'w') as f:
        f.write(artifact.content)

# 保存会话上下文
await ctx.save_session()
```

## 示例项目

### Web Scraper

```python
task = Task(
    description="Create a web scraper for Hacker News",
    requirements=[
        "Fetch news.ycombinator.com front page",
        "Extract title and URL of top 10 stories",
        "Save to CSV file",
        "Handle network errors",
    ],
    constraints=["Use requests and BeautifulSoup"],
)
```

### CLI Tool

```python
task = Task(
    description="Create a CLI todo list manager",
    requirements=[
        "Add/delete/list todos",
        "Store in JSON file",
        "Use argparse for CLI",
        "Support priorities",
    ],
)
```

### API Server

```python
task = Task(
    description="Create a simple REST API with Flask",
    requirements=[
        "CRUD operations for items",
        "In-memory storage",
        "JSON request/response",
        "Error handling",
    ],
)
```

## 故障排除

### LLM 调用失败

- 检查 API key 是否正确
- 检查网络连接
- 查看 LLM provider 的状态页面

### 代码生成质量差

- 提供更详细的任务描述
- 添加更多约束条件
- 增加 max_iterations
- 启用 reflection

### 工具执行失败

- 检查工具配置
- 查看安全设置
- 检查权限

---

更多文档请参考：
- [API Reference](./API.md)
- [Architecture](./ARCHITECTURE.md)
- [Design](./DESIGN.md)
