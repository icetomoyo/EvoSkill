"""
Koda 配置系统

管理框架配置。
"""
import os
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "openai"  # openai, anthropic, google, local
    model: str = "gpt-4"
    api_key: str = ""
    api_base: str = ""  # 自定义 API 地址
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60


@dataclass
class AgentConfig:
    """Agent 配置"""
    max_iterations: int = 3
    enable_reflection: bool = True
    enable_api_discovery: bool = True
    auto_fix: bool = True
    verbose: bool = True


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_sandbox: bool = True
    allow_network: bool = False
    allow_shell: bool = True
    allowed_packages: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
    ])
    max_execution_time: int = 300  # 5分钟
    max_file_size: int = 10 * 1024 * 1024  # 10MB


@dataclass
class ToolConfig:
    """工具配置"""
    enabled_tools: List[str] = field(default_factory=lambda: [
        "file", "shell", "search", "api"
    ])
    shell_timeout: int = 60
    api_timeout: int = 30
    search_max_results: int = 100


@dataclass
class KodaConfig:
    """Koda 主配置"""
    version: str = "0.1.0"
    workspace: str = "./workspace"
    
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "KodaConfig":
        """
        从文件加载配置
        
        Args:
            path: 配置文件路径，默认查找 .koda.yaml
            
        Returns:
            KodaConfig
        """
        if path is None:
            # 查找配置文件
            for config_name in [".koda.yaml", ".koda.yml", "koda.yaml"]:
                config_path = Path(config_name)
                if config_path.exists():
                    path = config_path
                    break
        
        if path is None or not path.exists():
            # 返回默认配置
            return cls()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return cls(**data)
        except Exception:
            return cls()
    
    def save(self, path: Path) -> None:
        """
        保存配置到文件
        
        Args:
            path: 配置文件路径
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(asdict(self), f, default_flow_style=False, allow_unicode=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_env(cls) -> "KodaConfig":
        """
        从环境变量加载配置
        
        Returns:
            KodaConfig
        """
        config = cls()
        
        # LLM 配置
        if os.getenv("KODA_LLM_PROVIDER"):
            config.llm.provider = os.getenv("KODA_LLM_PROVIDER")
        if os.getenv("KODA_LLM_MODEL"):
            config.llm.model = os.getenv("KODA_LLM_MODEL")
        if os.getenv("KODA_LLM_API_KEY"):
            config.llm.api_key = os.getenv("KODA_LLM_API_KEY")
        
        # Agent 配置
        if os.getenv("KODA_MAX_ITERATIONS"):
            config.agent.max_iterations = int(os.getenv("KODA_MAX_ITERATIONS"))
        if os.getenv("KODA_VERBOSE"):
            config.agent.verbose = os.getenv("KODA_VERBOSE").lower() == "true"
        
        # 安全配置
        if os.getenv("KODA_ENABLE_SANDBOX"):
            config.security.enable_sandbox = os.getenv("KODA_ENABLE_SANDBOX").lower() == "true"
        
        return config


# 默认配置实例
default_config = KodaConfig()
