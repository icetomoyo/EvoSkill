"""
Skill 设计器 - 设计 Skill 结构和工具接口
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from evoskill.core.llm import LLMProvider
from evoskill.core.types import UserMessage
from evoskill.evolution.analyzer import NeedAnalysis


@dataclass
class ParameterSchema:
    """参数模式"""
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDesign:
    """工具设计"""
    name: str
    description: str
    parameters: Dict[str, ParameterSchema]
    returns: str
    errors: List[str]
    implementation_hint: str  # 实现提示


@dataclass
class SkillDesign:
    """Skill 设计"""
    name: str
    description: str
    version: str = "0.1.0"
    author: str = "EvoSkill"
    tools: List[ToolDesign] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)


class SkillDesigner:
    """
    Skill 设计器
    
    根据需求分析结果，设计 Skill 的完整结构
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def design(
        self,
        need: NeedAnalysis,
        existing_skills: List[Dict[str, Any]],
    ) -> SkillDesign:
        """
        设计新 Skill
        
        Args:
            need: 需求分析结果
            existing_skills: 现有 Skills（避免重复）
            
        Returns:
            SkillDesign 设计结果
        """
        # 构建设计 prompt
        existing_names = [s.get("name", "") for s in existing_skills]
        
        prompt = f"""根据用户需求设计一个新的 Skill。

用户需求: {need.intent}
领域: {need.domain}
需要的能力: {', '.join(need.required_capabilities)}
复杂度: {need.complexity}
建议名称: {need.suggested_skill_name or 'auto_generate'}

现有 Skill 名称（避免重复）: {', '.join(existing_names) if existing_names else '无'}

请设计一个包含以下内容的 Skill：

1. **Skill 元数据**
   - 名称（英文，小写，下划线分隔）
   - 描述（一句话说明用途）
   - 版本（从 0.1.0 开始）
   - 依赖包（如果需要）

2. **工具设计**（可以设计 1-3 个工具）
   每个工具需要：
   - 名称（英文，小写，动词开头）
   - 描述（做什么）
   - 参数（名称、类型、是否必需、描述）
   - 返回值说明
   - 可能的错误
   - 实现提示（关键逻辑思路）

3. **使用示例**
   - 1-2 个示例，展示如何调用

请以 JSON 格式输出：
{{
    "name": "skill_name",
    "description": "Skill 描述",
    "version": "0.1.0",
    "dependencies": ["package1", "package2"],
    "tools": [
        {{
            "name": "tool_name",
            "description": "工具描述",
            "parameters": {{
                "param1": {{
                    "type": "string",
                    "description": "参数说明",
                    "required": true
                }}
            }},
            "returns": "返回什么",
            "errors": ["可能的错误1", "错误2"],
            "implementation_hint": "实现思路"
        }}
    ],
    "examples": [
        {{
            "description": "示例描述",
            "usage": "tool_name(arg=value)"
        }}
    ]
}}

注意：
- 工具必须可测试，避免需要真实 API Key 才能运行的工具
- 参数设计要合理，有默认值时设置 required: false
- 错误处理要完善，考虑边界情况"""

        try:
            # 调用 LLM
            messages = [UserMessage(content=prompt)]
            
            response_text = ""
            async for event in self.llm.chat(messages=messages, stream=False):
                if event.get("type") == "text_delta":
                    response_text += event.get("content", "")
            
            # 解析 JSON
            response_text = self._extract_json(response_text)
            result = json.loads(response_text)
            
            # 构建 SkillDesign
            tools = []
            for tool_data in result.get("tools", []):
                parameters = {}
                for param_name, param_data in tool_data.get("parameters", {}).items():
                    parameters[param_name] = ParameterSchema(
                        type=param_data.get("type", "string"),
                        description=param_data.get("description", ""),
                        required=param_data.get("required", True),
                        default=param_data.get("default"),
                    )
                
                tools.append(ToolDesign(
                    name=tool_data.get("name", "unnamed_tool"),
                    description=tool_data.get("description", ""),
                    parameters=parameters,
                    returns=tool_data.get("returns", "Dict with success and result/error"),
                    errors=tool_data.get("errors", []),
                    implementation_hint=tool_data.get("implementation_hint", ""),
                ))
            
            return SkillDesign(
                name=result.get("name", need.suggested_skill_name or "new_skill"),
                description=result.get("description", need.intent),
                version=result.get("version", "0.1.0"),
                tools=tools,
                dependencies=result.get("dependencies", []),
                examples=result.get("examples", []),
            )
            
        except Exception as e:
            # 失败时返回默认设计
            return self._default_design(need)
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        text = text.strip()
        
        # 移除 markdown 代码块
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()
    
    def _default_design(self, need: NeedAnalysis) -> SkillDesign:
        """生成默认设计（当 LLM 失败时）"""
        skill_name = need.suggested_skill_name or "custom_tool"
        
        return SkillDesign(
            name=skill_name,
            description=need.intent,
            version="0.1.0",
            tools=[
                ToolDesign(
                    name="execute",
                    description=f"Execute {need.intent}",
                    parameters={
                        "input": ParameterSchema(
                            type="string",
                            description="Input data",
                            required=True,
                        ),
                    },
                    returns="Dict with success and result",
                    errors=["Invalid input", "Execution failed"],
                    implementation_hint="Implement the core logic here",
                ),
            ],
            dependencies=[],
            examples=[
                {
                    "description": "Basic usage",
                    "usage": f"execute(input='data')",
                },
            ],
        )
