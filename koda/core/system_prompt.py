"""
System Prompt Builder - 系统提示词构建器

参考 Pi Coding Agent 的实现，动态构建系统提示词。
支持：
- 根据工具动态生成使用指南
- 自定义提示词
- 上下文文件注入
- Skills 注入
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


# 工具描述
TOOL_DESCRIPTIONS: Dict[str, str] = {
    "read": "Read the contents of a file. Supports text files. Use offset/limit to read partial content.",
    "write": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Automatically creates parent directories.",
    "edit": "Edit a file by replacing exact text. The old_text must match exactly (including whitespace and indentation). Use this for precise, surgical edits.",
    "bash": "Execute bash commands in the current working directory. Use for file operations, running scripts, installing packages, etc.",
    "grep": "Search file contents for patterns using regular expressions. Respects .gitignore.",
    "find": "Find files by name pattern. Respects .gitignore.",
    "ls": "List directory contents.",
}


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    content: str


@dataclass
class ContextFile:
    """上下文文件"""
    path: str
    content: str


@dataclass
class SystemPromptOptions:
    """系统提示词选项"""
    # 完全替换默认提示词
    custom_prompt: Optional[str] = None
    
    # 选中的工具（默认全部）
    selected_tools: Optional[List[str]] = None
    
    # 追加到提示词末尾的内容
    append_prompt: Optional[str] = None
    
    # 上下文文件（如 AGENTS.md）
    context_files: List[ContextFile] = field(default_factory=list)
    
    # 技能列表
    skills: List[Skill] = field(default_factory=list)
    
    # 当前工作目录
    cwd: Optional[str] = None
    
    # 框架文档路径（用于扩展自我改进时参考）
    docs_path: Optional[str] = None


class SystemPromptBuilder:
    """
    系统提示词构建器
    
    动态构建适合当前任务和可用工具的系统提示词。
    """
    
    def __init__(self, options: SystemPromptOptions):
        self.options = options
    
    def build(self) -> str:
        """
        构建系统提示词
        
        Returns:
            完整的系统提示词
        """
        # 如果提供了自定义提示词，使用它
        if self.options.custom_prompt:
            return self._build_custom()
        
        # 否则构建默认提示词
        return self._build_default()
    
    def _build_default(self) -> str:
        """构建默认系统提示词"""
        parts = []
        
        # 1. 基础身份描述
        parts.append(self._get_base_description())
        
        # 2. 可用工具列表
        parts.append(self._get_tools_section())
        
        # 3. 使用指南（根据工具动态生成）
        parts.append(self._get_guidelines_section())
        
        # 4. 框架文档引用（用于自扩展）
        if self.options.docs_path:
            parts.append(self._get_docs_section())
        
        # 5. 项目上下文
        if self.options.context_files:
            parts.append(self._get_context_section())
        
        # 6. Skills
        if self.options.skills:
            parts.append(self._get_skills_section())
        
        # 7. 时间和环境信息
        parts.append(self._get_environment_section())
        
        # 8. 追加内容
        if self.options.append_prompt:
            parts.append(self.options.append_prompt)
        
        return "\n\n".join(parts)
    
    def _build_custom(self) -> str:
        """使用自定义提示词构建"""
        prompt = self.options.custom_prompt
        
        # 添加上下文文件
        if self.options.context_files:
            prompt += "\n\n# Project Context\n\n"
            for cf in self.options.context_files:
                prompt += f"## {cf.path}\n\n{cf.content}\n\n"
        
        # 添加 Skills
        if self.options.skills and self.options.selected_tools and "read" in self.options.selected_tools:
            prompt += self._get_skills_section()
        
        # 添加环境信息
        prompt += f"\n\nCurrent date and time: {self._get_datetime()}"
        prompt += f"\nCurrent working directory: {self.options.cwd or Path.cwd()}"
        
        # 追加内容
        if self.options.append_prompt:
            prompt += f"\n\n{self.options.append_prompt}"
        
        return prompt
    
    def _get_base_description(self) -> str:
        """获取基础身份描述"""
        return """You are an expert coding assistant operating inside Koda, an autonomous coding agent framework. You help users by reading files, executing commands, editing code, writing new files, and generating tools.

Your core philosophy: "If you need a capability, don't ask for it - write code to achieve it." You can extend yourself by writing new tools and extensions."""
    
    def _get_tools_section(self) -> str:
        """获取工具列表部分"""
        tools = self.options.selected_tools or ["read", "bash", "edit", "write"]
        
        lines = ["Available tools:"]
        for tool in tools:
            desc = TOOL_DESCRIPTIONS.get(tool, f"Tool: {tool}")
            lines.append(f"- {tool}: {desc}")
        
        lines.append("\nYou may also have access to custom tools depending on the project.")
        
        return "\n".join(lines)
    
    def _get_guidelines_section(self) -> str:
        """获取使用指南（根据工具动态生成）"""
        tools = self.options.selected_tools or ["read", "bash", "edit", "write"]
        guidelines = []
        
        has_bash = "bash" in tools
        has_grep = "grep" in tools
        has_find = "find" in tools
        has_ls = "ls" in tools
        has_read = "read" in tools
        has_edit = "edit" in tools
        has_write = "write" in tools
        
        # Bash 相关
        if has_bash and not (has_grep or has_find or has_ls):
            guidelines.append("Use bash for file operations like ls, grep, find")
        elif has_bash and (has_grep or has_find or has_ls):
            guidelines.append("Prefer grep/find/ls tools over bash for file exploration (faster, respects .gitignore)")
        
        # Read 相关
        if has_read and has_edit:
            guidelines.append("Use read to examine files before editing. You must use this tool instead of cat or sed.")
        
        # Edit 相关
        if has_edit:
            guidelines.append("Use edit for precise changes (old_text must match exactly including whitespace)")
        
        # Write 相关
        if has_write:
            guidelines.append("Use write only for new files or complete rewrites")
        
        # 通用
        if has_edit or has_write:
            guidelines.append("When summarizing your actions, output plain text directly - do NOT use cat or bash to display what you did")
        
        guidelines.append("Be concise in your responses")
        guidelines.append("Show file paths clearly when working with files")
        guidelines.append("Think step by step, but keep the thought process internal")
        
        # 自扩展相关
        guidelines.append("If you need a tool that doesn't exist, consider writing it yourself")
        
        lines = ["Guidelines:"]
        for g in guidelines:
            lines.append(f"- {g}")
        
        return "\n".join(lines)
    
    def _get_docs_section(self) -> str:
        """获取文档引用部分"""
        docs_path = self.options.docs_path or "./docs"
        return f"""Koda documentation (read only when the user asks about Koda itself, extensions, or framework internals):
- Main documentation: {docs_path}/README.md
- API reference: {docs_path}/API.md
- Architecture: {docs_path}/ARCHITECTURE.md
- Tutorial: {docs_path}/TUTORIAL.md

When working on Koda topics, read the docs and follow cross-references before implementing."""
    
    def _get_context_section(self) -> str:
        """获取项目上下文部分"""
        lines = ["# Project Context", ""]
        lines.append("Project-specific instructions and guidelines:")
        lines.append("")
        
        for cf in self.options.context_files:
            lines.append(f"## {cf.path}")
            lines.append("")
            lines.append(cf.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_skills_section(self) -> str:
        """获取 Skills 部分"""
        lines = ["# Skills", ""]
        lines.append("When relevant, follow these skill instructions:")
        lines.append("")
        
        for skill in self.options.skills:
            lines.append(f"## {skill.name}")
            lines.append("")
            lines.append(f"Use when: {skill.description}")
            lines.append("")
            lines.append(skill.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_environment_section(self) -> str:
        """获取环境信息部分"""
        return f"""Current date and time: {self._get_datetime()}
Current working directory: {self.options.cwd or Path.cwd()}"""
    
    def _get_datetime(self) -> str:
        """获取格式化的日期时间"""
        return datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
    
    # ============ 便捷构造方法 ============
    
    @classmethod
    def for_task(
        cls,
        task_description: str,
        tools: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> "SystemPromptBuilder":
        """
        为特定任务创建提示词构建器
        
        Args:
            task_description: 任务描述
            tools: 可用工具列表
            cwd: 工作目录
        """
        options = SystemPromptOptions(
            selected_tools=tools,
            append_prompt=f"\nYour current task: {task_description}",
            cwd=cwd,
        )
        return cls(options)
    
    @classmethod
    def for_extension_writing(
        cls,
        extension_capability: str,
        cwd: Optional[str] = None,
    ) -> "SystemPromptBuilder":
        """
        为扩展编写任务创建提示词构建器
        
        Args:
            extension_capability: 扩展能力描述
            cwd: 工作目录
        """
        docs_path = Path(__file__).parent.parent / "docs"
        
        options = SystemPromptOptions(
            selected_tools=["read", "write", "edit", "bash"],
            append_prompt=f"""
You are writing a Koda extension to enable: {extension_capability}

Extension requirements:
1. Create a Python class with an async execute() method
2. Handle errors gracefully
3. Return dict with 'success' and 'result' or 'error'
4. Include docstrings
5. Be self-contained

Read the Koda documentation before implementing.""",
            cwd=cwd,
            docs_path=str(docs_path),
        )
        return cls(options)
    
    @classmethod
    def with_agents_md(
        cls,
        agents_md_path: Path,
        tools: Optional[List[str]] = None,
    ) -> "SystemPromptBuilder":
        """
        加载 AGENTS.md 作为上下文
        
        Args:
            agents_md_path: AGENTS.md 文件路径
            tools: 可用工具列表
        """
        context_files = []
        
        if agents_md_path.exists():
            content = agents_md_path.read_text(encoding='utf-8')
            context_files.append(ContextFile(
                path="AGENTS.md",
                content=content,
            ))
        
        options = SystemPromptOptions(
            selected_tools=tools,
            context_files=context_files,
            cwd=str(agents_md_path.parent),
        )
        return cls(options)
