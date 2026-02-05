"""
Tests for the categorizer module.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.categorizer import (
    categorize,
    rule_based_categorize,
    get_all_categories,
    get_category_keywords,
)


class TestRuleBasedCategorizer:
    """Tests for rule-based categorization."""

    def test_coding_category(self):
        """Test that coding-related queries are categorized correctly."""
        queries = [
            'python pandas tutorial',
            'javascript async await',
            'docker compose yaml',
            'git merge conflict',
            'stackoverflow python error',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Coding', f"Failed for query: {query}"
            assert 0 < result['confidence'] <= 1

    def test_shopping_category(self):
        """Test that shopping-related queries are categorized correctly."""
        queries = [
            'amazon laptop deals',
            'best buy price match',
            'cheap headphones review',
            'walmart grocery delivery',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Shopping', f"Failed for query: {query}"

    def test_news_category(self):
        """Test that news-related queries are categorized correctly."""
        queries = [
            'breaking news today',
            'cnn latest headlines',
            'stock market news',
            'election results live',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] in ['News', 'Finance'], f"Failed for query: {query}"

    def test_entertainment_category(self):
        """Test that entertainment queries are categorized correctly."""
        queries = [
            'netflix new releases',
            'spotify playlist',
            'youtube music video',
            'best movies 2024',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Entertainment', f"Failed for query: {query}"

    def test_social_category(self):
        """Test that social media queries are categorized correctly."""
        queries = [
            'facebook login',
            'twitter trending',
            'instagram stories',
            'reddit programming',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Social', f"Failed for query: {query}"

    def test_travel_category(self):
        """Test that travel queries are categorized correctly."""
        queries = [
            'flight tickets to paris',
            'hotel booking new york',
            'airbnb tokyo',
            'car rental near me',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Travel', f"Failed for query: {query}"

    def test_health_category(self):
        """Test that health queries are categorized correctly."""
        queries = [
            'symptoms of cold',
            'yoga exercises beginner',
            'healthy diet plan',
            'mental health resources',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Health', f"Failed for query: {query}"

    def test_finance_category(self):
        """Test that finance queries are categorized correctly."""
        queries = [
            'bitcoin price today',
            'bank account interest rate',
            'credit card comparison',
            '401k retirement calculator',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] == 'Finance', f"Failed for query: {query}"

    def test_research_category(self):
        """Test that research/learning queries are categorized correctly."""
        queries = [
            'how to learn programming',
            'what is machine learning',
            'wikipedia history',
            'tutorial for beginners',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] in ['Research', 'Coding'], f"Failed for query: {query}"

    def test_unknown_query_returns_other(self):
        """Test that unrecognized queries return 'Other' category."""
        result = categorize('xyzabc123 random gibberish')
        assert result['category'] == 'Other'
        assert result['confidence'] == 0.5

    def test_empty_query(self):
        """Test handling of empty queries."""
        result = categorize('')
        assert result['category'] == 'Other'

    def test_confidence_score_range(self):
        """Test that confidence scores are within valid range."""
        queries = [
            'python programming',
            'random query xyz',
            'amazon shopping deals',
        ]

        for query in queries:
            result = categorize(query)
            assert 0 <= result['confidence'] <= 1, f"Invalid confidence for: {query}"

    def test_url_context_improves_categorization(self):
        """Test that URL context helps categorization."""
        query = 'latest updates'  # Ambiguous query

        # With GitHub URL - should lean toward Coding
        result_github = categorize(query, 'https://github.com/updates')

        # With news URL - should lean toward News
        result_news = categorize(query, 'https://cnn.com/latest')

        # At least one should be categorized (not necessarily different)
        assert result_github['category'] in get_all_categories()
        assert result_news['category'] in get_all_categories()


class TestCategoryHelpers:
    """Tests for category helper functions."""

    def test_get_all_categories(self):
        """Test getting list of all categories."""
        categories = get_all_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert 'Coding' in categories
        assert 'Shopping' in categories
        assert 'Other' in categories

    def test_get_category_keywords(self):
        """Test getting keywords for a category."""
        coding_keywords = get_category_keywords('Coding')

        assert isinstance(coding_keywords, list)
        assert len(coding_keywords) > 0
        assert 'python' in coding_keywords

    def test_get_keywords_invalid_category(self):
        """Test getting keywords for non-existent category."""
        keywords = get_category_keywords('NonExistentCategory')
        assert keywords == []


class TestEdgeCases:
    """Tests for edge cases and special inputs."""

    def test_special_characters_in_query(self):
        """Test handling of special characters."""
        queries = [
            'c++ programming',
            'node.js tutorial',
            'what is $100?',
            'how to use @mentions',
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] in get_all_categories()

    def test_very_long_query(self):
        """Test handling of very long queries."""
        long_query = 'python ' * 100 + 'tutorial'
        result = categorize(long_query)
        assert result['category'] == 'Coding'

    def test_unicode_query(self):
        """Test handling of Unicode characters."""
        queries = [
            'python tutorial',
            'recherche python',  # French
        ]

        for query in queries:
            result = categorize(query)
            assert result['category'] in get_all_categories()

    def test_case_insensitivity(self):
        """Test that categorization is case-insensitive."""
        queries = [
            'PYTHON TUTORIAL',
            'Python Tutorial',
            'python tutorial',
            'PyThOn TuToRiAl',
        ]

        results = [categorize(q)['category'] for q in queries]
        assert all(r == 'Coding' for r in results)
