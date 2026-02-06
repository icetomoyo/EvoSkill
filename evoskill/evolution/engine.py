"""
Skill 进化引擎主类

整合需求分析、设计、生成、验证、部署全流程
"""

import shutil
from pathlib import Path
from typing import AsyncIterator, List, Optional

from evoskill.core.types import (
    Event,
    EventType,
    NeedAnalysis,
    SkillDesign,
    GeneratedSkill,
    DeployResult,
)
from evoskill.core.events import EventEmitter
from evoskill.evolution.analyzer import NeedAnalyzer
from evoskill.evolution.generator import SkillGenerator, SkillValidator


class SkillEvolutionEngine:
    """
    Skill 进化引擎
    
    负责自动识别需求 → 设计 → 生成 → 验证 → 部署的全流程
    """
    
    def __init__(
        self,
        skills_dir: Path,
        llm_client=None,
    ):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self.analyzer = NeedAnalyzer(llm_client)
        self.generator = SkillGenerator(llm_client)
        self.validator = SkillValidator()
        
        self.events = EventEmitter()
    
    async def evolve(
        self,
        user_request: str,
        conversation_context: str = "",
        available_skills: Optional[List[str]] = None,
    ) -> AsyncIterator[Event]:
        """
        执行 Skill 进化流程
        
        Args:
            user_request: 用户请求
            conversation_context: 对话上下文
            available_skills: 可用 Skills
            
        Yields:
            进度事件
        """
        await self.events.start()
        
        try:
            # Step 1: 需求分析
            yield Event(
                type=EventType.SKILL_CREATED,
                data={"step": "analyze", "status": "started"}
            )
            
            analysis = await self.analyzer.analyze(
                user_request,
                conversation_context,
                available_skills
            )
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "step": "analyze",
                    "status": "completed",
                    "analysis": {
                        "user_need": analysis.user_need,
                        "features": analysis.core_features,
                        "feasible": analysis.feasible,
                    }
                }
            )
            
            if not analysis.feasible:
                yield Event(
                    type=EventType.SKILL_CREATED,
                    data={
                        "step": "error",
                        "message": f"需求不可行: {analysis.reason}"
                    }
                )
                return
            
            # Step 2: 设计
            yield Event(
                type=EventType.SKILL_CREATED,
                data={"step": "design", "status": "started"}
            )
            
            design = await self.generator.design(analysis)
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "step": "design",
                    "status": "completed",
                    "design": {
                        "name": design.name,
                        "description": design.description,
                        "tools": [t.name for t in design.tools],
                    }
                }
            )
            
            # Step 3: 生成代码
            yield Event(
                type=EventType.SKILL_CREATED,
                data={"step": "generate", "status": "started"}
            )
            
            generated = await self.generator.generate(design, analysis)
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={
                    "step": "generate",
                    "status": "completed",
                    "files": design.file_structure,
                }
            )
            
            # Step 4: 验证
            yield Event(
                type=EventType.SKILL_CREATED,
                data={"step": "validate", "status": "started"}
            )
            
            is_valid, errors = await self.validator.validate(generated)
            
            if not is_valid:
                yield Event(
                    type=EventType.SKILL_CREATED,
                    data={
                        "step": "validate",
                        "status": "failed",
                        "errors": errors,
                    }
                )
                return
            
            yield Event(
                type=EventType.SKILL_CREATED,
                data={"step": "validate", "status": "passed"}
            )
            
            # Step 5: 部署
            yield Event(
                type=EventType.SKILL_CREATED,
                data={"step": "deploy", "status": "started"}
            )
            
            result = await self.deploy(generated)
            
            if result.success:
                yield Event(
                    type=EventType.SKILL_CREATED,
                    data={
                        "step": "deploy",
                        "status": "completed",
                        "skill_path": str(result.skill_path),
                        "skill_name": design.name,
                    }
                )
            else:
                yield Event(
                    type=EventType.SKILL_CREATED,
                    data={
                        "step": "deploy",
                        "status": "failed",
                        "error": result.error,
                    }
                )
        
        finally:
            await self.events.stop()
    
    async def deploy(self, generated: GeneratedSkill) -> DeployResult:
        """
        部署生成的 Skill
        
        Args:
            generated: 生成的 Skill
            
        Returns:
            部署结果
        """
        try:
            skill_path = self.skills_dir / generated.design.name
            
            # 如果已存在，备份旧版本
            if skill_path.exists():
                backup_path = skill_path.with_suffix(".backup")
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.move(skill_path, backup_path)
            
            # 创建目录结构
            skill_path.mkdir(parents=True)
            (skill_path / "tests").mkdir()
            
            # 写入文件
            with open(skill_path / "SKILL.md", "w", encoding="utf-8") as f:
                f.write(generated.skill_md)
            
            with open(skill_path / "main.py", "w", encoding="utf-8") as f:
                f.write(generated.main_code)
            
            with open(skill_path / "tests" / "test_main.py", "w", encoding="utf-8") as f:
                f.write(generated.test_code)
            
            with open(skill_path / "requirements.txt", "w", encoding="utf-8") as f:
                f.write(generated.requirements)
            
            return DeployResult(
                success=True,
                skill_path=skill_path,
            )
        
        except Exception as e:
            return DeployResult(
                success=False,
                error=str(e),
            )
    
    def should_evolve(
        self,
        user_request: str,
        available_skills: List[str]
    ) -> bool:
        """
        快速判断是否应该触发进化
        
        Args:
            user_request: 用户请求
            available_skills: 可用 Skills
            
        Returns:
            是否应该进化
        """
        return self.analyzer.should_create_skill(user_request, available_skills)
