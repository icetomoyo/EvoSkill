"""
Coding Defaults - Default values and settings
Equivalent to Pi Mono's defaults.ts
"""
from typing import Dict, List, Any

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are Koda, an expert coding assistant.

You help users with software development tasks including:
- Writing and editing code
- Debugging and fixing issues
- Explaining code and concepts
- Refactoring and optimization
- Running shell commands
- File operations

Guidelines:
1. Be helpful, accurate, and concise
2. Use the available tools to accomplish tasks
3. Explain your reasoning when appropriate
4. Ask for clarification when needed
5. Follow best practices and coding conventions
6. Be careful with destructive operations

Working directory: {working_dir}
"""

# Default tool descriptions
DEFAULT_TOOL_DESCRIPTIONS = {
    "read": "Read file contents. Use for examining code files.",
    "write": "Write content to a file. Creates or overwrites the file.",
    "edit": "Edit a file by replacing specific text. Use for targeted changes.",
    "bash": "Execute a shell command. Use for running tests, git, etc.",
    "grep": "Search for patterns in files using regular expressions.",
    "find": "Find files matching a pattern in a directory.",
    "ls": "List directory contents.",
    "glob": "Find files using glob patterns.",
}

# Default confirmation prompts
DEFAULT_CONFIRMATION_PROMPTS = {
    "write": "Write to file {file_path}?",
    "edit": "Edit file {file_path}?",
    "bash": "Execute command: {command}?",
    "bash_dangerous": "This command may be destructive. Execute: {command}?",
}

# Dangerous command patterns
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"mkfs",
    r"dd\s+if=",
    r">\s*/dev/",
    r"chmod\s+-R\s+777",
    r"chown\s+-R",
    r":(){ :\|:& };:",  # Fork bomb
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*bash",
]

# Default ignore patterns for file operations
DEFAULT_IGNORE_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.dll",
    ".DS_Store",
    "Thumbs.db",
]

# Default file extensions to treat as text
TEXT_EXTENSIONS = [
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".lua", ".r", ".m", ".mm",
    ".txt", ".md", ".rst", ".adoc",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".sql", ".graphql", ".proto",
    ".env", ".gitignore", ".dockerignore", ".editorconfig",
    ".jsx", ".tsx", ".vue", ".svelte",
]

# Binary file extensions (should not be read as text)
BINARY_EXTENSIONS = [
    ".exe", ".dll", ".so", ".dylib", ".a", ".lib",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mkv", ".mov", ".webm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pyc", ".pyo", ".class", ".jar", ".war",
    ".sqlite", ".db", ".mdb",
]

# Default max file sizes
MAX_FILE_SIZES = {
    "read": 10 * 1024 * 1024,  # 10 MB
    "write": 50 * 1024 * 1024,  # 50 MB
    "edit": 10 * 1024 * 1024,  # 10 MB
}

# Default timeouts (in seconds)
DEFAULT_TIMEOUTS = {
    "llm_request": 120,
    "tool_execution": 600,
    "shell_command": 600,
    "file_operation": 60,
}

# Default model settings by provider
DEFAULT_MODEL_SETTINGS: Dict[str, Dict[str, Any]] = {
    "anthropic": {
        "default_model": "claude-sonnet-4",
        "context_window": 200000,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": True,
    },
    "openai": {
        "default_model": "gpt-4o",
        "context_window": 128000,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,
    },
    "google": {
        "default_model": "gemini-2.0-flash",
        "context_window": 1048576,
        "supports_vision": True,
        "supports_tools": True,
        "supports_caching": False,
    },
}

# Default compaction settings
DEFAULT_COMPACTION_SETTINGS = {
    "threshold": 0.8,  # Compact at 80% of context window
    "target": 0.6,     # Target 60% after compaction
    "preserve_recent": 4,  # Always keep last 4 messages
    "preserve_tools": True,  # Keep tool call/result pairs together
}

# Environment variable mappings
ENV_VAR_MAPPINGS = {
    "ANTHROPIC_API_KEY": "anthropic",
    "OPENAI_API_KEY": "openai",
    "GOOGLE_API_KEY": "google",
    "GEMINI_API_KEY": "google",
    "MISTRAL_API_KEY": "mistral",
    "DEEPSEEK_API_KEY": "deepseek",
    "XAI_API_KEY": "xai",
    "GROQ_API_KEY": "groq",
    "CEREBRAS_API_KEY": "cerebras",
    "AWS_ACCESS_KEY_ID": "bedrock",
    "AWS_SECRET_ACCESS_KEY": "bedrock",
}


def get_default_system_prompt(working_dir: str = ".") -> str:
    """Get default system prompt with working directory"""
    return DEFAULT_SYSTEM_PROMPT.format(working_dir=working_dir)


def is_text_file(extension: str) -> bool:
    """Check if file extension should be treated as text"""
    return extension.lower() in TEXT_EXTENSIONS


def is_binary_file(extension: str) -> bool:
    """Check if file extension should be treated as binary"""
    return extension.lower() in BINARY_EXTENSIONS


def is_dangerous_command(command: str) -> bool:
    """Check if command matches dangerous patterns"""
    import re
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return True
    return False


def should_ignore_path(path: str) -> bool:
    """Check if path should be ignored"""
    import fnmatch
    for pattern in DEFAULT_IGNORE_PATTERNS:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def get_api_key_env_var(provider: str) -> str:
    """Get environment variable name for provider API key"""
    reverse_mapping = {v: k for k, v in ENV_VAR_MAPPINGS.items()}
    return reverse_mapping.get(provider, f"{provider.upper()}_API_KEY")


def get_provider_from_env() -> str:
    """Determine default provider from available API keys"""
    import os
    for env_var, provider in ENV_VAR_MAPPINGS.items():
        if os.getenv(env_var):
            return provider
    return "anthropic"  # Default
