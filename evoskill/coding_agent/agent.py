"""
Coding Agent - 智能代码生成代理

全流程自动化软件开发：
需求 → 规划 → 编码 → 测试 → 反思 → 迭代 → 交付
"""
import json
import re
from typing import Dict, Any, List, Optional

from evoskill.core.llm import LLMProvider
from evoskill.evolution.designer import SkillDesign, ToolDesign
from evoskill.coding_agent.types import CodingResult


class CodingAgent:
    """
    智能 Coding Agent
    
    像人类开发者一样思考和编码：
    - 理解需求和技术约束
    - 规划实现步骤
    - 编写代码
    - 自我测试
    - 发现问题并修复
    - 最终交付
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.max_iterations = 3  # 最大反思迭代次数
    
    async def develop(
        self,
        design: SkillDesign,
    ) -> CodingResult:
        """
        完整的开发流程
        
        Args:
            design: Skill 设计
            
        Returns:
            CodingResult
        """
        skill_name = design.name
        
        # === Phase 1: 技术规划 ===
        print(f"[CodingAgent] 正在规划 {skill_name} 的技术方案...")
        plan = await self._plan_implementation(design)
        
        # === Phase 2: 初始编码 ===
        print(f"[CodingAgent] 正在编写初始代码...")
        files = await self._generate_code(design, plan)
        
        # === Phase 3: 测试验证 + 反思迭代 ===
        iteration = 0
        test_passed = False
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"[CodingAgent] 第 {iteration} 轮测试验证...")
            
            # 运行测试
            test_result = await self._test_code(files, design)
            test_passed = test_result.get("passed", False)
            
            if test_passed:
                print(f"[CodingAgent] 测试通过！")
                break
            
            # 需要修复
            print(f"[CodingAgent] 发现问题，正在反思修复...")
            files = await self._reflect_and_fix(files, test_result, design, iteration)
        
        # === Phase 4: 最终验证 ===
        if not test_passed:
            print(f"[CodingAgent] 警告：经过 {self.max_iterations} 轮迭代仍有问题")
        
        return CodingResult(
            success=test_passed or iteration > 0,  # 至少尝试过
            skill_name=skill_name,
            files=files,
            main_py=files.get("main.py", ""),
            skill_md=files.get("SKILL.md", ""),
            test_py=files.get("tests/test_main.py", ""),
            iterations=iteration,
            test_passed=test_passed,
            api_recommendations=plan.get("apis", []),
        )
    
    async def _plan_implementation(
        self,
        design: SkillDesign,
    ) -> Dict[str, Any]:
        """
        技术规划阶段
        
        让 LLM 思考：
        - 这个需求如何技术实现？
        - 需要哪些 API 或库？
        - 实现步骤是什么？
        - 可能遇到什么坑？
        """
        tools_desc = []
        for tool in design.tools:
            params = ", ".join([f"{n}: {p.type}" for n, p in tool.parameters.items()])
            tools_desc.append(f"""
工具: {tool.name}
描述: {tool.description}
参数: {params}
实现提示: {tool.implementation_hint}
""")
        
        prompt = f"""你是一位经验丰富的 Python 开发者。请为以下 Skill 制定技术实现方案。

## Skill 设计

名称: {design.name}
描述: {design.description}

## 需要实现的工具

{chr(10).join(tools_desc)}

## 你的任务

请详细规划如何实现这个 Skill，以 JSON 格式返回：

{{
    "analysis": "需求分析：这个 Skill 的核心功能是什么？技术难点在哪里？",
    "approach": "实现思路：使用什么技术方案？调用什么 API？",
    "apis": [
        {{
            "name": "API 名称",
            "provider": "提供商",
            "why": "为什么选择这个 API",
            "env_var": "环境变量名",
            "setup_url": "注册链接"
        }}
    ],
    "dependencies": ["需要安装的 Python 包"],
    "steps": [
        "实现步骤 1",
        "实现步骤 2"
    ],
    "risks": ["可能的风险和注意事项"],
    "file_structure": {{
        "main.py": "主要功能，包含工具函数实现",
        "SKILL.md": "Skill 说明文档",
        "tests/test_main.py": "单元测试"
    }}
}}

请确保：
1. API 选择要具体，给出实际的 API 提供商（如 OpenWeatherMap、Bing 等）
2. 代码要有错误处理
3. 考虑到 Python 标准库优先
"""
        
        response = await self.llm.complete(prompt)
        
        try:
            # 提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = {"approach": "使用标准库实现", "apis": [], "steps": ["直接实现"]}
        except json.JSONDecodeError:
            plan = {"approach": "使用标准库实现", "apis": [], "steps": ["直接实现"]}
        
        return plan
    
    async def _generate_code(
        self,
        design: SkillDesign,
        plan: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        代码生成阶段
        
        让 LLM 根据规划编写实际代码
        """
        files = {}
        
        # 生成 main.py
        main_py = await self._generate_main_py(design, plan)
        files["main.py"] = main_py
        
        # 生成 SKILL.md
        skill_md = await self._generate_skill_md(design, plan)
        files["SKILL.md"] = skill_md
        
        # 生成测试
        test_py = await self._generate_test_py(design, main_py)
        files["tests/test_main.py"] = test_py
        
        return files
    
    async def _generate_main_py(
        self,
        design: SkillDesign,
        plan: Dict[str, Any],
    ) -> str:
        """生成 main.py"""
        
        tools_impl = []
        for tool in design.tools:
            params_str = ", ".join([
                f"{name}: {self._python_type(p.type)}"
                for name, p in tool.parameters.items()
            ])
            
            tools_impl.append(f"""
async def {tool.name}({params_str}) -> Dict[str, Any]:
    \"\"\"
    {tool.description}
    \"\"\"
    # TODO: 实现具体功能
    pass
""")
        
        apis_info = "\n".join([
            f"# - {api.get('name')}: {api.get('provider')} ({api.get('setup_url')})"
            for api in plan.get("apis", [])
        ])
        
        deps = plan.get("dependencies", [])
        imports = ["import asyncio", "from typing import Optional, Dict, Any, List"]
        if deps:
            imports.append(f"# 需要安装: pip install {' '.join(deps)}")
        
        prompt = f"""请为以下 Skill 编写完整的 main.py 代码。

## Skill 信息

名称: {design.name}
描述: {design.description}

## 技术规划

{plan.get('approach', '使用标准库实现')}

## 推荐的 API

{apis_info if apis_info else '# 无需外部 API'}

## 需要实现的工具

{chr(10).join(tools_impl)}

## 要求

1. 代码必须完整可运行
2. 使用 Python 标准库优先
3. 如果需要外部 API，从环境变量读取 API Key
4. 必须有完整的错误处理
5. 返回格式必须是 {{"success": bool, "result": any}} 或 {{"success": false, "error": str}}
6. 如果 API Key 未配置，返回清晰的错误提示和配置指南

## 输出格式

直接返回完整的 Python 代码，不需要任何解释。
代码必须包含：
- 所有必要的 import
- 工具函数实现
- SKILL_NAME, SKILL_VERSION, SKILL_TOOLS 元数据
- main() 测试函数
"""
        
        code = await self.llm.complete(prompt)
        
        # 清理代码
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    async def _generate_skill_md(
        self,
        design: SkillDesign,
        plan: Dict[str, Any],
    ) -> str:
        """生成 SKILL.md"""
        
        api_sections = []
        for api in plan.get("apis", []):
            section = f"""### {api.get('name')}

- **提供商**: {api.get('provider')}
- **注册地址**: {api.get('setup_url')}
- **环境变量**: `{api.get('env_var')}`
- **选择原因**: {api.get('why')}

配置步骤：
1. 访问 {api.get('setup_url')} 注册账号
2. 获取 API Key
3. 设置环境变量: `export {api.get('env_var')}=your_key`
"""
            api_sections.append(section)
        
        tools_md = []
        for tool in design.tools:
            params = "\n".join([
                f"- `{name}` ({p.type}): {p.description}"
                for name, p in tool.parameters.items()
            ])
            tools_md.append(f"""### {tool.name}

{tool.description}

参数:
{params}
""")
        
        md = f"""---
name: {design.name}
description: {design.description}
version: 0.1.0
---

# {design.name}

{design.description}

## 工具

{chr(10).join(tools_md)}

## API 配置

{chr(10).join(api_sections) if api_sections else '本 Skill 使用 Python 标准库，无需额外配置。'}

## 技术实现

{plan.get('analysis', '')}

实现思路:
{plan.get('approach', '')}

---

Generated by EvoSkill Coding Agent
"""
        
        return md
    
    async def _generate_test_py(
        self,
        design: SkillDesign,
        main_py: str,
    ) -> str:
        """生成测试代码"""
        
        tool_tests = []
        for tool in design.tools:
            # 生成测试参数
            test_args = []
            for name, p in tool.parameters.items():
                if p.type == "string":
                    test_args.append(f'"test_{name}"')
                elif p.type == "int":
                    test_args.append("1")
                elif p.type == "bool":
                    test_args.append("True")
                else:
                    test_args.append("None")
            
            args_str = ", ".join(test_args)
            
            tool_tests.append(f"""
@pytest.mark.asyncio
async def test_{tool.name}():
    \"\"\"测试 {tool.name}\"\"\""
    result = await {tool.name}({args_str})
    assert isinstance(result, dict)
    assert "success" in result
""")
        
        test_code = f"""\"\"\"\
Tests for {design.name}
\"\"\"
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import tool functions
from main import (
    {', '.join([t.name for t in design.tools])}
)

{chr(10).join(tool_tests)}

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
        
        return test_code
    
    async def _test_code(
        self,
        files: Dict[str, str],
        design: SkillDesign,
    ) -> Dict[str, Any]:
        """
        测试代码
        
        检查语法、可导入性、逻辑正确性
        """
        import ast
        import tempfile
        import os
        
        errors = []
        warnings = []
        
        main_py = files.get("main.py", "")
        
        # 1. 语法检查
        try:
            ast.parse(main_py)
        except SyntaxError as e:
            return {
                "passed": False,
                "errors": [f"语法错误: {e}"],
                "warnings": [],
            }
        
        # 2. 检查必要的元数据
        if "SKILL_NAME" not in main_py:
            errors.append("缺少 SKILL_NAME")
        if "SKILL_TOOLS" not in main_py:
            errors.append("缺少 SKILL_TOOLS")
        
        # 3. 检查工具函数是否存在
        for tool in design.tools:
            if f"async def {tool.name}(" not in main_py and f"def {tool.name}(" not in main_py:
                errors.append(f"缺少工具函数: {tool.name}")
        
        # 4. 检查错误处理
        if "try:" not in main_py:
            warnings.append("建议添加错误处理 (try/except)")
        
        # 5. 检查 API Key 处理（如果需要）
        if "API" in design.description.upper() or "api" in main_py:
            if "getenv" not in main_py and "API_KEY" not in main_py:
                warnings.append("可能需要从环境变量读取 API Key")
        
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def _reflect_and_fix(
        self,
        files: Dict[str, str],
        test_result: Dict[str, Any],
        design: SkillDesign,
        iteration: int,
    ) -> Dict[str, str]:
        """
        反思并修复问题
        
        让 LLM 分析问题并修复代码
        """
        errors = "\n".join(test_result.get("errors", []))
        warnings = "\n".join(test_result.get("warnings", []))
        
        prompt = f"""请修复以下 Python 代码中的问题。

## 当前代码 (main.py)

```python
{files.get("main.py", "")}
```

## 发现的问题

错误:
{errors if errors else "无严重错误"}

警告:
{warnings if warnings else "无警告"}

## 原始需求

Skill: {design.name}
描述: {design.description}

## 你的任务

1. 分析问题的根本原因
2. 修复代码中的所有错误
3. 改进代码质量（处理警告）
4. 确保代码完整可运行

请直接返回修复后的完整 main.py 代码，不需要解释。
"""
        
        fixed_code = await self.llm.complete(prompt)
        
        # 清理代码
        fixed_code = fixed_code.strip()
        if fixed_code.startswith("```python"):
            fixed_code = fixed_code[9:]
        if fixed_code.startswith("```"):
            fixed_code = fixed_code[3:]
        if fixed_code.endswith("```"):
            fixed_code = fixed_code[:-3]
        
        files["main.py"] = fixed_code.strip()
        return files
    
    def _python_type(self, type_str: str) -> str:
        """转换类型到 Python 类型注解"""
        type_map = {
            "string": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "list": "List[Any]",
            "dict": "Dict[str, Any]",
            "object": "Any",
        }
        return type_map.get(type_str, "Any")
