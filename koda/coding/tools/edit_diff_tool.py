"""
Edit-Diff Tool - Structured file editing with diff format
Equivalent to Pi Mono's packages/coding-agent/src/core/tools/edit-diff.ts

Uses unified diff format for precise, reviewable edits.
"""
import re
import difflib
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
from enum import Enum
from pathlib import Path


class EditDiffError(Exception):
    """Error during diff application"""
    pass


@dataclass
class DiffHunk:
    """A single diff hunk"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]  # Lines with +/- prefix or space for context
    
    def __str__(self) -> str:
        return f"@@ -{self.old_start},{self.old_count} +{self.new_start},{self.new_count} @@"


@dataclass
class EditResult:
    """Result of applying an edit"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    hunks_applied: int = 0
    hunks_failed: int = 0


class EditDiffTool:
    """
    Apply edits using unified diff format.
    More precise than simple string replacement.
    """
    
    def apply_diff(
        self,
        original_content: str,
        diff_content: str,
        fuzz: int = 0
    ) -> EditResult:
        """
        Apply unified diff to content.
        
        Args:
            original_content: Original file content
            diff_content: Unified diff format patch
            fuzz: Allow fuzz factor for inexact matching
            
        Returns:
            EditResult with new content or error
        """
        try:
            # Parse the diff
            hunks = self._parse_diff(diff_content)
            
            if not hunks:
                return EditResult(
                    success=False,
                    error="No valid diff hunks found"
                )
            
            # Apply hunks
            lines = original_content.split('\n')
            new_lines = list(lines)
            
            # Track offset as we apply hunks
            line_offset = 0
            hunks_applied = 0
            hunks_failed = 0
            
            for hunk in hunks:
                try:
                    new_lines, adjustment = self._apply_hunk(
                        new_lines, 
                        hunk, 
                        line_offset,
                        fuzz
                    )
                    line_offset += adjustment
                    hunks_applied += 1
                except EditDiffError as e:
                    hunks_failed += 1
                    if hunks_failed == 1:  # First failure
                        return EditResult(
                            success=False,
                            error=f"Failed to apply hunk at line {hunk.old_start}: {e}"
                        )
            
            return EditResult(
                success=hunks_failed == 0,
                content='\n'.join(new_lines),
                hunks_applied=hunks_applied,
                hunks_failed=hunks_failed
            )
            
        except Exception as e:
            return EditResult(
                success=False,
                error=f"Failed to apply diff: {str(e)}"
            )
    
    def apply_diff_to_file(
        self,
        file_path: Union[str, Path],
        diff_content: str,
        dry_run: bool = False
    ) -> EditResult:
        """
        Apply diff directly to a file.
        
        Args:
            file_path: Path to file
            diff_content: Unified diff
            dry_run: If True, don't actually write changes
            
        Returns:
            EditResult
        """
        path = Path(file_path)
        
        if not path.exists():
            return EditResult(
                success=False,
                error=f"File not found: {file_path}"
            )
        
        original = path.read_text(encoding='utf-8')
        result = self.apply_diff(original, diff_content)
        
        if result.success and not dry_run:
            path.write_text(result.content, encoding='utf-8')
        
        return result
    
    def _parse_diff(self, diff_content: str) -> List[DiffHunk]:
        """Parse unified diff format into hunks"""
        hunks = []
        lines = diff_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for hunk header: @@ -start,count +start,count @@
            match = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1
                
                # Collect hunk lines
                hunk_lines = []
                i += 1
                
                while i < len(lines):
                    hunk_line = lines[i]
                    
                    # Stop at next hunk or end of diff
                    if hunk_line.startswith('@@') or hunk_line.startswith('diff '):
                        break
                    
                    # Only process diff lines
                    if hunk_line.startswith('+') or hunk_line.startswith('-') or \
                       hunk_line.startswith(' ') or hunk_line == '':
                        hunk_lines.append(hunk_line)
                        i += 1
                    else:
                        break
                
                hunks.append(DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    lines=hunk_lines
                ))
            else:
                i += 1
        
        return hunks
    
    def _apply_hunk(
        self,
        lines: List[str],
        hunk: DiffHunk,
        offset: int,
        fuzz: int
    ) -> Tuple[List[str], int]:
        """
        Apply a single hunk.
        
        Returns:
            Tuple of (new_lines, line_adjustment)
        """
        # Calculate actual line position (1-indexed in diff, 0-indexed in list)
        start_pos = hunk.old_start - 1 + offset
        
        if start_pos < 0 or start_pos > len(lines):
            raise EditDiffError(f"Hunk start position {start_pos} out of range")
        
        # Extract old and new content from hunk
        old_lines = []
        new_lines_in_hunk = []
        context_before = []
        context_after = []
        
        in_old = False
        for line in hunk.lines:
            if line.startswith('-'):
                old_lines.append(line[1:])
                in_old = True
            elif line.startswith('+'):
                new_lines_in_hunk.append(line[1:])
                in_old = False
            elif line.startswith(' '):
                content = line[1:]
                if not in_old and not old_lines:
                    context_before.append(content)
                else:
                    context_after.append(content)
                old_lines.append(content)
                new_lines_in_hunk.append(content)
        
        # Verify context matches
        if start_pos >= len(lines):
            raise EditDiffError("Hunk starts beyond file end")
        
        # Check context before
        for i, ctx_line in enumerate(context_before):
            check_pos = start_pos + i
            if check_pos < len(lines) and lines[check_pos] != ctx_line:
                if fuzz == 0:
                    raise EditDiffError(
                        f"Context mismatch at line {check_pos + 1}: "
                        f"expected '{ctx_line[:30]}...', got '{lines[check_pos][:30]}...'"
                    )
        
        # Apply the change
        # Remove old lines, insert new lines
        end_pos = start_pos + len(old_lines) - len(context_after)
        
        new_file_lines = lines[:start_pos] + new_lines_in_hunk + lines[end_pos:]
        
        # Calculate adjustment for subsequent hunks
        adjustment = len(new_lines_in_hunk) - len(old_lines)
        
        return new_file_lines, adjustment
    
    def generate_diff(
        self,
        original: str,
        modified: str,
        filename: str = "file",
        context_lines: int = 3
    ) -> str:
        """
        Generate unified diff between two contents.
        
        Args:
            original: Original content
            modified: Modified content
            filename: Filename for diff header
            context_lines: Number of context lines
            
        Returns:
            Unified diff string
        """
        original_lines = original.split('\n')
        modified_lines = modified.split('\n')
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm='',
            n=context_lines
        )
        
        return '\n'.join(diff)
    
    def apply_edit_instructions(
        self,
        content: str,
        instructions: str,
        old_string: Optional[str] = None,
        new_string: Optional[str] = None
    ) -> EditResult:
        """
        Apply edit using natural language instructions or explicit strings.
        Fallback for when diff format is not available.
        
        Args:
            content: Original content
            instructions: Description of changes
            old_string: Exact text to replace
            new_string: Replacement text
            
        Returns:
            EditResult
        """
        if old_string is not None and new_string is not None:
            # Exact string replacement
            if old_string not in content:
                return EditResult(
                    success=False,
                    error=f"Old string not found in content: {old_string[:50]}..."
                )
            
            new_content = content.replace(old_string, new_string, 1)
            return EditResult(
                success=True,
                content=new_content,
                hunks_applied=1
            )
        
        # Try to parse as diff first
        if '---' in instructions and '+++' in instructions:
            return self.apply_diff(content, instructions)
        
        return EditResult(
            success=False,
            error="Could not parse edit instructions. Provide diff format or old_string/new_string."
        )


def apply_edit(
    file_path: Union[str, Path],
    old_string: str,
    new_string: str
) -> EditResult:
    """
    Simple helper for string replacement edit.
    
    Args:
        file_path: Path to file
        old_string: Text to find
        new_string: Text to replace with
        
    Returns:
        EditResult
    """
    tool = EditDiffTool()
    path = Path(file_path)
    
    if not path.exists():
        return EditResult(
            success=False,
            error=f"File not found: {file_path}"
        )
    
    content = path.read_text(encoding='utf-8')
    result = tool.apply_edit_instructions(content, "", old_string, new_string)
    
    if result.success:
        path.write_text(result.content, encoding='utf-8')
    
    return result


def apply_diff_file(
    target_file: Union[str, Path],
    diff_file: Union[str, Path],
    dry_run: bool = False
) -> EditResult:
    """
    Apply a diff file to a target file.
    
    Args:
        target_file: File to patch
        diff_file: File containing unified diff
        dry_run: If True, don't actually apply changes
        
    Returns:
        EditResult
    """
    tool = EditDiffTool()
    diff_content = Path(diff_file).read_text(encoding='utf-8')
    return tool.apply_diff_to_file(target_file, diff_content, dry_run)
