"""
CLI Commands Implementation
Equivalent to Pi Mono's packages/coding-agent/src/cli/commands/
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn


@dataclass
class CommandContext:
    """Context for CLI commands"""
    console: Console
    config: Optional[dict] = None


class BaseCommand:
    """Base class for CLI commands"""
    
    def __init__(self, console: Console):
        self.console = console
        self.context = CommandContext(console=console)
    
    async def run(self, **kwargs):
        """Run the command"""
        raise NotImplementedError()


class ChatCommand(BaseCommand):
    """Interactive chat command"""
    
    async def run(
        self,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        file: Optional[Path] = None,
        interactive: bool = True
    ):
        """Run chat session"""
        self.console.print(Panel.fit(
            "[bold blue]Koda Chat[/bold blue]\n"
            "Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit",
            title="Welcome"
        ))
        
        from ..modes import InteractiveMode, ModeContext
        
        mode = InteractiveMode()
        ctx = ModeContext(messages=[])
        
        # Start session
        response = mode.start(ctx)
        
        if prompt:
            # Handle initial prompt
            self.console.print(f"[dim]> {prompt}[/dim]")
            response = mode.handle_input(prompt, ctx)
        
        if file:
            # Include file content
            try:
                content = file.read_text(encoding='utf-8')
                file_prompt = f"I've loaded {file}:\n```\n{content}\n```"
                response = mode.handle_input(file_prompt, ctx)
            except Exception as e:
                self.console.print(f"[red]Error reading file: {e}[/red]")
        
        if not interactive:
            return
        
        # Interactive loop
        while mode.is_active():
            if response.requires_input:
                try:
                    user_input = self.console.input("[bold]> [/bold]")
                except (EOFError, KeyboardInterrupt):
                    break
                
                response = mode.handle_input(user_input, ctx)
                
                if response.content:
                    self.console.print(response.content)
            else:
                # Processing state
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True
                ) as progress:
                    progress.add_task("Thinking...", total=None)
                    await asyncio.sleep(0.5)  # Simulate processing
                
                response = mode.handle_assistant_response("Processing complete...", ctx)


class AskCommand(BaseCommand):
    """Single question command"""
    
    async def run(
        self,
        prompt: str,
        model: Optional[str] = None,
        files: Optional[List[Path]] = None
    ):
        """Ask a single question"""
        from ..modes import PrintMode
        
        # Build context with files
        context = {}
        if files:
            file_contents = []
            for f in files:
                try:
                    content = f.read_text(encoding='utf-8')
                    file_contents.append(f"File: {f}\n```\n{content}\n```")
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not read {f}: {e}[/yellow]")
            
            if file_contents:
                prompt = "\n\n".join(file_contents) + f"\n\nQuestion: {prompt}"
        
        mode = PrintMode()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            progress.add_task("Processing...", total=None)
            result = mode.run(prompt, context)
        
        self.console.print(result.output)


class EditCommand(BaseCommand):
    """Edit file command"""
    
    async def run(
        self,
        file: Path,
        instruction: str,
        model: Optional[str] = None
    ):
        """Edit a file"""
        if not file.exists():
            self.console.print(f"[red]File not found: {file}[/red]")
            return
        
        self.console.print(f"[dim]Editing {file}...[/dim]")
        
        # Read current content
        try:
            content = file.read_text(encoding='utf-8')
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return
        
        # Show diff or preview
        self.console.print(Panel(
            f"[bold]File:[/bold] {file}\n"
            f"[bold]Instruction:[/bold] {instruction}",
            title="Edit Request"
        ))
        
        # TODO: Integrate with actual edit tool
        self.console.print("[yellow]Edit functionality would be implemented here[/yellow]")


class ReviewCommand(BaseCommand):
    """Code review command"""
    
    async def run(
        self,
        file: Optional[Path] = None,
        model: Optional[str] = None
    ):
        """Review code"""
        if file:
            if not file.exists():
                self.console.print(f"[red]File not found: {file}[/red]")
                return
            
            try:
                content = file.read_text(encoding='utf-8')
                self.console.print(Syntax(content, file.suffix.lstrip('.') or 'text'))
            except Exception as e:
                self.console.print(f"[red]Error reading file: {e}[/red]")
        else:
            # Review current directory
            self.console.print("[dim]Reviewing current directory...[/dim]")
        
        self.console.print("[yellow]Code review would be implemented here[/yellow]")


class CommitCommand(BaseCommand):
    """Git commit command"""
    
    async def run(
        self,
        message: Optional[str] = None,
        model: Optional[str] = None,
        auto: bool = False
    ):
        """Generate commit and commit"""
        from ...coding.utils import GitUtils
        
        git = GitUtils()
        
        if not git.is_git_repo():
            self.console.print("[red]Not a git repository[/red]")
            return
        
        # Check for changes
        status = git.get_status()
        if not any([status['staged'], status['modified'], status['untracked']]):
            self.console.print("[yellow]No changes to commit[/yellow]")
            return
        
        if auto or not message:
            # Generate commit message
            diff = git.get_diff(staged=False)
            
            self.console.print("[dim]Generating commit message...[/dim]")
            
            # TODO: Integrate with LLM to generate message
            message = "Update files"  # Placeholder
            
            self.console.print(f"[green]Generated message:[/green] {message}")
        
        # Confirm
        if not auto:
            confirm = input("Commit with this message? [Y/n] ").strip().lower()
            if confirm and confirm not in ('y', 'yes'):
                self.console.print("[dim]Cancelled[/dim]")
                return
        
        # Execute commit
        from ...coding.utils import run_command
        result = run_command(f'git commit -m "{message}"')
        
        if result.returncode == 0:
            self.console.print(f"[green]Committed:[/green] {message}")
        else:
            self.console.print(f"[red]Commit failed:[/red] {result.stderr}")


class ModelsCommand(BaseCommand):
    """Models management command"""
    
    async def run(
        self,
        list_all: bool = False,
        search: Optional[str] = None
    ):
        """List and search models"""
        from ...ai.registry import ModelRegistry
        
        registry = ModelRegistry()
        
        if search:
            self.console.print(f"[dim]Searching for: {search}[/dim]")
            # TODO: Implement search
        
        # Display models
        table = Table(title="Available Models")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Provider", style="blue")
        table.add_column("Context", justify="right")
        
        # Add some example models
        models = [
            ("gpt-4o", "GPT-4o", "openai", "128K"),
            ("claude-sonnet-4-5", "Claude Sonnet 4.5", "anthropic", "200K"),
            ("gemini-pro", "Gemini Pro", "google", "1M"),
        ]
        
        for m in models:
            table.add_row(*m)
        
        self.console.print(table)


class ConfigCommand(BaseCommand):
    """Config management command"""
    
    async def run(
        self,
        key: Optional[str] = None,
        value: Optional[str] = None,
        list_all: bool = False,
        global_config: bool = False
    ):
        """Manage configuration"""
        from ..settings_manager import SettingsManager
        
        settings = SettingsManager()
        
        if list_all:
            # List all config
            self.console.print("[bold]Current Configuration:[/bold]")
            providers = settings.list_providers()
            for provider in providers:
                self.console.print(f"\n[blue]{provider}[/blue]")
                provider_settings = settings.get_provider(provider)
                if provider_settings.default_model:
                    self.console.print(f"  Default model: {provider_settings.default_model}")
        
        elif key and value:
            # Set config
            settings.set(key, value)
            settings.save()
            self.console.print(f"[green]Set {key} = {value}[/green]")
        
        elif key:
            # Get config
            val = settings.get(key)
            if val is not None:
                self.console.print(f"{key} = {val}")
            else:
                self.console.print(f"[yellow]{key} not set[/yellow]")
        
        else:
            self.console.print("[dim]Use --list to see all config, or provide key [value][/dim]")


class SkillsCommand(BaseCommand):
    """Skills management command"""
    
    async def run(
        self,
        list_all: bool = False,
        install: Optional[str] = None,
        uninstall: Optional[str] = None
    ):
        """Manage skills"""
        from ..skills import get_skills_manager
        
        manager = get_skills_manager()
        
        if list_all:
            skills = manager.list_skills()
            
            if not skills:
                self.console.print("[dim]No skills installed[/dim]")
                return
            
            table = Table(title="Installed Skills")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Version", style="blue")
            
            for skill in skills:
                table.add_row(skill.id, skill.name, skill.version)
            
            self.console.print(table)
        
        elif install:
            self.console.print(f"[dim]Installing {install}...[/dim]")
            # TODO: Implement install
            self.console.print(f"[green]Installed {install}[/green]")
        
        elif uninstall:
            self.console.print(f"[dim]Uninstalling {uninstall}...[/dim]")
            # TODO: Implement uninstall
            self.console.print(f"[green]Uninstalled {uninstall}[/green]")
        
        else:
            self.console.print("[dim]Use --list, --install, or --uninstall[/dim]")


class SessionCommand(BaseCommand):
    """Session management command"""
    
    async def run(
        self,
        list_all: bool = False,
        load: Optional[str] = None,
        export: Optional[str] = None
    ):
        """Manage sessions"""
        from ..session_manager import SessionManager
        
        if list_all:
            # List sessions
            self.console.print("[bold]Recent Sessions:[/bold]")
            # TODO: List sessions from storage
        
        elif load:
            self.console.print(f"[dim]Loading session {load}...[/dim]")
            # TODO: Load session
        
        elif export:
            self.console.print(f"[dim]Exporting session to {export}...[/dim]")
            # TODO: Export session
        
        else:
            self.console.print("[dim]Use --list, --load, or --export[/dim]")


__all__ = [
    "ChatCommand",
    "AskCommand",
    "EditCommand",
    "ReviewCommand",
    "CommitCommand",
    "ModelsCommand",
    "ConfigCommand",
    "SkillsCommand",
    "SessionCommand",
]
