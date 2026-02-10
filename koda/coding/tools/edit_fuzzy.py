"""
Edit Fuzzy Matching - Advanced fuzzy text matching for edits

Equivalent to Pi Mono's fuzzy matching features:
- fuzzyFindText with similarity scoring
- normalizeForFuzzyMatch with Unicode normalization
- Levenshtein distance for approximate matching
"""
import re
import difflib
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class FuzzyMatch:
    """Detailed fuzzy match result"""
    found: bool
    start: int = -1
    end: int = -1
    matched_text: str = ""
    similarity: float = 0.0
    confidence: str = "none"  # none, low, medium, high, exact
    
    def is_good_match(self, threshold: float = 0.8) -> bool:
        """Check if this is a good enough match"""
        return self.found and self.similarity >= threshold


class FuzzyMatcher:
    """
    Advanced fuzzy text matcher
    
    Implements multiple matching strategies with confidence scoring
    """
    
    # Confidence thresholds
    EXACT = 1.0
    HIGH = 0.9
    MEDIUM = 0.75
    LOW = 0.6
    
    def __init__(self, context_lines: int = 2):
        self.context_lines = context_lines
    
    def find(
        self,
        content: str,
        pattern: str,
        threshold: float = 0.8
    ) -> FuzzyMatch:
        """
        Find pattern in content using multiple strategies
        
        Args:
            content: Text to search in
            pattern: Text to find
            threshold: Minimum similarity threshold
            
        Returns:
            FuzzyMatch with results
        """
        if not pattern or not content:
            return FuzzyMatch(found=False)
        
        # Strategy 1: Exact match
        match = self._exact_match(content, pattern)
        if match.found:
            return match
        
        # Strategy 2: Normalize both and try exact
        match = self._normalized_exact_match(content, pattern)
        if match.found and match.similarity >= threshold:
            return match
        
        # Strategy 3: Line-based matching
        match = self._line_based_match(content, pattern)
        if match.found and match.similarity >= threshold:
            return match
        
        # Strategy 4: Block-based approximate matching
        match = self._block_match(content, pattern)
        if match.found and match.similarity >= threshold:
            return match
        
        # Strategy 5: Sequence matcher (slowest but most flexible)
        match = self._sequence_match(content, pattern)
        if match.found and match.similarity >= threshold:
            return match
        
        # Return best match found even if below threshold
        return match
    
    def _exact_match(self, content: str, pattern: str) -> FuzzyMatch:
        """Try exact substring match"""
        if pattern in content:
            idx = content.index(pattern)
            return FuzzyMatch(
                found=True,
                start=idx,
                end=idx + len(pattern),
                matched_text=pattern,
                similarity=1.0,
                confidence="exact"
            )
        return FuzzyMatch(found=False)
    
    def _normalized_exact_match(self, content: str, pattern: str) -> FuzzyMatch:
        """Try match after normalizing both strings"""
        norm_content = normalize_for_fuzzy_match(content)
        norm_pattern = normalize_for_fuzzy_match(pattern)
        
        if norm_pattern in norm_content:
            idx = norm_content.index(norm_pattern)
            # Map back to original indices (approximate)
            original_text = content[idx:idx + len(pattern)]
            return FuzzyMatch(
                found=True,
                start=idx,
                end=idx + len(pattern),
                matched_text=original_text,
                similarity=0.95,
                confidence="high"
            )
        return FuzzyMatch(found=False)
    
    def _line_based_match(self, content: str, pattern: str) -> FuzzyMatch:
        """Match line by line with whitespace tolerance"""
        content_lines = content.split('\n')
        pattern_lines = pattern.split('\n')
        
        if not pattern_lines:
            return FuzzyMatch(found=False)
        
        # Try to find first line match
        first_pattern_line = pattern_lines[0].rstrip()
        
        for i, content_line in enumerate(content_lines):
            if content_line.rstrip() == first_pattern_line:
                # Check subsequent lines
                match = True
                for j, pl in enumerate(pattern_lines[1:], 1):
                    if i + j >= len(content_lines):
                        match = False
                        break
                    if content_lines[i + j].rstrip() != pl.rstrip():
                        match = False
                        break
                
                if match:
                    # Calculate positions
                    start = sum(len(l) + 1 for l in content_lines[:i])
                    end = start + sum(len(l) + 1 for l in pattern_lines) - 1
                    matched = content[start:end]
                    
                    return FuzzyMatch(
                        found=True,
                        start=start,
                        end=end,
                        matched_text=matched,
                        similarity=0.9,
                        confidence="high"
                    )
        
        return FuzzyMatch(found=False)
    
    def _block_match(self, content: str, pattern: str) -> FuzzyMatch:
        """Match blocks with approximate line matching"""
        content_lines = [l.rstrip() for l in content.split('\n')]
        pattern_lines = [l.rstrip() for l in pattern.split('\n')]
        
        if len(pattern_lines) < 2:
            return FuzzyMatch(found=False)
        
        # Use sliding window to find best matching block
        best_match = None
        best_score = 0.0
        
        for i in range(len(content_lines) - len(pattern_lines) + 1):
            window = content_lines[i:i + len(pattern_lines)]
            
            # Calculate similarity for this window
            matches = sum(1 for a, b in zip(window, pattern_lines) if a == b)
            score = matches / len(pattern_lines)
            
            if score > best_score:
                best_score = score
                best_match = i
        
        if best_match is not None and best_score >= 0.7:
            start = sum(len(l) + 1 for l in content_lines[:best_match])
            end = start + sum(len(l) + 1 for l in pattern_lines) - 1
            matched = content[start:end]
            
            confidence = "medium" if best_score < 0.9 else "high"
            
            return FuzzyMatch(
                found=True,
                start=start,
                end=end,
                matched_text=matched,
                similarity=best_score,
                confidence=confidence
            )
        
        return FuzzyMatch(found=False)
    
    def _sequence_match(self, content: str, pattern: str) -> FuzzyMatch:
        """Use difflib SequenceMatcher for approximate matching"""
        matcher = difflib.SequenceMatcher(None, content, pattern)
        
        # Find best matching block
        best = matcher.find_longest_match(0, len(content), 0, len(pattern))
        
        if best.size > 0:
            # Calculate similarity ratio for this block
            matched_text = content[best.a:best.a + best.size]
            similarity = difflib.SequenceMatcher(None, matched_text, pattern).ratio()
            
            if similarity >= 0.6:
                confidence = "low"
                if similarity >= 0.9:
                    confidence = "high"
                elif similarity >= 0.75:
                    confidence = "medium"
                
                return FuzzyMatch(
                    found=True,
                    start=best.a,
                    end=best.a + best.size,
                    matched_text=matched_text,
                    similarity=similarity,
                    confidence=confidence
                )
        
        return FuzzyMatch(found=False)


def normalize_for_fuzzy_match(text: str) -> str:
    """
    Normalize text for fuzzy matching
    
    Normalizations:
    - Smart quotes -> ASCII quotes
    - Dash variants -> ASCII dash
    - Non-breaking space -> regular space
    - Ellipsis -> ...
    - Bullet -> *
    - Strip trailing whitespace per line
    """
    # Smart single quotes
    text = text.replace('\u2018', "'")  # Left single quote
    text = text.replace('\u2019', "'")  # Right single quote
    text = text.replace('\u201a', ",")  # Single low quote
    text = text.replace('\u201b', "'")  # Single high reversed quote
    
    # Smart double quotes
    text = text.replace('\u201c', '"')  # Left double quote
    text = text.replace('\u201d', '"')  # Right double quote
    text = text.replace('\u201e', '"')  # Double low quote
    text = text.replace('\u201f', '"')  # Double high reversed quote
    
    # Dashes
    text = text.replace('\u2014', '-')  # Em dash
    text = text.replace('\u2013', '-')  # En dash
    text = text.replace('\u2015', '-')  # Horizontal bar
    
    # Spaces
    text = text.replace('\xa0', ' ')    # Non-breaking space
    text = text.replace('\u2002', ' ')  # En space
    text = text.replace('\u2003', ' ')  # Em space
    text = text.replace('\u2009', ' ')  # Thin space
    
    # Other
    text = text.replace('\u2026', '...')  # Ellipsis
    text = text.replace('\u2022', '*')    # Bullet
    text = text.replace('\u00a9', '(c)')  # Copyright
    text = text.replace('\u00ae', '(r)')  # Registered
    
    return text


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein edit distance between two strings
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Number of single-character edits required
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio between two strings
    
    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    if s1 == s2:
        return 1.0
    
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    
    distance = levenshtein_distance(s1, s2)
    return 1.0 - (distance / max_len)


def find_best_match(
    content: str,
    pattern: str,
    candidates: int = 3
) -> List[FuzzyMatch]:
    """
    Find multiple candidate matches
    
    Args:
        content: Text to search in
        pattern: Pattern to find
        candidates: Maximum number of candidates
        
    Returns:
        List of FuzzyMatch candidates sorted by similarity
    """
    matcher = FuzzyMatcher()
    results = []
    
    # Try different thresholds to find candidates
    for threshold in [0.99, 0.9, 0.8, 0.7, 0.6]:
        match = matcher.find(content, pattern, threshold)
        if match.found:
            # Check if this is a new match
            is_new = True
            for existing in results:
                if abs(match.start - existing.start) < 10:
                    is_new = False
                    break
            
            if is_new:
                results.append(match)
                
            if len(results) >= candidates:
                break
    
    # Sort by similarity descending
    results.sort(key=lambda m: m.similarity, reverse=True)
    return results


# Convenience function
def fuzzy_find_text(
    content: str,
    old_text: str,
    threshold: float = 0.8
) -> FuzzyMatch:
    """
    Main entry point for fuzzy text finding
    
    Args:
        content: Content to search in
        old_text: Text to find
        threshold: Minimum similarity threshold
        
    Returns:
        FuzzyMatch result
    """
    matcher = FuzzyMatcher()
    return matcher.find(content, old_text, threshold)
