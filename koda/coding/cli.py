"""
CLI Entry Point
Equivalent to Pi Mono's packages/coding-agent/src/cli.ts

Command-line interface for the coding agent.
"""
import sys
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .. import __version__

# Create CLI app
app = typer.Typer(
    name="koda",
    help="Koda Coding Agent - AI-powered coding assistant",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Verbose output"),
):
    """Koda Coding Agent CLI"""
    if version:
        console.print(f"Koda version {__version__}")
        raise typer.Exit()


@app.command()
def chat(
    prompt: Optional[str] = typer.Argument(None, help="Initial prompt"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to include"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i/-I", help="Interactive mode"),
):
    """Start a chat session with the AI"""
    from .cli.commands import ChatCommand
    
    cmd = ChatCommand(console=console)
    asyncio.run(cmd.run(
        prompt=prompt,
        model=model,
        file=file,
        interactive=interactive
    ))


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="Question to ask"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    files: Optional[list[Path]] = typer.Option(None, "--file", "-f", help="Files to include"),
):
    """Ask a single question (non-interactive)"""
    from .cli.commands import AskCommand
    
    cmd = AskCommand(console=console)
    asyncio.run(cmd.run(prompt=prompt, model=model, files=files))


@app.command()
def edit(
    file: Path = typer.Argument(..., help="File to edit"),
    instruction: str = typer.Argument(..., help="Edit instruction"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Edit a file based on instructions"""
    from .cli.commands import EditCommand
    
    cmd = EditCommand(console=console)
    asyncio.run(cmd.run(file=file, instruction=instruction, model=model))


@app.command()
def review(
    file: Optional[Path] = typer.Argument(None, help="File to review"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Review code for issues"""
    from .cli.commands import ReviewCommand
    
    cmd = ReviewCommand(console=console)
    asyncio.run(cmd.run(file=file, model=model))


@app.command()
def commit(
    message: Optional[str] = typer.Argument(None, help="Commit message (optional)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Auto-generate message"),
):
    """Generate commit message and commit changes"""
    from .cli.commands import CommitCommand
    
    cmd = CommitCommand(console=console)
    asyncio.run(cmd.run(message=message, model=model, auto=auto))


@app.command()
def models(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all models"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search models"),
):
    """Manage and list available models"""
    from .cli.commands import ModelsCommand
    
    cmd = ModelsCommand(console=console)
    asyncio.run(cmd.run(list_all=list_all, search=search))


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all config"),
    global_config: bool = typer.Option(False, "--global", "-g", help="Use global config"),
):
    """Manage configuration"""
    from .cli.commands import ConfigCommand
    
    cmd = ConfigCommand(console=console)
    asyncio.run(cmd.run(
        key=key,
        value=value,
        list_all=list_all,
        global_config=global_config
    ))


@app.command()
def skills(
    list_all: bool = typer.Option(False, "--list", "-l", help="List skills"),
    install: Optional[str] = typer.Option(None, "--install", "-i", help="Install skill"),
    uninstall: Optional[str] = typer.Option(None, "--uninstall", "-u", help="Uninstall skill"),
):
    """Manage skills"""
    from .cli.commands import SkillsCommand
    
    cmd = SkillsCommand(console=console)
    asyncio.run(cmd.run(
        list_all=list_all,
        install=install,
        uninstall=uninstall
    ))


@app.command()
def session(
    list_all: bool = typer.Option(False, "--list", "-l", help="List sessions"),
    load: Optional[str] = typer.Option(None, "--load", help="Load session"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export session"),
):
    """Manage sessions"""
    from .cli.commands import SessionCommand
    
    cmd = SessionCommand(console=console)
    asyncio.run(cmd.run(
        list_all=list_all,
        load=load,
        export=export
    ))


def run_cli():
    """Entry point for CLI"""
    app()


if __name__ == "__main__":
    run_cli()
