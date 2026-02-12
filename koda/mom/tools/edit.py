"""
Edit Tool - Precise file editing for Mom agent

Pi Mono compatible implementation:
- Precise string replacement
- Multi-occurrence detection
- Diff generation
- BOM and line ending handling
- Fuzzy matching fallback
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import re

from koda.mom.tools.write import write_file


# BOM constants
BOM_UTF8 = '\ufeff'

# Unicode normalization mappings for fuzzy matching
FUZZY_CHAR_MAPPINGS = {
    '\u2018': "'", '\u2019': "'",  # Smart single quotes
    '\u201c': '"', '\u201d': '"',  # Smart double quotes
    '\u2013': '-', '\u2014': '-', '\u2010': '-', '\u2011': '-',  # Dashes
    '\u00a0': ' ', '\u2002': ' ', '\u2003': ' ', '\u2009': ' ', '\u202f': ' ',  # Spaces
}


@dataclass
class EditResult:
    """Result from editing a file"""
    success: bool
    path: str
    diff: Optional[str] = None
    first_changed_line: Optional[int] = None
    occurrences_replaced: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EditOperation:
    """Represents a single edit operation"""
    old_string: str
    new_string: str
    replace_all: bool = False


def strip_bom(content: str) -> Tuple[str, str]:
    """Strip BOM from content."""
    if content.startswith(BOM_UTF8):
        return content[len(BOM_UTF8):], BOM_UTF8
    return content, ""


def detect_line_ending(content: str) -> str:
    """Detect line ending type."""
    if '\r\n' in content:
        return '\r\n'
    elif '\r' in content:
        return '\r'
    return '\n'


def normalize_to_lf(content: str) -> str:
    """Normalize all line endings to LF."""
    return content.replace('\r\n', '\n').replace('\r', '\n')


def restore_line_endings(content: str, original_ending: str) -> str:
    """Restore original line endings."""
    if original_ending == '\r\n':
        return content.replace('\n', '\r\n')
    elif original_ending == '\r':
        return content.replace('\n', '\r')
    return content


def normalize_unicode_chars(text: str) -> str:
    """Normalize Unicode special characters to ASCII equivalents."""
    for unicode_char, ascii_char in FUZZY_CHAR_MAPPINGS.items():
        text = text.replace(unicode_char, ascii_char)
    return text


def normalize_line_for_fuzzy(line: str) -> str:
    """Normalize a line for fuzzy matching."""
    line = normalize_unicode_chars(line)
    line = line.rstrip()  # Remove trailing whitespace
    line = re.sub(r'[ \t]+', ' ', line)  # Normalize internal whitespace
    return line


def count_occurrences(content: str, search_text: str) -> int:
    """Count occurrences of search text in content."""
    content_lines = content.split('\n')
    search_lines = search_text.split('\n')

    # Remove trailing empty lines from search text
    if search_lines and search_lines[-1] == '':
        search_lines = search_lines[:-1]

    norm_content_lines = [normalize_line_for_fuzzy(line) for line in content_lines]
    norm_search_lines = [normalize_line_for_fuzzy(line) for line in search_lines]

    if not norm_search_lines:
        return 0

    # Single line search
    if len(norm_search_lines) == 1:
        search_term = norm_search_lines[0]
        if not search_term:
            return 0
        # Count in normalized content
        norm_content = '\n'.join(norm_content_lines)
        return norm_content.count(search_term)

    # Multi-line search using sliding window
    count = 0
    for start_idx in range(len(content_lines) - len(search_lines) + 1):
        match = True
        for i, search_line in enumerate(norm_search_lines):
            if search_line != norm_content_lines[start_idx + i]:
                match = False
                break
        if match:
            count += 1

    return count


def fuzzy_find_with_replacement(
    content: str,
    search_text: str,
    replacement_text: str
) -> Tuple[bool, int, int, str]:
    """
    Fuzzy find text and prepare replacement.

    Returns:
        Tuple of (found, index, match_length, replacement_content)
    """
    # 1. Try exact match first
    if search_text in content:
        idx = content.index(search_text)
        new_content = content[:idx] + replacement_text + content[idx + len(search_text):]
        return True, idx, len(search_text), new_content

    # 2. Try fuzzy match
    content_lines = content.split('\n')
    search_lines = search_text.split('\n')

    # Remove trailing empty lines
    if search_lines and search_lines[-1] == '':
        search_lines = search_lines[:-1]

    # Normalize lines
    norm_content_lines = [normalize_line_for_fuzzy(line) for line in content_lines]
    norm_search_lines = [normalize_line_for_fuzzy(line) for line in search_lines]

    # Try line-level matching
    for start_idx in range(len(content_lines) - len(search_lines) + 1):
        match = True
        for i, search_line in enumerate(norm_search_lines):
            if search_line != norm_content_lines[start_idx + i]:
                match = False
                break

        if match:
            # Found match! Build replacement content
            end_idx = start_idx + len(search_lines)

            before = '\n'.join(content_lines[:start_idx])
            after_lines = content_lines[end_idx:]
            if after_lines and after_lines[-1] == '':
                after_lines = after_lines[:-1]
            after = '\n'.join(after_lines)

            result_parts = []
            if before:
                result_parts.append(before)
            result_parts.append(replacement_text.rstrip('\n'))
            if after:
                result_parts.append(after)

            new_content = '\n'.join(result_parts)

            # Preserve trailing newline if original had one
            if content.endswith('\n') and not new_content.endswith('\n'):
                new_content += '\n'

            # Calculate position
            start_pos = sum(len(content_lines[i]) + 1 for i in range(start_idx))
            end_pos = sum(len(content_lines[i]) + 1 for i in range(end_idx))

            return True, start_pos, end_pos - start_pos, new_content

    return False, 0, 0, content


def generate_diff(
    old_content: str,
    new_content: str,
    context: int = 3
) -> Tuple[str, Optional[int]]:
    """
    Generate unified diff format.

    Returns:
        Tuple of (diff_text, first_changed_line)
    """
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')

    diff_lines = []
    first_changed = None

    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None

        if old_line != new_line:
            if first_changed is None:
                first_changed = i + 1

            start = max(0, i - context)
            end = min(max_len, i + context + 1)

            if diff_lines:
                diff_lines.append("...")

            for j in range(start, end):
                if j < len(old_lines) and j < len(new_lines):
                    if old_lines[j] != new_lines[j]:
                        diff_lines.append(f"-{old_lines[j]}")
                        diff_lines.append(f"+{new_lines[j]}")
                    else:
                        diff_lines.append(f" {old_lines[j]}")
                elif j < len(old_lines):
                    diff_lines.append(f"-{old_lines[j]}")
                else:
                    diff_lines.append(f"+{new_lines[j]}")

    diff_text = '\n'.join(diff_lines) if diff_lines else "No changes"
    return diff_text, first_changed


def edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    base_path: Optional[Path] = None,
    replace_all: bool = False,
) -> EditResult:
    """
    Edit a file by replacing text (Pi Mono compatible).

    Args:
        file_path: Path to file (relative or absolute)
        old_string: Text to replace
        new_string: Replacement text
        base_path: Base directory for relative paths
        replace_all: Replace all occurrences (default: False)

    Returns:
        EditResult with status and diff
    """
    # Resolve path
    path = Path(file_path)
    if not path.is_absolute():
        if base_path:
            path = base_path / path
        else:
            path = Path.cwd() / path

    # Resolve to absolute path
    try:
        path = path.resolve()
    except Exception:
        pass

    # Check if file exists
    if not path.exists():
        return EditResult(
            success=False,
            path=str(path),
            error=f"File not found: {file_path}",
        )

    try:
        # Read file
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            raw_content = f.read()

        # Handle BOM
        content, bom = strip_bom(raw_content)

        # Detect and save original line ending
        original_ending = detect_line_ending(content)

        # Normalize to LF for matching
        normalized_content = normalize_to_lf(content)
        normalized_old = normalize_to_lf(old_string)
        normalized_new = normalize_to_lf(new_string)

        # Check for multiple occurrences
        if not replace_all:
            occurrences = count_occurrences(normalized_content, normalized_old)
            if occurrences > 1:
                return EditResult(
                    success=False,
                    path=str(path),
                    error=f"Found {occurrences} occurrences of the text in {file_path}. The text must be unique. Please provide more context to make it unique.",
                )

        # Find and replace
        if replace_all:
            # Replace all occurrences
            if normalized_old not in normalized_content:
                return EditResult(
                    success=False,
                    path=str(path),
                    error=f"Text not found in file: {file_path}",
                )
            new_normalized = normalized_content.replace(normalized_old, normalized_new)
            count = normalized_content.count(normalized_old)
        else:
            # Single replacement with fuzzy matching
            found, idx, match_len, new_normalized = fuzzy_find_with_replacement(
                normalized_content, normalized_old, normalized_new
            )

            if not found:
                return EditResult(
                    success=False,
                    path=str(path),
                    error=f"Could not find the exact text in {file_path}. The old text must match exactly including all whitespace and newlines.",
                )
            count = 1

        # Verify change
        if normalized_content == new_normalized:
            return EditResult(
                success=False,
                path=str(path),
                error=f"No changes made to {file_path}. The replacement produced identical content.",
            )

        # Restore line endings and BOM
        final_content = bom + restore_line_endings(new_normalized, original_ending)

        # Write back
        write_result = write_file(str(path), final_content, atomic=True)
        if not write_result.success:
            return EditResult(
                success=False,
                path=str(path),
                error=write_result.error,
            )

        # Generate diff
        diff_text, first_changed = generate_diff(normalized_content, new_normalized)

        return EditResult(
            success=True,
            path=str(path),
            diff=diff_text,
            first_changed_line=first_changed,
            occurrences_replaced=count,
        )

    except Exception as e:
        return EditResult(
            success=False,
            path=str(path),
            error=str(e),
        )


def create_edit(
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> EditOperation:
    """Create an edit operation."""
    return EditOperation(
        old_string=old_string,
        new_string=new_string,
        replace_all=replace_all,
    )


class EditTool:
    """
    Edit Tool class for Mom agent.

    Provides precise file editing capabilities with:
    - Exact string replacement
    - Multi-occurrence detection
    - Diff generation
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit a file."""
        return edit_file(file_path, old_string, new_string, self.base_path, replace_all)

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for LLM."""
        return {
            "name": "edit",
            "description": "Edit a file by replacing exact text. The old text must match exactly including whitespace and newlines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (relative or absolute)",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Text to replace (must match exactly)",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                    "replace_all": {
                        "type": "boolean",
                        "default": False,
                        "description": "Replace all occurrences",
                    },
                },
                "required": ["file_path", "old_string", "new_string"],
            },
        }
