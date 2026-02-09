"""
Tool Registry

Tool registration and execution framework.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


@dataclass
class ToolContext:
    """Context passed to tool during execution"""
    working_dir: str
    env: Dict[str, str]
    timeout: int = 60
    
    @classmethod
    def default(cls) -> "ToolContext":
        import os
        return cls(
            working_dir=os.getcwd(),
            env=dict(os.environ),
            timeout=60
        )


@dataclass
class Tool:
    """Tool definition"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    requires_confirmation: bool = False
    
    def to_definition(self) -> Dict[str, Any]:
        """Convert to LLM tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [
                        k for k, v in self.parameters.items()
                        if isinstance(v, dict) and "default" not in v
                    ],
                },
            },
        }


class ToolRegistry:
    """
    Registry for tools
    
    Features:
    - Register/unregister tools
    - Tool lookup by name
    - Execute tools with context
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._execution_history: List[Dict[str, Any]] = []
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool
        
        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            name: Tool name
            
        Returns:
            True if tool was removed
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Get tool by name
        
        Args:
            name: Tool name
            
        Returns:
            Tool or None
        """
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """Check if tool exists"""
        return name in self._tools
    
    def list_tools(self) -> List[str]:
        """List all tool names"""
        return list(self._tools.keys())
    
    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for LLM"""
        return [tool.to_definition() for tool in self._tools.values()]
    
    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolContext] = None
    ) -> str:
        """
        Execute a tool
        
        Args:
            name: Tool name
            arguments: Tool arguments
            context: Execution context
            
        Returns:
            Tool output as string
        """
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        
        ctx = context or ToolContext.default()
        
        # Record execution
        execution_record = {
            "tool": name,
            "arguments": arguments,
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            # Check if async
            import asyncio
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            
            # Convert result to string
            if hasattr(result, 'output'):
                output = result.output
            elif hasattr(result, 'content'):
                output = result.content
            elif hasattr(result, 'success') and hasattr(result, 'result'):
                output = result.result if result.success else str(getattr(result, 'error', 'Unknown error'))
            else:
                output = str(result)
            
            execution_record["success"] = True
            execution_record["output_length"] = len(output)
            
            return output
            
        except Exception as e:
            execution_record["success"] = False
            execution_record["error"] = str(e)
            raise
        finally:
            self._execution_history.append(execution_record)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get tool execution history"""
        return list(self._execution_history)
    
    def clear_history(self) -> None:
        """Clear execution history"""
        self._execution_history.clear()
