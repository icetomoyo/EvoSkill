"""
EvoSkill 配置管理

支持配置文件 + 环境变量，优先级：
1. 代码中显式传入的参数
2. 环境变量
3. 配置文件
4. 默认值
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Literal

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "base_url": None,
    "api_key": None,
    "temperature": 0.7,
    "max_tokens": None,
    "thinking_level": None,
}


class EvoSkillConfig(BaseSettings):
    """
    EvoSkill 配置类
    
    支持从以下位置加载配置（按优先级排序）：
    1. 代码中显式传入的参数
    2. 环境变量（EVOSKILL_*）
    3. 配置文件（~/.config/evoskill/config.yaml）
    4. 默认值
    """
    
    model_config = SettingsConfigDict(
        env_prefix="EVOSKILL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # LLM 配置
    provider: Literal["openai", "anthropic", "kimi-coding", "custom"] = Field(
        default="openai",
        description="LLM 提供商"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="模型名称"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="API 基础 URL（用于第三方代理）"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API 密钥"
    )
    
    # 模型参数
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="最大生成 token 数"
    )
    thinking_level: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="思考级别（用于支持推理的模型）"
    )
    
    # 自定义 HTTP 头（用于 Kimi For Coding 等需要特殊 User-Agent 的 API）
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="自定义 HTTP 请求头"
    )
    
    # 路径配置
    workspace: Path = Field(
        default=Path.cwd(),
        description="工作目录"
    )
    skills_dir: Optional[Path] = Field(
        default=None,
        description="Skills 目录"
    )
    sessions_dir: Optional[Path] = Field(
        default=None,
        description="会话存储目录"
    )
    
    # 上下文配置 (简化设计)
    max_context_tokens: int = Field(
        default=80000,
        description="最大上下文 token 数，达到此值时自动触发压缩"
    )
    
    # 安全配置
    require_confirmation: bool = Field(
        default=True,
        description="危险操作是否需要确认"
    )
    
    @field_validator("skills_dir", mode="before")
    @classmethod
    def set_default_skills_dir(cls, v, info):
        if v is None:
            workspace = info.data.get("workspace", Path.cwd())
            return Path(workspace) / ".evoskill" / "skills"
        return Path(v)
    
    @field_validator("sessions_dir", mode="before")
    @classmethod
    def set_default_sessions_dir(cls, v, info):
        if v is None:
            workspace = info.data.get("workspace", Path.cwd())
            return Path(workspace) / ".evoskill" / "sessions"
        return Path(v)
    
    @field_validator("workspace", mode="before")
    @classmethod
    def validate_workspace(cls, v):
        return Path(v).expanduser().resolve()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于保存）"""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else None,  # 脱敏
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "thinking_level": self.thinking_level,
            "headers": self.headers,
            "workspace": str(self.workspace),
            "skills_dir": str(self.skills_dir) if self.skills_dir else None,
            "sessions_dir": str(self.sessions_dir) if self.sessions_dir else None,
            "max_context_tokens": self.max_context_tokens,
            "require_confirmation": self.require_confirmation,
        }
    
    def get_api_key(self) -> Optional[str]:
        """
        获取 API 密钥（优先级：显式配置 > 环境变量）
        """
        if self.api_key:
            return self.api_key
        
        # 尝试常见环境变量名
        env_vars = {
            "openai": ["OPENAI_API_KEY", "EVOSKILL_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "EVOSKILL_API_KEY"],
            "kimi-coding": ["KIMI_API_KEY", "KIMICODE_API_KEY", "EVOSKILL_API_KEY"],
            "custom": ["EVOSKILL_API_KEY"],
        }
        
        for var in env_vars.get(self.provider, ["EVOSKILL_API_KEY"]):
            key = os.getenv(var)
            if key:
                return key
        
        return None


class ConfigManager:
    """
    配置管理器
    
    负责配置的加载、保存和管理
    """
    
    def __init__(self):
        self.config_path = self._get_config_path()
    
    @staticmethod
    def _get_config_path() -> Path:
        """获取配置文件路径"""
        # 优先级：
        # 1. EVOSKILL_CONFIG 环境变量
        # 2. ~/.config/evoskill/config.yaml (Linux/Mac)
        # 3. ~/AppData/Local/evoskill/config.yaml (Windows)
        
        env_path = os.getenv("EVOSKILL_CONFIG")
        if env_path:
            return Path(env_path)
        
        if os.name == "nt":  # Windows
            config_dir = Path.home() / "AppData" / "Local" / "evoskill"
        else:  # Linux/Mac
            config_dir = Path.home() / ".config" / "evoskill"
        
        return config_dir / "config.yaml"
    
    def load(self) -> EvoSkillConfig:
        """
        加载配置
        
        优先级：
        1. 环境变量（已自动由 Pydantic 处理）
        2. 配置文件
        3. 默认值
        """
        config_dict = {}
        
        # 从配置文件加载
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_dict = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
        
        return EvoSkillConfig(**config_dict)
    
    def save(self, config: EvoSkillConfig) -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置对象
        """
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存（注意：API key 会被保存，请确保文件权限安全）
        config_dict = config.to_dict()
        
        # 如果用户想保存 API key，需要显式设置
        if config.api_key and os.getenv("EVOSKILL_SAVE_API_KEY") == "1":
            config_dict["api_key"] = config.api_key
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        
        # 设置文件权限（仅限 Unix）
        if os.name != "nt":
            os.chmod(self.config_path, 0o600)
    
    def create_default(self) -> None:
        """创建默认配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        default_content = '''# EvoSkill 配置文件
# 放置位置: ~/.config/evoskill/config.yaml (Linux/Mac)
#          %LOCALAPPDATA%/evoskill/config.yaml (Windows)
# 优先级: 环境变量 > 本配置文件 > 默认值

# ============================================
# LLM 配置 (重要!)
# ============================================

# provider: API 提供商类型
#   - openai      : OpenAI 或兼容 OpenAI API 格式的服务
#   - anthropic   : Anthropic Claude 官方 API
#   - kimi-coding : Kimi For Coding (需要特殊 User-Agent)
#   - custom      : 其他自定义 API (需同时设置 base_url)
provider: openai

# model: 模型名称
#   OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo
#   Kimi For Coding: k2p5 (需要 provider 设为 kimi-coding)
#   Kimi 普通: moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k
#   OpenRouter: 参照 https://openrouter.ai/docs#models
model: gpt-4o-mini

# base_url: API 基础 URL (用于第三方代理)
#   默认 (不设置): 使用官方 API 地址
#   Kimi For Coding: https://api.kimi.com/coding/v1
#   Kimi 普通: https://api.moonshot.cn/v1
#   OpenRouter: https://openrouter.ai/api/v1
#   SiliconFlow: https://api.siliconflow.cn/v1
# base_url: https://api.kimi.com/coding/v1

# api_key: API 密钥
#   安全建议: 优先使用环境变量 EVOSKILL_API_KEY，而非写入此文件
#   环境变量设置: export EVOSKILL_API_KEY=sk-xxxx (Linux/Mac)
#                 set EVOSKILL_API_KEY=sk-xxxx (Windows CMD)
# api_key: sk-xxxx

# ============================================
# 模型参数 (可选)
# ============================================

# temperature: 随机性 (0.0-2.0)
#   0.0: 最确定，适合代码生成
#   0.7: 平衡，适合一般对话
#   1.0+: 更有创意，适合头脑风暴
temperature: 0.7

# max_tokens: 单次回复最大 token 数
#   不设置则使用模型默认值
# max_tokens: 4096

# thinking_level: 思考级别 (仅 Claude 支持)
#   - low    : 快速回答
#   - medium : 平衡
#   - high   : 深度思考
# thinking_level: medium

# ============================================
# 路径配置 (可选)
# ============================================

# workspace: 默认工作目录
#   不设置则使用当前目录
# workspace: ~/projects

# skills_dir: Skills 存储目录
#   不设置则使用 <workspace>/.evoskill/skills/
# skills_dir: ~/.evoskill/skills

# sessions_dir: 会话存储目录
#   不设置则使用 <workspace>/.evoskill/sessions/
# sessions_dir: ~/.evoskill/sessions

# ============================================
# 上下文配置 (重要!)
# ============================================

# max_context_tokens: 最大上下文 token 数
#   - 当上下文接近此值时，自动触发压缩
#   - 建议设置为模型上下文窗口的 80-90%
#   - 例如:
#     * gpt-4o-mini (128k): 设为 100000
#     * Kimi 128k: 设为 100000
#     * Kimi 32k: 设为 25000
#     * 本地小模型 (8k): 设为 6000
max_context_tokens: 80000

# ============================================
# 安全配置
# ============================================

# require_confirmation: 危险操作前是否询问确认
#   true : 执行删除/覆盖/命令前询问用户 (推荐)
#   false: 直接执行 (仅在信任环境中使用)
require_confirmation: true
'''
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(default_content)
        
        print(f"Created default config at: {self.config_path}")
    
    def exists(self) -> bool:
        """检查配置文件是否存在"""
        return self.config_path.exists()
    
# 全局配置实例
_config_manager = ConfigManager()


def get_config() -> EvoSkillConfig:
    """获取全局配置"""
    return _config_manager.load()


def save_config(config: EvoSkillConfig) -> None:
    """保存全局配置"""
    _config_manager.save(config)


def init_config() -> None:
    """初始化配置文件"""
    _config_manager.create_default()


def get_config_path() -> Path:
    """获取配置文件路径"""
    return _config_manager.config_path
