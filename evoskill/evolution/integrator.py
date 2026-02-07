"""
Skill 集成器 - 将验证通过的 Skill 集成到系统
"""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from evoskill.core.session import AgentSession


class SkillIntegrator:
    """
    Skill 集成器
    
    将新创建的 Skill 加载到系统中，立即可用
    """
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
    
    def integrate(
        self,
        skill_path: Path,
        session: Optional[AgentSession] = None,
    ) -> Dict[str, Any]:
        """
        集成 Skill 到系统
        
        Args:
            skill_path: Skill 目录路径
            session: 可选的 Session，用于立即注册工具
            
        Returns:
            集成结果信息
        """
        skill_name = skill_path.name
        main_py = skill_path / "main.py"
        
        if not main_py.exists():
            return {
                "success": False,
                "error": f"main.py not found in {skill_path}",
            }
        
        try:
            # 1. 加载模块
            module = self._load_module(skill_path)
            
            if not module:
                return {
                    "success": False,
                    "error": f"Failed to load module from {skill_path}",
                }
            
            # 2. 提取 Skill 信息
            skill_info = self._extract_skill_info(module)
            
            # 3. 如果有 session，注册工具
            registered_tools = []
            if session and skill_info["tools"]:
                for tool_info in skill_info["tools"]:
                    tool_name = tool_info.get("name")
                    handler = tool_info.get("handler")
                    description = tool_info.get("description", "")
                    
                    if tool_name and handler:
                        # 提取参数信息
                        params = self._extract_parameters(handler)
                        
                        session.register_tool(
                            name=tool_name,
                            description=description,
                            parameters=params,
                            handler=handler,
                        )
                        registered_tools.append(tool_name)
            
            return {
                "success": True,
                "skill_name": skill_name,
                "skill_path": skill_path,
                "version": skill_info.get("version", "unknown"),
                "tools": [t.get("name") for t in skill_info["tools"]],
                "registered_tools": registered_tools,
                "description": skill_info.get("description", ""),
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def _load_module(self, skill_path: Path):
        """动态加载 Skill 模块"""
        skill_name = skill_path.name
        main_py = skill_path / "main.py"
        
        # 使用 importlib 动态加载
        spec = importlib.util.spec_from_file_location(
            skill_name,
            main_py,
        )
        
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # 临时添加到 sys.modules
        sys.modules[skill_name] = module
        
        try:
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            # 清理
            if skill_name in sys.modules:
                del sys.modules[skill_name]
            return None
    
    def _extract_skill_info(self, module) -> Dict[str, Any]:
        """从模块提取 Skill 信息"""
        return {
            "name": getattr(module, "SKILL_NAME", "unknown"),
            "version": getattr(module, "SKILL_VERSION", "0.1.0"),
            "description": getattr(module, "SKILL_DESCRIPTION", ""),
            "tools": getattr(module, "SKILL_TOOLS", []),
        }
    
    def _extract_parameters(self, handler) -> Dict[str, Any]:
        """从函数提取参数信息"""
        import inspect
        
        sig = inspect.signature(handler)
        params = {}
        
        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue
            
            param_info = {
                "type": "string",  # 默认类型
                "description": f"Parameter {name}",
                "required": param.default == inspect.Parameter.empty,
            }
            
            # 从注解获取类型
            if param.annotation != inspect.Parameter.empty:
                type_str = str(param.annotation).lower()
                if "str" in type_str:
                    param_info["type"] = "string"
                elif "int" in type_str:
                    param_info["type"] = "int"
                elif "float" in type_str:
                    param_info["type"] = "float"
                elif "bool" in type_str:
                    param_info["type"] = "bool"
                elif "list" in type_str:
                    param_info["type"] = "list"
                elif "dict" in type_str:
                    param_info["type"] = "dict"
            
            # 默认值
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            
            params[name] = param_info
        
        return params
    
    def reload_skill(self, skill_name: str) -> bool:
        """
        重新加载已存在的 Skill
        
        用于 Skill 更新后热重载
        """
        skill_path = self.skills_dir / skill_name
        
        if not skill_path.exists():
            return False
        
        # 从 sys.modules 移除旧模块
        if skill_name in sys.modules:
            del sys.modules[skill_name]
        
        # 重新加载
        module = self._load_module(skill_path)
        return module is not None
