"""
SDK Interface
Equivalent to Pi Mono's packages/coding-agent/src/core/sdk.ts

Public SDK for integrating Koda into other applications.
"""
import asyncio
from typing import Optional, List, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ..agent.agent import Agent
from ..ai.types import Context, ModelInfo


@dataclass
class SDKConfig:
    """SDK configuration"""
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    base_url: Optional[str] = None
    timeout: float = 60.0
    max_iterations: int = 10
    working_directory: Optional[str] = None


@dataclass
class CodeResult:
    """Result of code operation"""
    success: bool
    code: str
    language: str
    explanation: str
    files_created: List[str] = None
    files_modified: List[str] = None
    error: Optional[str] = None


@dataclass
class ReviewResult:
    """Result of code review"""
    success: bool
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    summary: str
    score: int  # 0-100


class KodaSDK:
    """
    Public SDK for Koda coding agent.
    
    Provides high-level APIs for common operations.
    
    Example:
        >>> sdk = KodaSDK(api_key="your-key")
        >>> result = await sdk.generate_code("Create a web scraper")
        >>> print(result.code)
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        """
        Initialize SDK.
        
        Args:
            config: SDK configuration
        """
        self.config = config or SDKConfig()
        self._agent: Optional[Agent] = None
        self._init_agent()
    
    def _init_agent(self):
        """Initialize internal agent"""
        # This would create the actual agent instance
        # Simplified for SDK interface
        pass
    
    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None,
        files: Optional[List[str]] = None
    ) -> CodeResult:
        """
        Generate code from description.
        
        Args:
            description: What code should do
            language: Programming language
            context: Additional context
            files: Reference files
            
        Returns:
            CodeResult with generated code
        """
        prompt = self._build_code_prompt(description, language, context, files)
        
        # Execute through agent
        response = await self._execute_prompt(prompt)
        
        return CodeResult(
            success=True,
            code=response.get("code", ""),
            language=language,
            explanation=response.get("explanation", ""),
            files_created=response.get("files_created", []),
            files_modified=response.get("files_modified", [])
        )
    
    async def review_code(
        self,
        code: str,
        language: str = "python",
        focus_areas: Optional[List[str]] = None
    ) -> ReviewResult:
        """
        Review code for issues.
        
        Args:
            code: Code to review
            language: Programming language
            focus_areas: Specific areas to focus on
            
        Returns:
            ReviewResult with findings
        """
        prompt = self._build_review_prompt(code, language, focus_areas)
        
        response = await self._execute_prompt(prompt)
        
        return ReviewResult(
            success=True,
            issues=response.get("issues", []),
            suggestions=response.get("suggestions", []),
            summary=response.get("summary", ""),
            score=response.get("score", 0)
        )
    
    async def explain_code(
        self,
        code: str,
        language: str = "python",
        detail_level: str = "medium"
    ) -> str:
        """
        Explain what code does.
        
        Args:
            code: Code to explain
            language: Programming language
            detail_level: "brief", "medium", or "detailed"
            
        Returns:
            Explanation text
        """
        prompt = f"""Explain the following {language} code:

```{language}
{code}
```

Detail level: {detail_level}"""
        
        response = await self._execute_prompt(prompt)
        return response.get("explanation", "")
    
    async def refactor_code(
        self,
        code: str,
        goal: str,
        language: str = "python"
    ) -> CodeResult:
        """
        Refactor code to improve it.
        
        Args:
            code: Code to refactor
            goal: What to improve (e.g., "performance", "readability")
            language: Programming language
            
        Returns:
            CodeResult with refactored code
        """
        prompt = f"""Refactor the following {language} code to improve {goal}:

```{language}
{code}
```

Provide:
1. The refactored code
2. Explanation of changes"""
        
        response = await self._execute_prompt(prompt)
        
        return CodeResult(
            success=True,
            code=response.get("code", ""),
            language=language,
            explanation=response.get("explanation", "")
        )
    
    async def generate_tests(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest"
    ) -> CodeResult:
        """
        Generate unit tests for code.
        
        Args:
            code: Code to test
            language: Programming language
            framework: Testing framework
            
        Returns:
            CodeResult with test code
        """
        prompt = f"""Generate {framework} tests for the following {language} code:

```{language}
{code}
```

Requirements:
- Cover main functionality
- Include edge cases
- Tests should be self-contained"""
        
        response = await self._execute_prompt(prompt)
        
        return CodeResult(
            success=True,
            code=response.get("code", ""),
            language=language,
            explanation="Generated test suite"
        )
    
    async def chat(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Send a chat message.
        
        Args:
            message: User message
            history: Conversation history
            
        Returns:
            Assistant response
        """
        context = Context(
            messages=history or [],
            system_prompt=None
        )
        context.messages.append({"role": "user", "content": message})
        
        response = await self._execute_context(context)
        return response.get("content", "")
    
    async def stream_chat(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """
        Stream chat response.
        
        Args:
            message: User message
            history: Conversation history
            
        Yields:
            Response chunks
        """
        context = Context(
            messages=history or [],
            system_prompt=None
        )
        context.messages.append({"role": "user", "content": message})
        
        # This would stream from agent
        yield "Response would be streamed here..."
    
    def _build_code_prompt(
        self,
        description: str,
        language: str,
        context: Optional[str],
        files: Optional[List[str]]
    ) -> str:
        """Build prompt for code generation"""
        prompt = f"Generate {language} code for: {description}\n\n"
        
        if context:
            prompt += f"Context:\n{context}\n\n"
        
        if files:
            prompt += "Reference files:\n"
            for f in files:
                prompt += f"- {f}\n"
            prompt += "\n"
        
        prompt += f"Provide the {language} code and brief explanation."
        return prompt
    
    def _build_review_prompt(
        self,
        code: str,
        language: str,
        focus_areas: Optional[List[str]]
    ) -> str:
        """Build prompt for code review"""
        prompt = f"Review the following {language} code:\n\n"
        prompt += f"```{language}\n{code}\n```\n\n"
        
        if focus_areas:
            prompt += f"Focus areas: {', '.join(focus_areas)}\n\n"
        
        prompt += """Provide:
1. List of issues found
2. Improvement suggestions
3. Overall summary
4. Quality score (0-100)"""
        
        return prompt
    
    async def _execute_prompt(self, prompt: str) -> Dict[str, Any]:
        """Execute prompt and parse response"""
        # This would actually call the agent
        # Simplified for SDK interface
        return {
            "code": "# Generated code would appear here",
            "explanation": "Explanation would appear here",
            "files_created": [],
            "files_modified": [],
            "issues": [],
            "suggestions": [],
            "summary": "Summary would appear here",
            "score": 80,
            "content": "Response content"
        }
    
    async def _execute_context(self, context: Context) -> Dict[str, Any]:
        """Execute with context"""
        # This would actually call the agent
        return {"content": "Response would appear here"}


# Convenience functions for quick usage
_sdk_instance: Optional[KodaSDK] = None


def init_sdk(api_key: str, **kwargs) -> KodaSDK:
    """Initialize global SDK instance"""
    global _sdk_instance
    config = SDKConfig(api_key=api_key, **kwargs)
    _sdk_instance = KodaSDK(config)
    return _sdk_instance


def get_sdk() -> Optional[KodaSDK]:
    """Get global SDK instance"""
    return _sdk_instance


async def generate_code(description: str, **kwargs) -> CodeResult:
    """Generate code using global SDK"""
    sdk = get_sdk() or KodaSDK()
    return await sdk.generate_code(description, **kwargs)


async def review_code(code: str, **kwargs) -> ReviewResult:
    """Review code using global SDK"""
    sdk = get_sdk() or KodaSDK()
    return await sdk.review_code(code, **kwargs)


__all__ = [
    "KodaSDK",
    "SDKConfig",
    "CodeResult",
    "ReviewResult",
    "init_sdk",
    "get_sdk",
    "generate_code",
    "review_code",
]
