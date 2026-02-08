"""
APITool - HTTP 请求工具

执行 HTTP 请求，支持 REST API 调用。
"""
import json
import asyncio
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class APIResponse:
    """API 响应"""
    success: bool
    status_code: int
    headers: Dict[str, str]
    body: str
    url: str
    duration_ms: int


class APITool:
    """
    HTTP 请求工具
    
    Example:
        api = APITool()
        result = await api.get("https://api.example.com/data")
        print(result.body)
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.default_headers = {
            'User-Agent': 'Koda-Framework/0.1',
            'Accept': 'application/json',
        }
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        执行 HTTP 请求
        
        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE, etc.)
            url: 请求 URL
            headers: 请求头
            data: 请求体
            params: URL 参数
            
        Returns:
            APIResponse
        """
        import time
        start = time.time()
        
        try:
            # 添加 URL 参数
            if params:
                query = urllib.parse.urlencode(params)
                url = f"{url}?{query}"
            
            # 创建请求
            req = urllib.request.Request(
                url,
                data=data.encode('utf-8') if data else None,
                headers={**self.default_headers, **(headers or {})},
                method=method,
            )
            
            # 执行请求
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=self.timeout)),
                timeout=self.timeout,
            )
            
            body = response.read().decode('utf-8')
            duration = int((time.time() - start) * 1000)
            
            return APIResponse(
                success=200 <= response.status < 300,
                status_code=response.status,
                headers=dict(response.headers),
                body=body,
                url=url,
                duration_ms=duration,
            )
            
        except urllib.error.HTTPError as e:
            duration = int((time.time() - start) * 1000)
            return APIResponse(
                success=False,
                status_code=e.code,
                headers=dict(e.headers) if hasattr(e, 'headers') else {},
                body=e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else str(e),
                url=url,
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return APIResponse(
                success=False,
                status_code=0,
                headers={},
                body=str(e),
                url=url,
                duration_ms=duration,
            )
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """GET 请求"""
        return await self.request("GET", url, headers=headers, params=params)
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json_data: Optional[Dict] = None,
    ) -> APIResponse:
        """POST 请求"""
        if json_data:
            data = json.dumps(json_data)
            headers = {**(headers or {}), 'Content-Type': 'application/json'}
        return await self.request("POST", url, headers=headers, data=data)
    
    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json_data: Optional[Dict] = None,
    ) -> APIResponse:
        """PUT 请求"""
        if json_data:
            data = json.dumps(json_data)
            headers = {**(headers or {}), 'Content-Type': 'application/json'}
        return await self.request("PUT", url, headers=headers, data=data)
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """DELETE 请求"""
        return await self.request("DELETE", url, headers=headers)
    
    async def download(
        self,
        url: str,
        dest_path: str,
    ) -> bool:
        """
        下载文件
        
        Args:
            url: 文件 URL
            dest_path: 保存路径
            
        Returns:
            是否成功
        """
        try:
            req = urllib.request.Request(url, headers=self.default_headers)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=self.timeout),
            )
            
            with open(dest_path, 'wb') as f:
                f.write(response.read())
            
            return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "api",
            "timeout": self.timeout,
        }
