"""
Context Manager - 上下文管理器

管理项目上下文、对话历史和知识库。
"""
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


@dataclass
class Message:
    """对话消息"""
    role: str  # system, user, assistant, tool
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectContext:
    """项目上下文"""
    name: str
    path: str
    language: str = "python"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    structure: Dict[str, Any] = field(default_factory=dict)
    key_files: List[str] = field(default_factory=list)


@dataclass
class SessionContext:
    """会话上下文"""
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: List[Message] = field(default_factory=list)
    project: Optional[ProjectContext] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    上下文管理器
    
    管理项目、对话和知识。
    
    Example:
        ctx = ContextManager("./workspace")
        await ctx.load_project("./my_project")
        await ctx.add_message("user", "Create a weather tool")
        history = await ctx.get_conversation_history()
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace = Path(workspace_path)
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.sessions_dir = self.workspace / ".koda" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.knowledge_dir = self.workspace / ".koda" / "knowledge"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[SessionContext] = None
    
    async def create_session(
        self,
        session_id: Optional[str] = None,
    ) -> SessionContext:
        """
        创建新会话
        
        Args:
            session_id: 会话 ID，自动生成
            
        Returns:
            SessionContext
        """
        import uuid
        session_id = session_id or str(uuid.uuid4())[:8]
        
        self.current_session = SessionContext(
            session_id=session_id,
        )
        
        return self.current_session
    
    async def load_session(self, session_id: str) -> Optional[SessionContext]:
        """
        加载会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            SessionContext or None
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.current_session = SessionContext(**data)
            return self.current_session
        except Exception:
            return None
    
    async def save_session(self) -> None:
        """保存当前会话"""
        if not self.current_session:
            return
        
        session_file = self.sessions_dir / f"{self.current_session.session_id}.json"
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.current_session), f, indent=2, default=str)
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加对话消息
        
        Args:
            role: 角色 (system/user/assistant/tool)
            content: 内容
            metadata: 元数据
        """
        if not self.current_session:
            await self.create_session()
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        self.current_session.messages.append(message)
        
        # 自动保存
        await self.save_session()
    
    async def get_conversation_history(
        self,
        limit: int = 50,
    ) -> List[Message]:
        """
        获取对话历史
        
        Args:
            limit: 返回最近多少条
            
        Returns:
            消息列表
        """
        if not self.current_session:
            return []
        
        return self.current_session.messages[-limit:]
    
    async def load_project(self, project_path: Path) -> ProjectContext:
        """
        加载项目上下文
        
        Args:
            project_path: 项目路径
            
        Returns:
            ProjectContext
        """
        project_path = Path(project_path).resolve()
        
        # 分析项目结构
        structure = await self._analyze_structure(project_path)
        
        # 检测语言
        language = self._detect_language(project_path)
        
        # 查找关键文件
        key_files = await self._find_key_files(project_path)
        
        # 读取依赖
        dependencies = await self._read_dependencies(project_path, language)
        
        project = ProjectContext(
            name=project_path.name,
            path=str(project_path),
            language=language,
            structure=structure,
            key_files=key_files,
            dependencies=dependencies,
        )
        
        if self.current_session:
            self.current_session.project = project
            await self.save_session()
        
        return project
    
    async def _analyze_structure(self, path: Path) -> Dict[str, Any]:
        """分析项目结构"""
        structure = {
            "files": [],
            "directories": [],
        }
        
        try:
            for item in path.iterdir():
                if item.is_file():
                    structure["files"].append(item.name)
                elif item.is_dir() and not item.name.startswith('.'):
                    structure["directories"].append(item.name)
        except Exception:
            pass
        
        return structure
    
    def _detect_language(self, path: Path) -> str:
        """检测项目语言"""
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            return "python"
        elif (path / "package.json").exists():
            return "javascript"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "go.mod").exists():
            return "go"
        return "unknown"
    
    async def _find_key_files(self, path: Path) -> List[str]:
        """查找关键文件"""
        key_patterns = [
            "README*",
            "main.py",
            "app.py",
            "setup.py",
            "pyproject.toml",
            "requirements.txt",
        ]
        
        key_files = []
        for pattern in key_patterns:
            for file in path.glob(pattern):
                if file.is_file():
                    key_files.append(str(file.relative_to(path)))
        
        return key_files[:10]  # 最多10个
    
    async def _read_dependencies(self, path: Path, language: str) -> List[str]:
        """读取依赖列表"""
        deps = []
        
        if language == "python":
            req_file = path / "requirements.txt"
            if req_file.exists():
                content = req_file.read_text()
                deps = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
        
        return deps[:20]  # 最多20个
    
    async def add_artifact(
        self,
        artifact_type: str,
        name: str,
        content: str,
    ) -> None:
        """
        添加产物
        
        Args:
            artifact_type: 类型 (code/doc/test)
            name: 名称
            content: 内容
        """
        if not self.current_session:
            await self.create_session()
        
        artifact = {
            "type": artifact_type,
            "name": name,
            "content": content[:1000],  # 只存前1000字符
            "timestamp": datetime.now().isoformat(),
        }
        
        self.current_session.artifacts.append(artifact)
        await self.save_session()
    
    async def get_project_summary(self) -> str:
        """获取项目摘要"""
        if not self.current_session or not self.current_session.project:
            return "No project loaded"
        
        p = self.current_session.project
        return f"""Project: {p.name}
Language: {p.language}
Path: {p.path}
Dependencies: {len(p.dependencies)}
Key Files: {', '.join(p.key_files[:5])}
"""
    
    async def clear_history(self) -> None:
        """清空对话历史"""
        if self.current_session:
            self.current_session.messages = []
            await self.save_session()
