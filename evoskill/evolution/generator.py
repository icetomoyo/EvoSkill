"""
Skill 生成器

根据需求分析生成 Skill 代码
"""

from pathlib import Path
from typing import Any, Dict, List

from evoskill.core.types import NeedAnalysis, SkillDesign, GeneratedSkill, ToolDefinition


class SkillGenerator:
    """
    Skill 生成器
    
    生成:
    1. SKILL.md
    2. main.py
    3. tests/test_main.py
    4. requirements.txt
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def design(
        self,
        analysis: NeedAnalysis
    ) -> SkillDesign:
        """
        设计 Skill
        
        Args:
            analysis: 需求分析结果
            
        Returns:
            Skill 设计方案
        """
        # 生成名称（kebab-case）
        name = self._generate_name(analysis.user_need)
        
        # 生成工具列表
        tools = self._design_tools(analysis)
        
        return SkillDesign(
            name=name,
            description=analysis.user_need[:100],
            tools=tools,
            file_structure=[
                "SKILL.md",
                "main.py",
                "tests/test_main.py",
                "requirements.txt",
            ],
            implementation_plan=self._generate_plan(analysis),
        )
    
    def _generate_name(self, user_need: str) -> str:
        """从需求生成 Skill 名称"""
        # 简单实现：提取关键词并转换
        import re
        
        # 去除标点，取前 3-4 个词
        words = re.findall(r'\w+', user_need.lower())
        words = [w for w in words if len(w) > 2][:3]
        
        if not words:
            words = ["custom", "skill"]
        
        return "-".join(words)
    
    def _design_tools(self, analysis: NeedAnalysis) -> List[ToolDefinition]:
        """设计工具列表"""
        from evoskill.core.types import ParameterSchema
        
        tools = []
        
        for feature in analysis.core_features[:3]:  # 最多 3 个工具
            # 生成工具名
            tool_name = feature.replace(" ", "_").replace("-", "_")[:30]
            
            tool = ToolDefinition(
                name=tool_name,
                description=feature,
                parameters={
                    "input": ParameterSchema(
                        type="string",
                        description="输入参数",
                        required=True,
                    )
                },
                handler=None,  # 稍后绑定
            )
            tools.append(tool)
        
        return tools
    
    def _generate_plan(self, analysis: NeedAnalysis) -> str:
        """生成实现计划"""
        return f"""实现计划:
1. 实现核心功能: {', '.join(analysis.core_features)}
2. 处理输入: {', '.join(analysis.inputs)}
3. 生成输出: {', '.join(analysis.outputs)}
4. 错误处理
"""
    
    async def generate(
        self,
        design: SkillDesign,
        analysis: NeedAnalysis
    ) -> GeneratedSkill:
        """
        生成 Skill 代码
        
        Args:
            design: Skill 设计方案
            analysis: 需求分析
            
        Returns:
            生成的 Skill
        """
        skill_md = self._generate_skill_md(design, analysis)
        main_code = self._generate_main_py(design, analysis)
        test_code = self._generate_test_py(design)
        requirements = self._generate_requirements(analysis)
        
        return GeneratedSkill(
            skill_md=skill_md,
            main_code=main_code,
            test_code=test_code,
            requirements=requirements,
            design=design,
        )
    
    def _generate_skill_md(
        self,
        design: SkillDesign,
        analysis: NeedAnalysis
    ) -> str:
        """生成 SKILL.md"""
        tools_yaml = []
        for tool in design.tools:
            params = []
            for param_name, param in tool.parameters.items():
                params.append(f"""
      {param_name}:
        type: {param.type}
        description: {param.description}
        required: {str(param.required).lower()}""")
            
            tools_yaml.append(f"""  - name: {tool.name}
    description: {tool.description}
    parameters:{''.join(params)}""")
        
        return f"""---
name: {design.name}
description: {design.description}
version: 1.0.0
author: evoskill
tools:
{chr(10).join(tools_yaml)}
---

# {design.name}

{design.description}

## 功能

{chr(10).join(f'- {f}' for f in analysis.core_features)}

## 使用场景

当用户需要 {design.description} 时使用此 Skill。

## 输入

{chr(10).join(f'- {i}' for i in analysis.inputs)}

## 输出

{chr(10).join(f'- {o}' for o in analysis.outputs)}

## 依赖

{chr(10).join(f'- {d}' for d in analysis.dependencies) if analysis.dependencies else "无特殊依赖"}

## 示例

```python
# 使用 {design.tools[0].name if design.tools else 'main_tool'}
result = {design.tools[0].name if design.tools else 'main_tool'}(
    input="示例输入"
)
print(result)
```
"""
    
    def _generate_main_py(
        self,
        design: SkillDesign,
        analysis: NeedAnalysis
    ) -> str:
        """生成 main.py"""
        
        # 生成工具函数
        tool_functions = []
        for tool in design.tools:
            params_str = ", ".join(
                f"{name}: {self._py_type(param.type)}"
                for name, param in tool.parameters.items()
            )
            
            tool_func = f'''
async def {tool.name}({params_str}) -> str:
    """
    {tool.description}
    
    Args:
{chr(10).join(f'        {name}: {param.description}' for name, param in tool.parameters.items())}
        
    Returns:
        处理结果
    """
    # TODO: 实现 {tool.name} 的逻辑
    
    try:
        # 核心逻辑
        result = f"处理了: {{{list(tool.parameters.keys())[0] if tool.parameters else 'input'}}}"
        return result
    except Exception as e:
        return f"Error: {{str(e)}}"
'''
            tool_functions.append(tool_func)
        
        return f'''"""
{design.name} - {design.description}

{chr(10).join(f"- {f}" for f in analysis.core_features)}
"""

import asyncio
from typing import Optional

{chr(10).join(tool_functions)}


if __name__ == "__main__":
    # 测试代码
    async def test():
        {f'result = await {design.tools[0].name}("测试输入")' if design.tools else 'print("No tools defined")'}
        {f'print(result)' if design.tools else ''}
    
    asyncio.run(test())
'''
    
    def _generate_test_py(self, design: SkillDesign) -> str:
        """生成测试文件"""
        
        test_cases = []
        for tool in design.tools:
            test_cases.append(f'''
@pytest.mark.asyncio
async def test_{tool.name}():
    """测试 {tool.name}"""
    result = await {tool.name}(
        input="测试输入"
    )
    assert result is not None
    assert isinstance(result, str)
''')
        
        return f'''"""
测试 {design.name}
"""

import pytest
from ..main import (
    {",".join(f"{tool.name}" for tool in design.tools)}
)

{chr(10).join(test_cases)}
'''
    
    def _generate_requirements(self, analysis: NeedAnalysis) -> str:
        """生成 requirements.txt"""
        deps = ["pytest-asyncio"] if analysis.dependencies else []
        return "\n".join(deps) or "# 无特殊依赖"
    
    def _py_type(self, json_type: str) -> str:
        """JSON 类型转 Python 类型"""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return type_map.get(json_type, "Any")


class SkillValidator:
    """Skill 验证器"""
    
    async def validate(self, generated: GeneratedSkill) -> tuple[bool, List[str]]:
        """
        验证生成的 Skill
        
        Returns:
            (是否通过, 错误信息列表)
        """
        errors = []
        
        # 1. 语法检查
        try:
            import ast
            ast.parse(generated.main_code)
        except SyntaxError as e:
            errors.append(f"Syntax error in main.py: {e}")
        
        # 2. 检查 SKILL.md 格式
        if "---" not in generated.skill_md:
            errors.append("SKILL.md missing frontmatter")
        
        # 3. 检查是否有工具定义
        if not generated.design.tools:
            errors.append("No tools defined")
        
        return len(errors) == 0, errors
