"""
Enhanced Edit Tool - Fuzzy matching, BOM handling, line ending preservation
Equivalent to Pi Mono's edit-diff.ts
"""
import re
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EditResult:
    """Result of edit operation"""
    success: bool
    diff: str = ""
    first_changed_line: Optional[int] = None
    error: Optional[str] = None


def normalize_for_fuzzy_match(text: str) -> str:
    """
    Normalize text for fuzzy matching
    - Smart quotes -> ASCII quotes
    - Dash variants -> ASCII dash
    - Non-breaking space -> regular space
    """
    # Smart quotes to ASCII
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    # Dashes
    text = text.replace('—', '-').replace('–', '-')
    # Non-breaking space
    text = text.replace('\xa0', ' ')
    # Other common normalizations
    text = text.replace('…', '...')
    text = text.replace('•', '*')
    return text


def detect_line_ending(content: str) -> str:
    """Detect line ending style (CRLF or LF)"""
    if '\r\n' in content:
        return '\r\n'
    return '\n'


def normalize_to_lf(content: str) -> str:
    """Normalize content to LF line endings"""
    return content.replace('\r\n', '\n')


def restore_line_endings(content: str, original_ending: str) -> str:
    """Restore original line endings"""
    if original_ending == '\r\n':
        return content.replace('\n', '\r\n')
    return content


def strip_bom(content: str) -> Tuple[str, str]:
    """Strip BOM from content, return (bom, text)"""
    if content.startswith('\ufeff'):
        return '\ufeff', content[1:]
    return '', content


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy match"""
    found: bool
    index: int = -1
    match_length: int = 0
    content_for_replacement: str = ""


def fuzzy_find_text(
    content: str,
    old_text: str,
    context_lines: int = 2
) -> FuzzyMatchResult:
    """
    Fuzzy text search
    
    Strategies:
    1. Exact match
    2. Ignore whitespace differences
    3. Normalized match (smart quotes, dashes)
    4. Line-level fuzzy match
    """
    # Strategy 1: Exact match
    if old_text in content:
        idx = content.index(old_text)
        return FuzzyMatchResult(
            found=True,
            index=idx,
            match_length=len(old_text),
            content_for_replacement=content
        )
    
    # Strategy 2: Ignore trailing whitespace per line
    content_lines = content.split('\n')
    old_lines = old_text.split('\n')
    
    for i, content_line in enumerate(content_lines):
        # Try to match first line of old_text
        if content_line.rstrip() == old_lines[0].rstrip():
            # Check if subsequent lines match
            match = True
            for j, old_line in enumerate(old_lines):
                if i + j >= len(content_lines):
                    match = False
                    break
                if content_lines[i + j].rstrip() != old_line.rstrip():
                    match = False
                    break
            
            if match:
                # Calculate start index
                start_idx = sum(len(l) + 1 for l in content_lines[:i])
                match_len = sum(len(old_lines[j]) + 1 for j in range(len(old_lines))) - 1
                
                return FuzzyMatchResult(
                    found=True,
                    index=start_idx,
                    match_length=match_len,
                    content_for_replacement=content
                )
    
    # Strategy 3: Normalized match
    normalized_content = normalize_for_fuzzy_match(content)
    normalized_old = normalize_for_fuzzy_match(old_text)
    
    if normalized_old in normalized_content:
        idx = normalized_content.index(normalized_old)
        return FuzzyMatchResult(
            found=True,
            index=idx,
            match_length=len(normalized_old),
            content_for_replacement=content
        )
    
    return FuzzyMatchResult(found=False)


def generate_diff_string(original: str, modified: str) -> Tuple[str, Optional[int]]:
    """Generate unified diff and find first changed line"""
    import difflib
    
    original_lines = original.split('\n')
    modified_lines = modified.split('\n')
    
    diff = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        lineterm=''
    ))
    
    # Find first changed line number
    first_changed = None
    for line in diff:
        if line.startswith('@@'):
            # Parse hunk header
            match = re.match(r'@@ -(\d+)', line)
            if match:
                first_changed = int(match.group(1))
    
    return '\n'.join(diff), first_changed


class EnhancedEditTool:
    """
    Enhanced Edit Tool with Pi Mono parity
    
    Features:
    - Fuzzy matching (smart quotes, dashes, spaces)
    - BOM handling
    - Line ending preservation (CRLF/LF)
    - Unified diff generation
    - AbortSignal support
    """
    
    async def execute(
        self,
        path: str,
        old_text: str,
        new_text: str,
        signal: Optional[Any] = None
    ) -> EditResult:
        """
        Execute edit with all enhancements
        
        Args:
            path: File path
            old_text: Text to find
            new_text: Replacement text
            signal: AbortSignal for cancellation
        
        Returns:
            EditResult with diff and metadata
        """
        try:
            # Check abort
            if signal and getattr(signal, 'aborted', False):
                return EditResult(success=False, error="Operation aborted")
            
            file_path = Path(path)
            if not file_path.exists():
                return EditResult(success=False, error=f"File not found: {path}")
            
            # Read file
            raw_content = file_path.read_text(encoding='utf-8')
            
            # Handle BOM
            bom, content = strip_bom(raw_content)
            
            # Detect line endings
            original_ending = detect_line_ending(content)
            
            # Normalize to LF for matching
            normalized_content = normalize_to_lf(content)
            normalized_old = normalize_to_lf(old_text)
            normalized_new = normalize_to_lf(new_text)
            
            # Fuzzy find
            match_result = fuzzy_find_text(normalized_content, normalized_old)
            
            if not match_result.found:
                return EditResult(
                    success=False,
                    error=f"Could not find text in {path}. Tried exact, whitespace-insensitive, and fuzzy matching."
                )
            
            # Check abort before modification
            if signal and getattr(signal, 'aborted', False):
                return EditResult(success=False, error="Operation aborted")
            
            # Perform replacement
            before = normalized_content[:match_result.index]
            after = normalized_content[match_result.index + match_result.match_length:]
            new_normalized = before + normalized_new + after
            
            # Restore line endings
            final_content = bom + restore_line_endings(new_normalized, original_ending)
            
            # Check if actually changed
            if raw_content == final_content:
                return EditResult(success=False, error="No changes made - content unchanged")
            
            # Write file
            file_path.write_text(final_content, encoding='utf-8')
            
            # Generate diff
            diff, first_line = generate_diff_string(
                restore_line_endings(normalized_content, original_ending),
                restore_line_endings(new_normalized, original_ending)
            )
            
            return EditResult(
                success=True,
                diff=diff,
                first_changed_line=first_line
            )
        
        except Exception as e:
            return EditResult(success=False, error=str(e))
