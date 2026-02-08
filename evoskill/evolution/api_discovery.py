"""
API 发现助手 - 帮助找到合适的 API

为 Skill 需求推荐可用的公共 API
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ApiInfo:
    """API 信息"""
    name: str
    provider: str
    description: str
    signup_url: str
    free_quota: str
    features: List[str]
    category: str  # weather, search, translate, etc.
    api_base_url: str
    auth_type: str  # api_key, oauth, none
    env_var_name: str  # 推荐的环境变量名


class ApiDiscovery:
    """
    API 发现助手
    
    为不同类型的 Skill 推荐合适的公共 API
    """
    
    # 预置的常用 API 数据库
    KNOWN_APIS: Dict[str, List[ApiInfo]] = {
        "weather": [
            ApiInfo(
                name="OpenWeatherMap",
                provider="OpenWeather",
                description="全球天气数据，支持 200+ 国家",
                signup_url="https://openweathermap.org/api",
                free_quota="1000 次/天",
                features=["当前天气", "5日预报", "空气质量"],
                category="weather",
                api_base_url="https://api.openweathermap.org/data/2.5",
                auth_type="api_key",
                env_var_name="OPENWEATHER_API_KEY"
            ),
            ApiInfo(
                name="和风天气",
                provider="QWeather",
                description="国内首选，支持格点天气、灾害预警",
                signup_url="https://dev.qweather.com",
                free_quota="1000 次/天",
                features=["实时天气", "7日预报", "灾害预警", "空气质量"],
                category="weather",
                api_base_url="https://devapi.qweather.com/v7",
                auth_type="api_key",
                env_var_name="QWEATHER_API_KEY"
            ),
            ApiInfo(
                name="WeatherAPI",
                provider="WeatherAPI.com",
                description="简单易用，支持历史数据",
                signup_url="https://www.weatherapi.com",
                free_quota="100 万次/月",
                features=["实时天气", "预报", "历史数据", "时区"],
                category="weather",
                api_base_url="http://api.weatherapi.com/v1",
                auth_type="api_key",
                env_var_name="WEATHERAPI_KEY"
            ),
        ],
        "search": [
            ApiInfo(
                name="Bing Web Search",
                provider="Microsoft Azure",
                description="微软必应搜索 API",
                signup_url="https://azure.microsoft.com/services/cognitive-services/bing-web-search-api/",
                free_quota="1000 次/月",
                features=["网页搜索", "图片搜索", "新闻搜索"],
                category="search",
                api_base_url="https://api.bing.microsoft.com/v7.0",
                auth_type="api_key",
                env_var_name="BING_SEARCH_API_KEY"
            ),
            ApiInfo(
                name="Google Custom Search",
                provider="Google",
                description="谷歌自定义搜索",
                signup_url="https://developers.google.com/custom-search",
                free_quota="100 次/天",
                features=["网页搜索", "图片搜索"],
                category="search",
                api_base_url="https://www.googleapis.com/customsearch/v1",
                auth_type="api_key",
                env_var_name="GOOGLE_SEARCH_API_KEY"
            ),
            ApiInfo(
                name="SerpAPI",
                provider="SerpAPI",
                description="聚合多个搜索引擎结果",
                signup_url="https://serpapi.com",
                free_quota="100 次/月",
                features=["Google", "Bing", "百度", "DuckDuckGo"],
                category="search",
                api_base_url="https://serpapi.com/search",
                auth_type="api_key",
                env_var_name="SERPAPI_KEY"
            ),
        ],
        "translate": [
            ApiInfo(
                name="Google Translate",
                provider="Google Cloud",
                description="谷歌翻译 API",
                signup_url="https://cloud.google.com/translate",
                free_quota="50万字符/月",
                features=["文本翻译", "语言检测", "批量翻译"],
                category="translate",
                api_base_url="https://translation.googleapis.com/language/translate/v2",
                auth_type="api_key",
                env_var_name="GOOGLE_TRANSLATE_API_KEY"
            ),
            ApiInfo(
                name="LibreTranslate",
                provider="LibreTranslate",
                description="开源免费翻译 API",
                signup_url="https://libretranslate.com",
                free_quota="自托管免费 / 官方 30 次/分钟",
                features=["文本翻译", "语言检测"],
                category="translate",
                api_base_url="https://libretranslate.de/translate",
                auth_type="api_key",
                env_var_name="LIBRETRANSLATE_API_KEY"
            ),
        ],
        "news": [
            ApiInfo(
                name="NewsAPI",
                provider="NewsAPI.org",
                description="全球新闻聚合",
                signup_url="https://newsapi.org",
                free_quota="100 次/天",
                features=["头条新闻", "搜索新闻", "新闻源"],
                category="news",
                api_base_url="https://newsapi.org/v2",
                auth_type="api_key",
                env_var_name="NEWSAPI_KEY"
            ),
            ApiInfo(
                name="GNews",
                provider="GNews.io",
                description="全球新闻 API",
                signup_url="https://gnews.io",
                free_quota="100 次/天",
                features=["搜索新闻", "头条", "主题"],
                category="news",
                api_base_url="https://gnews.io/api/v4",
                auth_type="api_key",
                env_var_name="GNEWS_API_KEY"
            ),
        ],
    }
    
    @classmethod
    def find_apis(cls, category: str) -> List[ApiInfo]:
        """
        查找某类别的 API
        
        Args:
            category: API 类别 (weather, search, translate, news, etc.)
            
        Returns:
            API 信息列表
        """
        return cls.KNOWN_APIS.get(category.lower(), [])
    
    @classmethod
    def suggest_api(cls, description: str) -> Optional[ApiInfo]:
        """
        根据描述推荐 API
        
        Args:
            description: Skill 描述
            
        Returns:
            推荐的 API 信息，或 None
        """
        desc_lower = description.lower()
        
        # 关键词匹配
        keywords = {
            "weather": ["天气", "weather", "temperature", "温度", "forecast", "预报"],
            "search": ["搜索", "search", "查询", "query", "find", "查找"],
            "translate": ["翻译", "translate", "translation", "语言", "language"],
            "news": ["新闻", "news", "头条", "headlines", "article"],
        }
        
        for category, words in keywords.items():
            if any(word in desc_lower for word in words):
                apis = cls.find_apis(category)
                if apis:
                    return apis[0]  # 返回第一个（推荐度最高的）
        
        return None
    
    @classmethod
    def get_setup_guide(cls, api_info: ApiInfo) -> str:
        """
        获取 API 配置指南
        
        Args:
            api_info: API 信息
            
        Returns:
            配置指南 Markdown 文本
        """
        return f"""## {api_info.name} API 配置指南

### 1. 注册账号
访问 {api_info.signup_url} 注册账号

### 2. 获取 API Key
- 登录后进入 API Keys 页面
- 创建新的 API Key
- 复制 Key 值备用

### 3. 配置环境变量
```bash
# Linux/macOS
export {api_info.env_var_name}=your_api_key_here

# Windows (PowerShell)
$env:{api_info.env_var_name}="your_api_key_here"

# Windows (CMD)
set {api_info.env_var_name}=your_api_key_here
```

### 4. API 信息
- **提供商**: {api_info.provider}
- **免费额度**: {api_info.free_quota}
- **认证方式**: {api_info.auth_type}
- **API 地址**: {api_info.api_base_url}

### 5. 功能特性
{chr(10).join(['- ' + f for f in api_info.features])}

---
配置完成后重新运行程序即可使用。
"""


def main():
    """测试 API 发现功能"""
    # 查找天气 API
    print("=== 天气 API ===")
    for api in ApiDiscovery.find_apis("weather"):
        print(f"- {api.name}: {api.free_quota}")
    
    # 测试推荐
    print("\n=== 推荐 API ===")
    api = ApiDiscovery.suggest_api("查询北京天气")
    if api:
        print(f"推荐: {api.name}")
        print(ApiDiscovery.get_setup_guide(api))


if __name__ == "__main__":
    main()
