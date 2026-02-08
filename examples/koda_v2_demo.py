"""
Koda V2 Demo - 展示新特性

- 树状会话管理
- 自扩展机制
- 自验证循环
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class MockLLM:
    """Mock LLM for demo"""
    
    async def complete(self, prompt: str, **kwargs) -> str:
        prompt_lower = prompt.lower()
        
        # 分析工具需求
        if "analyze what tools" in prompt_lower or "needed" in prompt_lower:
            if "weather" in prompt_lower:
                return "- Weather API client\n- Data parser"
            return "- File reader\n- HTTP client"
        
        # 生成扩展
        if "write a python tool class" in prompt_lower:
            return '''
class WeatherAPITool:
    """Tool to fetch weather data"""
    
    def __init__(self, api_key=""):
        self.api_key = api_key
    
    async def execute(self, city: str) -> dict:
        """Fetch weather for a city"""
        import urllib.request
        import json
        
        try:
            # Mock implementation for demo
            return {
                "success": True,
                "result": {"city": city, "temp": 25, "condition": "sunny"}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
'''
        
        # 生成代码
        if "write python code" in prompt_lower:
            return '''
import asyncio

async def get_weather(city: str) -> dict:
    """Get weather for a city"""
    # Using self-written WeatherAPITool
    tool = WeatherAPITool()
    return await tool.execute(city)

if __name__ == "__main__":
    result = asyncio.run(get_weather("Beijing"))
    print(result)
'''
        
        # 生成文档
        if "write documentation" in prompt_lower:
            return "# Weather Tool\n\nFetches weather data from API."
        
        # 修复代码
        if "fix this python code" in prompt_lower:
            return '''
import asyncio

async def get_weather(city: str) -> dict:
    """Get weather for a city - FIXED"""
    return {"success": True, "result": {"city": city, "temp": 25}}

if __name__ == "__main__":
    result = asyncio.run(get_weather("Beijing"))
    print(result)
'''
        
        return "OK"


async def demo_tree_session():
    """演示树状会话"""
    print("=" * 60)
    print("Demo 1: Tree Session Management")
    print("=" * 60)
    
    from koda.core.tree_session import TreeSession, SessionNode, TreeSessionManager
    
    # 创建会话管理器
    manager = TreeSessionManager("./demo_workspace")
    
    # 创建新会话
    session = manager.create_session("weather-app")
    print(f"Created session: {session.session_id}")
    
    # 获取根节点
    root = session.get_current_node()
    root.artifacts["main.py"] = "# Initial code"
    print(f"Root node: {root.name} ({root.id})")
    
    # 创建分支（开发新功能）
    feature_branch = session.create_branch(
        name="add-auth",
        description="Add authentication feature"
    )
    feature_branch.artifacts["main.py"] = "# Code with auth"
    print(f"Created branch: {feature_branch.name}")
    
    # 再创建一个分支（修复 bug）
    fix_branch = session.create_branch(
        name="fix-bug",
        description="Fix critical bug"
    )
    fix_branch.artifacts["main.py"] = "# Fixed code"
    print(f"Created branch: {fix_branch.name}")
    
    # 切换到功能分支
    session.checkout(feature_branch.id)
    print(f"Checked out to: {feature_branch.name}")
    
    # 合并修复分支
    session.merge(fix_branch.id)
    print(f"Merged {fix_branch.name} into {feature_branch.name}")
    
    # 查看树状结构
    print("\nSession Tree:")
    print(session.get_tree_visualization())
    
    # 保存会话
    manager.save_current_session()
    print("\nSession saved!")


async def demo_self_extension():
    """演示自扩展"""
    print("\n" + "=" * 60)
    print("Demo 2: Self-Extending (Code Writes Code)")
    print("=" * 60)
    
    from koda.core.extension_engine import ExtensionEngine, SelfExtendingAgent
    
    llm = MockLLM()
    engine = ExtensionEngine()
    agent = SelfExtendingAgent(engine, llm)
    
    print("Creating weather API tool...")
    
    # 创建工具
    extension = await agent.create_tool_for_capability(
        capability="fetch weather from API",
        requirements=[
            "Support multiple cities",
            "Handle API errors",
            "Return structured data"
        ]
    )
    
    print(f"Created extension: {extension.name}")
    print(f"Description: {extension.description}")
    print(f"Code length: {len(extension.code)} chars")
    
    # 列出所有扩展
    print(f"\nRegistered extensions: {engine.list_extensions()}")
    
    # 执行扩展
    print("\nExecuting extension...")
    result = await engine.execute_extension(
        extension.name,
        city="Beijing"
    )
    print(f"Result: {result}")


async def demo_full_agent():
    """演示完整代理"""
    print("\n" + "=" * 60)
    print("Demo 3: Full Koda V2 Agent")
    print("=" * 60)
    
    from koda.core.agent_v2 import KodaAgentV2, AgentConfig
    
    llm = MockLLM()
    config = AgentConfig(
        enable_self_extension=True,
        enable_branches=True,
        enable_validation=True,
        verbose=True,
    )
    
    agent = KodaAgentV2(llm=llm, config=config, workspace=Path("./demo_workspace"))
    
    # 执行任务
    result = await agent.execute(
        description="Create a weather query tool",
        requirements=[
            "Fetch weather from API",
            "Support multiple cities",
            "Handle errors gracefully"
        ]
    )
    
    print("\n" + "=" * 60)
    print("Execution Result:")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Node ID: {result['node_id']}")
    print(f"\nGenerated Code:\n{result['code'][:500]}...")
    
    # 显示树状结构
    print("\n" + "=" * 60)
    print("Session Tree:")
    print("=" * 60)
    print(agent.get_tree_view())


async def main():
    """主入口"""
    print("""
 _  __     _       _                
| |/ /    | |     | |               
| ' / ___ | | __ _| |__   ___  __ _ 
|  < / _ \\| |/ _` | '_ \\ / _ \\/ _` |
| . \\ (_) | | (_| | |_) |  __/ (_| |
|_|\\_\\___/|_|\\__,_|_.__/ \\___|\\__,_|
                                      
Koda V2 - Self-Extending Coding Agent
Features:
  - Tree Session Management
  - Self-Written Extensions  
  - Self-Validation Loop
""")
    
    # Demo 1: 树状会话
    await demo_tree_session()
    
    # Demo 2: 自扩展
    await demo_self_extension()
    
    # Demo 3: 完整代理
    await demo_full_agent()
    
    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
