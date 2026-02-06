"""
Weather Query Skill - 天气查询

查询指定城市的天气信息。
"""

import random
from typing import Optional


# 模拟天气数据（实际应用中应调用真实天气 API）
WEATHER_CONDITIONS = ["晴", "多云", "阴", "小雨", "中雨", "雷阵雨"]


async def get_weather(city: str, units: str = "celsius") -> str:
    """
    获取指定城市的当前天气
    
    Args:
        city: 城市名称
        units: 温度单位，celsius 或 fahrenheit
        
    Returns:
        天气信息字符串
    """
    # 模拟天气数据
    # 实际应用中，这里应该调用天气 API（如 OpenWeatherMap、和风天气等）
    
    # 基于城市名生成固定的"随机"数据
    random.seed(city)
    
    condition = random.choice(WEATHER_CONDITIONS)
    temp_c = random.randint(15, 35)
    humidity = random.randint(30, 90)
    
    # 温度转换
    if units.lower() == "fahrenheit":
        temp = temp_c * 9 // 5 + 32
        temp_unit = "°F"
    else:
        temp = temp_c
        temp_unit = "°C"
    
    return (
        f"{city}当前天气：{condition}\n"
        f"温度: {temp}{temp_unit}\n"
        f"湿度: {humidity}%\n"
        f"(注：这是模拟数据，实际应用请接入真实天气 API)"
    )


async def get_forecast(city: str, days: int = 3) -> str:
    """
    获取天气预报
    
    Args:
        city: 城市名称
        days: 预报天数
        
    Returns:
        预报信息
    """
    random.seed(city + "forecast")
    
    forecast_lines = [f"{city}未来{days}天天气预报："]
    
    for i in range(days):
        condition = random.choice(WEATHER_CONDITIONS)
        high = random.randint(20, 35)
        low = high - random.randint(5, 15)
        forecast_lines.append(f"  第{i+1}天: {condition}, {low}°C ~ {high}°C")
    
    return "\n".join(forecast_lines)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=== Weather Query Skill Test ===\n")
        
        print(await get_weather("北京"))
        print()
        
        print(await get_weather("Shanghai", units="fahrenheit"))
        print()
        
        print(await get_forecast("深圳", days=3))
    
    asyncio.run(test())
