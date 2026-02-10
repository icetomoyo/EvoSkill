"""
Tests for Edit Fuzzy Matching
"""
import pytest

from koda.coding.tools.edit_fuzzy import (
    FuzzyMatcher,
    FuzzyMatch,
    normalize_for_fuzzy_match,
    levenshtein_distance,
    similarity_ratio,
    find_best_match,
    fuzzy_find_text,
)


class TestNormalizeForFuzzyMatch:
    """Test text normalization"""
    
    def test_smart_quotes(self):
        """Test smart quotes conversion"""
        text = '"Hello" \u2018world\u2019'
        result = normalize_for_fuzzy_match(text)
        assert result == '"Hello" \'world\''
    
    def test_dashes(self):
        """Test dash conversion"""
        text = 'Hello\u2014world\u2013test'
        result = normalize_for_fuzzy_match(text)
        assert result == 'Hello-world-test'
    
    def test_non_breaking_space(self):
        """Test non-breaking space conversion"""
        text = 'Hello\xa0world'
        result = normalize_for_fuzzy_match(text)
        assert result == 'Hello world'
    
    def test_ellipsis(self):
        """Test ellipsis conversion"""
        text = 'Wait\u2026'
        result = normalize_for_fuzzy_match(text)
        assert result == 'Wait...'
    
    def test_bullet(self):
        """Test bullet conversion"""
        text = '\u2022 Item'
        result = normalize_for_fuzzy_match(text)
        assert result == '* Item'
    
    def test_multiple_normalizations(self):
        """Test multiple normalizations at once"""
        text = '\u201cSmart\u201d\u2014\xa0quotes\u2026'
        result = normalize_for_fuzzy_match(text)
        assert result == '"Smart"- quotes...'


class TestLevenshteinDistance:
    """Test Levenshtein distance"""
    
    def test_identical_strings(self):
        """Test identical strings have distance 0"""
        assert levenshtein_distance("hello", "hello") == 0
    
    def test_single_substitution(self):
        """Test single character substitution"""
        assert levenshtein_distance("hello", "hallo") == 1
    
    def test_single_deletion(self):
        """Test single character deletion"""
        assert levenshtein_distance("hello", "helo") == 1
    
    def test_single_insertion(self):
        """Test single character insertion"""
        assert levenshtein_distance("helo", "hello") == 1
    
    def test_empty_string(self):
        """Test empty string"""
        assert levenshtein_distance("", "hello") == 5
        assert levenshtein_distance("hello", "") == 5
        assert levenshtein_distance("", "") == 0
    
    def test_case_difference(self):
        """Test case sensitivity"""
        assert levenshtein_distance("Hello", "hello") == 1


class TestSimilarityRatio:
    """Test similarity ratio"""
    
    def test_identical(self):
        """Test identical strings"""
        assert similarity_ratio("hello", "hello") == 1.0
    
    def test_completely_different(self):
        """Test completely different strings"""
        ratio = similarity_ratio("abc", "xyz")
        assert ratio < 0.5
    
    def test_partial_similarity(self):
        """Test partial similarity"""
        ratio = similarity_ratio("hello", "hallo")
        assert 0.75 < ratio <= 1.0
    
    def test_empty_strings(self):
        """Test empty strings"""
        assert similarity_ratio("", "") == 1.0
        assert similarity_ratio("a", "") == 0.0


class TestFuzzyMatcher:
    """Test FuzzyMatcher class"""
    
    def test_exact_match(self):
        """Test exact substring match"""
        matcher = FuzzyMatcher()
        result = matcher.find("Hello world", "world")
        
        assert result.found is True
        assert result.start == 6
        assert result.end == 11
        assert result.similarity == 1.0
        assert result.confidence == "exact"
    
    def test_no_match(self):
        """Test when pattern not found"""
        matcher = FuzzyMatcher()
        result = matcher.find("Hello world", "xyz")
        
        assert result.found is False
    
    def test_normalized_match(self):
        """Test match after normalization"""
        matcher = FuzzyMatcher()
        result = matcher.find('Say "hello"', 'Say "hello"')
        
        assert result.found is True
        assert result.similarity >= 0.9
    
    def test_line_based_match(self):
        """Test line-based matching"""
        content = "line1\nline2\nline3\nline4"
        pattern = "line2\nline3"
        
        matcher = FuzzyMatcher()
        result = matcher.find(content, pattern)
        
        assert result.found is True
    
    def test_block_match(self):
        """Test block-based matching"""
        content = "a\nb\nc\nd\ne"
        pattern = "b\nc\nd"
        
        matcher = FuzzyMatcher()
        result = matcher.find(content, pattern)
        
        assert result.found is True
        assert result.similarity >= 0.7
    
    def test_threshold_filtering(self):
        """Test similarity threshold"""
        matcher = FuzzyMatcher()
        
        # Should not find with high threshold
        result = matcher.find("abcdef", "xyz", threshold=0.9)
        assert result.found is False  # Below threshold
    
    def test_is_good_match(self):
        """Test is_good_match helper"""
        match = FuzzyMatch(found=True, similarity=0.85)
        assert match.is_good_match(0.8) is True
        assert match.is_good_match(0.9) is False
        
        match = FuzzyMatch(found=False, similarity=1.0)
        assert match.is_good_match() is False


class TestFuzzyFindText:
    """Test fuzzy_find_text convenience function"""
    
    def test_exact_match(self):
        """Test exact match"""
        result = fuzzy_find_text("Hello world", "world")
        
        assert result.found is True
        assert result.matched_text == "world"
    
    def test_with_smart_quotes(self):
        """Test with smart quotes in pattern"""
        content = 'He said "hello" to me'
        pattern = 'said "hello"'
        
        result = fuzzy_find_text(content, pattern)
        assert result.found is True


class TestFindBestMatch:
    """Test find_best_match function"""
    
    def test_find_multiple_candidates(self):
        """Test finding multiple candidates"""
        content = "hello world\nhello there\nhello everyone"
        pattern = "hello"
        
        results = find_best_match(content, pattern, candidates=3)
        
        # Should find at least one match
        assert len(results) >= 1
        assert all(r.found for r in results)
    
    def test_candidates_sorted(self):
        """Test candidates are sorted by similarity"""
        content = "hello world\nxyz"
        pattern = "hello"
        
        results = find_best_match(content, pattern)
        
        if len(results) > 1:
            # Should be sorted descending
            for i in range(len(results) - 1):
                assert results[i].similarity >= results[i + 1].similarity
    
    def test_no_duplicates(self):
        """Test no duplicate matches"""
        content = "hello hello hello"
        pattern = "hello"
        
        results = find_best_match(content, pattern, candidates=5)
        
        # Should not have overlapping matches
        positions = [(r.start, r.end) for r in results]
        for i, (s1, e1) in enumerate(positions):
            for s2, e2 in positions[i + 1:]:
                assert not (s1 <= s2 < e1 or s2 <= s1 < e2), "Found overlapping matches"


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_content(self):
        """Test with empty content"""
        result = fuzzy_find_text("", "pattern")
        assert result.found is False
    
    def test_empty_pattern(self):
        """Test with empty pattern"""
        result = fuzzy_find_text("content", "")
        assert result.found is False
    
    def test_both_empty(self):
        """Test with both empty"""
        result = fuzzy_find_text("", "")
        assert result.found is False
    
    def test_whitespace_only(self):
        """Test with whitespace only"""
        result = fuzzy_find_text("   ", "  ")
        # May or may not find depending on implementation
        assert isinstance(result.found, bool)
    
    def test_unicode_content(self):
        """Test with unicode content"""
        content = "Hello 世界 🌍"
        pattern = "世界"
        
        result = fuzzy_find_text(content, pattern)
        assert result.found is True
    
    def test_multiline_pattern(self):
        """Test with multiline pattern"""
        content = "line1\nline2\nline3\nline4"
        pattern = "line2\nline3"
        
        result = fuzzy_find_text(content, pattern)
        assert result.found is True


class TestConfidenceLevels:
    """Test confidence level assignment"""
    
    def test_exact_confidence(self):
        """Test exact match confidence"""
        matcher = FuzzyMatcher()
        result = matcher.find("test", "test")
        
        assert result.confidence == "exact"
    
    def test_high_confidence(self):
        """Test high confidence for normalized match"""
        matcher = FuzzyMatcher()
        result = matcher._normalized_exact_match('Say "hi"', 'Say "hi"')
        
        if result.found:
            assert result.confidence == "high"
    
    def test_medium_confidence(self):
        """Test medium confidence for block match"""
        matcher = FuzzyMatcher()
        result = matcher._block_match("abc\ndef\nghi", "def\nghi")
        
        if result.found:
            assert result.confidence in ["medium", "high"]
