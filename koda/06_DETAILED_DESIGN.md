# Detailed Design: Remaining Features

> Complete design specifications for remaining features to achieve 100% parity
> Created: 2026-02-10

---

## Table of Contents

1. [packages/ai - Remaining Features](#1-packagesai---remaining-features)
2. [packages/agent - Remaining Features](#2-packagesagent---remaining-features)
3. [packages/coding-agent - Remaining Features](#3-packagescoding-agent---remaining-features)
4. [packages/mom - Remaining Features](#4-packagesmom---remaining-features)
5. [Implementation Roadmap](#5-implementation-roadmap)

---

## 1. packages/ai - Remaining Features

### 1.1 Claude Code Tool Name Mapping

**Pi Mono Reference**: `packages/ai/src/providers/anthropic.ts:90-120`

**Design**:
```python
# koda/ai/claude_code_mapping.py

from typing import Dict, Optional
from enum import Enum

class ClaudeCodeTool(str, Enum):
    """Claude Code canonical tool names"""
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    BASH = "Bash"
    GREP = "Grep"
    GLOB = "Glob"
    ASK_USER = "AskUserQuestion"
    ENTER_PLAN = "EnterPlanMode"
    EXIT_PLAN = "ExitPlanMode"
    KILL_SHELL = "KillShell"
    NOTEBOOK_EDIT = "NotebookEdit"
    SKILL = "Skill"
    TASK = "Task"
    TASK_OUTPUT = "TaskOutput"
    TODO_WRITE = "TodoWrite"
    WEB_FETCH = "WebFetch"
    WEB_SEARCH = "WebSearch"

class ToolNameMapper:
    """
    Maps tool names between Koda and Claude Code conventions
    
    Claude Code uses PascalCase tool names, while Koda uses lowercase_snake
    """
    
    # Mapping from lowercase to PascalCase
    _TO_CLAUDE_CODE: Dict[str, str] = {
        "read": "Read",
        "write": "Write",
        "edit": "Edit",
        "bash": "Bash",
        "grep": "Grep",
        "glob": "Glob",
        "ask_user": "AskUserQuestion",
        "enter_plan": "EnterPlanMode",
        "exit_plan": "ExitPlanMode",
        "kill_shell": "KillShell",
        "notebook_edit": "NotebookEdit",
        "skill": "Skill",
        "task": "Task",
        "task_output": "TaskOutput",
        "todo_write": "TodoWrite",
        "web_fetch": "WebFetch",
        "web_search": "WebSearch",
    }
    
    # Reverse mapping
    _FROM_CLAUDE_CODE: Dict[str, str] = {
        v: k for k, v in _TO_CLAUDE_CODE.items()
    }
    
    @classmethod
    def to_claude_code(cls, name: str) -> str:
        """Convert Koda tool name to Claude Code format"""
        normalized = name.lower().replace("-", "_")
        return cls._TO_CLAUDE_CODE.get(normalized, name)
    
    @classmethod
    def from_claude_code(cls, name: str) -> str:
        """Convert Claude Code tool name to Koda format"""
        return cls._FROM_CLAUDE_CODE.get(name, name.lower())
    
    @classmethod
    def is_claude_code_tool(cls, name: str) -> bool:
        """Check if name is a valid Claude Code tool"""
        return name in cls._FROM_CLAUDE_CODE

# Integration with Anthropic Provider
def transform_tool_for_anthropic(tool_name: str, arguments: dict) -> tuple[str, dict]:
    """
    Transform tool call for Anthropic API
    
    Returns:
        (transformed_name, transformed_arguments)
    """
    mapper = ToolNameMapper()
    new_name = mapper.to_claude_code(tool_name)
    
    # Some tools may need argument transformation
    transformed_args = arguments.copy()
    
    if new_name == "Read":
        # Claude Code Read expects "file_path" not "path"
        if "path" in transformed_args and "file_path" not in transformed_args:
            transformed_args["file_path"] = transformed_args.pop("path")
    
    return new_name, transformed_args
```

**Test Cases**:
```python
def test_tool_mapping():
    assert ToolNameMapper.to_claude_code("read") == "Read"
    assert ToolNameMapper.to_claude_code("ask_user") == "AskUserQuestion"
    assert ToolNameMapper.from_claude_code("Read") == "read"
    assert ToolNameMapper.from_claude_code("AskUserQuestion") == "ask_user"
```

---

### 1.2 Interleaved Thinking Support

**Pi Mono Reference**: `packages/ai/src/providers/anthropic.ts:200-250`

**Design**:
```python
# koda/ai/interleaved_thinking.py

from dataclasses import dataclass
from typing import List, Union, Iterator
from enum import Enum

class ContentBlockType(Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"

@dataclass
class ContentBlock:
    """A single content block in interleaved format"""
    type: ContentBlockType
    content: str
    signature: Optional[str] = None  # For thinking blocks
    tool_use_id: Optional[str] = None  # For tool blocks
    tool_name: Optional[str] = None

class InterleavedContentParser:
    """
    Parse and generate interleaved thinking content
    
    Anthropic's newer models can output thinking and text
    in an interleaved manner rather than strictly separated.
    """
    
    def parse(self, stream: Iterator[dict]) -> List[ContentBlock]:
        """
        Parse interleaved stream into content blocks
        
        Input stream format:
        [
            {"type": "thinking", "thinking": "...", "signature": "..."},
            {"type": "text", "text": "..."},
            {"type": "thinking", "thinking": "..."},
        ]
        """
        blocks = []
        
        for chunk in stream:
            block_type = chunk.get("type")
            
            if block_type == "thinking":
                blocks.append(ContentBlock(
                    type=ContentBlockType.THINKING,
                    content=chunk["thinking"],
                    signature=chunk.get("signature")
                ))
            elif block_type == "text":
                blocks.append(ContentBlock(
                    type=ContentBlockType.TEXT,
                    content=chunk["text"]
                ))
            elif block_type == "tool_use":
                blocks.append(ContentBlock(
                    type=ContentBlockType.TOOL_USE,
                    content=chunk.get("input", ""),
                    tool_use_id=chunk.get("id"),
                    tool_name=chunk.get("name")
                ))
        
        return blocks
    
    def to_assistant_message(self, blocks: List[ContentBlock]) -> AssistantMessage:
        """Convert content blocks to AssistantMessage"""
        content = []
        
        for block in blocks:
            if block.type == ContentBlockType.TEXT:
                content.append(TextContent(type="text", text=block.content))
            elif block.type == ContentBlockType.THINKING:
                content.append(ThinkingContent(
                    type="thinking",
                    thinking=block.content,
                    thinking_signature=block.signature
                ))
            elif block.type == ContentBlockType.TOOL_USE:
                content.append(ToolCall(
                    type="toolCall",
                    id=block.tool_use_id or "",
                    name=block.tool_name or "",
                    arguments={}  # Parse from content if JSON
                ))
        
        return AssistantMessage(
            role="assistant",
            content=content,
            api="anthropic-messages",
            provider="anthropic",
            model="claude-opus-4",
            usage=Usage(),
            stop_reason=StopReason.STOP
        )
```

---

### 1.3 Token Overflow Handling

**Pi Mono Reference**: `packages/ai/src/utils/overflow.ts`

**Design**:
```python
# koda/ai/overflow.py

from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class OverflowConfig:
    """Configuration for token overflow handling"""
    max_context_tokens: int = 128000
    max_completion_tokens: int = 16384
    buffer_ratio: float = 0.95  # Trigger at 95% of limit
    strategy: str = "truncate"  # truncate, compact, or error

class TokenOverflowHandler:
    """
    Handle token overflow situations gracefully
    
    Strategies:
    1. truncate: Remove oldest messages
    2. compact: Summarize older messages
    3. error: Raise exception
    """
    
    def __init__(self, config: OverflowConfig = None):
        self.config = config or OverflowConfig()
        self._compactor: Optional[Callable] = None
    
    def set_compactor(self, compactor: Callable):
        """Set message compactor for 'compact' strategy"""
        self._compactor = compactor
    
    def check_overflow(
        self,
        current_tokens: int,
        estimated_completion: int = 0
    ) -> tuple[bool, str]:
        """
        Check if overflow would occur
        
        Returns:
            (would_overflow, reason)
        """
        threshold = int(self.config.max_context_tokens * self.config.buffer_ratio)
        
        if current_tokens > threshold:
            return True, f"Context tokens ({current_tokens}) exceed threshold ({threshold})"
        
        total = current_tokens + estimated_completion
        if total > self.config.max_context_tokens:
            return True, f"Total tokens ({total}) would exceed limit"
        
        return False, ""
    
    def handle(
        self,
        messages: List[Message],
        current_tokens: int
    ) -> List[Message]:
        """
        Handle overflow according to configured strategy
        
        Returns:
            Adjusted message list
        """
        would_overflow, reason = self.check_overflow(current_tokens)
        
        if not would_overflow:
            return messages
        
        if self.config.strategy == "error":
            raise TokenOverflowError(reason)
        
        elif self.config.strategy == "truncate":
            return self._truncate(messages)
        
        elif self.config.strategy == "compact":
            if self._compactor:
                return self._compactor(messages)
            return self._truncate(messages)
        
        return messages
    
    def _truncate(self, messages: List[Message]) -> List[Message]:
        """Truncate oldest non-system messages"""
        system_msgs = [m for m in messages if m.role == "system"]
        other_msgs = [m for m in messages if m.role != "system"]
        
        # Keep last N messages
        keep_count = max(len(other_msgs) // 2, 3)
        kept_msgs = other_msgs[-keep_count:]
        
        return system_msgs + kept_msgs

class TokenOverflowError(Exception):
    """Raised when token limit would be exceeded"""
    pass
```

---

## 2. packages/agent - Remaining Features

### 2.1 Enhanced Task Routing

**Pi Mono Reference**: `packages/agent/src/proxy.ts:150-300`

**Design**:
```python
# koda/agent/routing.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from enum import Enum
import re

class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    CAPABILITY_MATCH = "capability_match"
    LOAD_BALANCED = "load_balanced"
    COST_OPTIMIZED = "cost_optimized"

@dataclass
class RoutingRule:
    """A routing rule for task delegation"""
    pattern: str  # Regex pattern to match task description
    required_capabilities: List[str]
    preferred_agents: List[str]
    priority: int = 0

class TaskRouter:
    """
    Advanced task routing for AgentProxy
    
    Routes tasks to appropriate agents based on:
    - Task content analysis
    - Agent capabilities
    - Current load
    - Cost considerations
    """
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH):
        self.strategy = strategy
        self.rules: List[RoutingRule] = []
        self._capability_index: Dict[str, List[str]] = {}  # capability -> agent_ids
    
    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule"""
        self.rules.append(rule)
        # Sort by priority (higher first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def index_capabilities(self, agents: Dict[str, AgentInfo]) -> None:
        """Build capability index from agents"""
        self._capability_index.clear()
        
        for agent_id, info in agents.items():
            for cap in info.capabilities:
                if cap not in self._capability_index:
                    self._capability_index[cap] = []
                self._capability_index[cap].append(agent_id)
    
    def route(
        self,
        task_description: str,
        task_capabilities: List[str],
        agents: Dict[str, AgentInfo]
    ) -> Optional[str]:
        """
        Route task to best agent
        
        Returns:
            agent_id or None if no suitable agent
        """
        # Check rules first
        for rule in self.rules:
            if re.search(rule.pattern, task_description, re.IGNORECASE):
                for agent_id in rule.preferred_agents:
                    if agent_id in agents:
                        return agent_id
        
        # Apply routing strategy
        if self.strategy == RoutingStrategy.CAPABILITY_MATCH:
            return self._route_by_capability(task_capabilities, agents)
        
        elif self.strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(list(agents.keys()))
        
        elif self.strategy == RoutingStrategy.LOAD_BALANCED:
            return self._route_by_load(agents)
        
        return None
    
    def _route_by_capability(
        self,
        capabilities: List[str],
        agents: Dict[str, AgentInfo]
    ) -> Optional[str]:
        """Route to agent with best capability match"""
        best_agent = None
        best_score = -1
        
        for agent_id, info in agents.items():
            if info.status != AgentStatus.IDLE:
                continue
            
            # Score based on matching capabilities
            score = sum(1 for cap in capabilities if cap in info.capabilities)
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    def _route_round_robin(self, agent_ids: List[str]) -> Optional[str]:
        """Simple round-robin routing"""
        if not agent_ids:
            return None
        
        # Use rotating index
        idx = getattr(self, '_rr_index', 0) % len(agent_ids)
        self._rr_index = idx + 1
        
        return agent_ids[idx]
    
    def _route_by_load(self, agents: Dict[str, AgentInfo]) -> Optional[str]:
        """Route to least loaded agent"""
        available = [
            (agent_id, info)
            for agent_id, info in agents.items()
            if info.status == AgentStatus.IDLE
        ]
        
        if not available:
            return None
        
        # Sort by total tasks (least first)
        available.sort(key=lambda x: x[1].total_tasks)
        
        return available[0][0]
```

---

## 3. packages/coding-agent - Remaining Features

### 3.1 ModelRegistry Schema Validation

**Pi Mono Reference**: `packages/coding-agent/src/core/model-registry.ts:100-200`

**Design**:
```python
# koda/ai/model_registry_schema.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum

class KnownApi(str, Enum):
    OPENAI_COMPLETIONS = "openai-completions"
    OPENAI_RESPONSES = "openai-responses"
    ANTHROPIC_MESSAGES = "anthropic-messages"
    BEDROCK_CONVERSE = "bedrock-converse-stream"
    GOOGLE_GENERATIVE = "google-generative-ai"

class CostConfig(BaseModel):
    """Cost configuration per million tokens"""
    input: float = Field(..., ge=0)
    output: float = Field(..., ge=0)
    cache_read: float = Field(0, ge=0)
    cache_write: float = Field(0, ge=0)

class ModelOverride(BaseModel):
    """Override settings for a specific model"""
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    custom_headers: Optional[Dict[str, str]] = None

class ModelDefinition(BaseModel):
    """Model definition schema"""
    id: str = Field(..., min_length=1, description="Model identifier")
    name: Optional[str] = None
    api: KnownApi
    provider: str
    base_url: str = Field(..., pattern=r"^https?://")
    cost: CostConfig
    context_window: int = Field(..., gt=0)
    max_tokens: int = Field(..., gt=0)
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_thinking: bool = False
    reasoning: bool = False
    input: List[str] = Field(default_factory=lambda: ["text"])
    headers: Optional[Dict[str, str]] = None
    
    @validator("input")
    def validate_input_types(cls, v):
        allowed = {"text", "image"}
        for item in v:
            if item not in allowed:
                raise ValueError(f"Invalid input type: {item}")
        return v

class ProviderConfig(BaseModel):
    """Provider configuration"""
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None  # e.g., ${OPENAI_API_KEY}
    models: List[ModelDefinition] = Field(default_factory=list)
    model_overrides: Dict[str, ModelOverride] = Field(default_factory=dict)
    default_model: Optional[str] = None
    enabled: bool = True

class ModelsConfig(BaseModel):
    """Root models.json schema"""
    version: str = Field(default="1.0")
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    
    @validator("providers")
    def validate_providers(cls, v):
        for name, config in v.items():
            # Validate that default_model exists in models
            if config.default_model:
                model_ids = [m.id for m in config.models]
                if config.default_model not in model_ids:
                    raise ValueError(
                        f"default_model '{config.default_model}' not found in models"
                    )
        return v

class ModelRegistryValidator:
    """
    Validate models.json configuration files
    
    Uses Pydantic for JSON Schema validation
    """
    
    def validate(self, config: dict) -> tuple[bool, List[str]]:
        """
        Validate configuration
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            validated = ModelsConfig(**config)
            return True, []
        except Exception as e:
            # Extract validation errors
            if hasattr(e, 'errors'):
                for err in e.errors():
                    loc = ".".join(str(x) for x in err['loc'])
                    msg = err['msg']
                    errors.append(f"{loc}: {msg}")
            else:
                errors.append(str(e))
            
            return False, errors
    
    def load_and_validate(self, path: str) -> tuple[Optional[ModelsConfig], List[str]]:
        """Load and validate models.json from file"""
        import json
        
        try:
            with open(path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return None, [f"Invalid JSON: {e}"]
        except FileNotFoundError:
            return None, [f"File not found: {path}"]
        
        is_valid, errors = self.validate(config)
        
        if is_valid:
            return ModelsConfig(**config), []
        else:
            return None, errors
```

---

### 3.2 Config Value Resolution

**Pi Mono Reference**: `packages/coding-agent/src/core/resolve-config-value.ts`

**Design**:
```python
# koda/ai/config_resolver.py

import re
import os
import subprocess
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class ResolverConfig:
    """Configuration for value resolver"""
    allow_shell_commands: bool = True
    max_command_length: int = 1000
    timeout: float = 5.0
    allowed_commands: Optional[list] = None  # Whitelist

class ConfigValueResolver:
    """
    Resolve configuration values with variable substitution
    
    Supports:
    - Environment variables: ${VAR} or ${VAR:-default}
    - Shell commands: $(command)
    """
    
    # Pattern for environment variables
    ENV_PATTERN = re.compile(r'\$\{(\w+)(?::-(.*))?\}')
    
    # Pattern for shell commands
    SHELL_PATTERN = re.compile(r'\$\(([^)]+)\)')
    
    def __init__(self, config: ResolverConfig = None):
        self.config = config or ResolverConfig()
    
    def resolve(self, value: str) -> str:
        """
        Resolve all substitutions in a value
        
        Examples:
            "${HOME}/.config" -> "/home/user/.config"
            "${API_KEY:-default_key}" -> uses API_KEY or "default_key"
            "$(date +%Y)" -> "2026"
        """
        result = value
        
        # Resolve shell commands first
        result = self._resolve_shell_commands(result)
        
        # Then environment variables
        result = self._resolve_env_vars(result)
        
        return result
    
    def _resolve_env_vars(self, value: str) -> str:
        """Replace ${VAR} with environment variable values"""
        def replace(match):
            var_name = match.group(1)
            default = match.group(2)
            
            env_value = os.environ.get(var_name)
            
            if env_value is not None:
                return env_value
            elif default is not None:
                return default
            else:
                # Return original if not found and no default
                return match.group(0)
        
        return self.ENV_PATTERN.sub(replace, value)
    
    def _resolve_shell_commands(self, value: str) -> str:
        """Replace $(command) with command output"""
        if not self.config.allow_shell_commands:
            return value
        
        def replace(match):
            command = match.group(1).strip()
            
            # Security check
            if len(command) > self.config.max_command_length:
                return match.group(0)  # Return original
            
            if self.config.allowed_commands:
                cmd_base = command.split()[0]
                if cmd_base not in self.config.allowed_commands:
                    return match.group(0)
            
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    return match.group(0)  # Return original on error
                    
            except subprocess.TimeoutExpired:
                return match.group(0)
            except Exception:
                return match.group(0)
        
        return self.SHELL_PATTERN.sub(replace, value)
    
    def resolve_dict(self, data: dict) -> dict:
        """Recursively resolve all string values in a dictionary"""
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.resolve(value)
            elif isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = self._resolve_list(value)
            else:
                result[key] = value
        
        return result
    
    def _resolve_list(self, items: list) -> list:
        """Resolve values in a list"""
        result = []
        
        for item in items:
            if isinstance(item, str):
                result.append(self.resolve(item))
            elif isinstance(item, dict):
                result.append(self.resolve_dict(item))
            elif isinstance(item, list):
                result.append(self._resolve_list(item))
            else:
                result.append(item)
        
        return result

# Usage example
resolver = ConfigValueResolver()
config = {
    "api_key": "${OPENAI_API_KEY}",
    "base_url": "${OPENAI_BASE_URL:-https://api.openai.com}",
    "user_dir": "${HOME}/.koda",
    "current_year": "$(date +%Y)"
}

resolved = resolver.resolve_dict(config)
```

---

### 3.3 Hierarchical Settings Manager

**Pi Mono Reference**: `packages/coding-agent/src/core/settings-manager.ts`

**Design**:
```python
# koda/coding/settings_manager.py

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Callable, List
from threading import Lock

@dataclass
class CompactionSettings:
    max_tokens: int = 128000
    reserve_tokens: int = 4000
    trigger_ratio: float = 0.8

@dataclass
class ImageSettings:
    max_width: int = 2048
    max_height: int = 2048
    quality: int = 80
    format: str = "jpeg"

@dataclass
class RetrySettings:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0

@dataclass
class Settings:
    """Complete settings schema"""
    compaction: CompactionSettings = field(default_factory=CompactionSettings)
    images: ImageSettings = field(default_factory=ImageSettings)
    retry: RetrySettings = field(default_factory=RetrySettings)
    custom: Dict[str, Any] = field(default_factory=dict)

class SettingsManager:
    """
    Hierarchical settings management
    
    Settings are merged from (low to high priority):
    1. Default values
    2. ~/.koda/settings.json (global)
    3. .koda/settings.json (project)
    4. Environment variables
    5. Runtime modifications
    
    Supports file watching for auto-reload.
    """
    
    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self._settings: Settings = Settings()
        self._lock = Lock()
        self._watchers: List[Callable] = []
        self._file_watchers: List[Any] = []
    
    @property
    def global_config_path(self) -> Path:
        """Path to global settings file"""
        return Path.home() / ".koda" / "settings.json"
    
    @property
    def project_config_path(self) -> Path:
        """Path to project settings file"""
        return self.project_dir / ".koda" / "settings.json"
    
    def load(self) -> Settings:
        """Load and merge all settings"""
        with self._lock:
            # Start with defaults
            settings = Settings()
            
            # Merge global settings
            if self.global_config_path.exists():
                global_data = self._load_file(self.global_config_path)
                settings = self._merge_settings(settings, global_data)
            
            # Merge project settings (higher priority)
            if self.project_config_path.exists():
                project_data = self._load_file(self.project_config_path)
                settings = self._merge_settings(settings, project_data)
            
            # Apply environment variables
            settings = self._apply_env_vars(settings)
            
            self._settings = settings
            return settings
    
    def _load_file(self, path: Path) -> dict:
        """Load settings from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _merge_settings(self, base: Settings, override: dict) -> Settings:
        """Merge override dict into base Settings"""
        base_dict = asdict(base)
        merged = self._deep_merge(base_dict, override)
        
        # Convert back to Settings
        return Settings(
            compaction=CompactionSettings(**merged.get('compaction', {})),
            images=ImageSettings(**merged.get('images', {})),
            retry=RetrySettings(**merged.get('retry', {})),
            custom=merged.get('custom', {})
        )
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_vars(self, settings: Settings) -> Settings:
        """Apply environment variable overrides"""
        # KODA_COMPACTION_MAX_TOKENS -> settings.compaction.max_tokens
        prefix = "KODA_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split('_')
                self._set_nested_attr(settings, parts, value)
        
        return settings
    
    def _set_nested_attr(self, obj: Any, path: List[str], value: str):
        """Set nested attribute by path"""
        try:
            # Convert value to appropriate type
            converted = self._convert_value(value)
            
            # Navigate to parent
            current = obj
            for part in path[:-1]:
                current = getattr(current, part)
            
            # Set value
            setattr(current, path[-1], converted)
        except (AttributeError, ValueError):
            pass  # Ignore invalid paths
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        # Try int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try bool
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        return value
    
    def save(self, settings: Settings, scope: str = "project") -> None:
        """
        Save settings to file
        
        Args:
            settings: Settings to save
            scope: "global" or "project"
        """
        path = self.global_config_path if scope == "global" else self.project_config_path
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(asdict(settings), f, indent=2)
    
    def watch(self, callback: Callable[[Settings], None]) -> None:
        """
        Watch for settings changes
        
        Args:
            callback: Called when settings change
        """
        self._watchers.append(callback)
        
        # Start file watchers if available
        try:
            self._start_file_watching()
        except ImportError:
            pass  # watchfiles not installed
    
    def _start_file_watching(self):
        """Start watching settings files for changes"""
        try:
            from watchfiles import watch, Change
            
            def watch_thread():
                paths = [self.global_config_path, self.project_config_path]
                paths = [p for p in paths if p.exists()]
                
                for changes in watch(*paths):
                    # Reload settings
                    new_settings = self.load()
                    
                    # Notify callbacks
                    for callback in self._watchers:
                        try:
                            callback(new_settings)
                        except Exception:
                            pass
            
            import threading
            thread = threading.Thread(target=watch_thread, daemon=True)
            thread.start()
            
        except ImportError:
            pass
    
    def get(self) -> Settings:
        """Get current settings"""
        with self._lock:
            return self._settings
```

---

## 4. packages/mom - Remaining Features

### 4.1 MOMAgent Class

**Pi Mono Reference**: `packages/mom/src/agent.ts`

**Design**:
```python
# koda/mom/mom_agent.py

import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

from koda.ai.types import Context, AssistantMessage, ModelInfo
from koda.agent.loop import AgentLoop, AgentTool
from koda.mes.compaction_advanced import AdvancedCompactor
from koda.mom.sandbox import Sandbox
from koda.mom.store import Store

@dataclass
class MOMAgentConfig:
    """Configuration for MOMAgent"""
    model: ModelInfo
    sandbox: Optional[Sandbox] = None
    store: Optional[Store] = None
    max_iterations: int = 50
    enable_compaction: bool = True
    compaction_threshold: float = 0.8
    working_dir: Path = Path.cwd()

class MOMAgent:
    """
    Model-Optimized Messages Agent
    
    The main MOM agent that integrates:
    - Context management
    - Automatic compaction
    - Sandbox execution
    - Persistent storage
    - Event handling
    
    This is the high-level agent interface that users interact with.
    """
    
    def __init__(self, config: MOMAgentConfig):
        self.config = config
        
        # Core components
        self._sandbox = config.sandbox
        self._store = config.store
        
        # Agent loop
        self._agent_loop: Optional[AgentLoop] = None
        self._tools: List[AgentTool] = []
        
        # Compaction
        self._compactor: Optional[AdvancedCompactor] = None
        if config.enable_compaction:
            self._compactor = AdvancedCompactor(
                max_tokens=config.model.context_window,
                reserve_tokens=4000
            )
        
        # State
        self._context = Context(
            system_prompt=self._build_system_prompt(),
            messages=[]
        )
        self._running = False
        self._event_handlers: List[Callable] = []
    
    def _build_system_prompt(self) -> str:
        """Build default system prompt for MOM agent"""
        return """You are a helpful coding assistant with access to a sandbox environment.

You can:
- Read and write files
- Execute shell commands in the sandbox
- Use tools to accomplish tasks

Always be helpful, accurate, and efficient."""
    
    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool for the agent"""
        self._tools.append(tool)
    
    def on_event(self, handler: Callable[[str, Any], None]) -> None:
        """Register event handler"""
        self._event_handlers.append(handler)
    
    def _emit_event(self, event_type: str, data: Any) -> None:
        """Emit event to all handlers"""
        for handler in self._event_handlers:
            try:
                handler(event_type, data)
            except Exception:
                pass
    
    async def run(
        self,
        user_input: str,
        provider: Any,  # BaseProvider
        on_token: Optional[Callable[[str], None]] = None
    ) -> AssistantMessage:
        """
        Run the agent with user input
        
        Args:
            user_input: User's message
            provider: LLM provider
            on_token: Callback for streaming tokens
            
        Returns:
            Final assistant message
        """
        self._running = True
        
        # Add user message to context
        from koda.ai.types import UserMessage
        self._context.messages.append(UserMessage(
            role="user",
            content=user_input
        ))
        
        # Check if compaction needed
        if self._compactor:
            from koda.mes.compaction_advanced import SessionEntry, MessageEntry
            entries = [
                MessageEntry(id=f"msg_{i}", role=m.role, content=str(m.content))
                for i, m in enumerate(self._context.messages)
            ]
            
            should_compact = self._compactor.should_compact(
                entries,
                self.config.model.context_window,
                self.config.compaction_threshold
            )
            
            if should_compact:
                self._emit_event("compaction_start", {})
                new_entries, summary = await self._compactor.compact_with_summary(
                    entries,
                    summarizer=lambda p: provider.complete(
                        self.config.model,
                        Context(system_prompt="Summarize:", messages=[UserMessage(role="user", content=p)])
                    )
                )
                self._emit_event("compaction_end", {"summary": summary.summary})
        
        # Create agent loop if needed
        if not self._agent_loop:
            self._agent_loop = AgentLoop(
                provider=provider,
                model=self.config.model,
                tools=self._tools
            )
        
        # Run agent loop
        try:
            result = await self._agent_loop.run(
                context=self._context,
                on_event=lambda e: self._emit_event("agent_event", e)
            )
            
            # Add result to context
            self._context.messages.append(result)
            
            return result
            
        finally:
            self._running = False
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> str:
        """
        Execute a tool directly
        
        Used for programmatic tool execution outside of agent loop.
        """
        tool = next((t for t in self._tools if t.name == tool_name), None)
        
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Execute in sandbox if available
        if self._sandbox and tool_name in ["bash", "shell"]:
            result = await self._sandbox.execute(
                command=arguments.get("command", "").split(),
                timeout=arguments.get("timeout", 60)
            )
            return result.output if result.success else result.error
        
        # Direct execution
        return await tool.execute(**arguments)
    
    def save_state(self) -> dict:
        """Save agent state for persistence"""
        return {
            "context": self._context,
            "config": self.config,
            "message_count": len(self._context.messages)
        }
    
    def load_state(self, state: dict) -> None:
        """Load agent state from persistence"""
        if "context" in state:
            self._context = state["context"]
```

---

## 5. Implementation Roadmap

### Phase 1: AI Package Completion (Week 1-2)

**Day 1-2: Tool Name Mapping**
- [ ] Implement `ToolNameMapper`
- [ ] Add transformation logic to Anthropic provider
- [ ] Write tests

**Day 3-4: Interleaved Thinking**
- [ ] Implement `InterleavedContentParser`
- [ ] Integrate with Anthropic provider
- [ ] Write tests

**Day 5-7: Token Overflow**
- [ ] Implement `TokenOverflowHandler`
- [ ] Add overflow detection
- [ ] Write tests

### Phase 2: Agent Package Completion (Week 3)

**Day 1-2: Enhanced Routing**
- [ ] Implement `TaskRouter`
- [ ] Add routing strategies
- [ ] Integrate with AgentProxy

### Phase 3: Coding-Agent Package Completion (Week 4-5)

**Day 1-3: Model Registry Schema**
- [ ] Define Pydantic schemas
- [ ] Implement validator
- [ ] Write tests

**Day 4-5: Config Resolution**
- [ ] Implement `ConfigValueResolver`
- [ ] Add security checks
- [ ] Write tests

**Day 6-7: Settings Manager**
- [ ] Implement hierarchical settings
- [ ] Add file watching
- [ ] Write tests

### Phase 4: MOM Package Completion (Week 6)

**Day 1-4: MOMAgent**
- [ ] Implement MOMAgent class
- [ ] Integrate with sandbox and store
- [ ] Add event handling
- [ ] Write tests

**Day 5-7: Download Functionality**
- [ ] Implement file download
- [ ] Add progress tracking
- [ ] Write tests

### Phase 5: Integration & Testing (Week 7)

- [ ] Integration tests
- [ ] Documentation
- [ ] Performance testing
- [ ] Final polish

---

*Design Document Version: 1.0*
