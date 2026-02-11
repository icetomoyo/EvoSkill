"""
Session Picker
等效于 Pi-Mono 的 packages/coding-agent/src/cli/session-picker.ts

交互式会话选择器。
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Session:
    """会话信息"""
    id: str
    name: str
    path: str
    created_at: datetime
    modified_at: datetime
    message_count: int
    is_active: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SessionPicker:
    """
    会话选择器
    
    提供交互式会话选择界面。
    
    Example:
        >>> picker = SessionPicker()
        >>> session = await picker.pick(sessions)
    """
    
    def __init__(self, use_tui: bool = True):
        self.use_tui = use_tui
        self._tui_available = self._check_tui()
    
    def _check_tui(self) -> bool:
        """检查TUI库"""
        try:
            import questionary
            return True
        except ImportError:
            return False
    
    async def pick(
        self,
        sessions: List[Session],
        title: str = "Select session",
    ) -> Optional[Session]:
        """
        选择会话
        
        Args:
            sessions: 会话列表
            title: 标题
        
        Returns:
            选中的会话或None
        """
        if not sessions:
            print("No sessions available.")
            return None
        
        if len(sessions) == 1:
            return sessions[0]
        
        if self.use_tui and self._tui_available:
            return await self._pick_tui(sessions, title)
        else:
            return await self._pick_cli(sessions, title)
    
    async def _pick_tui(
        self,
        sessions: List[Session],
        title: str,
    ) -> Optional[Session]:
        """TUI选择"""
        import questionary
        
        # Sort by modified time (newest first)
        sorted_sessions = sorted(
            sessions,
            key=lambda s: s.modified_at,
            reverse=True,
        )
        
        choices = []
        for session in sorted_sessions:
            label = self._format_session_label(session)
            choices.append(questionary.Choice(title=label, value=session))
        
        choices.append(questionary.Choice(title="Cancel", value=None))
        
        result = await questionary.select(
            title,
            choices=choices,
        ).ask_async()
        
        return result
    
    async def _pick_cli(
        self,
        sessions: List[Session],
        title: str,
    ) -> Optional[Session]:
        """CLI选择"""
        print(f"\n{title}:\n")
        
        # Sort by modified time
        sorted_sessions = sorted(
            sessions,
            key=lambda s: s.modified_at,
            reverse=True,
        )
        
        for i, session in enumerate(sorted_sessions, 1):
            label = self._format_session_label(session, plain=True)
            print(f"  {i}. {label}")
        
        print(f"  0. Cancel")
        print()
        
        try:
            choice = input(f"Enter number (0-{len(sessions)}): ").strip()
            idx = int(choice)
            
            if idx == 0:
                return None
            if 1 <= idx <= len(sessions):
                return sorted_sessions[idx - 1]
            
            print("Invalid selection")
            return None
            
        except (ValueError, KeyboardInterrupt):
            return None
    
    async def pick_with_search(
        self,
        sessions: List[Session],
        title: str = "Search sessions",
    ) -> Optional[Session]:
        """
        带搜索的选择
        
        Args:
            sessions: 会话列表
            title: 标题
        """
        if self.use_tui and self._tui_available:
            import questionary
            
            choices = [
                questionary.Choice(
                    title=self._format_session_label(s),
                    value=s,
                )
                for s in sessions
            ]
            
            result = await questionary.autocomplete(
                title,
                choices=[c.title for c in choices],
            ).ask_async()
            
            if result:
                for s in sessions:
                    if result == self._format_session_label(s):
                        return s
            return None
        else:
            return await self.pick(sessions, title)
    
    async def multi_pick(
        self,
        sessions: List[Session],
        title: str = "Select sessions",
    ) -> List[Session]:
        """多选会话"""
        if self.use_tui and self._tui_available:
            import questionary
            
            sorted_sessions = sorted(
                sessions,
                key=lambda s: s.modified_at,
                reverse=True,
            )
            
            choices = [
                questionary.Choice(
                    title=self._format_session_label(s),
                    value=s,
                    checked=False,
                )
                for s in sorted_sessions
            ]
            
            result = await questionary.checkbox(
                title,
                choices=choices,
            ).ask_async()
            
            return result or []
        else:
            print("Multi-select requires TUI. Selecting one:")
            session = await self.pick(sessions, title)
            return [session] if session else []
    
    def _format_session_label(self, session: Session, plain: bool = False) -> str:
        """格式化会话标签"""
        name = session.name or "Untitled"
        
        # Format date
        if isinstance(session.modified_at, datetime):
            date_str = session.modified_at.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = str(session.modified_at)[:16]
        
        # Format message count
        msg_str = f"{session.message_count} msgs"
        
        # Active indicator
        active_str = " ●" if session.is_active else ""
        
        if plain:
            return f"{name} ({date_str}, {msg_str}){active_str}"
        
        return f"{name}{active_str} - {date_str} - {msg_str}"


def format_session_table(sessions: List[Session]) -> str:
    """格式化会话表格"""
    if not sessions:
        return "No sessions available."
    
    # Sort by modified time
    sorted_sessions = sorted(
        sessions,
        key=lambda s: s.modified_at,
        reverse=True,
    )
    
    lines = []
    lines.append(f"{'Name':<25} {'Modified':<20} {'Msgs':<8} {'Path'}")
    lines.append("-" * 90)
    
    for session in sorted_sessions:
        name = session.name[:23] + ".." if len(session.name) > 25 else session.name
        modified = session.modified_at.strftime("%Y-%m-%d %H:%M") if isinstance(session.modified_at, datetime) else str(session.modified_at)[:16]
        msgs = str(session.message_count)
        path = session.path[:40] + "..." if len(session.path) > 43 else session.path
        
        active_mark = "● " if session.is_active else "  "
        lines.append(f"{active_mark}{name:<23} {modified:<20} {msgs:<8} {path}")
    
    return "\n".join(lines)


__all__ = [
    "Session",
    "SessionPicker",
    "format_session_table",
]
