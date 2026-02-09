"""
Find Tool - Search for files by glob pattern

Pi-compatible implementation based on: packages/coding-agent/src/core/tools/find.ts
"""
import subprocess
import os
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from koda.coding._support.truncation import truncate_head, format_size, DEFAULT_MAX_BYTES


@dataclass
class FindResult:
    """Find search result"""
    success: bool
    output: str
    file_count: int = 0
    truncated: bool = False
    limit_reached: bool = False
    error: Optional[str] = None


class FindTool:
    """
    Pi-compatible find tool using fd
    
    Features:
    - Glob pattern matching
    - Respects .gitignore
    - Hidden files included
    - Output truncation (1000 results or 50KB)
    """
    
    DEFAULT_LIMIT = 1000
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._fd_available = None
    
    def _check_fd(self) -> bool:
        """Check if fd is available"""
        if self._fd_available is not None:
            return self._fd_available
        
        try:
            subprocess.run(['fd', '--version'], capture_output=True, check=True)
            self._fd_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._fd_available = False
        
        return self._fd_available
    
    async def search(
        self,
        pattern: str,
        path: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> FindResult:
        """
        Search for files by glob pattern
        
        Args:
            pattern: Glob pattern to match files, e.g. '*.py', '**/*.json'
            path: Directory to search in (default: current directory)
            limit: Maximum number of results (default: 1000)
            
        Returns:
            FindResult
        """
        search_path = self.base_path / (path or ".")
        search_path = search_path.resolve()
        
        if not search_path.exists():
            return FindResult(
                success=False,
                output="",
                error=f"Path not found: {search_path}"
            )
        
        effective_limit = limit or self.DEFAULT_LIMIT
        
        # Try using fd first
        if self._check_fd():
            return await self._search_with_fd(pattern, search_path, effective_limit)
        else:
            # Fallback to Python glob
            return await self._search_with_glob(pattern, search_path, effective_limit)
    
    async def _search_with_fd(
        self,
        pattern: str,
        search_path: Path,
        limit: int
    ) -> FindResult:
        """Search using fd command"""
        try:
            # Build fd arguments
            args = [
                'fd',
                '--glob',
                '--color=never',
                '--hidden',
                '--max-results', str(limit),
                pattern,
                str(search_path)
            ]
            
            # Add .gitignore files
            gitignore_files = []
            root_gitignore = search_path / ".gitignore"
            if root_gitignore.exists():
                gitignore_files.append(str(root_gitignore))
            
            # Find nested .gitignore files
            try:
                for root, dirs, files in os.walk(search_path):
                    if '.git' in root or 'node_modules' in root:
                        dirs[:] = []
                        continue
                    for file in files:
                        if file == '.gitignore':
                            gitignore_files.append(os.path.join(root, file))
            except Exception:
                pass
            
            for gitignore_path in gitignore_files:
                args.extend(['--ignore-file', gitignore_path])
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # fd returns 1 when no matches found
            if result.returncode not in (0, 1):
                return FindResult(
                    success=False,
                    output="",
                    error=f"fd error: {result.stderr or f'exited with code {result.returncode}'}"
                )
            
            lines = result.stdout.strip().split('\n') if result.stdout else []
            lines = [l for l in lines if l]
            
            if not lines:
                return FindResult(
                    success=True,
                    output="No files found matching pattern",
                    file_count=0
                )
            
            # Relativize paths
            results = []
            for line in lines:
                line = line.rstrip('\\/')
                if line.startswith(str(search_path)):
                    relative = line[len(str(search_path)):].lstrip('\\/')
                else:
                    relative = os.path.relpath(line, search_path)
                results.append(relative.replace('\\', '/'))
            
            return self._format_results(results, limit)
            
        except subprocess.TimeoutExpired:
            return FindResult(
                success=False,
                output="",
                error="Search timed out after 30 seconds"
            )
        except Exception as e:
            return FindResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}"
            )
    
    async def _search_with_glob(
        self,
        pattern: str,
        search_path: Path,
        limit: int
    ) -> FindResult:
        """Fallback search using Python glob"""
        try:
            import glob
            
            # Build search pattern
            if '**' in pattern:
                # Recursive glob
                search_pattern = str(search_path / '**' / pattern.replace('**/', ''))
            else:
                search_pattern = str(search_path / pattern)
            
            matches = glob.glob(search_pattern, recursive=True)
            
            # Filter out ignored directories
            filtered = []
            for match in matches:
                if '.git' in match or 'node_modules' in match:
                    continue
                filtered.append(match)
            
            # Limit results
            limit_reached = len(filtered) > limit
            filtered = filtered[:limit]
            
            if not filtered:
                return FindResult(
                    success=True,
                    output="No files found matching pattern",
                    file_count=0
                )
            
            # Relativize paths
            results = []
            for match in filtered:
                if os.path.isdir(match):
                    match += '/'
                relative = os.path.relpath(match, search_path)
                results.append(relative.replace('\\', '/'))
            
            return self._format_results(results, limit)
            
        except Exception as e:
            return FindResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}"
            )
    
    def _format_results(self, results: List[str], limit: int) -> FindResult:
        """Format and truncate results"""
        limit_reached = len(results) >= limit
        
        raw_output = '\n'.join(results)
        truncation = truncate_head(raw_output, max_lines=float('inf'))
        
        output = truncation.content
        notices = []
        
        if limit_reached:
            notices.append(f"{limit} results limit reached. Use limit={limit * 2} for more, or refine pattern")
        
        if truncation.truncated:
            notices.append(f"{format_size(DEFAULT_MAX_BYTES)} limit reached")
        
        if notices:
            output += f"\n\n[{'. '.join(notices)}]"
        
        return FindResult(
            success=True,
            output=output,
            file_count=len(results),
            truncated=truncation.truncated,
            limit_reached=limit_reached
        )
