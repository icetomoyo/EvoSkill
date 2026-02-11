"""
Print Mode
Equivalent to Pi Mono's packages/coding-agent/src/modes/print-mode.ts

Non-interactive print mode for one-shot operations.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class PrintResult:
    """Result of print mode operation"""
    output: str
    exit_code: int
    metadata: Dict[str, Any]


class PrintMode:
    """
    Print mode for non-interactive operations.
    
    Processes a single request and returns output.
    Suitable for scripting and CI/CD.
    
    Example:
        >>> mode = PrintMode()
        >>> result = mode.run("Explain Python decorators", context={})
        >>> print(result.output)
    """
    
    def __init__(self):
        self._output_buffer: List[str] = []
        self._metadata: Dict[str, Any] = {}
    
    def run(
        self,
        prompt: str,
        context: Optional[Dict] = None,
        max_iterations: int = 10
    ) -> PrintResult:
        """
        Run print mode with a prompt.
        
        Args:
            prompt: User prompt
            context: Optional context
            max_iterations: Maximum tool iterations
            
        Returns:
            PrintResult with output
        """
        context = context or {}
        
        # In a real implementation, this would:
        # 1. Send prompt to LLM
        # 2. Execute any tool calls
        # 3. Return final output
        
        # For now, return a placeholder
        return PrintResult(
            output=f"Print mode processing: {prompt[:50]}...",
            exit_code=0,
            metadata={"iterations": 0}
        )
    
    def run_with_files(
        self,
        prompt: str,
        files: List[str],
        context: Optional[Dict] = None
    ) -> PrintResult:
        """
        Run with file inputs.
        
        Args:
            prompt: User prompt
            files: List of file paths to include
            context: Optional context
            
        Returns:
            PrintResult with output
        """
        # Read files and include in context
        file_contents = []
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_contents.append(f"File: {filepath}\n```\n{content}\n```")
            except Exception as e:
                file_contents.append(f"Error reading {filepath}: {e}")
        
        full_prompt = "\n\n".join(file_contents) + f"\n\n{prompt}"
        
        return self.run(full_prompt, context)
    
    def _append_output(self, text: str):
        """Append to output buffer"""
        self._output_buffer.append(text)
    
    def _get_output(self) -> str:
        """Get full output"""
        return "\n".join(self._output_buffer)


__all__ = ["PrintMode", "PrintResult"]
