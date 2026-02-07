"""
Skill 匹配器 - 找到最匹配的现有 Skill
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from evoskill.evolution.analyzer import NeedAnalysis


@dataclass
class MatchResult:
    """匹配结果"""
    skill_name: str
    match_score: float  # 0-1，匹配度
    match_reason: str   # 匹配原因
    can_fulfill: bool   # 是否能完全满足需求


class SkillMatcher:
    """
    Skill 匹配器
    
    根据需求分析结果，在现有 Skills 中找到最佳匹配
    """
    
    def find_best_match(
        self,
        need: NeedAnalysis,
        existing_skills: List[Dict[str, Any]],
    ) -> Optional[MatchResult]:
        """
        找到最佳匹配的 Skill
        
        Args:
            need: 需求分析结果
            existing_skills: 现有 Skills 列表
            
        Returns:
            MatchResult 或 None（没有匹配）
        """
        if not existing_skills:
            return None
        
        best_match = None
        best_score = 0.0
        
        for skill in existing_skills:
            score = self._calculate_match_score(need, skill)
            
            if score > best_score and score >= 0.6:  # 阈值 0.6
                best_score = score
                best_match = skill
        
        if best_match:
            return MatchResult(
                skill_name=best_match.get("name", "unknown"),
                match_score=best_score,
                match_reason=self._generate_match_reason(need, best_match),
                can_fulfill=best_score >= 0.8,  # 0.8 以上认为可以完全满足
            )
        
        return None
    
    def _calculate_match_score(
        self,
        need: NeedAnalysis,
        skill: Dict[str, Any],
    ) -> float:
        """
        计算匹配分数
        
        策略：
        1. 名称匹配（关键词重叠）
        2. 领域匹配
        3. 能力匹配
        """
        scores = []
        
        # 1. 名称关键词匹配
        skill_name = skill.get("name", "").lower()
        skill_desc = skill.get("description", "").lower()
        suggested_name = (need.suggested_skill_name or "").lower()
        
        # 如果建议的名称和现有 skill 名称相似
        if suggested_name and skill_name:
            # 简单字符串匹配
            if suggested_name in skill_name or skill_name in suggested_name:
                scores.append(0.9)
            # 关键词匹配
            suggested_words = set(suggested_name.split("_"))
            skill_words = set(skill_name.split("_"))
            overlap = len(suggested_words & skill_words)
            if overlap > 0:
                scores.append(0.5 + 0.2 * overlap)
        
        # 2. 领域匹配
        skill_domain = self._infer_domain(skill)
        if need.domain == skill_domain:
            scores.append(0.7)
        elif self._domain_related(need.domain, skill_domain):
            scores.append(0.4)
        
        # 3. 能力匹配
        skill_tools = skill.get("tools", [])
        if skill_tools:
            tool_names = [t.get("name", "").lower() for t in skill_tools]
            tool_desc = " ".join([t.get("description", "").lower() for t in skill_tools])
            
            for capability in need.required_capabilities:
                cap_lower = capability.lower()
                # 检查能力关键词是否在工具名称或描述中
                if any(cap_lower in name for name in tool_names):
                    scores.append(0.6)
                if cap_lower in tool_desc:
                    scores.append(0.4)
        
        # 4. 描述匹配（简单关键词）
        intent_keywords = set(need.intent.lower().split())
        desc_keywords = set(skill_desc.split())
        keyword_overlap = len(intent_keywords & desc_keywords)
        if keyword_overlap > 0:
            scores.append(min(0.3 * keyword_overlap, 0.8))
        
        # 返回最高分
        return max(scores) if scores else 0.0
    
    def _infer_domain(self, skill: Dict[str, Any]) -> str:
        """从 Skill 推断领域"""
        name = skill.get("name", "").lower()
        desc = skill.get("description", "").lower()
        text = name + " " + desc
        
        # 关键词匹配
        domain_keywords = {
            "file": ["file", "read", "write", "directory", "folder"],
            "network": ["http", "url", "web", "api", "fetch", "download"],
            "data": ["data", "json", "csv", "parse", "convert"],
            "system": ["command", "shell", "exec", "system", "process"],
            "git": ["git", "commit", "branch", "repository"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in text for kw in keywords):
                return domain
        
        return "other"
    
    def _domain_related(self, domain1: str, domain2: str) -> bool:
        """判断两个领域是否相关"""
        if domain1 == domain2:
            return True
        
        # 相关领域映射
        related = {
            "file": ["data", "system"],
            "network": ["data", "system"],
            "data": ["file", "network"],
            "system": ["file", "network"],
        }
        
        return domain2 in related.get(domain1, [])
    
    def _generate_match_reason(
        self,
        need: NeedAnalysis,
        skill: Dict[str, Any],
    ) -> str:
        """生成匹配原因说明"""
        skill_name = skill.get("name", "unknown")
        
        reasons = []
        
        # 名称相似
        if need.suggested_skill_name:
            if need.suggested_skill_name.lower() in skill_name.lower():
                reasons.append(f"名称相似（{need.suggested_skill_name}）")
        
        # 领域匹配
        skill_domain = self._infer_domain(skill)
        if need.domain == skill_domain:
            reasons.append(f"同属{need.domain}领域")
        
        # 工具能力
        tools = skill.get("tools", [])
        if tools:
            tool_names = [t.get("name", "") for t in tools[:2]]
            reasons.append(f"包含工具：{', '.join(tool_names)}")
        
        return "；".join(reasons) if reasons else "功能匹配"
