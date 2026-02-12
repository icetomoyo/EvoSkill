"""
Path Utilities - 路径工具函数

提供安全、可靠的路径操作功能。
"""
import os
import re
from pathlib import Path
from typing import Optional, Union, Tuple, List


def normalize_path(path: Union[str, Path]) -> str:
    """
    规范化路径

    - 转换为标准格式
    - 解析 .. 和 .
    - 移除多余的分隔符
    - 展开 ~ 和环境变量

    Args:
        path: 输入路径

    Returns:
        规范化后的路径字符串

    Example:
        >>> normalize_path("~/Documents/../Downloads")
        '/home/user/Downloads'
    """
    path_str = str(path)

    # 展开环境变量和用户目录
    expanded = os.path.expandvars(os.path.expanduser(path_str))

    # 使用 Path 进行规范化
    normalized = Path(expanded)

    # 解析相对路径组件
    try:
        resolved = normalized.resolve(strict=False)
        return str(resolved)
    except (OSError, ValueError):
        # 如果无法解析，返回清理后的路径
        return os.path.normpath(expanded)


def is_safe_path(
    path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
    allow_symlinks: bool = False
) -> Tuple[bool, str]:
    """
    检查路径是否安全

    安全性检查包括：
    - 路径遍历攻击（..）
    - 符号链接检查
    - 是否在允许的基础目录内

    Args:
        path: 要检查的路径
        base_dir: 基础目录（如果提供，路径必须在此目录内）
        allow_symlinks: 是否允许符号链接

    Returns:
        (is_safe, reason) 元组

    Example:
        >>> is_safe_path("../etc/passwd", "/home/user")
        (False, "Path escapes base directory")
    """
    path_str = str(path)

    # 检查空路径
    if not path_str or not path_str.strip():
        return False, "Empty path"

    # 检查危险模式
    dangerous_patterns = [
        r'\.\.',  # 路径遍历
        r'^/etc/',
        r'^/proc/',
        r'^/sys/',
        r'^/dev/',
        r'^/root/',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, path_str):
            # 如果是路径遍历，需要进一步检查
            if pattern == r'\.\.':
                # 在基础目录内的 .. 可能是安全的
                if base_dir is None:
                    return False, "Path traversal detected without base directory"
            else:
                return False, f"Access to restricted path: {pattern}"

    # 解析路径
    try:
        resolved_path = Path(normalize_path(path_str))

        # 检查符号链接
        if resolved_path.exists() and resolved_path.is_symlink():
            if not allow_symlinks:
                return False, "Symbolic links not allowed"

            # 检查符号链接目标
            link_target = resolved_path.resolve()
            if base_dir:
                base = Path(normalize_path(base_dir))
                try:
                    link_target.relative_to(base)
                except ValueError:
                    return False, "Symbolic link target escapes base directory"

        # 检查是否在基础目录内
        if base_dir:
            base = Path(normalize_path(base_dir))
            try:
                resolved_path.relative_to(base)
            except ValueError:
                return False, "Path escapes base directory"

        return True, ""

    except Exception as e:
        return False, f"Path validation error: {str(e)}"


def resolve_path(
    path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
    must_exist: bool = False
) -> Path:
    """
    解析相对路径为绝对路径

    Args:
        path: 要解析的路径
        base_dir: 基础目录（用于相对路径解析）
        must_exist: 路径是否必须存在

    Returns:
        解析后的 Path 对象

    Raises:
        FileNotFoundError: 如果 must_exist=True 且路径不存在
        ValueError: 如果路径不安全

    Example:
        >>> resolve_path("Documents/file.txt", "/home/user")
        PosixPath('/home/user/Documents/file.txt')
    """
    path_str = str(path)

    # 展开用户目录和环境变量
    expanded = os.path.expandvars(os.path.expanduser(path_str))

    # 创建 Path 对象
    result = Path(expanded)

    # 如果是相对路径且有基础目录
    if not result.is_absolute() and base_dir:
        base = Path(normalize_path(base_dir))
        result = base / result

    # 规范化
    result = result.resolve(strict=False)

    # 检查是否存在
    if must_exist and not result.exists():
        raise FileNotFoundError(f"Path does not exist: {result}")

    return result


def get_relative_path(
    path: Union[str, Path],
    base_dir: Union[str, Path]
) -> str:
    """
    获取相对于基础目录的相对路径

    Args:
        path: 目标路径
        base_dir: 基础目录

    Returns:
        相对路径字符串

    Raises:
        ValueError: 如果路径不在基础目录内

    Example:
        >>> get_relative_path("/home/user/Documents/file.txt", "/home/user")
        'Documents/file.txt'
    """
    target = Path(normalize_path(path))
    base = Path(normalize_path(base_dir))

    try:
        relative = target.relative_to(base)
        return str(relative)
    except ValueError:
        raise ValueError(f"Path '{path}' is not relative to '{base_dir}'")


def ensure_directory(
    path: Union[str, Path],
    mode: int = 0o755,
    parents: bool = True
) -> Path:
    """
    确保目录存在，如不存在则创建

    Args:
        path: 目录路径
        mode: 目录权限（仅对新建目录生效）
        parents: 是否创建父目录

    Returns:
        目录的 Path 对象

    Raises:
        OSError: 如果创建失败
        NotADirectoryError: 如果路径存在但不是目录

    Example:
        >>> ensure_directory("/tmp/myapp/data")
        PosixPath('/tmp/myapp/data')
    """
    dir_path = Path(normalize_path(path))

    if dir_path.exists():
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Path exists but is not a directory: {dir_path}")
        return dir_path

    try:
        if parents:
            dir_path.mkdir(parents=True, mode=mode, exist_ok=True)
        else:
            dir_path.mkdir(mode=mode, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create directory '{dir_path}': {e}")

    return dir_path


def split_path(path: Union[str, Path]) -> Tuple[str, str, str]:
    """
    分割路径为目录、文件名和扩展名

    Args:
        path: 输入路径

    Returns:
        (directory, filename, extension) 元组

    Example:
        >>> split_path("/home/user/docs/file.txt")
        ('/home/user/docs', 'file', '.txt')
    """
    p = Path(path)
    directory = str(p.parent)
    filename = p.stem
    extension = p.suffix
    return (directory, filename, extension)


def join_path(*parts: Union[str, Path]) -> str:
    """
    安全地连接路径组件

    Args:
        *parts: 路径组件

    Returns:
        连接后的路径字符串

    Example:
        >>> join_path("/home", "user", "Documents", "file.txt")
        '/home/user/Documents/file.txt'
    """
    if not parts:
        return ""

    result = Path(str(parts[0]))
    for part in parts[1:]:
        result = result / str(part)

    return str(result)


def is_absolute_path(path: Union[str, Path]) -> bool:
    """
    检查是否是绝对路径

    Args:
        path: 要检查的路径

    Returns:
        是否是绝对路径
    """
    return Path(path).is_absolute()


def get_common_prefix(paths: List[Union[str, Path]]) -> Optional[Path]:
    """
    获取多个路径的公共前缀

    Args:
        paths: 路径列表

    Returns:
        公共前缀路径，如果没有则返回 None
    """
    if not paths:
        return None

    normalized = [Path(normalize_path(p)) for p in paths]

    if len(normalized) == 1:
        return normalized[0]

    common = normalized[0].parts
    for path in normalized[1:]:
        parts = path.parts
        # 找公共部分
        new_common = []
        for i, (c, p) in enumerate(zip(common, parts)):
            if c == p:
                new_common.append(c)
            else:
                break
        common = tuple(new_common)
        if not common:
            return None

    if common:
        return Path(*common)
    return None


class PathUtils:
    """
    路径工具类

    提供面向对象的路径操作接口。

    Example:
        >>> utils = PathUtils(base_dir="/home/user")
        >>> utils.resolve("Documents/file.txt")
        PosixPath('/home/user/Documents/file.txt')
    """

    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        """
        初始化路径工具

        Args:
            base_dir: 基础目录
        """
        self._base_dir = Path(normalize_path(base_dir)) if base_dir else None

    @property
    def base_dir(self) -> Optional[Path]:
        """获取基础目录"""
        return self._base_dir

    def normalize(self, path: Union[str, Path]) -> str:
        """规范化路径"""
        return normalize_path(path)

    def is_safe(
        self,
        path: Union[str, Path],
        allow_symlinks: bool = False
    ) -> Tuple[bool, str]:
        """检查路径是否安全"""
        return is_safe_path(path, self._base_dir, allow_symlinks)

    def resolve(
        self,
        path: Union[str, Path],
        must_exist: bool = False
    ) -> Path:
        """解析路径"""
        return resolve_path(path, self._base_dir, must_exist)

    def get_relative(self, path: Union[str, Path]) -> str:
        """获取相对路径"""
        if not self._base_dir:
            raise ValueError("Base directory not set")
        return get_relative_path(path, self._base_dir)

    def ensure_dir(
        self,
        path: Union[str, Path],
        mode: int = 0o755
    ) -> Path:
        """确保目录存在"""
        return ensure_directory(path, mode)

    def join(self, *parts: Union[str, Path]) -> str:
        """连接路径"""
        return join_path(*parts)

    def split(self, path: Union[str, Path]) -> Tuple[str, str, str]:
        """分割路径"""
        return split_path(path)


__all__ = [
    "normalize_path",
    "is_safe_path",
    "resolve_path",
    "get_relative_path",
    "ensure_directory",
    "split_path",
    "join_path",
    "is_absolute_path",
    "get_common_prefix",
    "PathUtils",
]
