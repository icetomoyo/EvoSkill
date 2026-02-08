"""
SearchTool - 代码和文件搜索工具

支持文本搜索、代码搜索、文件查找等。
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path


@dataclass
class SearchResult:
    """搜索结果"""
    file: str
    line: int
    column: int
    content: str
    context: List[str]  # 上下文行


class SearchTool:
    """
    代码搜索工具
    
    Example:
        tool = SearchTool("/path/to/project")
        results = await tool.search_text("TODO", "*.py")
        for r in results:
            print(f"{r.file}:{r.line}: {r.content}")
    """
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
    
    async def search_text(
        self,
        query: str,
        pattern: str = "*",
        context_lines: int = 2,
    ) -> List[SearchResult]:
        """
        文本搜索
        
        Args:
            query: 搜索关键词
            pattern: 文件匹配模式
            context_lines: 上下文行数
            
        Returns:
            搜索结果列表
        """
        results = []
        
        for file_path in self.base_path.rglob(pattern):
            if not file_path.is_file():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    if query in line:
                        # 获取上下文
                        start = max(0, i - context_lines - 1)
                        end = min(len(lines), i + context_lines)
                        context = [l.rstrip() for l in lines[start:end]]
                        
                        results.append(SearchResult(
                            file=str(file_path.relative_to(self.base_path)),
                            line=i,
                            column=line.find(query),
                            content=line.strip(),
                            context=context,
                        ))
            except Exception:
                continue
        
        return results
    
    async def search_regex(
        self,
        pattern: str,
        file_pattern: str = "*",
        context_lines: int = 2,
    ) -> List[SearchResult]:
        """
        正则表达式搜索
        
        Args:
            pattern: 正则表达式
            file_pattern: 文件匹配模式
            context_lines: 上下文行数
            
        Returns:
            搜索结果列表
        """
        regex = re.compile(pattern)
        results = []
        
        for file_path in self.base_path.rglob(file_pattern):
            if not file_path.is_file():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        start = max(0, i - context_lines - 1)
                        end = min(len(lines), i + context_lines)
                        context = lines[start:end]
                        
                        match = regex.search(line)
                        results.append(SearchResult(
                            file=str(file_path.relative_to(self.base_path)),
                            line=i,
                            column=match.start() if match else 0,
                            content=line.strip(),
                            context=context,
                        ))
            except Exception:
                continue
        
        return results
    
    async def find_files(
        self,
        pattern: str,
        exclude_dirs: Optional[List[str]] = None,
    ) -> List[str]:
        """
        查找文件
        
        Args:
            pattern: 文件匹配模式
            exclude_dirs: 排除的目录
            
        Returns:
            文件路径列表
        """
        exclude_dirs = exclude_dirs or ['.git', '__pycache__', 'node_modules', '.venv']
        results = []
        
        for file_path in self.base_path.rglob(pattern):
            if not file_path.is_file():
                continue
            
            # 检查是否在排除目录中
            relative = file_path.relative_to(self.base_path)
            if any(part in exclude_dirs for part in relative.parts):
                continue
            
            results.append(str(relative))
        
        return results
    
    async def grep_code(
        self,
        symbol: str,
        language: str = "python",
    ) -> List[SearchResult]:
        """
        代码符号搜索（函数、类等）
        
        Args:
            symbol: 符号名
            language: 编程语言
            
        Returns:
            搜索结果列表
        """
        patterns = {
            "python": [
                rf"^\s*def\s+{symbol}\s*\(",  # 函数定义
                rf"^\s*class\s+{symbol}\s*[\(:]",  # 类定义
                rf"\b{symbol}\s*\(",  # 函数调用
            ],
            "javascript": [
                rf"function\s+{symbol}\s*\(",
                rf"{symbol}\s*[:=]\s*function",
                rf"class\s+{symbol}",
            ],
        }
        
        regex_patterns = patterns.get(language, patterns["python"])
        all_results = []
        
        for regex in regex_patterns:
            results = await self.search_regex(regex, f"*.{language[:2]}")
            all_results.extend(results)
        
        return all_results
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "search",
            "base_path": str(self.base_path),
        }
