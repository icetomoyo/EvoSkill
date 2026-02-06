"""
Skill 加载器

支持从本地目录、GitHub 等来源动态加载 Skills
"""

import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml

from evoskill.core.types import Skill, SkillMetadata, ToolDefinition, ParameterSchema


class SkillLoader:
    """
    Skill 加载器
    
    支持:
    1. 从本地目录加载
    2. 从远程 URL 加载（TODO）
    3. 热重载
    """
    
    def __init__(self, skills_dir: Union[str, Path]):
        self.skills_dir = Path(skills_dir)
        self._loaded_skills: Dict[str, Skill] = {}
    
    def discover_skills(self) -> List[Path]:
        """
        发现 skills 目录下的所有 Skills
        
        Returns:
            Skill 目录路径列表
        """
        skill_paths = []
        
        if not self.skills_dir.exists():
            return skill_paths
        
        for item in self.skills_dir.iterdir():
            if item.is_dir():
                # 检查是否包含 SKILL.md
                if (item / "SKILL.md").exists():
                    skill_paths.append(item)
        
        return skill_paths
    
    def load_skill(self, skill_path: Union[str, Path]) -> Optional[Skill]:
        """
        加载单个 Skill
        
        Args:
            skill_path: Skill 目录路径
            
        Returns:
            Skill 对象，加载失败返回 None
        """
        skill_path = Path(skill_path)
        
        if not skill_path.exists():
            print(f"Skill path not found: {skill_path}")
            return None
        
        # 解析 SKILL.md
        skill_md_path = skill_path / "SKILL.md"
        if not skill_md_path.exists():
            print(f"SKILL.md not found in {skill_path}")
            return None
        
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 解析 frontmatter
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
            
            if not frontmatter_match:
                print(f"Invalid SKILL.md format in {skill_path}")
                return None
            
            yaml_content = frontmatter_match.group(1)
            markdown_content = frontmatter_match.group(2)
            
            metadata = yaml.safe_load(yaml_content)
            
            # 提取工具定义
            tools = self._parse_tools(metadata.get("tools", []), skill_path)
            
            # 创建 Skill 对象
            skill = Skill(
                name=metadata.get("name", skill_path.name),
                description=metadata.get("description", ""),
                tools=tools,
                metadata=SkillMetadata(
                    version=metadata.get("version", "0.1.0"),
                    author=metadata.get("author", "unknown"),
                    tags=metadata.get("tags", []),
                    dependencies=metadata.get("dependencies", []),
                ),
                source_path=skill_path,
                readme=markdown_content,
            )
            
            self._loaded_skills[skill.name] = skill
            return skill
        
        except Exception as e:
            print(f"Error loading skill from {skill_path}: {e}")
            return None
    
    def _parse_tools(
        self,
        tools_config: List[Dict[str, Any]],
        skill_path: Path
    ) -> List[ToolDefinition]:
        """
        解析工具定义
        
        Args:
            tools_config: 工具配置列表
            skill_path: Skill 目录路径
            
        Returns:
            工具定义列表
        """
        tools = []
        
        for tool_config in tools_config:
            name = tool_config.get("name")
            description = tool_config.get("description", "")
            parameters_config = tool_config.get("parameters", {})
            
            # 构建参数模式
            parameters = {}
            for param_name, param_config in parameters_config.items():
                parameters[param_name] = ParameterSchema(
                    type=param_config.get("type", "string"),
                    description=param_config.get("description", ""),
                    required=param_config.get("required", True),
                    default=param_config.get("default"),
                )
            
            # 查找处理函数
            handler = self._load_tool_handler(skill_path, name)
            
            tool = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=handler,
            )
            tools.append(tool)
        
        return tools
    
    def _load_tool_handler(
        self,
        skill_path: Path,
        tool_name: str
    ) -> Optional[Callable]:
        """
        加载工具处理函数
        
        Args:
            skill_path: Skill 目录路径
            tool_name: 工具名称
            
        Returns:
            处理函数，找不到返回 None
        """
        # 尝试加载 main.py
        main_file = skill_path / "main.py"
        
        if not main_file.exists():
            return None
        
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_path.name}",
                main_file
            )
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找处理函数（多种命名约定）
            handler_names = [
                tool_name,
                f"handle_{tool_name}",
                tool_name.replace("-", "_"),
            ]
            
            for name in handler_names:
                if hasattr(module, name):
                    return getattr(module, name)
            
            return None
        
        except Exception as e:
            print(f"Error loading tool handler {tool_name}: {e}")
            return None
    
    def load_all_skills(self) -> List[Skill]:
        """
        加载所有发现的 Skills
        
        Returns:
            Skill 对象列表
        """
        skills = []
        
        for skill_path in self.discover_skills():
            skill = self.load_skill(skill_path)
            if skill:
                skills.append(skill)
        
        return skills
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """
        获取已加载的 Skill
        
        Args:
            name: Skill 名称
            
        Returns:
            Skill 对象
        """
        return self._loaded_skills.get(name)
    
    def reload_skill(self, name: str) -> Optional[Skill]:
        """
        热重载 Skill
        
        Args:
            name: Skill 名称
            
        Returns:
            重新加载的 Skill 对象
        """
        skill = self._loaded_skills.get(name)
        if skill:
            return self.load_skill(skill.source_path)
        return None
    
    def list_skills(self) -> List[str]:
        """
        列出所有已加载的 Skill 名称
        
        Returns:
            Skill 名称列表
        """
        return list(self._loaded_skills.keys())


def create_default_skill(skill_path: Path, name: str, description: str) -> None:
    """
    创建默认 Skill 模板
    
    Args:
        skill_path: Skill 目录路径
        name: Skill 名称
        description: Skill 描述
    """
    skill_path.mkdir(parents=True, exist_ok=True)
    
    # 创建 SKILL.md
    skill_md = f"""---
name: {name}
description: {description}
version: 1.0.0
author: evoskill
tools:
  - name: example_tool
    description: 示例工具
    parameters:
      param1:
        type: string
        description: 参数1
        required: true
---

# {name}

{description}

## 使用示例

```python
# 使用示例工具
result = example_tool(param1="value")
```
"""
    
    with open(skill_path / "SKILL.md", "w", encoding="utf-8") as f:
        f.write(skill_md)
    
    # 创建 main.py
    main_py = f'''"""
{name} - {description}
"""

async def example_tool(param1: str) -> str:
    """
    示例工具
    
    Args:
        param1: 参数1
        
    Returns:
        结果字符串
    """
    return f"Hello, {{param1}}!"


if __name__ == "__main__":
    import asyncio
    result = asyncio.run(example_tool("World"))
    print(result)
'''
    
    with open(skill_path / "main.py", "w", encoding="utf-8") as f:
        f.write(main_py)
    
    # 创建 tests 目录
    (skill_path / "tests").mkdir(exist_ok=True)
    
    test_py = f'''import pytest
from ..main import example_tool


@pytest.mark.asyncio
async def test_example_tool():
    result = await example_tool("Test")
    assert result == "Hello, Test!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
    
    with open(skill_path / "tests" / "test_main.py", "w", encoding="utf-8") as f:
        f.write(test_py)
    
    print(f"Created skill template at: {skill_path}")
