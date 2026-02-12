"""
Tools Manager - 工具管理器

提供工具注册、发现和验证功能。
"""
import inspect
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, List, Optional, Type, Union,
    get_type_hints, get_origin, get_args
)
from pathlib import Path
from enum import Enum
import importlib
import asyncio


class ToolStatus(Enum):
    """工具状态"""
    REGISTERED = "registered"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class ToolCategory(Enum):
    """工具分类"""
    FILE = "file"
    EDIT = "edit"
    SEARCH = "search"
    SHELL = "shell"
    GIT = "git"
    NETWORK = "network"
    SYSTEM = "system"
    UTILITY = "utility"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    """工具参数"""
    name: str
    type: Type
    description: str = ""
    default: Any = None
    required: bool = True
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None  # 正则表达式

    def validate(self, value: Any) -> tuple:
        """
        验证参数值

        Args:
            value: 参数值

        Returns:
            (is_valid, error_message)
        """
        # 检查必填
        if value is None:
            if self.required:
                return False, f"Parameter '{self.name}' is required"
            return True, ""

        # 类型检查
        if not isinstance(value, self.type):
            # 尝试类型转换
            try:
                value = self.type(value)
            except (ValueError, TypeError):
                return False, f"Parameter '{self.name}' must be of type {self.type.__name__}"

        # 选择值检查
        if self.choices is not None and value not in self.choices:
            return False, f"Parameter '{self.name}' must be one of {self.choices}"

        # 范围检查
        if self.min_value is not None and value < self.min_value:
            return False, f"Parameter '{self.name}' must be >= {self.min_value}"
        if self.max_value is not None and value > self.max_value:
            return False, f"Parameter '{self.name}' must be <= {self.max_value}"

        # 正则检查
        if self.pattern is not None and isinstance(value, str):
            import re
            if not re.match(self.pattern, value):
                return False, f"Parameter '{self.name}' does not match pattern {self.pattern}"

        return True, ""


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSchema:
    """工具 Schema"""
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: Type = Any
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.__name__,
                    "description": p.description,
                    "default": p.default,
                    "required": p.required,
                    "choices": p.choices,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "pattern": p.pattern,
                }
                for p in self.parameters
            ],
            "returns": self.returns.__name__ if hasattr(self.returns, "__name__") else str(self.returns),
            "category": self.category.value,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "examples": self.examples,
        }


@dataclass
class ToolInfo:
    """工具信息"""
    schema: ToolSchema
    func: Callable
    status: ToolStatus = ToolStatus.REGISTERED
    instance: Optional[Any] = None
    error: Optional[str] = None


class ToolValidator:
    """工具验证器"""

    @staticmethod
    def validate_function(func: Callable) -> tuple:
        """
        验证工具函数

        Args:
            func: 工具函数

        Returns:
            (is_valid, error_message)
        """
        if not callable(func):
            return False, "Tool must be callable"

        # 检查签名
        try:
            sig = inspect.signature(func)
        except ValueError as e:
            return False, f"Invalid function signature: {e}"

        return True, ""

    @staticmethod
    def validate_parameters(params: Dict[str, Any], schema: ToolSchema) -> tuple:
        """
        验证参数

        Args:
            params: 参数字典
            schema: 工具 Schema

        Returns:
            (is_valid, errors)
        """
        errors = []
        provided_params = set(params.keys())

        for param in schema.parameters:
            value = params.get(param.name, param.default)
            is_valid, error = param.validate(value)
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors


class ToolManager:
    """
    工具管理器

    提供工具的注册、发现、验证和执行功能。

    Example:
        >>> manager = ToolManager()
        >>> manager.register(my_function, schema)
        >>> result = await manager.execute("my_function", {"arg": "value"})
    """

    def __init__(self):
        """初始化工具管理器"""
        self._tools: Dict[str, ToolInfo] = {}
        self._validators: List[Callable] = []
        self._hooks: Dict[str, List[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_error": [],
        }

    @property
    def tools(self) -> Dict[str, ToolInfo]:
        """获取所有工具"""
        return self._tools.copy()

    def register(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: str = "",
        parameters: Optional[List[ToolParameter]] = None,
        category: ToolCategory = ToolCategory.UTILITY,
        **kwargs
    ) -> str:
        """
        注册工具

        Args:
            func: 工具函数
            name: 工具名称（默认使用函数名）
            description: 描述
            parameters: 参数列表
            category: 分类
            **kwargs: 其他 Schema 属性

        Returns:
            工具名称

        Raises:
            ValueError: 如果验证失败
        """
        # 验证函数
        is_valid, error = ToolValidator.validate_function(func)
        if not is_valid:
            raise ValueError(f"Invalid tool function: {error}")

        # 确定名称
        tool_name = name or func.__name__

        # 检查是否已注册
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' already registered")

        # 自动提取参数
        if parameters is None:
            parameters = self._extract_parameters(func)

        # 创建 Schema
        description = description or func.__doc__ or ""
        schema = ToolSchema(
            name=tool_name,
            description=description.strip(),
            parameters=parameters,
            category=category,
            **kwargs
        )

        # 创建工具信息
        tool_info = ToolInfo(
            schema=schema,
            func=func,
            status=ToolStatus.REGISTERED
        )

        self._tools[tool_name] = tool_info
        return tool_name

    def _extract_parameters(self, func: Callable) -> List[ToolParameter]:
        """从函数签名提取参数"""
        parameters = []

        try:
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            for name, param in sig.parameters.items():
                if name in ('self', 'cls'):
                    continue

                param_type = type_hints.get(name, Any)
                default = None
                required = True

                if param.default is not inspect.Parameter.empty:
                    default = param.default
                    required = False

                # 处理 Optional 类型
                origin = get_origin(param_type)
                if origin is Union:
                    args = get_args(param_type)
                    # 检查是否是 Optional[T] (即 Union[T, None])
                    non_none_args = [a for a in args if a is not type(None)]
                    if len(non_none_args) == 1:
                        param_type = non_none_args[0]

                parameters.append(ToolParameter(
                    name=name,
                    type=param_type if param_type is not Any else str,
                    required=required,
                    default=default
                ))

        except Exception:
            pass

        return parameters

    def unregister(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            True 如果成功注销
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[ToolInfo]:
        """
        获取工具信息

        Args:
            name: 工具名称

        Returns:
            ToolInfo 或 None
        """
        return self._tools.get(name)

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        """
        获取工具 Schema

        Args:
            name: 工具名称

        Returns:
            ToolSchema 或 None
        """
        tool = self._tools.get(name)
        return tool.schema if tool else None

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
        tag: Optional[str] = None
    ) -> List[ToolSchema]:
        """
        列出工具

        Args:
            category: 按分类过滤
            status: 按状态过滤
            tag: 按标签过滤

        Returns:
            ToolSchema 列表
        """
        result = []

        for tool in self._tools.values():
            # 分类过滤
            if category and tool.schema.category != category:
                continue

            # 状态过滤
            if status and tool.status != status:
                continue

            # 标签过滤
            if tag and tag not in tool.schema.tags:
                continue

            result.append(tool.schema)

        return result

    def enable(self, name: str) -> bool:
        """
        启用工具

        Args:
            name: 工具名称

        Returns:
            True 如果成功
        """
        tool = self._tools.get(name)
        if tool and tool.status != ToolStatus.ERROR:
            tool.status = ToolStatus.ENABLED
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        禁用工具

        Args:
            name: 工具名称

        Returns:
            True 如果成功
        """
        tool = self._tools.get(name)
        if tool:
            tool.status = ToolStatus.DISABLED
            return True
        return False

    async def execute(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        执行工具

        Args:
            name: 工具名称
            params: 参数

        Returns:
            ToolResult 对象
        """
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")

        if tool.status == ToolStatus.DISABLED:
            return ToolResult(success=False, error=f"Tool '{name}' is disabled")

        # 验证参数
        params = params or {}
        is_valid, errors = ToolValidator.validate_parameters(params, tool.schema)
        if not is_valid:
            return ToolResult(success=False, error="; ".join(errors))

        # 填充默认值
        full_params = {}
        for param in tool.schema.parameters:
            if param.name in params:
                full_params[param.name] = params[param.name]
            elif param.default is not None:
                full_params[param.name] = param.default
            elif not param.required:
                full_params[param.name] = None

        # 执行前置钩子
        for hook in self._hooks["before_execute"]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(name, full_params)
                else:
                    hook(name, full_params)
            except Exception:
                pass

        try:
            # 执行工具
            if asyncio.iscoroutinefunction(tool.func):
                result = await tool.func(**full_params)
            else:
                result = tool.func(**full_params)

            # 包装结果
            if isinstance(result, ToolResult):
                tool_result = result
            else:
                tool_result = ToolResult(success=True, data=result)

            # 执行后置钩子
            for hook in self._hooks["after_execute"]:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(name, full_params, tool_result)
                    else:
                        hook(name, full_params, tool_result)
                except Exception:
                    pass

            return tool_result

        except Exception as e:
            error_result = ToolResult(success=False, error=str(e))

            # 执行错误钩子
            for hook in self._hooks["on_error"]:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(name, full_params, e)
                    else:
                        hook(name, full_params, e)
                except Exception:
                    pass

            tool.status = ToolStatus.ERROR
            tool.error = str(e)

            return error_result

    def add_hook(self, event: str, hook: Callable) -> None:
        """
        添加钩子

        Args:
            event: 事件名称 (before_execute, after_execute, on_error)
            hook: 钩子函数
        """
        if event in self._hooks:
            self._hooks[event].append(hook)

    def remove_hook(self, event: str, hook: Callable) -> bool:
        """
        移除钩子

        Args:
            event: 事件名称
            hook: 钩子函数

        Returns:
            True 如果成功移除
        """
        if event in self._hooks and hook in self._hooks[event]:
            self._hooks[event].remove(hook)
            return True
        return False

    def discover_tools(
        self,
        module_path: str,
        prefix: str = ""
    ) -> List[str]:
        """
        从模块发现并注册工具

        扫描模块中所有带有 @tool 装饰器或特定命名模式的函数。

        Args:
            module_path: 模块路径
            prefix: 名称前缀

        Returns:
            注册的工具名称列表
        """
        registered = []

        try:
            module = importlib.import_module(module_path)

            for name, obj in inspect.getmembers(module):
                # 跳过私有成员
                if name.startswith("_"):
                    continue

                # 检查是否是函数
                if not callable(obj):
                    continue

                # 检查是否有工具标记
                if hasattr(obj, "_is_tool"):
                    tool_name = f"{prefix}{name}" if prefix else name
                    schema = getattr(obj, "_tool_schema", None)

                    if schema:
                        self._tools[tool_name] = ToolInfo(
                            schema=schema,
                            func=obj,
                            status=ToolStatus.REGISTERED
                        )
                        registered.append(tool_name)

        except ImportError:
            pass

        return registered

    def export_schemas(self) -> List[Dict[str, Any]]:
        """
        导出所有工具 Schema

        Returns:
            Schema 字典列表
        """
        return [tool.schema.to_dict() for tool in self._tools.values()]

    def import_schemas(self, schemas: List[Dict[str, Any]]) -> int:
        """
        导入工具 Schema

        注意：这只是导入 Schema 定义，实际函数需要单独注册。

        Args:
            schemas: Schema 字典列表

        Returns:
            导入数量
        """
        # 这个方法主要用于文档和类型检查
        # 实际的工具注册需要通过 register() 方法
        return len(schemas)


def tool(
    name: Optional[str] = None,
    description: str = "",
    category: ToolCategory = ToolCategory.UTILITY,
    **kwargs
) -> Callable:
    """
    工具装饰器

    用于标记函数为工具。

    Example:
        >>> @tool(name="my_tool", description="My tool")
        ... def my_function(arg: str) -> str:
        ...     return arg.upper()
    """
    def decorator(func: Callable) -> Callable:
        func._is_tool = True

        # 创建 Schema
        tool_name = name or func.__name__
        func._tool_schema = ToolSchema(
            name=tool_name,
            description=description or func.__doc__ or "",
            parameters=[],  # 稍后由管理器填充
            category=category,
            **kwargs
        )

        return func

    return decorator


def parameter(
    name: str,
    type: Type,
    description: str = "",
    default: Any = None,
    required: bool = True,
    **kwargs
) -> ToolParameter:
    """
    创建工具参数的便捷函数

    Args:
        name: 参数名
        type: 参数类型
        description: 描述
        default: 默认值
        required: 是否必填

    Returns:
        ToolParameter 对象
    """
    return ToolParameter(
        name=name,
        type=type,
        description=description,
        default=default,
        required=required,
        **kwargs
    )


# 全局工具管理器实例
_global_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    """
    获取全局工具管理器

    Returns:
        ToolManager 实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = ToolManager()
    return _global_manager


def register_tool(func: Callable, **kwargs) -> str:
    """
    注册工具到全局管理器

    Args:
        func: 工具函数
        **kwargs: 传递给 register() 的参数

    Returns:
        工具名称
    """
    return get_tool_manager().register(func, **kwargs)


async def execute_tool(name: str, params: Optional[Dict[str, Any]] = None) -> ToolResult:
    """
    使用全局管理器执行工具

    Args:
        name: 工具名称
        params: 参数

    Returns:
        ToolResult 对象
    """
    return await get_tool_manager().execute(name, params)


__all__ = [
    "ToolStatus",
    "ToolCategory",
    "ToolParameter",
    "ToolResult",
    "ToolSchema",
    "ToolInfo",
    "ToolValidator",
    "ToolManager",
    "tool",
    "parameter",
    "get_tool_manager",
    "register_tool",
    "execute_tool",
]
