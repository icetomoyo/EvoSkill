"""
Skill Evolution Demo - Complete Loop Demo

Show: Query -> Create -> Use -> Evolve
"""
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Skill:
    """Skill model"""
    name: str
    description: str
    version: str = "1.0.0"
    created_at: str = ""
    tools: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.tools is None:
            self.tools = []


class MockSkillEvolutionEngine:
    """Mock Skill evolution engine"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.skills_dir = workspace / "skills"
        self.skills_dir.mkdir(exist_ok=True)
        self._skills: Dict[str, Skill] = {}
        
        # Init builtin skills
        self._init_builtin_skills()
    
    def _init_builtin_skills(self):
        """Initialize builtin skills"""
        builtin_skills = [
            Skill(
                name="read_file",
                description="Read file content",
                tools=[{"name": "read_file", "params": ["file_path"]}],
            ),
            Skill(
                name="write_file",
                description="Write file content",
                tools=[{"name": "write_file", "params": ["file_path", "content"]}],
            ),
            Skill(
                name="bash",
                description="Execute commands",
                tools=[{"name": "bash", "params": ["command"]}],
            ),
        ]
        for skill in builtin_skills:
            self._skills[skill.name] = skill
    
    def list_skills(self) -> List[Skill]:
        """List all skills"""
        return list(self._skills.values())
    
    def get_skill(self, name: str) -> Skill:
        """Get skill"""
        return self._skills.get(name)
    
    async def create_skill(self, description: str) -> Skill:
        """Create new skill"""
        # Analyze
        print("  [Analyzer] Analyzing need...")
        await asyncio.sleep(0.5)
        
        # Extract name
        if "time" in description.lower():
            skill_name = "time_tool"
            tools = [{"name": "get_current_time", "params": ["timezone"]}]
        elif "weather" in description.lower():
            skill_name = "weather"
            tools = [{"name": "get_weather", "params": ["city"]}]
        else:
            skill_name = "custom_tool"
            tools = [{"name": "execute", "params": ["input"]}]
        
        print(f"  [Designer] Design skill: {skill_name}...")
        await asyncio.sleep(0.5)
        
        # Create dir
        skill_dir = self.skills_dir / skill_name
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "tests").mkdir(exist_ok=True)
        
        # Gen SKILL.md
        print("  [Generator] Generate SKILL.md...")
        skill_md = f"""# {skill_name}

## Description
{description}

## Version
1.0.0

## Tools

{chr(10).join([f"### {t['name']}\nGet/process data\n\nParams: {', '.join(t['params'])}" for t in tools])}

## Example

```python
result = {tools[0]['name']}({tools[0]['params'][0]}="value")
```
"""
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        
        # Gen main.py
        print("  [Generator] Generate main.py...")
        main_py = f'''"""
{description}
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any


async def {tools[0]['name']}({tools[0]['params'][0]}: Optional[str] = None) -> Dict[str, Any]:
    """{description}"""
    try:
        if "time" in "{skill_name}":
            result = datetime.now().isoformat()
        elif "weather" in "{skill_name}":
            result = {{"temperature": 25, "condition": "sunny"}}
        else:
            result = "processed: " + str({tools[0]['params'][0]})
        
        return {{"success": True, "result": result}}
    except Exception as e:
        return {{"success": False, "error": str(e)}}


SKILL_NAME = "{skill_name}"
SKILL_VERSION = "1.0.0"
'''
        (skill_dir / "main.py").write_text(main_py, encoding="utf-8")
        
        # Gen test
        print("  [Generator] Generate tests...")
        test_py = f'''"""Tests for {skill_name}"""
import pytest
from ..main import {tools[0]['name']}

async def test_{tools[0]['name']}():
    result = await {tools[0]['name']}({tools[0]['params'][0]}="test")
    assert result["success"] is True

if __name__ == "__main__":
    asyncio.run(test_{tools[0]['name']}())
    print("Tests passed!")
'''
        (skill_dir / "tests" / "test_main.py").write_text(test_py, encoding="utf-8")
        
        # Validate
        print("  [Validator] Validate skill...")
        await asyncio.sleep(0.3)
        print("    [OK] Syntax check passed")
        print("    [OK] Tests passed")
        
        # Create skill
        skill = Skill(
            name=skill_name,
            description=description,
            tools=tools,
        )
        
        # Register
        print("  [Integrator] Register to system...")
        self._skills[skill_name] = skill
        
        return skill
    
    async def evolve_skill(self, skill_name: str, request: str) -> Skill:
        """Evolve existing skill"""
        skill = self._skills.get(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found")
        
        print(f"  [Analyzer] Analyze '{skill_name}' improvement need...")
        await asyncio.sleep(0.3)
        
        print(f"  [Evolver] Modify code to add: {request}...")
        await asyncio.sleep(0.5)
        
        # Add feature
        if "utc" in request.lower():
            skill.tools.append({"name": "get_utc_time", "params": []})
            skill.version = "1.1.0"
        
        print("  [Validator] Validate update...")
        await asyncio.sleep(0.3)
        print("    [OK] Backward compatible")
        print("    [OK] Tests passed")
        
        return skill
    
    async def execute_skill(self, skill_name: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute skill"""
        skill = self._skills.get(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill '{skill_name}' not found"}
        
        await asyncio.sleep(0.2)
        
        if skill_name == "time_tool":
            from datetime import datetime
            if tool_name == "get_current_time":
                tz = kwargs.get("timezone", "local")
                if tz == "UTC":
                    result = datetime.utcnow().isoformat()
                else:
                    result = datetime.now().isoformat()
                return {"success": True, "result": result}
            elif tool_name == "get_utc_time":
                return {"success": True, "result": datetime.utcnow().isoformat()}
        
        elif skill_name == "weather":
            city = kwargs.get("city", "Unknown")
            return {
                "success": True,
                "result": {
                    "city": city,
                    "temperature": 25,
                    "condition": "sunny"
                }
            }
        
        return {"success": True, "result": f"Executed {tool_name} with {kwargs}"}


class DemoSession:
    """Demo session"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.engine = MockSkillEvolutionEngine(workspace)
    
    async def run_demo(self):
        """Run complete demo"""
        print("=" * 60)
        print("Skill Evolution Demo - Complete Loop")
        print("=" * 60)
        
        # Stage 1: Query
        print("\n[Stage 1] Query existing skills")
        print("-" * 40)
        print("User: /skills")
        print()
        print("AI: Available skills:")
        
        skills = self.engine.list_skills()
        for skill in skills:
            print(f"  - {skill.name}: {skill.description}")
        
        # Stage 2: Create
        print("\n" + "=" * 60)
        print("[Stage 2] Create new skill")
        print("-" * 40)
        print("User: Create a tool to query current time")
        print()
        print("AI: Detected need: query current time")
        print("    Existing skills cannot satisfy")
        print("    Creating time_tool...")
        print()
        
        skill = await self.engine.create_skill("Query current time")
        
        print()
        print(f"    [OK] time_tool ({skill.version}) created and activated!")
        print()
        print(f"    Generated files:")
        print(f"      - skills/{skill.name}/SKILL.md")
        print(f"      - skills/{skill.name}/main.py")
        print(f"      - skills/{skill.name}/tests/test_main.py")
        
        # Stage 3: Use
        print("\n" + "=" * 60)
        print("[Stage 3] Use new skill")
        print("-" * 40)
        print("User: What time is it now?")
        print()
        print("AI: [Invoke time_tool.get_current_time()]")
        
        result = await self.engine.execute_skill("time_tool", "get_current_time")
        
        if result["success"]:
            print(f"    Current time: {result['result']}")
        else:
            print(f"    Error: {result['error']}")
        
        # Stage 4: Evolve
        print("\n" + "=" * 60)
        print("[Stage 4] Skill evolution")
        print("-" * 40)
        print("User: Can the time tool show UTC time?")
        print()
        print("AI: Detected time_tool feature expansion need")
        print("    Adding UTC support...")
        print()
        
        evolved_skill = await self.engine.evolve_skill(
            "time_tool",
            "Add UTC time support"
        )
        
        print()
        print(f"    [OK] time_tool evolved to {evolved_skill.version}!")
        print()
        print("    New features:")
        print("      - get_current_time(timezone='UTC') - UTC time")
        print("      - get_utc_time() - Quick UTC time")
        
        # Use evolved
        print("\n" + "=" * 60)
        print("[Use] Use evolved skill")
        print("-" * 40)
        print("User: What's the UTC time?")
        print()
        print("AI: [Invoke time_tool.get_current_time(timezone='UTC')]")
        
        result = await self.engine.execute_skill(
            "time_tool",
            "get_current_time",
            timezone="UTC"
        )
        
        if result["success"]:
            print(f"    UTC time: {result['result']}")
        
        # Summary
        print("\n" + "=" * 60)
        print("[Summary] Loop demo summary")
        print("=" * 60)
        print("""
[OK] Query: User viewed existing skills
[OK] Create: System generated time_tool based on need
[OK] Use: User successfully used new skill to query time
[OK] Evolve: Added UTC support based on feedback

Key capabilities:
- Natural language need -> Auto skill generation
- No restart -> Hot reload immediately available
- Usage feedback -> Auto evolution improvement
- Complete loop -> Smarter with use
        """)
        
        print("\nFinal skill list:")
        all_skills = self.engine.list_skills()
        for skill in all_skills:
            version = getattr(skill, 'version', '1.0.0')
            print(f"  - {skill.name} (v{version}): {skill.description}")


async def main():
    """Main"""
    workspace = Path(__file__).parent / "demo_workspace"
    workspace.mkdir(exist_ok=True)
    
    session = DemoSession(workspace)
    await session.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
