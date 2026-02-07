"""
需求分析器 - 分析用户请求，提取需求特征
"""
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from evoskill.core.llm import LLMProvider
from evoskill.core.types import UserMessage


@dataclass
class NeedAnalysis:
    """需求分析结果"""
    intent: str                      # 用户意图
    domain: str                      # 领域（文件、网络、数据、系统等）
    required_capabilities: List[str] # 需要的能力
    complexity: str                  # 复杂度（simple/medium/complex）
    can_use_existing: bool           # 是否能用现有工具
    suggested_skill_name: Optional[str]  # 建议的 Skill 名称


class NeedAnalyzer:
    """
    需求分析器
    
    分析用户的自然语言请求，提取结构化需求信息
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def analyze(
        self,
        user_request: str,
        existing_skills: List[Dict[str, Any]],
    ) -> NeedAnalysis:
        """
        分析用户需求
        
        Args:
            user_request: 用户的自然语言请求
            existing_skills: 现有 Skills 列表
            
        Returns:
            NeedAnalysis 分析结果
        """
        # 构建 prompt
        existing_skills_text = "\n".join([
            f"- {s.get('name', 'unknown')}: {s.get('description', 'No description')}"
            for s in existing_skills
        ]) if existing_skills else "暂无现有 Skills"
        
        prompt = f"""分析用户的需求，提取关键信息。

用户请求: {user_request}

现有 Skills:
{existing_skills_text}

请分析以下内容：
1. 用户想做什么？（意图，用简洁的语言描述）
2. 属于什么领域？（文件操作、网络请求、数据处理、系统命令、其他）
3. 需要什么能力？（读取、写入、搜索、计算、转换等）
4. 复杂度如何？（simple-简单、medium-中等、complex-复杂）
5. 现有 Skills 能否满足？（如果能，请说明用哪个）
6. 如果创建新 Skill，建议什么名称？（简短、小写、下划线分隔）

请以 JSON 格式输出：
{{
    "intent": "用户意图描述",
    "domain": "领域",
    "required_capabilities": ["能力1", "能力2"],
    "complexity": "simple|medium|complex",
    "can_use_existing": true|false,
    "existing_skill_match": "匹配的现有 Skill 名称（如果没有则为空）",
    "suggested_skill_name": "建议的新 Skill 名称"
}}

只输出 JSON，不要有其他内容。"""

        try:
            # 调用 LLM
            messages = [UserMessage(content=prompt)]
            
            response_text = ""
            async for event in self.llm.chat(messages=messages, stream=False):
                if event.get("type") == "text_delta":
                    response_text += event.get("content", "")
            
            # 解析 JSON
            # 清理可能的 markdown 代码块
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            return NeedAnalysis(
                intent=result.get("intent", user_request),
                domain=result.get("domain", "other"),
                required_capabilities=result.get("required_capabilities", []),
                complexity=result.get("complexity", "medium"),
                can_use_existing=result.get("can_use_existing", False),
                suggested_skill_name=result.get("suggested_skill_name"),
            )
            
        except json.JSONDecodeError as e:
            # JSON 解析失败，使用默认值
            return NeedAnalysis(
                intent=user_request,
                domain="other",
                required_capabilities=[],
                complexity="medium",
                can_use_existing=False,
                suggested_skill_name=None,
            )
        except Exception as e:
            # 其他错误，使用默认值
            return NeedAnalysis(
                intent=user_request,
                domain="other",
                required_capabilities=[],
                complexity="medium",
                can_use_existing=False,
                suggested_skill_name=None,
            )
