---
name: weather-query
description: 查询指定城市的天气信息
version: 1.0.0
author: evoskill
tags: [weather, api, utility]
tools:
  - name: get_weather
    description: 获取指定城市的当前天气
    parameters:
      city:
        type: string
        description: 城市名称（中文或英文）
        required: true
      units:
        type: string
        description: 温度单位 (celsius/fahrenheit)
        required: false
---

# Weather Query Skill

查询城市天气信息的 Skill。

## 功能

- 获取当前天气状况
- 支持摄氏度和华氏度
- 返回温度、湿度、天气描述

## 使用场景

当用户询问天气时使用此 Skill：
- "北京今天天气怎么样？"
- "纽约的天气"
- "查询上海天气"

## 示例

```python
# 查询北京天气
result = await get_weather(city="北京")
print(result)
# 输出: 北京当前天气：晴，温度 25°C，湿度 45%
```
