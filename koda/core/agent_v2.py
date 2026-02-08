"""
KodaAgent V2 - 融合 Pi Coding Agent 优势的自主编程代理

核心特性：
1. 树状会话管理 - 支持分支、合并、导航
2. 自扩展机制 - 代理自己写工具扩展
3. 自验证循环 - 代码生成 -> 验证 -> 修复
4. Pi-兼容工具 - 完全兼容 Pi 的 4 个核心工具
"""
import asyncio
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

from koda.core.tree_session import TreeSession, TreeSessionManager, SessionNode, NodeStatus
from koda.core.extension_engine import ExtensionEngine
from koda.core.system_prompt import SystemPromptBuilder, SystemPromptOptions
from koda.core.truncation import TruncationResult

# Pi-兼容工具
from koda.tools.file_tool import FileTool, ReadResult, EditResult
from koda.tools.shell_tool import ShellTool


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class AgentConfig:
    """代理配置"""
    # 自扩展配置
    enable_self_extension: bool = True
    auto_create_missing_tools: bool = False  # 默认关闭，需要时手动开启
    
    # 树状会话配置
    enable_branches: bool = True
    max_branches: int = 10
    
    # 验证配置
    enable_validation: bool = True
    max_iterations: int = 3
    
    # 通用配置
    verbose: bool = True
    
    # 工具配置
    default_tools: List[str] = field(default_factory=lambda: ["read", "write", "edit", "bash"])


class KodaAgentV2:
    """
    Koda Agent V2
    
    融合 Pi Coding Agent 理念的自主编程代理
    """
    
    def __init__(
        self,
        llm: Any,
        config: Optional[AgentConfig] = None,
        workspace: Optional[Path] = None,
    ):
        self.llm = llm
        self.config = config or AgentConfig()
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.verbose = self.config.verbose
        
        # 初始化子系统
        self._koda_dir = self.workspace / ".koda"
        self._koda_dir.mkdir(exist_ok=True)
        
        self.session_manager = TreeSessionManager(self.workspace)
        self.extension_engine = ExtensionEngine(self._koda_dir / "extensions")
        
        # Pi-兼容工具
        self.file_tool = FileTool(self.workspace)
        self.shell_tool = ShellTool(self.workspace)
        
        # 当前会话
        self.session: Optional[TreeSession] = None
    
    # ============ Pi-兼容工具 API ============
    
    async def read(
        self,
        path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> ReadResult:
        """
        Pi-compatible read tool
        
        Read file content with optional offset and limit.
        Automatically handles truncation for large files.
        """
        self._log(f"Reading: {path}")
        
        result = await self.file_tool.read(path, offset, limit)
        
        if result.error:
            self._log(f"Read error: {result.error}")
        else:
            lines_info = f" lines {result.start_line}-{result.end_line}" if result.truncated else ""
            self._log(f"Read {len(result.content)} bytes{lines_info}")
        
        return result
    
    async def write(self, path: str, content: str) -> bool:
        """
        Pi-compatible write tool
        
        Write content to a file. Creates directories if needed.
        """
        self._log(f"Writing: {path}")
        success = await self.file_tool.write(path, content)
        
        if success:
            self._log(f"Written: {path}")
        else:
            self._log(f"Failed to write: {path}")
        
        return success
    
    async def edit(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> EditResult:
        """
        Pi-compatible edit tool
        
        Edit a file by replacing exact text.
        The old_text must match exactly (including whitespace).
        """
        self._log(f"Editing: {path}")
        
        result = await self.file_tool.edit(path, old_text, new_text)
        
        if result.success:
            self._log(f"Edited: {path}")
        else:
            self._log(f"Edit failed: {result.error}")
        
        return result
    
    async def bash(
        self,
        command: str,
        timeout: Optional[int] = None,
        signal=None,
        on_update: Optional[Callable[[str], None]] = None,
    ) -> ToolResult:
        """
        Pi-compatible bash tool
        
        Execute shell commands with streaming output.
        Automatically truncates large outputs.
        """
        self._log(f"Executing: {command[:50]}...")
        
        result = await self.shell_tool.execute(
            command=command,
            timeout=timeout,
            signal=signal,
            on_update=on_update,
        )
        
        # 转换格式
        return ToolResult(
            success=result.success,
            result=result.output if result.success else None,
            error=result.error if not result.success else None,
        )
    
    # ============ 主执行流程 ============
    
    async def execute_task(
        self,
        description: str,
        requirements: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        执行任务（兼容 Koda V1 API）
        
        完整流程：
        1. 创建/恢复会话
        2. 构建系统提示词
        3. 生成代码
        4. 验证代码
        5. 迭代直到成功
        """
        requirements = requirements or []
        
        # 1. 初始化会话
        if not self.session:
            self.session = self.session_manager.create_session("main")
        
        current_node = self.session.get_current_node()
        
        self._log(f"Starting task: {description[:50]}...")
        self._log(f"Current node: {current_node.name} ({current_node.id})")
        
        # 2. 构建系统提示词
        builder = SystemPromptBuilder.for_task(
            task_description=description,
            tools=self.config.default_tools,
            cwd=str(self.workspace),
        )
        system_prompt = builder.build()
        
        # 3. 生成代码
        iteration = 0
        last_code = ""
        
        while iteration < self.config.max_iterations:
            iteration += 1
            self._log(f"Iteration {iteration}/{self.config.max_iterations}")
            
            # 生成代码
            code_result = await self._generate_code(
                description=description,
                requirements=requirements,
                node=current_node,
                system_prompt=system_prompt,
            )
            
            last_code = code_result.get("code", "")
            
            # 更新节点
            current_node.artifacts["main.py"] = last_code
            current_node.artifacts["docs.md"] = code_result.get("docs", "")
            
            # 4. 验证（如果启用）
            if not self.config.enable_validation:
                self._log("Validation disabled")
                current_node.status = NodeStatus.SUCCESS
                break
            
            # 简单验证：尝试解析 Python
            is_valid, error = self._validate_python(last_code)
            
            if is_valid:
                self._log("Validation passed!")
                current_node.status = NodeStatus.SUCCESS
                break
            
            # 5. 修复
            self._log(f"Validation failed: {error}")
            
            # 创建修复分支或原地修复
            if self.config.enable_branches:
                fix_node = self.session.create_branch(
                    name=f"fix-iter{iteration}",
                    description=f"Fix syntax error - iteration {iteration}",
                )
                
                fixed_code = await self._fix_code(
                    code=last_code,
                    error=error,
                    node=fix_node,
                    system_prompt=system_prompt,
                )
                
                fix_node.artifacts["main.py"] = fixed_code
                
                # 验证修复
                is_valid, _ = self._validate_python(fixed_code)
                
                if is_valid:
                    self._log("Fix successful, merging to parent")
                    fix_node.status = NodeStatus.SUCCESS
                    self.session.merge(fix_node.id, fix_node.parent_id)
                    current_node = self.session.get_current_node()
                    break
                else:
                    self._log("Fix failed, abandoning branch")
                    self.session.abandon(fix_node.id)
            else:
                # 原地修复
                fixed_code = await self._fix_code(
                    code=last_code,
                    error=error,
                    node=current_node,
                    system_prompt=system_prompt,
                )
                current_node.artifacts["main.py"] = fixed_code
                last_code = fixed_code
        
        # 保存会话
        self.session_manager.save_current_session()
        
        # 最终验证
        final_code = current_node.artifacts.get("main.py", "")
        is_valid, final_error = self._validate_python(final_code)
        
        return {
            "success": is_valid,
            "iterations": iteration,
            "code": final_code,
            "node_id": current_node.id,
            "session_id": self.session.session_id,
            "error": final_error if not is_valid else None,
        }
    
    # ============ 核心方法 ============
    
    async def _generate_code(
        self,
        description: str,
        requirements: List[str],
        node: SessionNode,
        system_prompt: str,
    ) -> Dict[str, str]:
        """生成代码"""
        # 构建上下文
        context = self._build_context(node)
        
        # 构建用户提示词
        user_prompt = f"""Write Python code for:

{description}

Requirements:
{chr(10).join(f"- {r}" for r in requirements)}

Available tools:
- read(path, offset?, limit?): Read file contents
- write(path, content): Write to file
- edit(path, old_text, new_text): Edit file
- bash(command): Execute shell command

{context}

Generate complete, runnable Python code:
"""
        
        # 调用 LLM
        code = await self._llm_complete(system_prompt, user_prompt)
        
        # 生成文档
        doc_prompt = f"""Write brief documentation (2-3 sentences) for this code:

{code[:1000]}..."""
        docs = await self._llm_complete(system_prompt, doc_prompt)
        
        return {
            "code": self._clean_code(code),
            "docs": docs.strip(),
        }
    
    async def _fix_code(
        self,
        code: str,
        error: str,
        node: SessionNode,
        system_prompt: str,
    ) -> str:
        """修复代码"""
        user_prompt = f"""Fix this Python code:

```python
{code}
```

Error: {error}

Provide only the fixed code:
"""
        
        fixed = await self._llm_complete(system_prompt, user_prompt)
        return self._clean_code(fixed)
    
    def _validate_python(self, code: str) -> tuple[bool, Optional[str]]:
        """简单验证 Python 代码"""
        import ast
        
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    # ============ 分支操作 ============
    
    def create_branch(self, name: str, description: str) -> SessionNode:
        """创建新分支"""
        if not self.session:
            raise ValueError("No active session")
        
        return self.session.create_branch(name, description)
    
    def checkout(self, node_id: str) -> SessionNode:
        """切换到指定节点"""
        if not self.session:
            raise ValueError("No active session")
        
        return self.session.checkout(node_id)
    
    def merge(self, from_node_id: str, to_node_id: Optional[str] = None) -> SessionNode:
        """合并分支"""
        if not self.session:
            raise ValueError("No active session")
        
        to_id = to_node_id or self.session.get_current_node().parent_id
        return self.session.merge(from_node_id, to_id)
    
    def abandon(self, node_id: str) -> None:
        """放弃分支"""
        if not self.session:
            raise ValueError("No active session")
        
        self.session.abandon(node_id)
    
    def get_tree_view(self) -> str:
        """获取树状视图"""
        if not self.session:
            return "No active session"
        
        return self.session.get_tree_visualization()
    
    # ============ 扩展操作 ============
    
    async def create_extension(
        self,
        name: str,
        description: str,
        requirements: List[str],
    ) -> Dict[str, Any]:
        """创建新扩展"""
        if not self.config.enable_self_extension:
            return {"success": False, "error": "Self-extension disabled"}
        
        from koda.core.extension_engine import SelfExtendingAgent
        
        agent = SelfExtendingAgent(self.extension_engine, self.llm)
        
        try:
            extension = await agent.create_tool_for_capability(
                capability=description,
                requirements=requirements,
            )
            
            return {
                "success": True,
                "name": extension.name,
                "code": extension.code,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def list_extensions(self) -> List[str]:
        """列出所有扩展"""
        return self.extension_engine.list_extensions()
    
    # ============ 辅助方法 ============
    
    async def _llm_complete(self, system: str, user: str) -> str:
        """调用 LLM"""
        # 假设 llm 对象有 chat 方法
        if hasattr(self.llm, 'chat'):
            return await self.llm.chat([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ])
        elif hasattr(self.llm, 'complete'):
            return await self.llm.complete(user, system_prompt=system)
        else:
            # 简单实现
            return f"# TODO: Implement LLM call\n# System: {system[:100]}...\n# User: {user[:100]}..."
    
    def _build_context(self, node: SessionNode) -> str:
        """构建上下文"""
        path = self.session.get_path_to_root(node.id)
        
        if len(path) > 1:
            parent = path[-2]
            if "main.py" in parent.artifacts:
                return f"\nPrevious version:\n```python\n{parent.artifacts['main.py'][:500]}\n```"
        
        return ""
    
    def _clean_code(self, code: str) -> str:
        """清理代码"""
        code = code.strip()
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()
    
    def _log(self, message: str) -> None:
        """日志输出"""
        if self.verbose:
            print(f"[KodaV2] {message}")
    
    # ============ 便捷方法 ============
    
    async def quick_edit(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> bool:
        """
        快速编辑 - 自动重试
        
        如果精确匹配失败，尝试使用 LLM 进行模糊匹配。
        """
        result = await self.edit(path, old_text, new_text)
        
        if result.success:
            return True
        
        # 尝试 LLM 辅助编辑
        self._log("Exact match failed, trying LLM-assisted edit...")
        
        try:
            # 读取文件
            read_result = await self.read(path)
            if read_result.error:
                return False
            
            content = read_result.content
            
            # 使用 LLM 进行模糊编辑
            system_prompt = """You are a code editing assistant.
Given file content and an edit request, apply the edit and return the complete new file content.
Only output the new file content, no explanations."""
            
            user_prompt = f"""File: {path}

Current content:
```
{content}
```

Edit request:
Replace this:
```
{old_text}
```

With this:
```
{new_text}
```

Return the complete new file content:"""
            
            new_content = await self._llm_complete(system_prompt, user_prompt)
            new_content = self._clean_code(new_content)
            
            # 写回文件
            return await self.write(path, new_content)
            
        except Exception as e:
            self._log(f"LLM-assisted edit failed: {e}")
            return False


# 保持向后兼容
KodaAgent = KodaAgentV2
