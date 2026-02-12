"""
Coding Main - Main entry point for the Coding module
Equivalent to Pi Mono's main.ts / index.ts

Provides unified CLI entry point with:
- CLI argument parsing (argparse)
- Mode selection (interactive, print, headless, rpc)
- Configuration loading
- Agent startup logic
- Main loop for user input
"""
import sys
import os
import asyncio
import argparse
import signal
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from .. import __version__
from .config import (
    CodingConfig,
    OutputMode,
    ModelConfig,
    load_config,
    save_config,
    DEFAULT_CONFIG,
    FAST_CONFIG,
    REASONING_CONFIG,
)
from .core.defaults import get_default_system_prompt, get_provider_from_env
from .settings_manager import SettingsManager, get_settings_manager


class RunMode(Enum):
    """Available run modes"""
    INTERACTIVE = "interactive"
    PRINT = "print"
    HEADLESS = "headless"
    RPC = "rpc"


@dataclass
class CLIContext:
    """CLI execution context"""
    config: CodingConfig
    mode: RunMode
    working_dir: Path
    prompt: Optional[str] = None
    files: List[Path] = None
    resume_session: Optional[str] = None
    output_format: str = "text"
    verbose: bool = False

    def __post_init__(self):
        if self.files is None:
            self.files = []


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> logging.Logger:
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
        log_file: Optional log file path

    Returns:
        Configured logger
    """
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )

    return logging.getLogger("koda.coding")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create CLI argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="koda",
        description="Koda Coding Agent - AI-powered coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  koda                                    Start interactive mode
  koda "Fix the bug in app.py"            Ask a question
  koda -f app.py -f test.py "Review"      Include files in question
  koda --headless                         Run in headless mode
  koda --rpc --port 8080                  Start RPC server
  koda --print "What is Python?"          Non-interactive print mode

For more information, visit: https://github.com/your-repo/koda
        """
    )

    # Global options
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Initial prompt or question"
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit"
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=None,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to log file"
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--interactive", "-i",
        action="store_true",
        default=True,
        help="Run in interactive mode (default)"
    )
    mode_group.add_argument(
        "--print", "-p",
        action="store_true",
        help="Run in print mode (non-interactive)"
    )
    mode_group.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no UI)"
    )
    mode_group.add_argument(
        "--rpc",
        action="store_true",
        help="Start RPC server"
    )

    # Model options
    model_group = parser.add_argument_group("Model Options")
    model_group.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Model to use (e.g., claude-sonnet-4, gpt-4o)"
    )
    model_group.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Provider to use (anthropic, openai, google, etc.)"
    )
    model_group.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Model temperature (0.0-2.0)"
    )
    model_group.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens to generate"
    )
    model_group.add_argument(
        "--thinking",
        type=str,
        choices=["minimal", "low", "medium", "high", "xhigh"],
        default=None,
        help="Thinking level for extended thinking models"
    )
    model_group.add_argument(
        "--fast",
        action="store_true",
        help="Use fast preset (Haiku, minimal thinking)"
    )
    model_group.add_argument(
        "--reasoning",
        action="store_true",
        help="Use reasoning preset (high thinking)"
    )

    # Input options
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "--file", "-f",
        type=Path,
        action="append",
        default=[],
        help="Files to include in context (can be used multiple times)"
    )
    input_group.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume session by ID"
    )
    input_group.add_argument(
        "--continue-last",
        action="store_true",
        help="Continue from last session"
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output", "-o",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format"
    )
    output_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    output_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-essential output"
    )
    output_group.add_argument(
        "--stream/--no-stream",
        default=True,
        help="Enable/disable streaming output"
    )

    # Tool options
    tool_group = parser.add_argument_group("Tool Options")
    tool_group.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable all tools"
    )
    tool_group.add_argument(
        "--allowed-tools",
        type=str,
        default=None,
        help="Comma-separated list of allowed tools"
    )
    tool_group.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Auto-confirm tool executions (dangerous)"
    )
    tool_group.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Tool execution timeout in seconds"
    )

    # Context options
    context_group = parser.add_argument_group("Context Options")
    context_group.add_argument(
        "--max-context",
        type=int,
        default=None,
        help="Maximum context tokens"
    )
    context_group.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Custom system prompt"
    )
    context_group.add_argument(
        "--no-agents-md",
        action="store_true",
        help="Don't load AGENTS.md files"
    )

    # RPC options
    rpc_group = parser.add_argument_group("RPC Options")
    rpc_group.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="RPC server host"
    )
    rpc_group.add_argument(
        "--port",
        type=int,
        default=8080,
        help="RPC server port"
    )

    # Working directory
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Working directory"
    )

    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        args: Arguments to parse (default: sys.argv[1:])

    Returns:
        Parsed arguments
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def determine_mode(args: argparse.Namespace) -> RunMode:
    """
    Determine run mode from arguments.

    Args:
        args: Parsed arguments

    Returns:
        RunMode enum value
    """
    if args.rpc:
        return RunMode.RPC
    elif args.headless:
        return RunMode.HEADLESS
    elif args.print:
        return RunMode.PRINT
    else:
        return RunMode.INTERACTIVE


def build_config(args: argparse.Namespace) -> CodingConfig:
    """
    Build configuration from arguments.

    Args:
        args: Parsed arguments

    Returns:
        CodingConfig instance
    """
    # Start with preset or default
    if args.fast:
        config = FAST_CONFIG
    elif args.reasoning:
        config = REASONING_CONFIG
    else:
        config = load_config(args.config)

    # Override with command line options
    if args.model:
        config.model.model = args.model
    if args.provider:
        config.model.provider = args.provider
    if args.temperature is not None:
        config.model.temperature = args.temperature
    if args.max_tokens is not None:
        config.model.max_tokens = args.max_tokens
    if args.thinking:
        config.model.thinking_level = args.thinking

    # Tool settings
    if args.no_tools:
        config.tools.max_parallel_tools = 0
    if args.allowed_tools:
        config.tools.shell_allowed_commands = args.allowed_tools.split(",")
    if args.auto_confirm:
        config.tools.require_confirmation_for = []
    if args.timeout:
        config.tools.tool_timeout = args.timeout

    # Context settings
    if args.max_context:
        config.context.max_context_tokens = args.max_context
    if args.system_prompt:
        config.context.custom_system_prompt = args.system_prompt
    if args.no_agents_md:
        config.context.load_agents_md = False

    # UI settings
    if args.no_color:
        config.ui.use_colors = False
    if args.quiet:
        config.ui.show_timing = False
        config.ui.show_token_usage = False
    config.ui.stream_response = args.stream

    # Debug settings
    config.debug = args.debug or args.verbose
    if args.verbose:
        config.log_level = "DEBUG"

    # Output mode
    if args.print:
        config.ui.output_mode = OutputMode.PRINT

    return config


class CodingMain:
    """
    Main entry point for Koda Coding Agent.

    Handles CLI parsing, configuration loading, mode selection,
    and agent lifecycle management.
    """

    def __init__(
        self,
        args: Optional[argparse.Namespace] = None,
        config: Optional[CodingConfig] = None
    ):
        """
        Initialize CodingMain.

        Args:
            args: Pre-parsed arguments (default: parse from sys.argv)
            config: Pre-built configuration (default: build from args)
        """
        self.args = args or parse_args()
        self.config = config or build_config(self.args)
        self.mode = determine_mode(self.args)
        self.console = Console(no_color=self.args.no_color)
        self.logger = setup_logging(
            verbose=self.args.verbose,
            log_file=self.args.log_file
        )

        # Working directory
        self.working_dir = Path(self.args.cwd) if self.args.cwd else Path.cwd()

        # Session
        self._session = None
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def run(self) -> int:
        """
        Main entry point.

        Returns:
            Exit code
        """
        # Handle version
        if self.args.version:
            self.console.print(f"Koda version {__version__}")
            return 0

        self.logger.info(f"Starting Koda v{__version__} in {self.mode.value} mode")
        self.logger.debug(f"Working directory: {self.working_dir}")

        # Setup signal handlers
        self._setup_signal_handlers()

        try:
            # Dispatch to mode handler
            if self.mode == RunMode.INTERACTIVE:
                return await self._run_interactive()
            elif self.mode == RunMode.PRINT:
                return await self._run_print()
            elif self.mode == RunMode.HEADLESS:
                return await self._run_headless()
            elif self.mode == RunMode.RPC:
                return await self._run_rpc()
            else:
                self.console.print(f"[red]Unknown mode: {self.mode}[/red]")
                return 1

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
            return 130
        except Exception as e:
            self.logger.exception("Fatal error")
            self.console.print(f"[red]Fatal error: {e}[/red]")
            return 1
        finally:
            await self._cleanup()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            self.logger.info(f"Received signal {signum}")
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    async def _run_interactive(self) -> int:
        """
        Run interactive mode.

        Returns:
            Exit code
        """
        from .modes import InteractiveMode, ModeContext, ModeResponse, ModeState

        self.console.print(Panel.fit(
            f"[bold blue]Koda v{__version__}[/bold blue]\n"
            f"Working directory: [dim]{self.working_dir}[/dim]\n\n"
            "Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit",
            title="Welcome to Koda"
        ))

        # Create mode and context
        mode = InteractiveMode()
        context = ModeContext(
            messages=[],
            session_id=self.args.resume,
            metadata={"working_dir": str(self.working_dir)}
        )

        # Initialize session
        try:
            session = await self._create_session()
            self._session = session
        except Exception as e:
            self.console.print(f"[red]Failed to initialize session: {e}[/red]")
            return 1

        # Start mode
        response = mode.start(context)
        self._running = True

        # Handle initial prompt if provided
        if self.args.prompt:
            response = await self._process_prompt(
                self.args.prompt,
                mode,
                context,
                session
            )

        # Handle initial files
        for file_path in self.args.file:
            response = await self._process_file(file_path, mode, context, session)

        # Main loop
        while mode.is_active() and self._running:
            if response.requires_input:
                try:
                    user_input = self._get_user_input()
                    if user_input is None:  # EOF
                        break

                    # Handle slash commands
                    if user_input.startswith("/"):
                        response = mode.handle_input(user_input, context)
                        if response.state == ModeState.EXIT:
                            break
                    else:
                        # Process with LLM
                        response = await self._process_prompt(
                            user_input,
                            mode,
                            context,
                            session
                        )

                    if response.content:
                        self._display_response(response)

                except (EOFError, KeyboardInterrupt):
                    break

            elif response.state == ModeState.PROCESSING:
                # Wait for processing
                await asyncio.sleep(0.1)

            elif response.state == ModeState.TOOL_CONFIRM:
                # Handle tool confirmation
                confirmed = self._confirm_tools(response.tool_calls)
                response = mode.confirm_tools(confirmed, context)

            else:
                # Display and wait for input
                if response.content:
                    self._display_response(response)
                await asyncio.sleep(0.01)

        self.console.print("[dim]Goodbye![/dim]")
        return 0

    async def _run_print(self) -> int:
        """
        Run print mode (non-interactive).

        Returns:
            Exit code
        """
        from .modes import PrintMode

        if not self.args.prompt:
            self.console.print("[red]Error: No prompt provided for print mode[/red]")
            return 1

        mode = PrintMode()

        # Build context with files
        files = [str(f) for f in self.args.file]

        try:
            result = mode.run(
                prompt=self.args.prompt,
                context={"working_dir": str(self.working_dir)},
                max_iterations=self.config.max_iterations
            )

            # Output based on format
            if self.args.output == "json":
                output = json.dumps({
                    "output": result.output,
                    "exit_code": result.exit_code,
                    "metadata": result.metadata
                }, indent=2)
            else:
                output = result.output

            self.console.print(output)
            return result.exit_code

        except Exception as e:
            self.logger.exception("Print mode error")
            self.console.print(f"[red]Error: {e}[/red]")
            return 1

    async def _run_headless(self) -> int:
        """
        Run in headless mode (no UI, for automation/CI).

        Returns:
            Exit code
        """
        from .modes import PrintMode

        self.logger.info("Running in headless mode")

        if not self.args.prompt:
            self.logger.error("No prompt provided")
            return 1

        mode = PrintMode()

        try:
            # Read from stdin if prompt is "-"
            prompt = self.args.prompt
            if prompt == "-":
                prompt = sys.stdin.read()

            result = mode.run(
                prompt=prompt,
                context={"working_dir": str(self.working_dir)},
                max_iterations=self.config.max_iterations
            )

            # Always output as plain text in headless mode
            print(result.output)
            return result.exit_code

        except Exception as e:
            self.logger.exception("Headless mode error")
            print(f"Error: {e}", file=sys.stderr)
            return 1

    async def _run_rpc(self) -> int:
        """
        Start RPC server.

        Returns:
            Exit code
        """
        from .modes import RPCServer, RPCHandlers

        self.logger.info(f"Starting RPC server on {self.args.host}:{self.args.port}")
        self.console.print(f"[green]Starting RPC server on {self.args.host}:{self.args.port}[/green]")

        server = RPCServer()
        handlers = RPCHandlers()

        # Register handlers
        server.register_method("prompt", handlers.handle_prompt)
        server.register_method("continue", handlers.handle_continue)
        server.register_method("cancel", handlers.handle_cancel)
        server.register_method("status", handlers.handle_status)
        server.register_method("list_tools", handlers.handle_list_tools)

        self._running = True

        try:
            await server.start(host=self.args.host, port=self.args.port)
        except Exception as e:
            self.logger.exception("RPC server error")
            return 1

        return 0

    async def _create_session(self):
        """
        Create agent session.

        Returns:
            AgentSession instance
        """
        try:
            from .core.agent_session import AgentSession, AgentSessionConfig

            # Get provider
            from koda.ai import create_provider, get_model_info

            provider_name = self.config.model.provider or get_provider_from_env()
            provider = create_provider(provider_name)

            model_id = self.config.model.model
            model_info = get_model_info(provider_name, model_id)

            # Create session config
            session_config = AgentSessionConfig(
                model=model_id,
                provider=provider_name,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.max_tokens,
                max_context_tokens=self.config.context.max_context_tokens,
                compaction_threshold=self.config.context.compaction_threshold,
                enable_tools=not self.args.no_tools if hasattr(self.args, 'no_tools') else True,
                tool_timeout=self.config.tools.tool_timeout,
                max_parallel_tools=self.config.tools.max_parallel_tools,
                working_dir=self.working_dir,
                session_id=self.args.resume,
                auto_save=self.config.session.auto_save,
            )

            session = AgentSession(
                provider=provider,
                model=model_info,
                config=session_config
            )

            await session.initialize()
            return session

        except ImportError as e:
            self.logger.warning(f"Could not import agent session: {e}")
            # Return None - will work in simplified mode
            return None

    async def _process_prompt(self, prompt: str, mode, context, session) -> Any:
        """
        Process a prompt through the agent.

        Args:
            prompt: User prompt
            mode: Interactive mode instance
            context: Mode context
            session: Agent session

        Returns:
            ModeResponse
        """
        if session is not None:
            # Use full agent session
            try:
                response_content = []
                async for event in session.prompt(prompt):
                    if event.type == "text_delta":
                        response_content.append(event.data.get("text", ""))
                    elif event.type == "thinking_delta":
                        if self.config.ui.show_thinking:
                            response_content.append(f"[thinking: {event.data.get('thinking', '')[:50]}...]")
                    elif event.type == "complete":
                        break

                full_response = "".join(response_content)
                return mode.handle_assistant_response(full_response, context)

            except Exception as e:
                self.logger.exception("Session error")
                return mode.handle_assistant_response(f"Error: {e}", context)
        else:
            # Fallback to simple processing
            response = mode.handle_input(prompt, context)
            return mode.handle_assistant_response(
                f"Processing: {prompt[:50]}... (session not available)",
                context
            )

    async def _process_file(self, file_path: Path, mode, context, session) -> Any:
        """
        Process a file and add to context.

        Args:
            file_path: Path to file
            mode: Interactive mode instance
            context: Mode context
            session: Agent session

        Returns:
            ModeResponse
        """
        if not file_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return mode.handle_input("", context)

        try:
            content = file_path.read_text(encoding="utf-8")
            prompt = f"I've loaded the file `{file_path}`:\n```\n{content}\n```"
            return await self._process_prompt(prompt, mode, context, session)

        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return mode.handle_input("", context)

    def _get_user_input(self) -> Optional[str]:
        """
        Get user input from console.

        Returns:
            User input string or None on EOF
        """
        try:
            return self.console.input("[bold blue]> [/bold blue]")
        except EOFError:
            return None

    def _display_response(self, response):
        """Display response to user."""
        content = response.content

        if not content:
            return

        # Check if markdown
        if self.args.output == "markdown" or "```" in content:
            self.console.print(Markdown(content))
        else:
            self.console.print(content)

    def _confirm_tools(self, tool_calls: Optional[List[Dict]]) -> bool:
        """
        Confirm tool execution with user.

        Args:
            tool_calls: List of tool calls to confirm

        Returns:
            True if confirmed
        """
        if not tool_calls:
            return True

        self.console.print("\n[yellow]The following tools will be executed:[/yellow]")
        for tc in tool_calls:
            name = tc.get("name", "unknown")
            args = tc.get("arguments", {})
            self.console.print(f"  - [cyan]{name}[/cyan]: {args}")

        try:
            response = self.console.input("[yellow]Confirm? [Y/n] [/yellow]")
            return response.lower() in ("", "y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    async def _cleanup(self):
        """Cleanup resources."""
        self._running = False

        if self._session:
            try:
                # Save session if auto-save enabled
                pass
            except Exception as e:
                self.logger.warning(f"Error during cleanup: {e}")


async def main_async(args: Optional[List[str]] = None) -> int:
    """
    Async main entry point.

    Args:
        args: Command line arguments (default: sys.argv[1:])

    Returns:
        Exit code
    """
    parsed_args = parse_args(args)
    app = CodingMain(args=parsed_args)
    return await app.run()


def main(args: Optional[List[str]] = None) -> int:
    """
    Synchronous main entry point.

    Args:
        args: Command line arguments (default: sys.argv[1:])

    Returns:
        Exit code
    """
    return asyncio.run(main_async(args))


def run():
    """Entry point for console script."""
    sys.exit(main())


# CLI command shortcuts
def chat(prompt: Optional[str] = None, **kwargs) -> int:
    """
    Start chat mode.

    Args:
        prompt: Initial prompt
        **kwargs: Additional arguments

    Returns:
        Exit code
    """
    args = parse_args([prompt] if prompt else [])
    for key, value in kwargs.items():
        setattr(args, key, value)
    args.interactive = True
    args.print = False
    args.headless = False
    args.rpc = False
    return main_with_args(args)


def ask(prompt: str, **kwargs) -> int:
    """
    Ask a single question.

    Args:
        prompt: Question to ask
        **kwargs: Additional arguments

    Returns:
        Exit code
    """
    args = parse_args([prompt])
    for key, value in kwargs.items():
        setattr(args, key, value)
    args.print = True
    args.interactive = False
    args.headless = False
    args.rpc = False
    return main_with_args(args)


def main_with_args(args: argparse.Namespace) -> int:
    """
    Main with pre-parsed arguments.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    app = CodingMain(args=args)
    return asyncio.run(app.run())


if __name__ == "__main__":
    run()
