"""
Extension Engine - 自扩展引擎

实现 "代码写代码" 的核心理念：
- 代理可以自己编写工具扩展
- 扩展即时编译和热重载
- 扩展可以持久化到会话中
"""
import ast
import sys
import importlib
import importlib.util
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass
from pathlib import Path
import tempfile
import shutil


@dataclass
class ExtensionInfo:
    """扩展信息"""
    name: str
    description: str
    code: str
    version: str = "1.0.0"
    author: str = "koda-agent"
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ExtensionEngine:
    """
    自扩展引擎
    
    管理动态生成的工具扩展
    """
    
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        self.extensions: Dict[str, ExtensionInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.extension_dir = Path(tempfile.gettempdir()) / "koda_extensions"
        self.extension_dir.mkdir(exist_ok=True)
    
    # ============ 扩展生成 ============
    
    async def generate_extension(
        self,
        name: str,
        description: str,
        requirements: List[str],
        llm_client: Any,
    ) -> ExtensionInfo:
        """
        生成新扩展
        
        使用 LLM 根据需求生成工具代码
        
        Args:
            name: 扩展名称
            description: 扩展描述
            requirements: 功能需求列表
            llm_client: LLM 客户端
            
        Returns:
            ExtensionInfo
        """
        prompt = f"""Write a Python tool class for Koda framework.

Tool Name: {name}
Description: {description}

Requirements:
{chr(10).join(f"- {r}" for r in requirements)}

The tool class must:
1. Inherit from BaseTool (if available) or be a simple class
2. Have an async `execute` or `run` method
3. Include proper error handling
4. Have docstrings

Example structure:
```python
class {name.title()}Tool:
    '''Tool description'''
    
    def __init__(self, **config):
        self.config = config
    
    async def execute(self, **params) -> Dict[str, Any]:
        '''Execute the tool'''
        try:
            # Implementation
            return {{"success": True, "result": ...}}
        except Exception as e:
            return {{"success": False, "error": str(e)}}
```

Write the complete Python code:
"""
        
        # 调用 LLM 生成代码
        code = await llm_client.complete(prompt)
        
        # 清理代码
        code = self._clean_code(code)
        
        # 验证语法
        if not self._validate_syntax(code):
            raise ValueError("Generated code has syntax errors")
        
        # 创建扩展信息
        extension = ExtensionInfo(
            name=name,
            description=description,
            code=code,
        )
        
        return extension
    
    # ============ 扩展加载 ============
    
    def load_extension(self, extension: ExtensionInfo) -> Type:
        """
        加载扩展
        
        动态编译并加载扩展类
        
        Args:
            extension: 扩展信息
            
        Returns:
            扩展类
        """
        # 保存到临时文件
        file_path = self.extension_dir / f"{extension.name}.py"
        file_path.write_text(extension.code, encoding='utf-8')
        
        # 动态导入
        spec = importlib.util.spec_from_file_location(
            f"koda_ext.{extension.name}",
            file_path,
        )
        
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load extension {extension.name}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"koda_ext.{extension.name}"] = module
        spec.loader.exec_module(module)
        
        # 缓存
        self.loaded_modules[extension.name] = module
        self.extensions[extension.name] = extension
        
        # 找到工具类（假设有一个 Tool 后缀的类）
        tool_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr_name.endswith('Tool'):
                tool_class = attr
                break
        
        if not tool_class:
            # 如果没有找到 Tool 后缀的类，返回第一个类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and not attr_name.startswith('_'):
                    tool_class = attr
                    break
        
        return tool_class
    
    def hot_reload(self, name: str) -> bool:
        """
        热重载扩展
        
        重新加载已修改的扩展
        
        Args:
            name: 扩展名称
            
        Returns:
            是否成功
        """
        extension = self.extensions.get(name)
        if not extension:
            return False
        
        # 从 sys.modules 移除旧模块
        module_name = f"koda_ext.{name}"
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # 重新加载
        try:
            self.load_extension(extension)
            return True
        except Exception:
            return False
    
    # ============ 扩展执行 ============
    
    async def execute_extension(
        self,
        name: str,
        method: str = "execute",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        执行扩展
        
        Args:
            name: 扩展名称
            method: 要调用的方法名
            **kwargs: 参数
            
        Returns:
            执行结果
        """
        # 确保扩展已加载
        if name not in self.loaded_modules:
            if name in self.extensions:
                self.load_extension(self.extensions[name])
            else:
                return {"success": False, "error": f"Extension {name} not found"}
        
        module = self.loaded_modules[name]
        
        # 找到工具类并实例化
        tool_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and not attr_name.startswith('_'):
                tool_class = attr
                break
        
        if not tool_class:
            return {"success": False, "error": "No tool class found"}
        
        try:
            instance = tool_class()
            
            # 调用方法
            if hasattr(instance, method):
                func = getattr(instance, method)
                if asyncio.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": f"Method {method} not found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============ 扩展管理 ============
    
    def register_extension(self, extension: ExtensionInfo) -> None:
        """注册扩展"""
        self.extensions[extension.name] = extension
    
    def get_extension(self, name: str) -> Optional[ExtensionInfo]:
        """获取扩展信息"""
        return self.extensions.get(name)
    
    def list_extensions(self) -> List[str]:
        """列出所有扩展"""
        return list(self.extensions.keys())
    
    def delete_extension(self, name: str) -> bool:
        """删除扩展"""
        if name in self.extensions:
            del self.extensions[name]
            
            # 清理模块
            if name in self.loaded_modules:
                del self.loaded_modules[name]
            
            module_name = f"koda_ext.{name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            # 删除文件
            file_path = self.extension_dir / f"{name}.py"
            if file_path.exists():
                file_path.unlink()
            
            return True
        return False
    
    # ============ 辅助方法 ============
    
    def _clean_code(self, code: str) -> str:
        """清理代码"""
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()
    
    def _validate_syntax(self, code: str) -> bool:
        """验证代码语法"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def generate_extension_prompt(
        self,
        capability: str,
        context: str = "",
    ) -> str:
        """
        生成创建扩展的提示词
        
        用于指导代理自己写扩展
        """
        return f"""I need to create a new tool to {capability}.

Current context: {context}

Please write a Python tool class that:
1. Has a clear `__init__` with configuration
2. Has an async `execute` method
3. Handles errors gracefully
4. Returns a dict with 'success' and 'result' or 'error'

The tool should be self-contained and use standard library when possible.
"""


# 自扩展 Agent 类
class SelfExtendingAgent:
    """
    自扩展代理
    
    能够自己编写工具扩展来增强能力
    """
    
    def __init__(self, extension_engine: ExtensionEngine, llm_client: Any):
        self.extension_engine = extension_engine
        self.llm_client = llm_client
    
    async def create_tool_for_capability(
        self,
        capability: str,
        requirements: List[str],
    ) -> ExtensionInfo:
        """
        为特定能力创建工具
        
        这是 "代码写代码" 的核心实现
        """
        # 生成扩展名称
        tool_name = capability.lower().replace(" ", "_")[:20]
        
        # 生成扩展
        extension = await self.extension_engine.generate_extension(
            name=tool_name,
            description=f"Tool to {capability}",
            requirements=requirements,
            llm_client=self.llm_client,
        )
        
        # 加载扩展
        try:
            tool_class = self.extension_engine.load_extension(extension)
            
            # 注册到引擎
            self.extension_engine.register_extension(extension)
            
            print(f"[SelfExtendingAgent] Created and loaded tool: {tool_name}")
            
            return extension
            
        except Exception as e:
            print(f"[SelfExtendingAgent] Failed to load tool: {e}")
            raise
    
    async def improve_tool(
        self,
        tool_name: str,
        improvement: str,
    ) -> ExtensionInfo:
        """
        改进现有工具
        """
        old_extension = self.extension_engine.get_extension(tool_name)
        if not old_extension:
            raise ValueError(f"Tool {tool_name} not found")
        
        prompt = f"""Improve this tool:

Current code:
```python
{old_extension.code}
```

Improvement needed: {improvement}

Please provide the improved code:
"""
        
        new_code = await self.llm_client.complete(prompt)
        new_code = self.extension_engine._clean_code(new_code)
        
        # 创建新版本
        new_extension = ExtensionInfo(
            name=tool_name,
            description=old_extension.description,
            code=new_code,
            version=f"{float(old_extension.version) + 0.1:.1f}",
        )
        
        # 热重载
        self.extension_engine.register_extension(new_extension)
        self.extension_engine.hot_reload(tool_name)
        
        return new_extension


import asyncio