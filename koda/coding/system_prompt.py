"""
System Prompt Builder
Equivalent to Pi Mono's packages/coding-agent/src/core/system-prompt.ts

Builds system prompts for different contexts and modes.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class AgentMode(Enum):
    """Agent operation modes"""
    CODE = "code"
    CHAT = "chat"
    PLAN = "plan"
    REVIEW = "review"
    DEBUG = "debug"


class AgentPersonality(Enum):
    """Agent personality styles"""
    HELPFUL = "helpful"
    CONCISE = "concise"
    DETAILED = "detailed"
    Socratic = "socratic"


@dataclass
class SystemPromptConfig:
    """Configuration for system prompt generation"""
    mode: AgentMode = AgentMode.CODE
    personality: AgentPersonality = AgentPersonality.HELPFUL
    allowed_tools: Optional[List[str]] = None
    context_window: int = 128000
    enable_thinking: bool = True
    language_preference: Optional[str] = None
    custom_instructions: Optional[str] = None


class SystemPromptBuilder:
    """
    Builder for system prompts.
    
    Creates appropriate system prompts based on mode and context.
    
    Example:
        >>> builder = SystemPromptBuilder()
        >>> config = SystemPromptConfig(mode=AgentMode.CODE)
        >>> prompt = builder.build(config)
    """
    
    # Base prompts for each mode
    BASE_PROMPTS = {
        AgentMode.CODE: """You are an expert coding assistant. Your goal is to help write, review, and improve code.

Guidelines:
- Write clean, well-documented code following best practices
- Explain your reasoning when making changes
- Consider edge cases and error handling
- Use appropriate design patterns
- Keep code maintainable and readable""",

        AgentMode.CHAT: """You are a helpful assistant for general programming questions and discussions.

Guidelines:
- Provide clear, accurate information
- Ask clarifying questions when needed
- Offer multiple approaches when applicable
- Be concise but thorough""",

        AgentMode.PLAN: """You are in planning mode. Help break down tasks and create implementation plans.

Guidelines:
- Analyze requirements thoroughly
- Break down into clear, actionable steps
- Identify potential challenges
- Suggest alternative approaches
- Prioritize tasks logically""",

        AgentMode.REVIEW: """You are conducting a code review. Focus on finding issues and suggesting improvements.

Guidelines:
- Check for bugs, security issues, and performance problems
- Verify code follows best practices
- Look for maintainability issues
- Suggest specific improvements
- Be constructive and educational""",

        AgentMode.DEBUG: """You are debugging code. Help identify and fix issues.

Guidelines:
- Analyze error messages and stack traces carefully
- Consider root causes, not just symptoms
- Suggest minimal fixes
- Explain why the issue occurred
- Verify the fix resolves the problem""",
    }
    
    # Personality modifiers
    PERSONALITY_MODIFIERS = {
        AgentPersonality.HELPFUL: "Be helpful, friendly, and encouraging.",
        AgentPersonality.CONCISE: "Be concise and direct. Focus on essential information only.",
        AgentPersonality.DETAILED: "Be thorough and detailed. Provide comprehensive explanations.",
        AgentPersonality.Socratic: "Use the Socratic method. Guide with questions rather than direct answers.",
    }
    
    # Tool usage instructions
    TOOL_INSTRUCTIONS = """
Available Tools:
{{tools}}

When using tools:
- Choose the appropriate tool for the task
- Provide clear, specific arguments
- Check tool results carefully
- Combine multiple tools when needed"""
    
    def __init__(self):
        self._custom_sections: List[str] = []
    
    def build(self, config: SystemPromptConfig) -> str:
        """
        Build system prompt from configuration.
        
        Args:
            config: Prompt configuration
            
        Returns:
            Complete system prompt
        """
        sections = []
        
        # Base prompt for mode
        base = self.BASE_PROMPTS.get(config.mode, self.BASE_PROMPTS[AgentMode.CODE])
        sections.append(base)
        
        # Personality modifier
        personality = self.PERSONALITY_MODIFIERS.get(config.personality, "")
        if personality:
            sections.append(personality)
        
        # Tool instructions
        if config.allowed_tools:
            tools_list = "\n".join(f"- {tool}" for tool in config.allowed_tools)
            tool_section = self.TOOL_INSTRUCTIONS.replace("{{tools}}", tools_list)
            sections.append(tool_section)
        
        # Context window info
        sections.append(f"\nContext window: {config.context_window:,} tokens")
        
        # Thinking mode
        if config.enable_thinking:
            sections.append("Think step-by-step when solving complex problems.")
        
        # Language preference
        if config.language_preference:
            sections.append(f"Prefer using {config.language_preference} for code examples.")
        
        # Custom instructions
        if config.custom_instructions:
            sections.append(f"\nAdditional instructions:\n{config.custom_instructions}")
        
        # Add custom sections
        for section in self._custom_sections:
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def add_section(self, section: str):
        """Add a custom section to all prompts"""
        self._custom_sections.append(section)
    
    def build_for_code_review(
        self,
        language: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """
        Build prompt for code review.
        
        Args:
            language: Programming language
            focus_areas: Specific areas to focus on
            
        Returns:
            System prompt
        """
        config = SystemPromptConfig(
            mode=AgentMode.REVIEW,
            personality=AgentPersonality.DETAILED
        )
        
        custom = "Focus areas:\n"
        if focus_areas:
            for area in focus_areas:
                custom += f"- {area}\n"
        else:
            custom += "- Code correctness\n- Security issues\n- Performance\n- Maintainability\n"
        
        if language:
            custom += f"\nLanguage: {language}\nFollow {language} best practices."
        
        config.custom_instructions = custom
        return self.build(config)
    
    def build_for_debugging(
        self,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> str:
        """
        Build prompt for debugging.
        
        Args:
            error_type: Type of error
            stack_trace: Error stack trace
            
        Returns:
            System prompt
        """
        config = SystemPromptConfig(
            mode=AgentMode.DEBUG,
            personality=AgentPersonality.DETAILED
        )
        
        custom = ""
        if error_type:
            custom += f"Error type: {error_type}\n"
        if stack_trace:
            custom += f"Stack trace:\n{stack_trace}\n"
        
        config.custom_instructions = custom if custom else None
        return self.build(config)
    
    def build_for_planning(
        self,
        task_description: str,
        constraints: Optional[List[str]] = None
    ) -> str:
        """
        Build prompt for planning.
        
        Args:
            task_description: Description of the task
            constraints: List of constraints
            
        Returns:
            System prompt
        """
        config = SystemPromptConfig(
            mode=AgentMode.PLAN,
            personality=AgentPersonality.DETAILED
        )
        
        custom = f"Task: {task_description}\n\n"
        if constraints:
            custom += "Constraints:\n"
            for constraint in constraints:
                custom += f"- {constraint}\n"
        
        config.custom_instructions = custom
        return self.build(config)


# Convenience functions
def get_code_prompt(tools: Optional[List[str]] = None) -> str:
    """Get standard code assistant prompt"""
    builder = SystemPromptBuilder()
    config = SystemPromptConfig(
        mode=AgentMode.CODE,
        allowed_tools=tools
    )
    return builder.build(config)


def get_review_prompt(language: Optional[str] = None) -> str:
    """Get code review prompt"""
    builder = SystemPromptBuilder()
    return builder.build_for_code_review(language=language)


def get_debug_prompt(error: Optional[str] = None) -> str:
    """Get debugging prompt"""
    builder = SystemPromptBuilder()
    return builder.build_for_debugging(error_type=error)


__all__ = [
    "SystemPromptBuilder",
    "SystemPromptConfig",
    "AgentMode",
    "AgentPersonality",
    "get_code_prompt",
    "get_review_prompt",
    "get_debug_prompt",
]
