"""
Weather Query Skill 测试
"""

import pytest
from ..main import get_weather, get_forecast


@pytest.mark.asyncio
async def test_get_weather():
    """测试获取天气"""
    result = await get_weather("北京")
    
    assert "北京" in result
    assert "温度" in result
    assert "湿度" in result


@pytest.mark.asyncio
async def test_get_weather_fahrenheit():
    """测试华氏度"""
    result = await get_weather("New York", units="fahrenheit")
    
    assert "New York" in result
    assert "°F" in result


@pytest.mark.asyncio
async def test_get_forecast():
    """测试天气预报"""
    result = await get_forecast("上海", days=3)
    
    assert "上海" in result
    assert "未来3天" in result
    assert result.count("°C") >= 3  # 至少有3个温度


@pytest.mark.asyncio
async def test_get_weather_consistency():
    """测试同一城市返回一致结果"""
    result1 = await get_weather("TestCity")
    result2 = await get_weather("TestCity")
    
    assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
