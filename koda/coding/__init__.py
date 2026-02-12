"""
Koda Coding Package

Coding agent components.
"""
# Resource loading
from .resource_loader import (
    Resource,
    ResourceLoader,
    LoadOptions,
    load_resource,
    load_resources,
)

# Frontmatter
from .frontmatter import (
    Frontmatter,
    FrontmatterParser,
    parse,
    stringify,
)

# Utils
from .utils import (
    ShellUtils,
    ShellResult,
    run_command,
    GitUtils,
    GitInfo,
    is_git_repo,
    get_git_info,
    ClipboardUtils,
    copy_to_clipboard,
    paste_from_clipboard,
    ImageConverter,
    ImageInfo,
    image_to_base64,
    convert_image,
)

# Slash commands
from .slash_commands import (
    SlashCommandRegistry,
    SlashCommand,
    CommandResult,
    CommandResultType,
    BuiltInCommands,
    execute_command,
    get_default_registry,
)

# Bash executor
from .bash_executor import (
    BashExecutor,
    BashResult,
    BashHooks,
    BashHookContext,
    ExitCode,
    run_bash,
)

# Prompt templates
from .prompt_templates import (
    PromptTemplateRegistry,
    Template,
    get_default_registry as get_template_registry,
    render_template,
)

# System prompt
from .system_prompt import (
    SystemPromptBuilder,
    SystemPromptConfig,
    AgentMode,
    AgentPersonality,
    get_code_prompt,
    get_review_prompt,
    get_debug_prompt,
)

# SDK
from .sdk import (
    KodaSDK,
    SDKConfig,
    CodeResult,
    ReviewResult,
    init_sdk,
    get_sdk,
    generate_code,
    review_code,
)

# Messages
from .messages import (
    MessageFormatter,
    MarkdownFormatter,
    FormattedMessage,
    MessageType,
)

# Key bindings
from .keybindings import (
    KeyBindingManager,
    KeyBinding,
    KeyModifier,
    get_default_manager as get_keybinding_manager,
    bind,
    lookup,
)

# Footer data
from .footer_data_provider import (
    FooterDataProvider,
    FooterData,
    StatusBarManager,
    get_default_provider as get_footer_provider,
    get_footer,
)

# Timings
from .timings import (
    Timings,
    Timing,
    TimingReport,
    start_timings,
    get_timings,
    timed,
)

# Modes
from .modes import (
    InteractiveMode,
    ModeContext,
    ModeResponse,
    PrintMode,
)

# Main entry point
from .main import (
    CodingMain,
    RunMode,
    CLIContext,
    create_argument_parser,
    parse_args,
    build_config,
    main,
    main_async,
    main_with_args,
    run,
    chat,
    ask,
)

# Existing exports
from .download import (
    download_file,
    download_with_retry,
    DownloadResult,
    is_downloadable_url,
)
from .export_html import export_to_html, export_to_markdown, ExportOptions
from .extensions import (
    Extension,
    ExtensionMetadata,
    ExtensionRegistry,
    get_extension_registry,
    HookPoint,
    HookManager,
)
from .model_resolver import ModelResolver, ResolvedModel
from .skills import (
    Skill,
    SkillsRegistry,
    SkillsLoader,
    SkillsManager,
    get_skills_manager,
    set_skills_manager,
)
from .package_manager import Package, PackageLock, PackageRegistry, PackageManager
from .resolve_config_value import (
    resolve_config_value,
    clear_config_value_cache,
    is_cached,
    resolve_headers,
)

__all__ = [
    # Resource loading
    "Resource",
    "ResourceLoader",
    "LoadOptions",
    "load_resource",
    "load_resources",
    # Frontmatter
    "Frontmatter",
    "FrontmatterParser",
    "parse",
    "stringify",
    # Utils
    "ShellUtils",
    "ShellResult",
    "run_command",
    "GitUtils",
    "GitInfo",
    "is_git_repo",
    "get_git_info",
    "ClipboardUtils",
    "copy_to_clipboard",
    "paste_from_clipboard",
    "ImageConverter",
    "ImageInfo",
    "image_to_base64",
    "convert_image",
    # Slash commands
    "SlashCommandRegistry",
    "SlashCommand",
    "CommandResult",
    "CommandResultType",
    "BuiltInCommands",
    "execute_command",
    "get_default_registry",
    # Bash executor
    "BashExecutor",
    "BashResult",
    "BashHooks",
    "BashHookContext",
    "ExitCode",
    "run_bash",
    # Prompt templates
    "PromptTemplateRegistry",
    "Template",
    "get_template_registry",
    "render_template",
    # System prompt
    "SystemPromptBuilder",
    "SystemPromptConfig",
    "AgentMode",
    "AgentPersonality",
    "get_code_prompt",
    "get_review_prompt",
    "get_debug_prompt",
    # SDK
    "KodaSDK",
    "SDKConfig",
    "CodeResult",
    "ReviewResult",
    "init_sdk",
    "get_sdk",
    "generate_code",
    "review_code",
    # Messages
    "MessageFormatter",
    "MarkdownFormatter",
    "FormattedMessage",
    "MessageType",
    # Key bindings
    "KeyBindingManager",
    "KeyBinding",
    "KeyModifier",
    "get_keybinding_manager",
    "bind",
    "lookup",
    # Footer data
    "FooterDataProvider",
    "FooterData",
    "StatusBarManager",
    "get_footer_provider",
    "get_footer",
    # Timings
    "Timings",
    "Timing",
    "TimingReport",
    "start_timings",
    "get_timings",
    "timed",
    # Modes
    "InteractiveMode",
    "ModeContext",
    "ModeResponse",
    "PrintMode",
    # Main entry point
    "CodingMain",
    "RunMode",
    "CLIContext",
    "create_argument_parser",
    "parse_args",
    "build_config",
    "main",
    "main_async",
    "main_with_args",
    "run",
    "chat",
    "ask",
    # Download
    "download_file",
    "download_with_retry",
    "DownloadResult",
    "is_downloadable_url",
    # Export HTML
    "export_to_html",
    "export_to_markdown",
    "ExportOptions",
    # Extensions
    "Extension",
    "ExtensionMetadata",
    "ExtensionRegistry",
    "get_extension_registry",
    "HookPoint",
    "HookManager",
    # Model resolver
    "ModelResolver",
    "ResolvedModel",
    # Skills
    "Skill",
    "SkillsRegistry",
    "SkillsLoader",
    "SkillsManager",
    "get_skills_manager",
    "set_skills_manager",
    # Package manager
    "Package",
    "PackageLock",
    "PackageRegistry",
    "PackageManager",
    # Config value resolution
    "resolve_config_value",
    "clear_config_value_cache",
    "is_cached",
    "resolve_headers",
]
