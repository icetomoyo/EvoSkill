"""
测试配置和 fixtures
"""
import pytest
from pathlib import Path
from evoskill.core.types import LLMConfig, Message, UserMessage, ToolDefinition
from evoskill.config import EvoSkillConfig


@pytest.fixture
def temp_dir(tmp_path):
    """创建临时目录"""
    return tmp_path


@pytest.fixture
def mock_llm_config():
    """Mock LLM 配置（用于测试，不调用真实 API）"""
    return LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test-mock-key",
        base_url="https://api.mock.com/v1",
        temperature=0.7,
        max_tokens=1024,
    )


@pytest.fixture
def mock_kimi_coding_config():
    """Mock Kimi For Coding 配置"""
    return LLMConfig(
        provider="kimi-coding",
        model="k2p5",
        api_key="sk-kimi-mock-key",
        base_url="https://api.kimi.com/coding/v1",
        temperature=0.0,
        max_tokens=4096,
    )


@pytest.fixture
def sample_messages():
    """示例消息列表"""
    return [
        UserMessage(content="Hello, how are you?"),
        UserMessage(content="What is the weather today?"),
    ]


@pytest.fixture
def sample_tool():
    """示例工具定义"""
    return ToolDefinition(
        name="get_weather",
        description="Get weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    )


@pytest.fixture
def mock_config(temp_dir):
    """Mock EvoSkill 配置"""
    return EvoSkillConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test-key",
        workspace=temp_dir,
        skills_dir=temp_dir / ".evoskill" / "skills",
        sessions_dir=temp_dir / ".evoskill" / "sessions",
    )


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """清理环境变量，避免影响测试"""
    # 清除可能影响测试的环境变量
    env_vars_to_clear = [
        "EVOSKILL_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "KIMI_API_KEY",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)
