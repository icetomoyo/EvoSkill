"""
需求分析器

分析用户需求，判断是否触发 Skill 创建
"""

from typing import Any, Dict, List, Optional

from evoskill.core.types import NeedAnalysis


class NeedAnalyzer:
    """
    需求分析器
    
    负责:
    1. 从对话中提取潜在需求
    2. 评估现有 Skills 是否能满足
    3. 生成需求分析报告
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def analyze(
        self,
        user_request: str,
        conversation_context: str = "",
        available_skills: Optional[List[str]] = None
    ) -> NeedAnalysis:
        """
        分析用户需求
        
        Args:
            user_request: 用户请求
            conversation_context: 对话上下文
            available_skills: 可用 Skills 列表
            
        Returns:
            需求分析结果
        """
        # 构建分析提示词
        prompt = self._build_analysis_prompt(
            user_request,
            conversation_context,
            available_skills or []
        )
        
        # 调用 LLM 进行分析
        if self.llm_client:
            response = await self._call_llm(prompt)
            return self._parse_analysis_response(response)
        else:
            # 简化分析（无 LLM 时）
            return self._simple_analysis(user_request)
    
    def _build_analysis_prompt(
        self,
        user_request: str,
        context: str,
        available_skills: List[str]
    ) -> str:
        """构建分析提示词"""
        skills_list = "\n".join(f"- {skill}" for skill in available_skills)
        
        return f"""请分析以下用户需求，判断是否需要创建新的 Skill。

## 可用 Skills
{skills_list or "（无可用 Skills）"}

## 用户请求
{user_request}

## 对话上下文
{context or "（无上下文）"}

## 分析要求

请分析以下方面：

1. **核心需求**: 用户真正想要什么？
2. **功能点**: 需要哪些具体功能？
3. **输入/输出**: 需要什么输入，期望什么输出？
4. **技术依赖**: 需要哪些外部依赖（API、库等）？
5. **可行性评估**: 技术上是否可行？
6. **与现有 Skills 的关系**: 是否可以扩展现有 Skill，还是需要新建？

## 输出格式

请以 YAML 格式输出：

```yaml
user_need: "用户核心需求"
core_features:
  - "功能点1"
  - "功能点2"
inputs:
  - "输入1"
  - "输入2"
outputs:
  - "输出1"
dependencies:
  - "依赖1"
feasible: true/false
reason: "可行性说明或不可行原因"
existing_skill_can_handle: true/false
suggested_action: "use_existing" / "extend_existing" / "create_new"
```
"""
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        # 实际实现中调用 LLM
        # 这里简化处理
        return ""
    
    def _parse_analysis_response(self, response: str) -> NeedAnalysis:
        """解析 LLM 响应"""
        import yaml
        
        try:
            # 提取 YAML 内容
            if "```yaml" in response:
                yaml_content = response.split("```yaml")[1].split("```")[0]
            elif "```" in response:
                yaml_content = response.split("```")[1]
            else:
                yaml_content = response
            
            data = yaml.safe_load(yaml_content)
            
            return NeedAnalysis(
                user_need=data.get("user_need", ""),
                core_features=data.get("core_features", []),
                inputs=data.get("inputs", []),
                outputs=data.get("outputs", []),
                dependencies=data.get("dependencies", []),
                feasible=data.get("feasible", True),
                reason=data.get("reason"),
            )
        except Exception as e:
            return NeedAnalysis(
                user_need="",
                core_features=[],
                inputs=[],
                outputs=[],
                dependencies=[],
                feasible=False,
                reason=f"Parse error: {e}"
            )
    
    def _simple_analysis(self, user_request: str) -> NeedAnalysis:
        """简化分析（无 LLM 时）"""
        # 基于关键词的简单分析
        keywords = {
            "天气": ("weather", ["获取天气信息"]),
            "文件": ("file", ["文件操作"]),
            "代码": ("code", ["代码处理"]),
            "图片": ("image", ["图像处理"]),
            "搜索": ("search", ["信息搜索"]),
            "翻译": ("translate", ["文本翻译"]),
        }
        
        detected_features = []
        for keyword, (category, features) in keywords.items():
            if keyword in user_request:
                detected_features.extend(features)
        
        return NeedAnalysis(
            user_need=user_request,
            core_features=detected_features or ["未识别具体功能"],
            inputs=["用户输入"],
            outputs=["处理结果"],
            dependencies=[],
            feasible=len(detected_features) > 0,
            reason="基于关键词的简单分析" if detected_features else "无法识别需求",
        )
    
    def should_create_skill(
        self,
        user_request: str,
        available_skills: List[str]
    ) -> bool:
        """
        快速判断是否应该创建新 Skill
        
        Args:
            user_request: 用户请求
            available_skills: 可用 Skills
            
        Returns:
            是否应该创建
        """
        # 简单启发式规则
        # 1. 如果用户明确说"创建一个 Skill"，触发
        if "创建" in user_request and "skill" in user_request.lower():
            return True
        
        # 2. 如果请求包含编程任务，可能触发
        code_keywords = ["函数", "类", "模块", "脚本", "程序"]
        if any(kw in user_request for kw in code_keywords):
            return True
        
        # 3. 如果现有 Skills 无法匹配，触发
        # 简化：假设没有匹配
        return False
