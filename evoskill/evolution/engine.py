"""
Skill 进化引擎 - 核心协调器

协调整个 Skill 进化流程：
分析 → 匹配 → 决策 → 设计 → 生成 → 验证 → 集成
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncIterator

from evoskill.core.llm import LLMProvider
from evoskill.core.session import AgentSession
from evoskill.core.types import Event, EventType

from evoskill.evolution.analyzer import NeedAnalyzer, NeedAnalysis
from evoskill.evolution.matcher import SkillMatcher, MatchResult
from evoskill.evolution.designer import SkillDesigner, SkillDesign
from evoskill.evolution.generator import SkillGenerator
from evoskill.evolution.validator import SkillValidator, ValidationResult
from evoskill.evolution.integrator import SkillIntegrator


@dataclass
class EvolutionResult:
    """进化结果"""
    status: str  # "created", "reused", "modified", "failed"
    skill_name: str
    skill_path: Optional[Path]
    message: str
    need_analysis: NeedAnalysis
    match_result: Optional[MatchResult] = None
    validation_result: Optional[ValidationResult] = None
    details: Dict[str, Any] = field(default_factory=dict)


class SkillEvolutionEngine:
    """
    Skill 进化引擎
    
    核心协调器，管理整个 Skill 进化流程
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        skills_dir: Path,
    ):
        self.llm = llm_provider
        self.skills_dir = skills_dir
        
        # 子组件
        self.analyzer = NeedAnalyzer(llm_provider)
        self.matcher = SkillMatcher()
        self.designer = SkillDesigner(llm_provider)
        self.generator = SkillGenerator()
        self.validator = SkillValidator()
        self.integrator = SkillIntegrator(skills_dir)
    
    async def evolve(
        self,
        user_request: str,
        existing_skills: List[Dict[str, Any]],
        session: Optional[AgentSession] = None,
    ) -> AsyncIterator[Event]:
        """
        执行 Skill 进化流程
        
        Args:
            user_request: 用户自然语言请求
            existing_skills: 现有 Skills 列表
            session: 可选的 Session，用于立即集成
            
        Yields:
            Event 事件流，最后一个事件包含 result 字段
        """
        # 步骤 1: 需求分析
        yield Event(
            type=EventType.SKILL_CREATED,
            data={"status": "analyzing", "message": "正在分析需求..."}
        )
        
        need = await self.analyzer.analyze(user_request, existing_skills)
        
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "analyzed",
                "intent": need.intent,
                "domain": need.domain,
                "can_use_existing": need.can_use_existing,
            }
        )
        
        # 步骤 2: Skill 匹配
        yield Event(
            type=EventType.SKILL_CREATED,
            data={"status": "matching", "message": "正在匹配现有 Skills..."}
        )
        
        match = self.matcher.find_best_match(need, existing_skills)
        
        if match and match.can_fulfill:
            # 使用现有 Skill
            result = EvolutionResult(
                status="reused",
                skill_name=match.skill_name,
                skill_path=None,
                message=f"使用现有 Skill: {match.skill_name} ({match.match_reason})",
                need_analysis=need,
                match_result=match,
            )
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "status": "reused",
                    "skill_name": match.skill_name,
                    "message": f"使用现有 Skill: {match.skill_name}",
                    "match_reason": match.match_reason,
                    "result": result,
                }
            )
            return
        
        # 步骤 3: 创建新 Skill
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "designing",
                "message": "正在设计新 Skill...",
            }
        )
        
        design = await self.designer.design(need, existing_skills)
        
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "designed",
                "skill_name": design.name,
                "tools": [t.name for t in design.tools],
            }
        )
        
        # 步骤 4: 生成代码
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "generating",
                "message": f"正在生成 {design.name} 代码...",
            }
        )
        
        generated_files = self.generator.generate(design, self.skills_dir)
        
        skill_path = self.skills_dir / design.name
        
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "generated",
                "skill_path": str(skill_path),
                "files": list(generated_files.keys()),
            }
        )
        
        # 步骤 5: 验证
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "validating",
                "message": "正在验证代码...",
            }
        )
        
        validation = await self.validator.validate(skill_path)
        
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "validated",
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
            }
        )
        
        if not validation.valid:
            result = EvolutionResult(
                status="failed",
                skill_name=design.name,
                skill_path=skill_path,
                message=f"验证失败: {', '.join(validation.errors)}",
                need_analysis=need,
                match_result=match,
                validation_result=validation,
            )
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "status": "failed",
                    "message": f"验证失败: {', '.join(validation.errors)}",
                    "result": result,
                }
            )
            return
        
        # 步骤 6: 集成
        yield Event(
            type=EventType.SKILL_CREATED,
            data={
                "status": "integrating",
                "message": "正在集成到系统...",
            }
        )
        
        integration = self.integrator.integrate(skill_path, session)
        
        if integration["success"]:
            result = EvolutionResult(
                status="created",
                skill_name=design.name,
                skill_path=skill_path,
                message=f"成功创建 Skill '{design.name}'，包含 {len(design.tools)} 个工具",
                need_analysis=need,
                match_result=match,
                validation_result=validation,
                details={
                    "files": list(generated_files.keys()),
                    "tools": [t.name for t in design.tools],
                    "integration": integration,
                }
            )
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "status": "completed",
                    "skill_name": design.name,
                    "skill_path": str(skill_path),
                    "tools": integration.get("registered_tools", []),
                    "message": f"Skill '{design.name}' 创建完成并激活！",
                    "result": result,
                }
            )
        else:
            result = EvolutionResult(
                status="warning",
                skill_name=design.name,
                skill_path=skill_path,
                message=f"代码已生成，但集成失败: {integration.get('error')}",
                need_analysis=need,
                match_result=match,
                validation_result=validation,
            )
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "status": "warning",
                    "message": f"代码已生成，但集成失败: {integration.get('error')}",
                    "result": result,
                }
            )
    
    async def quick_create(
        self,
        skill_name: str,
        description: str,
        session: Optional[AgentSession] = None,
    ) -> EvolutionResult:
        """
        快速创建 Skill（简化版）
        
        用于直接根据名称和描述创建，跳过复杂的分析过程
        """
        # 构造简单需求
        need = NeedAnalysis(
            intent=description,
            domain="other",
            required_capabilities=[],
            complexity="medium",
            can_use_existing=False,
            suggested_skill_name=skill_name,
        )
        
        # 直接设计
        design = await self.designer.design(need, [])
        
        # 生成
        generated_files = self.generator.generate(design, self.skills_dir)
        skill_path = self.skills_dir / design.name
        
        # 验证
        validation = await self.validator.validate(skill_path)
        
        # 集成
        if validation.valid and session:
            integration = self.integrator.integrate(skill_path, session)
        
        return EvolutionResult(
            status="created" if validation.valid else "failed",
            skill_name=design.name,
            skill_path=skill_path,
            message=f"快速创建 {'成功' if validation.valid else '失败'}",
            need_analysis=need,
            validation_result=validation,
        )
