"""
Planner - 任务规划器

分析任务需求，制定技术方案和执行计划
"""
import json
import re
from typing import List, Dict, Any, Optional

from koda.core.task import Task, Plan, Step, APIDiscovery
from koda.core.types import TaskStatus


class Planner:
    """
    任务规划器
    
    将用户需求转换为可执行的技术计划
    """
    
    def __init__(self, llm: Any):
        self.llm = llm
    
    async def create_plan(self, task: Task) -> Plan:
        """
        为任务创建执行计划
        """
        # 分析需求并制定方案
        analysis = await self._analyze_task(task)
        
        # 发现合适的 API
        apis = await self._discover_apis(task, analysis)
        
        # 生成执行步骤
        steps = await self._generate_steps(task, analysis, apis)
        
        return Plan(
            task_id=str(hash(task.description))[:8],
            analysis=analysis.get("analysis", ""),
            approach=analysis.get("approach", ""),
            steps=steps,
            apis=apis,
            dependencies=analysis.get("dependencies", []),
            estimated_time=analysis.get("estimated_minutes", 10) * 60,
        )
    
    async def _analyze_task(self, task: Task) -> Dict[str, Any]:
        """分析任务需求"""
        prompt = f"""You are a senior architect. Analyze this coding task.

{task.to_prompt()}

Return JSON:
{{
    "analysis": "What is this task about? Technical challenges?",
    "approach": "Technical solution and architecture",
    "dependencies": ["Python packages needed"],
    "estimated_minutes": 10
}}

Prefer Python standard library.
"""
        
        response = await self.llm.complete(prompt)
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        return {
            "analysis": f"Need to implement: {task.description}",
            "approach": "Use Python standard library",
            "dependencies": [],
            "estimated_minutes": 10,
        }
    
    async def _discover_apis(self, task: Task, analysis: Dict) -> List[APIDiscovery]:
        """发现合适的 API"""
        api_knowledge = {
            "weather": [
                APIDiscovery(
                    name="OpenWeatherMap",
                    provider="OpenWeather",
                    description="Global weather data API",
                    signup_url="https://openweathermap.org/api",
                    free_quota="1000/day",
                    env_var="OPENWEATHER_API_KEY",
                    features=["Current weather", "Forecast"],
                ),
            ],
            "search": [
                APIDiscovery(
                    name="Bing Web Search",
                    provider="Microsoft",
                    description="Bing search API",
                    signup_url="https://azure.microsoft.com",
                    free_quota="1000/month",
                    env_var="BING_SEARCH_API_KEY",
                ),
            ],
        }
        
        task_lower = task.description.lower()
        discovered = []
        
        for keyword, apis in api_knowledge.items():
            if keyword in task_lower:
                discovered.extend(apis)
        
        return discovered
    
    async def _generate_steps(
        self, 
        task: Task, 
        analysis: Dict, 
        apis: List[APIDiscovery]
    ) -> List[Step]:
        """生成执行步骤"""
        steps = []
        
        if apis:
            steps.append(Step(
                id="setup",
                description=f"Configure APIs: {', '.join(a.name for a in apis[:2])}",
                status=TaskStatus.PENDING,
            ))
        
        steps.append(Step(
            id="implement",
            description="Implement core functionality",
            status=TaskStatus.PENDING,
            depends_on=["setup"] if apis else [],
        ))
        
        steps.append(Step(
            id="test",
            description="Write unit tests",
            status=TaskStatus.PENDING,
            depends_on=["implement"],
        ))
        
        return steps
