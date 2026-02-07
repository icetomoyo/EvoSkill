"""
Skill 进化系统

提供 Skill 的自动创建、修改和进化能力
"""

from evoskill.evolution.engine import SkillEvolutionEngine, EvolutionResult
from evoskill.evolution.analyzer import NeedAnalyzer, NeedAnalysis
from evoskill.evolution.matcher import SkillMatcher, MatchResult
from evoskill.evolution.designer import SkillDesigner, SkillDesign
from evoskill.evolution.generator import SkillGenerator
from evoskill.evolution.validator import SkillValidator, ValidationResult
from evoskill.evolution.integrator import SkillIntegrator

__all__ = [
    "SkillEvolutionEngine",
    "EvolutionResult",
    "NeedAnalyzer",
    "NeedAnalysis",
    "SkillMatcher",
    "MatchResult",
    "SkillDesigner",
    "SkillDesign",
    "SkillGenerator",
    "SkillValidator",
    "ValidationResult",
    "SkillIntegrator",
]
