"""
Coding Config - Configuration for the coding module
Equivalent to Pi Mono's config.ts
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from enum import Enum


class ModelProvider(Enum):
    """Available model providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    GROQ = "groq"
    CEREBRAS = "cerebras"
    BEDROCK = "bedrock"
    VERTEX = "vertex"


class OutputMode(Enum):
    """Output mode for coding assistant"""
    INTERACTIVE = "interactive"
    PRINT = "print"
    JSON = "json"
    HEADLESS = "headless"


@dataclass
class ModelConfig:
    """Model configuration"""
    provider: str = "anthropic"
    model: str = "claude-sonnet-4"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Reasoning settings
    thinking_level: Optional[str] = None  # minimal, low, medium, high, xhigh
    thinking_budget: Optional[int] = None

    # API settings
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Model-specific
    supports_vision: bool = True
    supports_tools: bool = True
    supports_caching: bool = False


@dataclass
class ToolConfig:
    """Tool configuration"""
    # Shell tool
    shell_timeout: float = 600.0
    shell_max_output: int = 50000
    shell_allowed_commands: Optional[List[str]] = None
    shell_blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf /",
        "mkfs",
        "dd if=",
        "> /dev/",
    ])

    # File tool
    file_max_size: int = 10 * 1024 * 1024  # 10 MB
    file_allowed_extensions: Optional[List[str]] = None

    # Edit tool
    edit_max_diff_size: int = 100000
    edit_require_confirmation: bool = True

    # General
    tool_timeout: float = 600.0
    max_parallel_tools: int = 8
    require_confirmation_for: List[str] = field(default_factory=lambda: [
        "write", "edit", "bash"
    ])


@dataclass
class ContextConfig:
    """Context management configuration"""
    max_context_tokens: int = 180000
    compaction_threshold: float = 0.8
    compaction_strategy: str = "smart"  # smart, truncate, summarize

    # System prompt
    custom_system_prompt: Optional[str] = None
    load_agents_md: bool = True

    # Cache settings
    enable_caching: bool = True
    cache_retention: str = "short"  # none, short, long


@dataclass
class SessionConfig:
    """Session configuration"""
    session_id: Optional[str] = None
    working_dir: Path = field(default_factory=Path.cwd)

    # Persistence
    auto_save: bool = True
    save_interval: float = 30.0
    session_dir: Path = field(default_factory=lambda: Path.home() / ".koda" / "sessions")

    # History
    max_history_entries: int = 1000
    keep_tool_results: bool = True


@dataclass
class UIConfig:
    """UI configuration"""
    output_mode: OutputMode = OutputMode.INTERACTIVE

    # Display settings
    show_thinking: bool = True
    show_tool_calls: bool = True
    show_token_usage: bool = True
    show_timing: bool = False

    # Colors (for interactive mode)
    use_colors: bool = True
    theme: str = "dark"  # dark, light

    # Streaming
    stream_response: bool = True
    typing_speed: int = 0  # 0 = instant


@dataclass
class ExtensionConfig:
    """Extension system configuration"""
    enabled: bool = True
    search_paths: List[Path] = field(default_factory=list)
    auto_load: bool = True
    strict_validation: bool = True


@dataclass
class CodingConfig:
    """
    Main configuration for the coding module.

    Combines all sub-configurations into a single config object.
    """
    # Sub-configs
    model: ModelConfig = field(default_factory=ModelConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    extensions: ExtensionConfig = field(default_factory=ExtensionConfig)

    # Agent settings
    max_iterations: int = 50
    enable_steering: bool = True
    enable_follow_up: bool = True

    # Debug
    debug: bool = False
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "model": {
                "provider": self.model.provider,
                "model": self.model.model,
                "temperature": self.model.temperature,
                "max_tokens": self.model.max_tokens,
            },
            "tools": {
                "shell_timeout": self.tools.shell_timeout,
                "max_parallel_tools": self.tools.max_parallel_tools,
            },
            "context": {
                "max_context_tokens": self.context.max_context_tokens,
                "compaction_threshold": self.context.compaction_threshold,
            },
            "session": {
                "working_dir": str(self.session.working_dir),
            },
            "ui": {
                "output_mode": self.ui.output_mode.value,
            },
            "max_iterations": self.max_iterations,
            "debug": self.debug,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodingConfig":
        """Create from dictionary"""
        config = cls()

        if "model" in data:
            m = data["model"]
            config.model = ModelConfig(
                provider=m.get("provider", "anthropic"),
                model=m.get("model", "claude-sonnet-4"),
                temperature=m.get("temperature", 0.7),
                max_tokens=m.get("max_tokens", 4096),
            )

        if "tools" in data:
            t = data["tools"]
            config.tools.shell_timeout = t.get("shell_timeout", 600.0)
            config.tools.max_parallel_tools = t.get("max_parallel_tools", 8)

        if "context" in data:
            c = data["context"]
            config.context.max_context_tokens = c.get("max_context_tokens", 180000)
            config.context.compaction_threshold = c.get("compaction_threshold", 0.8)

        if "session" in data:
            s = data["session"]
            if "working_dir" in s:
                config.session.working_dir = Path(s["working_dir"])

        if "ui" in data:
            u = data["ui"]
            if "output_mode" in u:
                config.ui.output_mode = OutputMode(u["output_mode"])

        if "max_iterations" in data:
            config.max_iterations = data["max_iterations"]

        if "debug" in data:
            config.debug = data["debug"]

        return config


# Default configurations for common scenarios
DEFAULT_CONFIG = CodingConfig()

FAST_CONFIG = CodingConfig(
    model=ModelConfig(
        model="claude-3-5-haiku",
        temperature=0.5,
    ),
    ui=UIConfig(
        show_thinking=False,
        show_timing=True,
    )
)

CHEAP_CONFIG = CodingConfig(
    model=ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
    ),
    context=ContextConfig(
        max_context_tokens=128000,
    )
)

REASONING_CONFIG = CodingConfig(
    model=ModelConfig(
        model="claude-sonnet-4",
        thinking_level="high",
        thinking_budget=16384,
    ),
    ui=UIConfig(
        show_thinking=True,
    )
)


def load_config(path: Optional[Path] = None) -> CodingConfig:
    """
    Load configuration from file.

    Args:
        path: Config file path (default: ~/.koda/config.json)

    Returns:
        Loaded configuration
    """
    import json

    if path is None:
        path = Path.home() / ".koda" / "config.json"

    if not path.exists():
        return CodingConfig()

    try:
        with open(path, "r") as f:
            data = json.load(f)
        return CodingConfig.from_dict(data)
    except Exception as e:
        print(f"Error loading config: {e}")
        return CodingConfig()


def save_config(config: CodingConfig, path: Optional[Path] = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save
        path: Config file path
    """
    import json

    if path is None:
        path = Path.home() / ".koda" / "config.json"

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)
