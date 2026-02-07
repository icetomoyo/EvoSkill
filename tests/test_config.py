"""
配置管理测试
"""
import pytest
import os
import yaml
from pathlib import Path
from unittest.mock import patch, Mock

from evoskill.config import (
    EvoSkillConfig,
    ConfigManager,
    get_config,
    save_config,
    init_config,
)


class TestEvoSkillConfig:
    """测试配置类"""
    
    def test_default_values(self):
        """测试默认值"""
        config = EvoSkillConfig()
        
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.require_confirmation is True
        assert config.max_context_tokens == 80000
    
    def test_custom_values(self):
        """测试自定义值"""
        config = EvoSkillConfig(
            provider="kimi-coding",
            model="k2p5",
            temperature=0.5,
            max_tokens=2048,
            require_confirmation=False,
        )
        
        assert config.provider == "kimi-coding"
        assert config.model == "k2p5"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.require_confirmation is False
    
    def test_temperature_validation(self):
        """测试温度参数范围验证"""
        # 有效范围
        config = EvoSkillConfig(temperature=0.0)
        assert config.temperature == 0.0
        
        config = EvoSkillConfig(temperature=2.0)
        assert config.temperature == 2.0
    
    def test_get_api_key_from_config(self):
        """测试从配置获取 API Key"""
        config = EvoSkillConfig(
            provider="openai",
            api_key="sk-config-key"
        )
        
        assert config.get_api_key() == "sk-config-key"
    
    def test_get_api_key_from_env(self, monkeypatch):
        """测试从环境变量获取 API Key"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        
        config = EvoSkillConfig(provider="openai", api_key=None)
        
        assert config.get_api_key() == "sk-env-key"
    
    def test_get_api_key_priority(self, monkeypatch):
        """测试配置优先于环境变量"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        
        config = EvoSkillConfig(
            provider="openai",
            api_key="sk-config-key"  # 配置中的 key
        )
        
        # 配置中的 key 应该优先
        assert config.get_api_key() == "sk-config-key"
    
    def test_get_api_key_kimi_coding_env(self, monkeypatch):
        """测试 Kimi Coding 环境变量"""
        monkeypatch.setenv("KIMI_API_KEY", "sk-kimi-key")
        
        config = EvoSkillConfig(provider="kimi-coding", api_key=None)
        
        assert config.get_api_key() == "sk-kimi-key"
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = EvoSkillConfig(
            provider="openai",
            model="gpt-4o",
            api_key="sk-secret",
        )
        
        result = config.to_dict()
        
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"
        assert result["api_key"] == "***"  # 脱敏处理
    
    def test_skills_dir_default(self, temp_dir):
        """测试默认 skills 目录"""
        config = EvoSkillConfig(workspace=temp_dir)
        
        expected = temp_dir / ".evoskill" / "skills"
        assert config.skills_dir == expected
    
    def test_sessions_dir_default(self, temp_dir):
        """测试默认 sessions 目录"""
        config = EvoSkillConfig(workspace=temp_dir)
        
        expected = temp_dir / ".evoskill" / "sessions"
        assert config.sessions_dir == expected


class TestConfigManager:
    """测试配置管理器"""
    
    def test_load_from_file(self, temp_dir, monkeypatch):
        """测试从文件加载配置"""
        # 创建临时配置文件
        config_file = temp_dir / "config.yaml"
        config_data = {
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "temperature": 0.5,
        }
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")
        
        # 设置环境变量指向临时配置
        monkeypatch.setenv("EVOSKILL_CONFIG", str(config_file))
        
        manager = ConfigManager()
        config = manager.load()
        
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet"
        assert config.temperature == 0.5
    
    def test_load_nonexistent_file(self, temp_dir, monkeypatch):
        """测试加载不存在的配置文件"""
        config_file = temp_dir / "nonexistent.yaml"
        monkeypatch.setenv("EVOSKILL_CONFIG", str(config_file))
        
        manager = ConfigManager()
        config = manager.load()
        
        # 应该返回默认配置
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
    
    def test_save_config(self, temp_dir, monkeypatch):
        """测试保存配置"""
        config_file = temp_dir / "config.yaml"
        monkeypatch.setenv("EVOSKILL_CONFIG", str(config_file))
        
        manager = ConfigManager()
        config = EvoSkillConfig(
            provider="kimi-coding",
            model="k2p5",
            api_key="sk-test-key",
        )
        
        # 设置环境变量允许保存 API key
        monkeypatch.setenv("EVOSKILL_SAVE_API_KEY", "1")
        manager.save(config)
        
        # 验证文件已创建
        assert config_file.exists()
        
        # 验证内容
        saved_data = yaml.safe_load(config_file.read_text())
        assert saved_data["provider"] == "kimi-coding"
        assert saved_data["model"] == "k2p5"
    
    def test_exists(self, temp_dir, monkeypatch):
        """测试检查配置文件是否存在"""
        config_file = temp_dir / "config.yaml"
        monkeypatch.setenv("EVOSKILL_CONFIG", str(config_file))
        
        manager = ConfigManager()
        
        assert manager.exists() is False
        
        # 创建文件
        config_file.write_text("provider: openai\n", encoding="utf-8")
        assert manager.exists() is True
    
    def test_get_config_path_windows(self, monkeypatch):
        """测试 Windows 配置路径"""
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.delenv("EVOSKILL_CONFIG", raising=False)
        
        manager = ConfigManager()
        path = manager.config_path
        
        assert "AppData" in str(path)
        assert "evoskill" in str(path)
        assert path.name == "config.yaml"
    
    def test_get_config_path_unix(self, monkeypatch):
        """测试 Unix/Linux/Mac 配置路径"""
        monkeypatch.setattr("os.name", "posix")
        monkeypatch.delenv("EVOSKILL_CONFIG", raising=False)
        
        manager = ConfigManager()
        path = manager.config_path
        
        assert ".config" in str(path)
        assert "evoskill" in str(path)
        assert path.name == "config.yaml"


class TestConfigFunctions:
    """测试全局配置函数"""
    
    def test_init_config(self, temp_dir, monkeypatch):
        """测试初始化配置文件"""
        config_file = temp_dir / "config.yaml"
        monkeypatch.setenv("EVOSKILL_CONFIG", str(config_file))
        
        init_config()
        
        assert config_file.exists()
        content = config_file.read_text()
        assert "provider" in content
        assert "EvoSkill" in content
    
    def test_get_and_save_config_roundtrip(self, temp_dir, monkeypatch):
        """测试配置读写循环"""
        config_file = temp_dir / "config.yaml"
        monkeypatch.setenv("EVOSKILL_CONFIG", str(config_file))
        
        # 创建并保存配置
        original = EvoSkillConfig(
            provider="anthropic",
            model="claude-3-opus",
            temperature=0.3,
        )
        save_config(original)
        
        # 重新加载
        loaded = get_config()
        
        assert loaded.provider == "anthropic"
        assert loaded.model == "claude-3-opus"
        assert loaded.temperature == 0.3
