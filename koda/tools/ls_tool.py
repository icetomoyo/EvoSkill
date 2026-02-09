"""
Ls Tool - List directory contents

Pi-compatible implementation based on: packages/coding-agent/src/core/tools/ls.ts
"""
import os
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from koda.tools._support.truncation import truncate_head, format_size, DEFAULT_MAX_BYTES


@dataclass
class LsResult:
    """Directory listing result"""
    success: bool
    output: str
    entry_count: int = 0
    truncated: bool = False
    limit_reached: bool = False
    error: Optional[str] = None


class LsTool:
    """
    Pi-compatible ls tool
    
    Features:
    - List directory entries
    - Sorted alphabetically (case-insensitive)
    - '/' suffix for directories
    - Includes dotfiles
    - Output truncation (500 entries or 50KB)
    """
    
    DEFAULT_LIMIT = 500
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
    
    async def list(
        self,
        path: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> LsResult:
        """
        List directory contents
        
        Args:
            path: Directory to list (default: current directory)
            limit: Maximum number of entries to return (default: 500)
            
        Returns:
            LsResult
        """
        dir_path = self.base_path / (path or ".")
        dir_path = dir_path.resolve()
        
        effective_limit = limit or self.DEFAULT_LIMIT
        
        # Check if path exists
        if not dir_path.exists():
            return LsResult(
                success=False,
                output="",
                error=f"Path not found: {dir_path}"
            )
        
        # Check if path is a directory
        if not dir_path.is_dir():
            return LsResult(
                success=False,
                output="",
                error=f"Not a directory: {dir_path}"
            )
        
        try:
            # Read directory entries
            try:
                entries = os.listdir(dir_path)
            except Exception as e:
                return LsResult(
                    success=False,
                    output="",
                    error=f"Cannot read directory: {e}"
                )
            
            # Sort alphabetically (case-insensitive)
            entries.sort(key=lambda x: x.lower())
            
            # Format entries with directory indicators
            results = []
            limit_reached = False
            
            for entry in entries:
                if len(results) >= effective_limit:
                    limit_reached = True
                    break
                
                full_path = dir_path / entry
                suffix = ""
                
                try:
                    if full_path.is_dir():
                        suffix = "/"
                except Exception:
                    # Skip entries we can't stat
                    continue
                
                results.append(entry + suffix)
            
            if not results:
                return LsResult(
                    success=True,
                    output="(empty directory)",
                    entry_count=0
                )
            
            # Apply byte truncation
            raw_output = '\n'.join(results)
            truncation = truncate_head(raw_output, max_lines=float('inf'))
            
            output = truncation.content
            notices = []
            
            if limit_reached:
                notices.append(f"{effective_limit} entries limit reached. Use limit={effective_limit * 2} for more")
            
            if truncation.truncated:
                notices.append(f"{format_size(DEFAULT_MAX_BYTES)} limit reached")
            
            if notices:
                output += f"\n\n[{'. '.join(notices)}]"
            
            return LsResult(
                success=True,
                output=output,
                entry_count=len(results),
                truncated=truncation.truncated,
                limit_reached=limit_reached
            )
            
        except Exception as e:
            return LsResult(
                success=False,
                output="",
                error=f"Failed to list directory: {str(e)}"
            )
