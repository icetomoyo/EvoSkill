"""
KodaAgent V2 - 融合 Pi Coding Agent 优势的自主编程代理

核心特性：
1. 树状会话管理 - 支持分支、合并、导航
2. 自扩展机制 - 代理自己写工具扩展
3. 自验证循环 - 代码生成 -> 验证 -> 反思 -> 修复
4. Pi-兼容工具 - 完全兼容 Pi 的 7 个核心工具
5. Koda 增强 - 多维度验证 + LLM 代码审查
"""
import asyncio
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

from koda.core.tree_session import TreeSession, TreeSessionManager, SessionNode, NodeStatus
from koda.core.extension_engine import ExtensionEngine
from koda.core.system_prompt import SystemPromptBuilder, SystemPromptOptions
from koda.core.truncation import TruncationResult

# Koda 增强：验证系统
from koda.core.validator import Validator
from koda.core.reflector import Reflector, ReflectionResult, ValidationReport, ExecutionResult, CodeArtifact

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
    auto_create_missing_tools: bool = False
    
    # 树状会话配置
    enable_branches: bool = True
    max_branches: int = 10
    
    # 验证配置 (Koda 增强)
    enable_validation: bool = True
    enable_reflection: bool = True  # LLM 深度分析
    max_iterations: int = 3
    validation_score_threshold: float = 80.0  # 质量分数阈值
    
    # 通用配置
    verbose: bool = True
    
    # 工具配置
    default_tools: List[str] = field(default_factory=lambda: ["read", "write", "edit", "bash"])


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    code: str
    iterations: int
    validation_score: float
    reflection: Optional[ReflectionResult]
    node_id: str
    session_id: str
    error: Optional[str] = None


class KodaAgentV2:
    """
    Koda Agent V2
    
    融合 Pi Coding Agent 理念的自主编程代理，
    加上 Koda 增强的自验证和代码审查功能。
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
        
        # Koda 增强：验证系统
        self.validator = Validator()
        self.reflector = Reflector(llm if self.config.enable_reflection else None)
        
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
        """Pi-compatible read tool"""
        self._log(f"Reading: {path}")
        result = await self.file_tool.read(path, offset, limit)
        if result.error:
            self._log(f"Read error: {result.error}")
        else:
            lines_info = f" lines {result.start_line}-{result.end_line}" if result.truncated else ""
            self._log(f"Read {len(result.content)} bytes{lines_info}")
        return result
    
    async def write(self, path: str, content: str) -> bool:
        """Pi-compatible write tool"""
        self._log(f"Writing: {path}")
        success = await self.file_tool.write(path, content)
        self._log(f"Written: {path}" if success else f"Failed to write: {path}")
        return success
    
    async def edit(
        self,
        path: str,
        old_text: str,
        new_text: str,
    ) -> EditResult:
        """Pi-compatible edit tool"""
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
        """Pi-compatible bash tool"""
        self._log(f"Executing: {command[:50]}...")
        result = await self.shell_tool.execute(command, timeout, signal, on_update)
        return ToolResult(
            success=result.success,
            result=result.output if result.success else None,
            error=result.error if not result.success else None,
        )
    
    # ============ Koda 增强：自验证任务执行 ============
    
    async def execute_task(
        self,
        description: str,
        requirements: Optional[List[str]] = None,
    ) -> TaskResult:
        """
        执行任务（Koda 增强版）
        
        完整流程：
        1. 生成代码
        2. Validator: 多维度验证
        3. Reflector: LLM 深度分析
        4. 智能修复
        5. 迭代直到成功或达到最大次数
        """
        requirements = requirements or []
        
        # 初始化会话
        if not self.session:
            self.session = self.session_manager.create_session("main")
        
        current_node = self.session.get_current_node()
        self._log(f"🚀 Starting task: {description[:50]}...")
        self._log(f"📍 Current node: {current_node.name} ({current_node.id})")
        
        iteration = 0
        best_code = ""
        best_score = 0.0
        last_reflection = None
        
        while iteration < self.config.max_iterations:
            iteration += 1
            self._log(f"\n📦 Iteration {iteration}/{self.config.max_iterations}")
            
            # 1. 生成代码
            code_result = await self._generate_code(
                description=description,
                requirements=requirements,
                node=current_node,
                iteration=iteration,
            )
            
            code = code_result.get("code", "")
            best_code = code
            
            # 2. Koda 增强：多维度验证
            if self.config.enable_validation:
                execution = ExecutionResult(
                    success=True,
                    artifacts=[CodeArtifact("main.py", code)]
                )
                
                validation_report = await self.validator.validate(execution)
                self._log(f"   📊 Validation score: {validation_report.score:.1f}/100")
                
                if validation_report.score > best_score:
                    best_score = validation_report.score
                
                # 检查是否通过验证
                if validation_report.passed and validation_report.score >= self.config.validation_score_threshold:
                    self._log("   ✅ Validation passed!")
                    
                    # 3. Koda 增强：LLM 深度反思
                    if self.config.enable_reflection and self.llm:
                        reflection = await self.reflector.reflect(execution, validation_report)
                        last_reflection = reflection
                        
                        self._log(f"   🔍 Reflection confidence: {reflection.confidence:.2f}")
                        
                        if not reflection.has_issues:
                            self._log("   ✅ Code quality approved!")
                            current_node.status = NodeStatus.SUCCESS
                            break
                        else:
                            self._log(f"   ⚠️  {len(reflection.issues)} issues found")
                            if reflection.improved_code:
                                code = reflection.improved_code
                                best_code = code
                                self._log("   ✨ Applied auto-fix from reflection")
                    else:
                        current_node.status = NodeStatus.SUCCESS
                        break
                else:
                    # 验证失败，需要修复
                    self._log(f"   ❌ Validation failed: {len(validation_report.errors)} errors, {len(validation_report.warnings)} warnings")
                    
                    # 尝试修复
                    fix_context = {
                        "errors": validation_report.errors,
                        "warnings": validation_report.warnings,
                        "suggestions": []
                    }
                    
                    code = await self._fix_code_with_context(code, fix_context)
                    best_code = code
            else:
                # 简单验证（仅语法）
                is_valid, error = self._validate_python(code)
                if is_valid:
                    current_node.status = NodeStatus.SUCCESS
                    break
                else:
                    self._log(f"   ❌ Syntax error: {error}")
                    code = await self._fix_code(code, error, current_node)
                    best_code = code
            
            # 更新节点产物
            current_node.artifacts["main.py"] = best_code
            current_node.artifacts["docs.md"] = code_result.get("docs", "")
            
            # 分支策略：如果失败，创建修复分支
            if iteration < self.config.max_iterations and self.config.enable_branches:
                if current_node.status != NodeStatus.SUCCESS:
                    fix_node = self.session.create_branch(
                        name=f"fix-iter{iteration}",
                        description=f"Fix iteration {iteration}",
                    )
                    self._log(f"   🌿 Created fix branch: {fix_node.name}")
        
        # 保存会话
        self.session_manager.save_current_session()
        
        # 最终验证
        final_execution = ExecutionResult(
            success=True,
            artifacts=[CodeArtifact("main.py", best_code)]
        )
        final_validation = await self.validator.validate(final_execution)
        
        success = final_validation.passed and final_validation.score >= self.config.validation_score_threshold
        
        return TaskResult(
            success=success,
            code=best_code,
            iterations=iteration,
            validation_score=final_validation.score,
            reflection=last_reflection,
            node_id=current_node.id,
            session_id=self.session.session_id,
            error=None if success else f"Failed after {iteration} iterations. Score: {final_validation.score:.1f}",
        )
    
    # ============ 核心方法 ============
    
    async def _generate_code(
        self,
        description: str,
        requirements: List[str],
        node: SessionNode,
        iteration: int = 1,
    ) -> Dict[str, str]:
        """生成代码"""
        # 构建上下文
        context = self._build_context(node)
        
        # 迭代提示词
        iteration_hint = ""
        if iteration > 1:
            iteration_hint = f"\n(This is iteration {iteration}. Previous attempts had issues that need to be fixed.)"
        
        user_prompt = f"""Write Python code for:

{description}{iteration_hint}

Requirements:
{chr(10).join(f"- {r}" for r in requirements)}

Available tools:
- read(path, offset?, limit?): Read file contents
- write(path, content): Write to file
- edit(path, old_text, new_text): Edit file
- bash(command): Execute shell command

Guidelines:
- Include proper error handling (try/except)
- Add docstrings to functions and classes
- Follow Python best practices
- Make code production-ready

{context}

Generate complete, runnable Python code:
"""
        
        # 调用 LLM
        code = await self._call_llm(user_prompt)
        
        # 生成文档
        doc_prompt = f"""Write a brief description (2-3 sentences) of what this code does:

```python
{code[:500]}
```"""
        docs = await self._call_llm(doc_prompt) if self.llm else "No documentation available"
        
        return {
            "code": self._clean_code(code),
            "docs": docs.strip(),
        }
    
    async def _fix_code(self, code: str, error: str, node: SessionNode) -> str:
        """修复代码（简单版本）"""
        prompt = f"""Fix this Python code:

```python
{code}
```

Error: {error}

Provide fixed code only:
"""
        fixed = await self._call_llm(prompt)
        return self._clean_code(fixed)
    
    async def _fix_code_with_context(self, code: str, context: Dict) -> str:
        """使用完整上下文修复代码"""
        errors_text = "\n".join(f"- {e}" for e in context.get("errors", []))
        warnings_text = "\n".join(f"- {w}" for w in context.get("warnings", []))
        suggestions_text = "\n".join(f"- {s}" for s in context.get("suggestions", []))
        
        prompt = f"""Fix this Python code based on validation results:

```python
{code}
```

Errors:
{errors_text}

Warnings:
{warnings_text}

Suggestions:
{suggestions_text}

Fix ALL issues and return complete code:
"""
        fixed = await self._call_llm(prompt)
        return self._clean_code(fixed)
    
    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        if not self.llm:
            return "# TODO: LLM not available"
        
        try:
            if hasattr(self.llm, 'complete'):
                return await self.llm.complete(prompt)
            elif hasattr(self.llm, 'chat'):
                return await self.llm.chat([{"role": "user", "content": prompt}])
            else:
                return "# TODO: LLM interface not supported"
        except Exception as e:
            self._log(f"LLM call failed: {e}")
            return "# TODO: LLM call failed"
    
    def _validate_python(self, code: str) -> tuple[bool, Optional[str]]:
        """简单语法验证"""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
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


# 保持向后兼容
KodaAgent = KodaAgentV2
