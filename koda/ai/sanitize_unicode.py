"""
Unicode Sanitization
Equivalent to Pi Mono's packages/ai/src/utils/sanitize-unicode.ts

Removes orphaned Unicode surrogates and other invalid characters.
"""
import re


def sanitize_surrogates(text: str) -> str:
    """
    Remove orphaned Unicode surrogate pairs from text.

    Surrogates are used in UTF-16 to encode characters outside the Basic Multilingual Plane
    (code points U+10000 to U+10FFFF). A surrogate pair consists of a high surrogate
    (U+D800 to U+DBFF) followed by a low surrogate (U+DC00 to U+DFFF).

    Orphaned surrogates (high without low, or low without high) are invalid in UTF-8
    and can cause issues with JSON encoding, databases, and other systems.

    This function removes:
    - Orphaned high surrogates (U+D800-U+DBFF not followed by U+DC00-U+DFFF)
    - Orphaned low surrogates (U+DC00-U+DFFF not preceded by U+D800-U+DBFF)
    - Lone surrogates at string boundaries

    Args:
        text: Input text that may contain surrogates

    Returns:
        Text with orphaned surrogates removed

    Examples:
        >>> sanitize_surrogates("Hello \ud800World")  # orphaned high
        'Hello World'
        >>> sanitize_surrogates("Hello \udc00World")  # orphaned low
        'Hello World'
        >>> sanitize_surrogates("Hello \ud800\udc00World")  # valid pair
        'Hello \ud800\udc00World'
    """
    if not text:
        return text

    # Pattern for orphaned high surrogate (U+D800-U+DBFF) not followed by low surrogate
    # Match: high surrogate at end of string, or followed by non-low-surrogate
    orphaned_high = re.compile(r'[\ud800-\udbff](?![\udc00-\udfff])')

    # Pattern for orphaned low surrogate (U+DC00-U+DFFF) not preceded by high surrogate
    # Match: low surrogate at start of string, or preceded by non-high-surrogate
    orphaned_low = re.compile(r'(?<![\ud800-\udbff])[\udc00-\udfff]')

    # Remove orphaned high surrogates first
    text = orphaned_high.sub('', text)

    # Then remove orphaned low surrogates
    text = orphaned_low.sub('', text)

    return text


def sanitize_control_chars(text: str, keep_newlines: bool = True) -> str:
    """
    Remove control characters from text.

    Removes C0 control characters (U+0000-U+001F) and C1 control characters (U+007F-U+009F),
    optionally keeping newlines and carriage returns.

    Args:
        text: Input text
        keep_newlines: If True, keep \n (0x0A) and \r (0x0D)

    Returns:
        Text with control characters removed
    """
    if not text:
        return text

    if keep_newlines:
        # Keep tab (\t), newline (\n), carriage return (\r)
        allowed = '\t\n\r'
        pattern = f'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]'
    else:
        pattern = '[\x00-\x1f\x7f-\x9f]'

    return re.sub(pattern, '', text)


def sanitize_for_json(text: str) -> str:
    """
    Sanitize text for safe JSON encoding.

    Combines surrogate removal and control character removal to ensure
    the text can be safely encoded as JSON.

    Args:
        text: Input text

    Returns:
        JSON-safe text
    """
    # Remove surrogates first
    text = sanitize_surrogates(text)

    # Remove control characters (keeping newlines)
    text = sanitize_control_chars(text, keep_newlines=True)

    return text


def has_surrogates(text: str) -> bool:
    """
    Check if text contains any Unicode surrogates.

    Args:
        text: Input text

    Returns:
        True if text contains high or low surrogates
    """
    if not text:
        return False

    # Check for high surrogates (U+D800-U+DBFF)
    high_surrogate = re.compile(r'[\ud800-\udbff]')
    # Check for low surrogates (U+DC00-U+DFFF)
    low_surrogate = re.compile(r'[\udc00-\udfff]')

    return bool(high_surrogate.search(text) or low_surrogate.search(text))


def has_orphaned_surrogates(text: str) -> bool:
    """
    Check if text contains orphaned Unicode surrogates.

    Args:
        text: Input text

    Returns:
        True if text contains orphaned surrogates
    """
    if not text:
        return False

    # Pattern for valid surrogate pairs
    valid_pair = re.compile(r'[\ud800-\udbff][\udc00-\udfff]')

    # Remove valid pairs and check if any surrogates remain
    remaining = valid_pair.sub('', text)

    # Check if any surrogates remain (these would be orphaned)
    return has_surrogates(remaining)
