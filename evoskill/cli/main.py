"""
EvoSkill CLI

命令行界面入口
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 修复 Windows 编码问题
import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from evoskill.core.session import AgentSession
from evoskill.core.llm import LLMConfig
from evoskill.core.types import EventType
from evoskill.skills.builtin import register_builtin_tools
from evoskill.skills.loader import SkillLoader, create_default_skill
from evoskill.evolution.engine import SkillEvolutionEngine
from evoskill.config import (
    get_config,
    save_config,
    init_config,
    get_config_path,
    EvoSkillConfig,
)

app = typer.Typer(
    name="evoskill",
    help="EvoSkill - 会造工具的 AI 对话系统",
    rich_markup_mode="rich",
)

console = Console()


def get_llm_config_from_settings(settings: Optional[EvoSkillConfig] = None) -> LLMConfig:
    """从设置创建 LLM 配置"""
    if settings is None:
        settings = get_config()
    
    return LLMConfig(
        provider=settings.provider,
        model=settings.model,
        api_key=settings.get_api_key(),
        base_url=settings.base_url,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        thinking_level=settings.thinking_level,
        headers=settings.headers,
    )


@app.command()
def chat(
    workspace: Optional[Path] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="工作目录",
    ),
    skills_dir: Optional[Path] = typer.Option(
        None,
        "--skills-dir",
        "-s",
        help="Skills 目录",
    ),
):
    """
    启动交互式对话模式
    
    示例:
        evoskill chat
        evoskill chat -w ./my-project
    """
    asyncio.run(_chat_async(workspace, skills_dir))


async def _chat_async(workspace: Optional[Path], skills_dir: Optional[Path]):
    """异步聊天主循环"""
    settings = get_config()
    
    # 检查 API key
    if not settings.get_api_key():
        console.print("[red]错误: 未配置 API Key[/red]")
        console.print("\n请通过以下方式之一配置：")
        console.print("  1. 环境变量: export EVOSKILL_API_KEY=your-key")
        console.print("  2. 配置文件: evoskill config --init && evoskill config --edit")
        raise typer.Exit(1)
    
    # 设置工作区和 Skills 目录
    if workspace:
        settings.workspace = workspace
    if skills_dir:
        settings.skills_dir = skills_dir
    
    # 确保目录存在
    settings.skills_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建 LLM 配置
    llm_config = get_llm_config_from_settings(settings)
    
    # 创建会话
    session = AgentSession(
        workspace=settings.workspace,
        llm_config=llm_config,
    )
    
    # 注册内置工具
    register_builtin_tools(session)
    
    # 加载现有 Skills
    skill_loader = SkillLoader(settings.skills_dir)
    loaded_skills = skill_loader.load_all_skills()
    for skill in loaded_skills:
        session.register_skill(skill)
    
    # 准备现有 skills 信息（用于匹配）
    existing_skills_info = [
        {
            "name": skill.name,
            "description": skill.description,
            "tools": [{"name": t.name, "description": t.description} for t in skill.tools],
        }
        for skill in loaded_skills
    ]
    
    # 创建进化引擎
    evolution = SkillEvolutionEngine(
        llm_provider=session.llm_provider,
        skills_dir=settings.skills_dir,
    )
    
    # 欢迎信息
    console.print(Panel.fit(
        f"[bold blue]EvoSkill[/bold blue] - 会造工具的 AI 助手\n"
        f"工作目录: [green]{settings.workspace}[/green]\n"
        f"已加载 Skills: [yellow]{len(loaded_skills)}[/yellow]\n"
        f"模型: [cyan]{settings.model}[/cyan]\n"
        f"提供商: [cyan]{settings.provider}[/cyan]\n"
        f"\n[dim]提示: 输入 /help 查看命令，/exit 退出[/dim]",
        title="[bold blue]欢迎使用 EvoSkill[/bold blue]",
    ))
    
    # 主循环
    while True:
        try:
            user_input = console.input("[bold blue]You[/bold blue]: ").strip()
            
            if not user_input:
                continue
            
            # 处理命令
            if user_input.startswith("/"):
                cmd = user_input[1:].lower()
                
                if cmd == "exit" or cmd == "quit":
                    console.print("[dim]再见！[/dim]")
                    break
                
                elif cmd == "help":
                    _show_help()
                    continue
                
                elif cmd == "skills":
                    _show_skills(skill_loader)
                    continue
                
                elif cmd == "clear":
                    session.clear_history()
                    console.print("[dim]对话历史已清空[/dim]")
                    continue
                
                elif cmd.startswith("create "):
                    skill_name = cmd[7:].strip()
                    if skill_name:
                        await _create_skill(evolution, skill_name, existing_skills_info)
                    continue
                
                else:
                    console.print(f"[red]未知命令: /{cmd}[/red]")
                    continue
            
            # 检查是否需要进化
            if evolution.should_evolve(user_input, skill_loader.list_skills()):
                console.print("[yellow]检测到新需求，正在创建 Skill...[/yellow]")
                
                async for event in evolution.evolve(
                    user_input,
                    available_skills=skill_loader.list_skills()
                ):
                    if event.type == EventType.SKILL_CREATED:
                        data = event.data
                        if data.get("step") == "deploy" and data.get("status") == "completed":
                            console.print(f"[green][OK] Skill '{data['skill_name']}' 已创建！[/green]")
                            # 重新加载 Skills
                            loaded_skills = skill_loader.load_all_skills()
                            for skill in loaded_skills:
                                if skill.name == data['skill_name']:
                                    session.register_skill(skill)
                        elif data.get("step") == "error":
                            console.print(f"[red][ERROR] {data.get('message')}[/red]")
            
            # 处理用户输入
            console.print(f"[bold green]EvoSkill[/bold green]: ", end="")
            
            async for event in session.prompt(user_input):
                if event.type == EventType.TEXT_DELTA:
                    console.print(event.data.get("content", ""), end="")
                elif event.type == EventType.TOOL_EXECUTION_START:
                    tool_name = event.data.get("tool_name", "")
                    console.print(f"\n[dim]▶ 使用工具: {tool_name}[/dim]")
                elif event.type == EventType.TOOL_EXECUTION_END:
                    if event.data.get("is_error"):
                        console.print(f"[red][ERROR] 工具执行失败[/red]")
                    else:
                        console.print(f"[dim][DONE] 工具执行完成[/dim]")
                elif event.type == EventType.CONTEXT_WARNING:
                    # 上下文警告（75% 阈值）
                    message = event.data.get("message", "")
                    if message:
                        console.print(f"\n[yellow][!] {message}[/yellow]")
                elif event.type == EventType.CONTEXT_COMPACTED:
                    # 上下文已压缩（80% 阈值）
                    original = event.data.get("original_tokens", 0)
                    new = event.data.get("new_tokens", 0)
                    saved = event.data.get("saved_ratio", 0) * 100
                    count = event.data.get("compacted_count", 0)
                    console.print(
                        f"\n[dim][↻] 上下文已压缩: "
                        f"{original}→{new} tokens (-{saved:.1f}%), "
                        f"合并 {count} 条消息[/dim]"
                    )
            
            console.print()  # 换行
        
        except KeyboardInterrupt:
            console.print("\n[dim]再见！[/dim]")
            break
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


def _show_help():
    """显示帮助信息"""
    table = Table(title="可用命令")
    table.add_column("命令", style="cyan")
    table.add_column("说明", style="green")
    
    commands = [
        ("/help", "显示此帮助"),
        ("/exit, /quit", "退出程序"),
        ("/skills", "显示已加载的 Skills"),
        ("/clear", "清空对话历史"),
        ("/create <name>", "创建新 Skill"),
    ]
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    
    console.print(table)


def _show_skills(loader: SkillLoader):
    """显示已加载的 Skills"""
    skills = loader.load_all_skills()
    
    if not skills:
        console.print("[dim]尚未加载任何 Skills[/dim]")
        return
    
    table = Table(title=f"已加载 Skills ({len(skills)})")
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="green")
    table.add_column("工具数", style="yellow")
    
    for skill in skills:
        table.add_row(
            skill.name,
            skill.description[:50] + "..." if len(skill.description) > 50 else skill.description,
            str(len(skill.tools))
        )
    
    console.print(table)


async def _create_skill(engine: SkillEvolutionEngine, description: str, existing_skills: list):
    """创建新 Skill"""
    console.print(f"[yellow]正在分析需求: {description}[/yellow]")
    
    current_stage = ""
    
    async for event in engine.evolve(description, existing_skills):
        if event.type == EventType.SKILL_CREATED:
            data = event.data
            status = data.get("status", "")
            
            # 显示进度
            if status == "analyzing":
                console.print("[dim]  → 正在分析需求...[/dim]")
            elif status == "matching":
                console.print("[dim]  → 正在匹配现有 Skills...[/dim]")
            elif status == "reused":
                console.print(f"[green]✓ 使用现有 Skill: {data.get('skill_name')}[/green]")
                console.print(f"[dim]   原因: {data.get('match_reason', '')}[/dim]")
                return
            elif status == "designing":
                console.print("[dim]  → 正在设计新 Skill...[/dim]")
            elif status == "designed":
                skill_name = data.get('skill_name')
                tools = data.get('tools', [])
                console.print(f"[green]✓ 设计完成: {skill_name}[/green]")
                console.print(f"[dim]   包含工具: {', '.join(tools)}[/dim]")
            elif status == "generating":
                console.print("[dim]  → 正在生成代码...[/dim]")
            elif status == "generated":
                files = data.get('files', [])
                console.print(f"[green]✓ 代码生成完成[/green]")
                console.print(f"[dim]   文件: {', '.join(files)}[/dim]")
            elif status == "validating":
                console.print("[dim]  → 正在验证代码...[/dim]")
            elif status == "validated":
                if data.get('valid'):
                    console.print("[green]✓ 验证通过[/green]")
                else:
                    console.print("[yellow]⚠ 验证警告[/yellow]")
                    if data.get('errors'):
                        for error in data.get('errors'):
                            console.print(f"[red]   - {error}[/red]")
            elif status == "integrating":
                console.print("[dim]  → 正在集成到系统...[/dim]")
            elif status == "completed":
                skill_name = data.get('skill_name')
                tools = data.get('tools', [])
                console.print(f"[green]✅ Skill '{skill_name}' 创建完成并激活！[/green]")
                console.print(f"[dim]   可用工具: {', '.join(tools)}[/dim]")
                console.print(f"[dim]   现在可以直接使用这些工具了[/dim]")
            elif status == "failed":
                console.print(f"[red]❌ 创建失败: {data.get('message', '')}[/red]")
            elif status == "warning":
                console.print(f"[yellow]⚠ {data.get('message', '')}[/yellow]")


@app.command()
def create(
    name: str = typer.Argument(..., help="Skill 名称"),
    description: str = typer.Option(
        "",
        "--description",
        "-d",
        help="Skill 描述",
    ),
    skills_dir: Optional[Path] = typer.Option(
        None,
        "--skills-dir",
        "-s",
        help="Skills 目录",
    ),
):
    """
    创建一个新的 Skill 模板
    
    示例:
        evoskill create my-skill -d "我的自定义 Skill"
    """
    workspace = Path.cwd()
    skills_dir = skills_dir or workspace / ".evoskill" / "skills"
    skill_path = skills_dir / name
    
    if skill_path.exists():
        console.print(f"[red]错误: Skill '{name}' 已存在[/red]")
        raise typer.Exit(1)
    
    create_default_skill(skill_path, name, description or f"{name} Skill")
    console.print(f"[green][OK] 创建成功: {skill_path}[/green]")


@app.command()
def list_skills(
    skills_dir: Optional[Path] = typer.Option(
        None,
        "--skills-dir",
        "-s",
        help="Skills 目录",
    ),
):
    """
    列出所有可用的 Skills
    
    示例:
        evoskill list
    """
    workspace = Path.cwd()
    skills_dir = skills_dir or workspace / ".evoskill" / "skills"
    
    if not skills_dir.exists():
        console.print("[dim]Skills 目录不存在[/dim]")
        return
    
    loader = SkillLoader(skills_dir)
    skills = loader.load_all_skills()
    
    if not skills:
        console.print("[dim]没有找到 Skills[/dim]")
        return
    
    table = Table(title="可用 Skills")
    table.add_column("名称", style="cyan")
    table.add_column("版本", style="yellow")
    table.add_column("描述", style="green")
    
    for skill in skills:
        table.add_row(
            skill.name,
            skill.metadata.version,
            skill.description[:40] + "..." if len(skill.description) > 40 else skill.description,
        )
    
    console.print(table)


@app.command()
def config(
    init: bool = typer.Option(
        False,
        "--init",
        help="初始化配置文件",
    ),
):
    """
    管理 EvoSkill 配置
    
    配置文件位置:
      - Linux/Mac: ~/.config/evoskill/config.yaml
      - Windows: ~/AppData/Local/evoskill/config.yaml
    
    示例:
        evoskill config              # 显示当前配置和配置文件路径
        evoskill config --init       # 创建默认配置文件
    """
    config_file = get_config_path()
    
    if init:
        init_config()
        console.print(f"[green][OK] 配置文件已创建[/green]")
        console.print(f"[cyan]配置文件路径:[/cyan] {config_file}")
        console.print("\n[dim]请用文本编辑器打开上述文件，修改配置后保存[/dim]")
        console.print("[dim]建议至少设置: provider, model, api_key, base_url[/dim]")
        return
    
    # 显示当前配置
    cfg = get_config()
    
    table = Table(title="当前配置")
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("Provider", cfg.provider)
    table.add_row("Model", cfg.model)
    table.add_row("Base URL", cfg.base_url or "[dim]默认[/dim]")
    table.add_row("API Key", "***" if cfg.get_api_key() else "[red]未设置[/red]")
    table.add_row("Temperature", str(cfg.temperature))
    table.add_row("Max Context", f"{cfg.max_context_tokens} tokens")
    table.add_row("Workspace", str(cfg.workspace))
    table.add_row("Skills Dir", str(cfg.skills_dir))
    
    console.print(table)
    
    # 显示配置文件状态
    console.print(f"\n[cyan]配置文件路径:[/cyan] {config_file}")
    if config_file.exists():
        console.print("[green][OK] 配置文件已存在[/green]")
    else:
        console.print("[yellow][MISSING] 配置文件不存在[/yellow]")
    
    console.print("\n[dim]配置优先级: 环境变量 > 配置文件 > 默认值[/dim]")
    console.print("[dim]环境变量: EVOSKILL_PROVIDER, EVOSKILL_MODEL, EVOSKILL_API_KEY, ...[/dim]")
    console.print("\n[dim]提示: 运行 `evoskill config --init` 创建默认配置文件[/dim]")


if __name__ == "__main__":
    app()
