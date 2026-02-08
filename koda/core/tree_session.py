"""
Tree Session - 树状会话管理

实现 Pi Coding Agent 的核心理念：
- 会话是树状结构，支持分支
- 可以在分支中实验/修复，然后回到主线
- 类似 Git 分支，但更轻量
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from enum import Enum
from pathlib import Path


class NodeStatus(Enum):
    """节点状态"""
    ACTIVE = "active"      # 当前活动节点
    SUCCESS = "success"    # 成功完成
    FAILED = "failed"      # 失败
    MERGED = "merged"      # 已合并到父节点
    ABANDONED = "abandoned" # 已放弃


@dataclass
class SessionNode:
    """
    会话树节点
    
    每个节点代表一个开发状态快照
    """
    id: str
    parent_id: Optional[str]
    name: str  # 节点名称，如 "main", "fix-auth", "refactor-db"
    description: str
    
    # 内容
    artifacts: Dict[str, str] = field(default_factory=dict)  # 文件名 -> 内容
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # 元数据
    status: NodeStatus = NodeStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 树结构
    children: List[str] = field(default_factory=list)  # 子节点 ID 列表
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionNode":
        """反序列化"""
        data = data.copy()
        data['status'] = NodeStatus(data['status'])
        return cls(**data)


@dataclass
class TreeSession:
    """
    树状会话
    
    管理整个开发历史的树形结构
    """
    session_id: str
    root_node_id: str
    nodes: Dict[str, SessionNode] = field(default_factory=dict)
    current_node_id: str = ""
    
    # 扩展注册表
    extensions: Dict[str, str] = field(default_factory=dict)  # 扩展名 -> 代码
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        if not self.current_node_id and self.root_node_id:
            self.current_node_id = self.root_node_id
    
    # ============ 节点操作 ============
    
    def create_branch(
        self,
        name: str,
        description: str,
        from_node_id: Optional[str] = None,
    ) -> SessionNode:
        """
        创建新分支（子节点）
        
        Args:
            name: 分支名称
            description: 分支描述
            from_node_id: 从哪个节点分叉，默认当前节点
            
        Returns:
            新节点
        """
        parent_id = from_node_id or self.current_node_id
        parent = self.nodes.get(parent_id)
        
        if not parent:
            raise ValueError(f"Parent node {parent_id} not found")
        
        # 创建新节点
        node = SessionNode(
            id=str(uuid.uuid4())[:8],
            parent_id=parent_id,
            name=name,
            description=description,
            # 复制父节点的 artifacts
            artifacts=parent.artifacts.copy(),
            messages=parent.messages.copy(),
            status=NodeStatus.ACTIVE,
        )
        
        # 更新树结构
        self.nodes[node.id] = node
        parent.children.append(node.id)
        
        return node
    
    def checkout(self, node_id: str) -> SessionNode:
        """
        切换到指定节点
        
        类似 git checkout
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        self.current_node_id = node_id
        return self.nodes[node_id]
    
    def merge(self, from_node_id: str, to_node_id: Optional[str] = None) -> SessionNode:
        """
        合并分支
        
        将 from_node 的更改合并到 to_node（默认当前节点）
        
        Args:
            from_node_id: 源节点
            to_node_id: 目标节点
            
        Returns:
            合并后的节点
        """
        target_id = to_node_id or self.current_node_id
        
        source = self.nodes.get(from_node_id)
        target = self.nodes.get(target_id)
        
        if not source or not target:
            raise ValueError("Source or target node not found")
        
        # 合并 artifacts（源节点的更改覆盖目标节点）
        target.artifacts.update(source.artifacts)
        
        # 标记源节点为已合并
        source.status = NodeStatus.MERGED
        source.metadata['merged_to'] = target_id
        
        return target
    
    def abandon(self, node_id: str) -> None:
        """
        放弃分支
        
        标记节点为放弃状态，但保留历史
        """
        node = self.nodes.get(node_id)
        if node:
            node.status = NodeStatus.ABANDONED
    
    # ============ 扩展管理 ============
    
    def register_extension(self, name: str, code: str) -> None:
        """
        注册扩展
        
        代理自己写的扩展工具
        """
        self.extensions[name] = code
    
    def get_extension(self, name: str) -> Optional[str]:
        """获取扩展代码"""
        return self.extensions.get(name)
    
    def list_extensions(self) -> List[str]:
        """列出所有扩展"""
        return list(self.extensions.keys())
    
    # ============ 查询 ============
    
    def get_current_node(self) -> SessionNode:
        """获取当前节点"""
        return self.nodes[self.current_node_id]
    
    def get_path_to_root(self, node_id: Optional[str] = None) -> List[SessionNode]:
        """
        获取从指定节点到根节点的路径
        
        Returns:
            从根到当前节点的路径
        """
        path = []
        current_id = node_id or self.current_node_id
        
        while current_id:
            node = self.nodes.get(current_id)
            if not node:
                break
            path.append(node)
            current_id = node.parent_id
        
        return list(reversed(path))
    
    def get_tree_visualization(self) -> str:
        """
        获取树的可视化字符串
        
        类似 git log --graph
        """
        lines = []
        
        def print_node(node_id: str, prefix: str = "", is_last: bool = True):
            node = self.nodes.get(node_id)
            if not node:
                return
            
            # 节点标记
            marker = "*" if node_id == self.current_node_id else " "
            status = node.status.value[0].upper()
            
            # 连接线
            connector = "└── " if is_last else "├── "
            
            lines.append(f"{prefix}{marker}{connector}[{status}] {node.name}: {node.description[:30]}")
            
            # 递归打印子节点
            for i, child_id in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                extension = "    " if is_last else "│   "
                print_node(child_id, prefix + extension, is_last_child)
        
        # 从根开始
        root = self.nodes.get(self.root_node_id)
        if root:
            lines.append(f"[{root.status.value[0].upper()}] {root.name}")
            for i, child_id in enumerate(root.children):
                print_node(child_id, "", i == len(root.children) - 1)
        
        return "\n".join(lines)
    
    def get_all_branches(self) -> List[SessionNode]:
        """获取所有分支节点"""
        return [n for n in self.nodes.values() if n.parent_id]
    
    # ============ 序列化 ============
    
    def save(self, path: Path) -> None:
        """保存到文件"""
        data = {
            "session_id": self.session_id,
            "root_node_id": self.root_node_id,
            "current_node_id": self.current_node_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "extensions": self.extensions,
            "created_at": self.created_at,
        }
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def load(cls, path: Path) -> "TreeSession":
        """从文件加载"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        session = cls(
            session_id=data["session_id"],
            root_node_id=data["root_node_id"],
            current_node_id=data["current_node_id"],
            nodes={k: SessionNode.from_dict(v) for k, v in data["nodes"].items()},
            extensions=data.get("extensions", {}),
            created_at=data["created_at"],
        )
        
        return session


class TreeSessionManager:
    """
    树状会话管理器
    
    管理多个会话的创建、加载和切换
    """
    
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.sessions_dir = self.workspace / ".koda" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[TreeSession] = None
    
    def create_session(self, name: str = "main") -> TreeSession:
        """
        创建新会话
        
        Args:
            name: 根节点名称
        """
        session_id = str(uuid.uuid4())[:8]
        
        # 创建根节点
        root = SessionNode(
            id=str(uuid.uuid4())[:8],
            parent_id=None,
            name=name,
            description="Root session",
        )
        
        session = TreeSession(
            session_id=session_id,
            root_node_id=root.id,
            nodes={root.id: root},
            current_node_id=root.id,
        )
        
        self.current_session = session
        return session
    
    def load_session(self, session_id: str) -> Optional[TreeSession]:
        """加载会话"""
        path = self.sessions_dir / f"{session_id}.json"
        
        if not path.exists():
            return None
        
        session = TreeSession.load(path)
        self.current_session = session
        return session
    
    def save_current_session(self) -> None:
        """保存当前会话"""
        if self.current_session:
            path = self.sessions_dir / f"{self.current_session.session_id}.json"
            self.current_session.save(path)
    
    def list_sessions(self) -> List[str]:
        """列出所有会话 ID"""
        return [f.stem for f in self.sessions_dir.glob("*.json")]
