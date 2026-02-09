"""
Grep Tool - Search file contents using ripgrep

Pi-compatible implementation based on: packages/coding-agent/src/core/tools/grep.ts
"""
import subprocess
import json
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from pathlib import Path

from koda.tools._support.truncation import truncate_head, format_size, DEFAULT_MAX_BYTES, GREP_MAX_LINE_LENGTH


@dataclass
class GrepResult:
    """Grep search result"""
    success: bool
    output: str
    match_count: int = 0
    truncated: bool = False
    match_limit_reached: bool = False
    lines_truncated: bool = False
    error: Optional[str] = None


class GrepTool:
    """
    Pi-compatible grep tool using ripgrep
    
    Features:
    - Regex or literal pattern search
    - Context lines before/after matches
    - Case insensitive option
    - Glob filtering
    - Respects .gitignore
    - Output truncation (100 matches or 50KB)
    """
    
    DEFAULT_LIMIT = 100
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._rg_available = None
    
    def _check_ripgrep(self) -> bool:
        """Check if ripgrep is available"""
        if self._rg_available is not None:
            return self._rg_available
        
        try:
            subprocess.run(['rg', '--version'], capture_output=True, check=True)
            self._rg_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self._rg_available = False
        
        return self._rg_available
    
    async def search(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        ignore_case: bool = False,
        literal: bool = False,
        context: int = 0,
        limit: Optional[int] = None,
    ) -> GrepResult:
        """
        Search file contents for a pattern
        
        Args:
            pattern: Search pattern (regex or literal string)
            path: Directory or file to search (default: current directory)
            glob: Filter files by glob pattern, e.g. '*.py'
            ignore_case: Case-insensitive search
            literal: Treat pattern as literal string instead of regex
            context: Number of context lines before/after each match
            limit: Maximum number of matches to return (default: 100)
            
        Returns:
            GrepResult
        """
        if not self._check_ripgrep():
            return GrepResult(
                success=False,
                output="",
                error="ripgrep (rg) is not available. Please install ripgrep."
            )
        
        search_path = self.base_path / (path or ".")
        search_path = search_path.resolve()
        
        if not search_path.exists():
            return GrepResult(
                success=False,
                output="",
                error=f"Path not found: {search_path}"
            )
        
        effective_limit = max(1, limit or self.DEFAULT_LIMIT)
        context_value = max(0, context or 0)
        
        # Build ripgrep arguments
        args = ['rg', '--json', '--line-number', '--color=never', '--hidden']
        
        if ignore_case:
            args.append('--ignore-case')
        
        if literal:
            args.append('--fixed-strings')
        
        if glob:
            args.extend(['--glob', glob])
        
        args.extend([pattern, str(search_path)])
        
        try:
            # Run ripgrep
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # ripgrep returns 1 when no matches found
            if result.returncode not in (0, 1):
                return GrepResult(
                    success=False,
                    output="",
                    error=f"ripgrep error: {result.stderr or f'exited with code {result.returncode}'}"
                )
            
            # Parse JSON output
            matches = []
            file_cache: Dict[str, List[str]] = {}
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                if event.get('type') == 'match':
                    data = event.get('data', {})
                    file_path = data.get('path', {}).get('text', '')
                    line_number = data.get('line_number', 0)
                    
                    if file_path and line_number:
                        matches.append({
                            'file': file_path,
                            'line': line_number
                        })
            
            if not matches:
                return GrepResult(
                    success=True,
                    output="No matches found",
                    match_count=0
                )
            
            # Limit matches
            match_limit_reached = len(matches) > effective_limit
            matches = matches[:effective_limit]
            
            # Format output with context
            output_lines = []
            lines_truncated = False
            
            for match in matches:
                file_path = match['file']
                line_number = match['line']
                
                # Cache file content
                if file_path not in file_cache:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        file_cache[file_path] = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
                    except Exception:
                        file_cache[file_path] = []
                
                lines = file_cache.get(file_path, [])
                if not lines:
                    output_lines.append(f"{file_path}:{line_number}: (unable to read file)")
                    continue
                
                # Calculate context range
                start = max(1, line_number - context_value)
                end = min(len(lines), line_number + context_value)
                
                for current in range(start, end + 1):
                    line_text = lines[current - 1] if current <= len(lines) else ""
                    is_match_line = current == line_number
                    
                    # Truncate long lines
                    truncated = truncate_line(line_text, GREP_MAX_LINE_LENGTH)
                    if truncated.was_truncated:
                        lines_truncated = True
                    
                    # Format output
                    relative_path = os.path.relpath(file_path, search_path)
                    if is_match_line:
                        output_lines.append(f"{relative_path}:{current}: {truncated.text}")
                    else:
                        output_lines.append(f"{relative_path}-{current}- {truncated.text}")
            
            # Apply byte truncation
            raw_output = '\n'.join(output_lines)
            truncation = truncate_head(raw_output, max_lines=float('inf'))
            
            output = truncation.content
            notices = []
            
            if match_limit_reached:
                notices.append(f"{effective_limit} matches limit reached. Use limit={effective_limit * 2} for more, or refine pattern")
            
            if truncation.truncated:
                notices.append(f"{format_size(DEFAULT_MAX_BYTES)} limit reached")
            
            if lines_truncated:
                notices.append(f"Some lines truncated to {GREP_MAX_LINE_LENGTH} chars. Use read tool to see full lines")
            
            if notices:
                output += f"\n\n[{'. '.join(notices)}]"
            
            return GrepResult(
                success=True,
                output=output,
                match_count=len(matches),
                truncated=truncation.truncated,
                match_limit_reached=match_limit_reached,
                lines_truncated=lines_truncated
            )
            
        except subprocess.TimeoutExpired:
            return GrepResult(
                success=False,
                output="",
                error="Search timed out after 60 seconds"
            )
        except Exception as e:
            return GrepResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}"
            )
