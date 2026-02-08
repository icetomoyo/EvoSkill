"""
Koda 框架使用示例

演示如何使用 Koda 独立开发代码
"""
import asyncio
from pathlib import Path

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class MockLLM:
    """Mock LLM for demo"""
    
    async def complete(self, prompt: str, **kwargs) -> str:
        # 模拟天气工具生成
        if "编写完整的 Python 代码" in prompt or "main.py" in prompt:
            return '''import os
import urllib.request
import json
from typing import Dict, Any

async def get_weather(city: str) -> Dict[str, Any]:
    """获取城市天气"""
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY", "")
        if not api_key:
            return {
                "success": False,
                "error": "请设置 OPENWEATHER_API_KEY 环境变量"
            }
        
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=zh_cn"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; Koda/0.1)'
        })
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        
        return {
            "success": True,
            "result": {
                "city": data.get("name"),
                "temperature": f"{data['main']['temp']}°C",
                "condition": data['weather'][0]['description'] if data.get('weather') else "未知",
                "humidity": f"{data['main']['humidity']}%",
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

SKILL_NAME = "weather_query"
SKILL_VERSION = "0.1.0"
SKILL_TOOLS = [{"name": "get_weather", "description": "获取天气", "handler": get_weather}]
'''
        elif "技术方案" in prompt or "analysis" in prompt.lower():
            return '''{
                "analysis": "需要实现天气查询功能，调用外部天气API",
                "approach": "使用 urllib 调用 OpenWeatherMap API，从环境变量读取 API Key",
                "dependencies": [],
                "estimated_minutes": 5
            }'''
        elif "审查" in prompt or "review" in prompt.lower():
            return '''{
                "issues": [],
                "suggestions": ["可以添加更多错误处理细节"],
                "can_fix": false,
                "confidence": 0.9
            }'''
        else:
            return "OK"


async def main():
    print("=" * 60)
    print("Koda Framework Demo")
    print("=" * 60)
    print()
    
    # 导入框架
    from koda import KodaAgent, Task
    
    # 创建 Mock LLM
    llm = MockLLM()
    
    # 创建 Agent
    agent = KodaAgent(llm=llm, verbose=True)
    
    print()
    print("Creating task...")
    print()
    
    # 定义任务
    task = Task(
        description="创建一个天气查询工具",
        requirements=[
            "根据城市名查询天气",
            "使用 OpenWeatherMap API",
            "完整的错误处理",
        ],
        constraints=["使用 Python 标准库"],
    )
    
    print("Executing task...")
    print("-" * 60)
    
    # 执行任务
    result = await agent.execute(task)
    
    print("-" * 60)
    print()
    
    # 输出结果
    print(f"Success: {result.success}")
    print(f"Status: {result.status.value}")
    print(f"Iterations: {result.iterations}")
    print(f"Total time: {result.total_time_ms}ms")
    print()
    
    if result.artifacts:
        print("Generated files:")
        for artifact in result.artifacts:
            print(f"  - {artifact.filename} ({len(artifact.content)} chars)")
        print()
        
        # 显示主代码
        main_code = result.get_main_code()
        if main_code:
            print("Main code preview (first 30 lines):")
            print("```python")
            lines = main_code.split('\n')[:30]
            for line in lines:
                print(line)
            print("```")
    
    print()
    print("=" * 60)
    print("Koda Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
