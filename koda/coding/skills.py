"""
Skills System
Equivalent to Pi Mono's packages/coding-agent/src/skills/skills.ts

Dynamic tool loading and management system.
"""
import os
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field


@dataclass
class Skill:
    """A loaded skill with metadata and handlers"""
    id: str
    name: str
    description: str
    version: str
    tools: List[Dict[str, Any]] = field(default_factory=list)
    handlers: Dict[str, Callable] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillsRegistry:
    """Registry of available skills"""
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._tool_map: Dict[str, str] = {}  # tool_name -> skill_id
    
    def register(self, skill: Skill):
        """Register a skill"""
        self._skills[skill.id] = skill
        
        # Map tools to skill
        for tool in skill.tools:
            tool_name = tool.get("function", {}).get("name", tool.get("name"))
            if tool_name:
                self._tool_map[tool_name] = skill.id
    
    def get(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self._skills.get(skill_id)
    
    def get_by_tool(self, tool_name: str) -> Optional[Skill]:
        """Get skill that provides a tool"""
        skill_id = self._tool_map.get(tool_name)
        if skill_id:
            return self._skills.get(skill_id)
        return None
    
    def list_all(self) -> List[Skill]:
        """List all registered skills"""
        return list(self._skills.values())
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all skills"""
        tools = []
        for skill in self._skills.values():
            tools.extend(skill.tools)
        return tools
    
    def get_handler(self, tool_name: str) -> Optional[Callable]:
        """Get handler for a tool"""
        skill = self.get_by_tool(tool_name)
        if skill:
            return skill.handlers.get(tool_name)
        return None


class SkillsLoader:
    """
    Loads skills from directories.
    
    Skills are organized as:
        skills/
            skill-name/
                skill.yaml      # Metadata and tool definitions
                handler.py      # Tool implementations
    """
    
    def __init__(self, registry: SkillsRegistry):
        self._registry = registry
    
    def load_directory(self, directory: str) -> List[Skill]:
        """
        Load all skills from a directory.
        
        Args:
            directory: Path to skills directory
            
        Returns:
            List of loaded skills
        """
        skills = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return skills
        
        for skill_dir in dir_path.iterdir():
            if not skill_dir.is_dir():
                continue
            
            try:
                skill = self._load_skill(skill_dir)
                if skill:
                    skills.append(skill)
                    self._registry.register(skill)
            except Exception as e:
                # Log error but continue loading other skills
                print(f"Failed to load skill from {skill_dir}: {e}")
        
        return skills
    
    def _load_skill(self, skill_dir: Path) -> Optional[Skill]:
        """Load a single skill from directory"""
        # Look for skill.yaml
        config_file = skill_dir / "skill.yaml"
        if not config_file.exists():
            config_file = skill_dir / "skill.yml"
        if not config_file.exists():
            config_file = skill_dir / "skill.json"
        
        if not config_file.exists():
            return None
        
        # Load config
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.suffix == ".json":
                config = json.load(f)
            else:
                # Simple YAML parsing (just key: value pairs)
                config = self._parse_simple_yaml(f.read())
        
        skill_id = config.get("id") or skill_dir.name
        
        # Load handlers if present
        handlers = {}
        handler_file = skill_dir / "handler.py"
        if handler_file.exists():
            handlers = self._load_handlers(handler_file, skill_id)
        
        # Build tools list
        tools = []
        for tool_def in config.get("tools", []):
            if isinstance(tool_def, dict):
                tools.append(tool_def)
            elif isinstance(tool_def, str):
                # Simple tool name, build basic structure
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_def,
                        "description": f"Tool {tool_def}",
                    }
                })
        
        skill = Skill(
            id=skill_id,
            name=config.get("name", skill_id),
            description=config.get("description", ""),
            version=config.get("version", "0.1.0"),
            tools=tools,
            handlers=handlers,
            metadata=config.get("metadata", {}),
        )
        
        return skill
    
    def _parse_simple_yaml(self, content: str) -> Dict[str, Any]:
        """Parse simple YAML content"""
        result = {}
        current_key = None
        current_list = None
        
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            
            if line.startswith("  - ") and current_key:
                # List item
                value = stripped[2:].strip()
                if isinstance(result.get(current_key), list):
                    result[current_key].append(value)
            elif ":" in stripped:
                # Key-value pair
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if value:
                    result[key] = value
                else:
                    # Start of list or nested structure
                    result[key] = []
                    current_key = key
            
        return result
    
    def _load_handlers(self, handler_file: Path, skill_id: str) -> Dict[str, Callable]:
        """Load handler functions from Python file"""
        handlers = {}
        
        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_id}",
            handler_file
        )
        if not spec or not spec.loader:
            return handlers
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find all callable handlers
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and not name.startswith("_"):
                handlers[name] = obj
        
        return handlers


class SkillsManager:
    """
    Manages skills loading and execution.
    
    Example:
        >>> manager = SkillsManager()
        >>> manager.load_skills("./skills")
        >>> result = await manager.execute("read_file", {"path": "/tmp/test.txt"})
    """
    
    def __init__(self, skills_dirs: Optional[List[str]] = None):
        self._registry = SkillsRegistry()
        self._loader = SkillsLoader(self._registry)
        self._skills_dirs = skills_dirs or []
        
        # Load skills from configured directories
        for directory in self._skills_dirs:
            self._loader.load_directory(directory)
    
    def load_skills(self, directory: str) -> List[Skill]:
        """
        Load skills from a directory.
        
        Args:
            directory: Path to skills directory
            
        Returns:
            List of loaded skills
        """
        return self._loader.load_directory(directory)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self._registry.get(skill_id)
    
    def list_skills(self) -> List[Skill]:
        """List all loaded skills"""
        return self._registry.list_all()
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all skills"""
        return self._registry.list_tools()
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        handler = self._registry.get_handler(tool_name)
        if not handler:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Execute handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        else:
            return handler(**arguments)
    
    def register_skill(self, skill: Skill):
        """Register a skill manually"""
        self._registry.register(skill)


# Global skills manager instance
_skills_manager: Optional[SkillsManager] = None


def get_skills_manager() -> SkillsManager:
    """Get global skills manager"""
    global _skills_manager
    if _skills_manager is None:
        # Initialize with default directories
        default_dirs = ["./skills", "~/.koda/skills"]
        expanded_dirs = [
            os.path.expanduser(d) for d in default_dirs
        ]
        _skills_manager = SkillsManager(expanded_dirs)
    return _skills_manager


def set_skills_manager(manager: SkillsManager):
    """Set global skills manager"""
    global _skills_manager
    _skills_manager = manager


__all__ = [
    "Skill",
    "SkillsRegistry",
    "SkillsLoader",
    "SkillsManager",
    "get_skills_manager",
    "set_skills_manager",
]
