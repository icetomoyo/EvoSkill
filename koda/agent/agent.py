"""
Enhanced Agent

Event-driven agent with full Pi-style features.
"""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from koda.ai.provider import LLMProvider, Message, StreamEvent, ToolCall
from koda.agent.events import EventBus, Event, EventType
from koda.agent.tools import ToolRegistry, ToolContext
from koda.agent.queue import MessageQueue, DeliveryMode
from koda.mes.history import HistoryManager


class AgentState(Enum):
    """Agent state"""
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"
    EXECUTING_TOOL = "executing_tool"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Agent configuration"""
    max_iterations: int = 10
    max_tokens: int = 128000
    temperature: float = 0.7
    enable_compaction: bool = True
    compaction_threshold: float = 0.75
    require_confirmation: bool = True
    working_dir: Path = field(default_factory=Path.cwd)
    
    # Tool settings
    default_tools: List[str] = field(default_factory=lambda: ["read", "write", "edit", "bash"])
    
    # Queue settings
    steering_mode: str = "one-at-a-time"
    follow_up_mode: str = "one-at-a-time"


class Agent:
    """
    Enhanced Agent with event system
    
    Features:
    - Event-driven architecture
    - Message queue (steering/follow-up)
    - Tool registry
    - History management with compaction
    - State management
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        config: Optional[AgentConfig] = None
    ):
        """
        Args:
            llm_provider: LLM provider
            config: Agent configuration
        """
        self.llm = llm_provider
        self.config = config or AgentConfig()
        
        # Components
        self.events = EventBus()
        self.tools = ToolRegistry()
        self.queue = MessageQueue(
            steering_mode=self.config.steering_mode,
            follow_up_mode=self.config.follow_up_mode
        )
        self.history = HistoryManager(
            max_tokens=self.config.max_tokens,
            compaction_threshold=self.config.compaction_threshold
        )
        
        # State
        self.state = AgentState.IDLE
        self._current_task: Optional[asyncio.Task] = None
        self._cancelled = False
        
        # Register built-in tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools"""
        from koda.tools.file_tool import FileTool
        from koda.tools.shell_tool import ShellTool
        from koda.tools.grep_tool import GrepTool
        from koda.tools.find_tool import FindTool
        from koda.tools.ls_tool import LsTool
        from koda.agent.tools import Tool
        
        file_tool = FileTool()
        shell_tool = ShellTool()
        grep_tool = GrepTool()
        find_tool = FindTool()
        ls_tool = LsTool()
        
        tool_map = {
            "read": Tool(
                name="read",
                description="Read file contents",
                parameters={
                    "file_path": {"type": "string", "description": "Path to file"},
                    "offset": {"type": "integer", "default": 1},
                    "limit": {"type": "integer", "default": 100},
                },
                handler=file_tool.read,
            ),
            "write": Tool(
                name="write",
                description="Write content to file",
                parameters={
                    "file_path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                handler=file_tool.write,
                requires_confirmation=True,
            ),
            "edit": Tool(
                name="edit",
                description="Edit file by replacing text",
                parameters={
                    "file_path": {"type": "string", "description": "Path to file"},
                    "old_string": {"type": "string", "description": "Text to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                handler=file_tool.edit,
                requires_confirmation=True,
            ),
            "bash": Tool(
                name="bash",
                description="Execute bash command",
                parameters={
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "default": 60},
                },
                handler=shell_tool.execute,
                requires_confirmation=True,
            ),
            "grep": Tool(
                name="grep",
                description="Search for patterns in files",
                parameters={
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "path": {"type": "string", "description": "Directory or file"},
                },
                handler=grep_tool.search,
            ),
            "find": Tool(
                name="find",
                description="Find files by pattern",
                parameters={
                    "path": {"type": "string", "description": "Directory to search"},
                    "pattern": {"type": "string", "default": "*"},
                },
                handler=find_tool.find,
            ),
            "ls": Tool(
                name="ls",
                description="List directory contents",
                parameters={
                    "path": {"type": "string", "default": "."},
                },
                handler=ls_tool.list,
            ),
        }
        
        for name in self.config.default_tools:
            if name in tool_map:
                self.tools.register(tool_map[name])
    
    async def run(self, user_input: str) -> AsyncIterator[Event]:
        """
        Run agent with user input
        
        Args:
            user_input: User message
            
        Yields:
            Events during execution
        """
        self.state = AgentState.RUNNING
        self._cancelled = False
        
        # Emit start event
        yield Event.create(EventType.AGENT_START, {"input": user_input})
        
        # Add to history
        self.history.add_message(Message.user(user_input))
        
        try:
            # Agent loop
            for iteration in range(self.config.max_iterations):
                if self._cancelled:
                    yield Event.create(EventType.CANCELLED)
                    self.state = AgentState.CANCELLED
                    return
                
                # Emit turn start
                yield Event.create(EventType.TURN_START, {"iteration": iteration})
                
                # Build messages
                messages = self._build_messages()
                
                # Call LLM
                self.state = AgentState.THINKING
                yield Event.create(EventType.LLM_START)
                
                tool_calls = []
                response_text = ""
                
                async for event in self._call_llm(messages):
                    if event.type == "text":
                        response_text += event.data
                        yield Event.create(EventType.LLM_DELTA, {"text": event.data})
                    elif event.type == "tool_call":
                        tool_calls.append(event.data)
                    elif event.type == "stop":
                        break
                
                yield Event.create(EventType.LLM_END, {"text": response_text})
                
                # Handle tool calls
                if tool_calls:
                    self.state = AgentState.EXECUTING_TOOL
                    
                    # Add assistant message with tool calls
                    self.history.add_message(Message.assistant(response_text, tool_calls))
                    
                    for tool_call in tool_calls:
                        yield Event.create(EventType.TOOL_CALL_START, {"tool": tool_call.name})
                        
                        try:
                            result = await self.tools.execute(
                                tool_call.name,
                                tool_call.arguments,
                                ToolContext(
                                    working_dir=str(self.config.working_dir),
                                    env={},
                                    timeout=60
                                )
                            )
                            
                            # Add tool result to history
                            self.history.add_message(Message.tool(
                                tool_call_id=tool_call.id,
                                output=result,
                                name=tool_call.name
                            ))
                            
                            yield Event.create(EventType.TOOL_RESULT, {
                                "tool": tool_call.name,
                                "result": result
                            })
                            
                        except Exception as e:
                            error_msg = f"Error executing {tool_call.name}: {str(e)}"
                            yield Event.create(EventType.TOOL_ERROR, {
                                "tool": tool_call.name,
                                "error": error_msg
                            })
                        
                        yield Event.create(EventType.TOOL_CALL_END, {"tool": tool_call.name})
                else:
                    # Final response
                    self.history.add_message(Message.assistant(response_text))
                    yield Event.create(EventType.MESSAGE_END, {"text": response_text})
                    break
                
                yield Event.create(EventType.TURN_END, {"iteration": iteration})
                
                # Check compaction
                if self.config.enable_compaction and self.history.should_compact():
                    yield Event.create(EventType.COMPACTION_START)
                    result = self.history.compact()
                    yield Event.create(EventType.COMPACTION_END, {
                        "summary": result.summary,
                        "tokens_saved": result.tokens_saved
                    })
            
            else:
                # Max iterations reached
                yield Event.create(EventType.ERROR, {"message": "Max iterations reached"})
                self.state = AgentState.ERROR
                
        except Exception as e:
            yield Event.create(EventType.ERROR, {"message": str(e)})
            self.state = AgentState.ERROR
        
        finally:
            yield Event.create(EventType.AGENT_END)
            if self.state not in (AgentState.ERROR, AgentState.CANCELLED):
                self.state = AgentState.IDLE
    
    def _build_messages(self) -> List[Message]:
        """Build message list for LLM"""
        # System message
        system_content = self._build_system_prompt()
        
        messages = [Message.system(system_content)]
        messages.extend(self.history.get_messages())
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        lines = [
            "You are Koda, a helpful coding assistant.",
            "",
            "Available tools:",
        ]
        
        for name in self.tools.list_tools():
            tool = self.tools.get(name)
            lines.append(f"- {name}: {tool.description}")
        
        lines.extend([
            "",
            f"Working directory: {self.config.working_dir}",
            "",
            "Rules:",
            "1. Use tools to accomplish tasks",
            "2. Reference files with @filename",
            "3. Use bash for file operations when appropriate",
        ])
        
        # Load AGENTS.md
        agents_md = self._load_agents_md()
        if agents_md:
            lines.extend(["", "Context from AGENTS.md:", agents_md])
        
        return "\n".join(lines)
    
    def _load_agents_md(self) -> str:
        """Load AGENTS.md files"""
        content = []
        
        # Global
        global_path = Path.home() / ".koda" / "AGENTS.md"
        if global_path.exists():
            content.append(global_path.read_text(encoding="utf-8"))
        
        # Local
        local_path = self.config.working_dir / "AGENTS.md"
        if local_path.exists():
            content.append(local_path.read_text(encoding="utf-8"))
        
        return "\n\n".join(content)
    
    async def _call_llm(self, messages: List[Message]) -> AsyncIterator[StreamEvent]:
        """Call LLM provider"""
        tool_definitions = self.tools.get_definitions()
        
        async for event in self.llm.chat(
            messages=messages,
            tools=tool_definitions,
            temperature=self.config.temperature,
            stream=True
        ):
            yield event
    
    def cancel(self) -> None:
        """Cancel current execution"""
        self._cancelled = True
    
    def queue_steering(self, content: str) -> None:
        """Queue steering message"""
        self.queue.queue_steering(content)
    
    def queue_follow_up(self, content: str) -> None:
        """Queue follow-up message"""
        self.queue.queue_follow_up(content)
