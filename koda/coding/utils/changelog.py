"""
Changelog Utilities - 变更日志工具

解析和处理 CHANGELOG.md 文件，支持语义化版本。
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Dict, Union
from enum import Enum


class VersionBump(Enum):
    """版本号变更类型"""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    NONE = "none"


@dataclass
class Version:
    """语义化版本号"""
    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None
    build: Optional[str] = None

    @classmethod
    def parse(cls, version_str: str) -> Optional["Version"]:
        """
        解析版本字符串

        Args:
            version_str: 版本字符串（如 "1.2.3" 或 "v1.2.3-alpha+build"）

        Returns:
            Version 对象，解析失败返回 None
        """
        # 移除 'v' 前缀
        version_str = version_str.lstrip("vV")

        # 语义化版本正则
        pattern = r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$"
        match = re.match(pattern, version_str)

        if not match:
            return None

        major = int(match.group(1))
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)
        prerelease = match.group(4)
        build = match.group(5)

        return cls(major, minor, patch, prerelease, build)

    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.build:
            result += f"+{self.build}"
        return result

    def __lt__(self, other: "Version") -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        # 预发布版本低于正式版本
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return (self.prerelease or "") < (other.prerelease or "")

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        return not self < other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch, self.prerelease) == \
               (other.major, other.minor, other.patch, other.prerelease)

    def bump(self, bump_type: VersionBump) -> "Version":
        """
        增加版本号

        Args:
            bump_type: 变更类型

        Returns:
            新的 Version 对象
        """
        if bump_type == VersionBump.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif bump_type == VersionBump.MINOR:
            return Version(self.major, self.minor + 1, 0)
        elif bump_type == VersionBump.PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        return Version(self.major, self.minor, self.patch)


@dataclass
class ChangelogEntry:
    """变更日志条目"""
    version: Optional[Version] = None
    date: Optional[date] = None
    title: str = ""
    description: str = ""
    changes: Dict[str, List[str]] = field(default_factory=dict)  # 分类 -> 变更列表
    raw_content: str = ""

    @property
    def is_unreleased(self) -> bool:
        """是否是未发布版本"""
        return self.version is None or self.title.lower() == "unreleased"

    def get_changes(self, category: str) -> List[str]:
        """
        获取指定分类的变更

        Args:
            category: 分类名称（如 "Added", "Changed", "Fixed"）

        Returns:
            变更列表
        """
        # 支持不区分大小写的分类查找
        for key, values in self.changes.items():
            if key.lower() == category.lower():
                return values
        return []

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = []

        # 标题行
        if self.is_unreleased:
            lines.append("## [Unreleased]")
        else:
            version_str = str(self.version) if self.version else ""
            date_str = f" - {self.date}" if self.date else ""
            lines.append(f"## [{version_str}]{date_str}")

        # 描述
        if self.description:
            lines.append("")
            lines.append(self.description)

        # 各分类变更
        for category, items in self.changes.items():
            lines.append("")
            lines.append(f"### {category}")
            for item in items:
                if not item.startswith("-"):
                    lines.append(f"- {item}")
                else:
                    lines.append(item)

        return "\n".join(lines)


@dataclass
class Changelog:
    """变更日志"""
    title: str = "Changelog"
    description: str = ""
    entries: List[ChangelogEntry] = field(default_factory=list)

    def get_latest_entry(self) -> Optional[ChangelogEntry]:
        """获取最新条目"""
        if not self.entries:
            return None
        # 排除 Unreleased，获取第一个正式版本
        for entry in self.entries:
            if not entry.is_unreleased:
                return entry
        return self.entries[0]

    def get_entry(self, version: Union[str, Version]) -> Optional[ChangelogEntry]:
        """
        获取指定版本的条目

        Args:
            version: 版本号

        Returns:
            ChangelogEntry 或 None
        """
        target_version = Version.parse(str(version)) if isinstance(version, str) else version

        for entry in self.entries:
            if entry.version == target_version:
                return entry

        return None

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [f"# {self.title}"]

        if self.description:
            lines.append("")
            lines.append(self.description)

        for entry in self.entries:
            lines.append("")
            lines.append(entry.to_markdown())

        return "\n".join(lines)


class ChangelogParser:
    """
    变更日志解析器

    支持多种 CHANGELOG 格式：
    - Keep a Changelog
    - GitHub Releases
    - 简单版本列表

    Example:
        >>> parser = ChangelogParser()
        >>> changelog = parser.parse("CHANGELOG.md")
        >>> latest = changelog.get_latest_entry()
        >>> print(latest.version)
    """

    # 版本标题正则
    VERSION_PATTERNS = [
        # [1.2.3] - 2024-01-15
        r"^##\s*\[?v?(\d+\.\d+\.\d+(?:[-+][\w.]+)?)\]?\s*(?:-\s*(\d{4}-\d{2}-\d{2}))?",
        # ## 1.2.3 (2024-01-15)
        r"^##\s*v?(\d+\.\d+\.\d+(?:[-+][\w.]+)?)\s*\((\d{4}-\d{2}-\d{2})\)",
        # ## Release 1.2.3
        r"^##\s+Release\s+v?(\d+\.\d+\.\d+(?:[-+][\w.]+)?)",
        # ## Unreleased
        r"^##\s*\[Unreleased\]",
    ]

    # 变更分类
    CHANGE_CATEGORIES = [
        "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security",
        "Features", "Bug Fixes", "Improvements", "Documentation", "Refactoring",
        "New", "Updates", "Notes"
    ]

    def __init__(self):
        self._category_pattern = re.compile(
            r"^###\s+(" + "|".join(self.CHANGE_CATEGORIES) + r")",
            re.IGNORECASE
        )

    def parse(self, source: Union[str, Path]) -> Changelog:
        """
        解析 CHANGELOG

        Args:
            source: 文件路径或内容字符串

        Returns:
            Changelog 对象
        """
        # 判断是文件路径还是内容
        if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and len(source) < 256):
            path = Path(source)
            if path.exists():
                content = path.read_text(encoding="utf-8")
            else:
                content = source
        else:
            content = source

        return self._parse_content(content)

    def _parse_content(self, content: str) -> Changelog:
        """解析内容"""
        lines = content.split("\n")
        changelog = Changelog()

        # 解析标题和描述
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith("# "):
                changelog.title = line[2:].strip()
                i += 1
                continue

            # 遇到版本标题，开始解析条目
            if self._is_version_header(line):
                break

            # 收集描述
            if line and not line.startswith("##"):
                changelog.description += line + "\n"

            i += 1

        changelog.description = changelog.description.strip()

        # 解析版本条目
        while i < len(lines):
            line = lines[i].strip()

            if self._is_version_header(line):
                entry, i = self._parse_entry(lines, i)
                changelog.entries.append(entry)
            else:
                i += 1

        return changelog

    def _is_version_header(self, line: str) -> bool:
        """检查是否是版本标题"""
        if not line.startswith("## "):
            return False

        for pattern in self.VERSION_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        return False

    def _parse_entry(self, lines: List[str], start: int) -> tuple:
        """解析单个条目"""
        entry = ChangelogEntry()
        i = start
        current_category = None
        content_lines = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 遇到下一个版本标题，结束当前条目
            if i > start and self._is_version_header(stripped):
                break

            content_lines.append(line)

            # 解析版本标题
            if i == start:
                entry.title = stripped[3:].strip()  # 移除 "## "

                # 尝试提取版本和日期
                for pattern in self.VERSION_PATTERNS:
                    match = re.match(pattern, stripped, re.IGNORECASE)
                    if match:
                        if "Unreleased" in stripped:
                            entry.version = None
                        else:
                            entry.version = Version.parse(match.group(1))

                        if len(match.groups()) > 1 and match.group(2):
                            try:
                                entry.date = datetime.strptime(match.group(2), "%Y-%m-%d").date()
                            except ValueError:
                                pass
                        break

            # 解析分类标题
            elif self._category_pattern.match(stripped):
                current_category = self._category_pattern.match(stripped).group(1)
                entry.changes[current_category] = []

            # 解析变更项
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if current_category:
                    entry.changes[current_category].append(stripped)
                else:
                    # 没有分类的变更
                    if "Other" not in entry.changes:
                        entry.changes["Other"] = []
                    entry.changes["Other"].append(stripped)

            # 描述文本
            elif stripped and not stripped.startswith("#"):
                if not current_category and not entry.changes:
                    entry.description += stripped + "\n"

            i += 1

        entry.description = entry.description.strip()
        entry.raw_content = "\n".join(content_lines)

        return entry, i


def parse_changelog(source: Union[str, Path]) -> Changelog:
    """
    解析 CHANGELOG 的便捷函数

    Args:
        source: 文件路径或内容

    Returns:
        Changelog 对象
    """
    parser = ChangelogParser()
    return parser.parse(source)


def compare_versions(v1: Union[str, Version], v2: Union[str, Version]) -> int:
    """
    比较两个版本

    Args:
        v1: 版本1
        v2: 版本2

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    ver1 = Version.parse(str(v1)) if isinstance(v1, str) else v1
    ver2 = Version.parse(str(v2)) if isinstance(v2, str) else v2

    if ver1 < ver2:
        return -1
    elif ver1 > ver2:
        return 1
    return 0


def detect_version_bump(changes: Dict[str, List[str]]) -> VersionBump:
    """
    根据变更类型检测版本变更类型

    Args:
        changes: 变更字典 {category: [items]}

    Returns:
        VersionBump 类型
    """
    categories_lower = {k.lower() for k in changes.keys()}

    # Breaking changes 或 Removed -> Major
    if "removed" in categories_lower or "breaking" in categories_lower:
        return VersionBump.MAJOR

    # Added, Features -> Minor
    if "added" in categories_lower or "features" in categories_lower or "new" in categories_lower:
        return VersionBump.MINOR

    # Fixed, Changed, Security -> Patch
    if "fixed" in categories_lower or "changed" in categories_lower or "security" in categories_lower:
        return VersionBump.PATCH

    return VersionBump.NONE


__all__ = [
    "Version",
    "VersionBump",
    "ChangelogEntry",
    "Changelog",
    "ChangelogParser",
    "parse_changelog",
    "compare_versions",
    "detect_version_bump",
]
