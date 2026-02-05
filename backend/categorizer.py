"""
SearchSift Categorizer

Rule-based categorization with optional spaCy/ML fallback.
"""

import re
import logging
from typing import Dict, Tuple, Optional
from backend.config import (
    CATEGORIES, DEFAULT_CATEGORY, DEFAULT_CONFIDENCE,
    ENABLE_SPACY, SPACY_MODEL, USE_TFIDF_FALLBACK
)

logger = logging.getLogger(__name__)

# Optional spaCy import
nlp = None
if ENABLE_SPACY:
    try:
        import spacy
        nlp = spacy.load(SPACY_MODEL)
        logger.info(f'spaCy loaded with model: {SPACY_MODEL}')
    except ImportError:
        logger.warning('spaCy not installed. Using rule-based categorization only.')
    except OSError:
        logger.warning(f'spaCy model {SPACY_MODEL} not found. Run: python -m spacy download {SPACY_MODEL}')


def categorize(query: str, url: Optional[str] = None) -> Dict[str, any]:
    """
    Categorize a search query into one or more categories.

    Args:
        query: The search query text
        url: Optional URL for additional context

    Returns:
        Dict with 'category' (comma-separated if multiple), 'categories' (list), and 'confidence' keys
    """
    if not query:
        return {'category': DEFAULT_CATEGORY, 'categories': [DEFAULT_CATEGORY], 'confidence': DEFAULT_CONFIDENCE}

    # Normalize query
    query_lower = query.lower().strip()

    # Try rule-based categorization first (now returns multiple categories)
    result = rule_based_categorize(query_lower, url)

    if result['categories'] and result['categories'][0] != DEFAULT_CATEGORY:
        return result

    # Try spaCy if enabled and rule-based didn't match
    if nlp and ENABLE_SPACY:
        result = spacy_categorize(query_lower)
        if result['category'] != DEFAULT_CATEGORY:
            result['categories'] = [result['category']]
            return result

    # Try TF-IDF fallback if enabled
    if USE_TFIDF_FALLBACK:
        result = tfidf_categorize(query_lower)
        if result['category'] != DEFAULT_CATEGORY:
            result['categories'] = [result['category']]
            return result

    return {'category': DEFAULT_CATEGORY, 'categories': [DEFAULT_CATEGORY], 'confidence': DEFAULT_CONFIDENCE}


def rule_based_categorize(query: str, url: Optional[str] = None) -> Dict[str, any]:
    """
    Simple keyword-based categorization.

    Looks for keywords in the query and optionally the URL.
    Returns all categories that have keyword matches (multi-category support).
    """
    text = query
    if url:
        text = f'{query} {url}'

    text_lower = text.lower()

    # Count matches for each category
    scores = {}
    for category, keywords in CATEGORIES.items():
        score = 0
        matched_keywords = []

        for keyword in keywords:
            # Use word boundary matching for better accuracy
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                score += matches
                matched_keywords.append(keyword)

        if score > 0:
            scores[category] = {
                'score': score,
                'matched': matched_keywords,
            }

    if not scores:
        return {
            'category': DEFAULT_CATEGORY,
            'categories': [DEFAULT_CATEGORY],
            'confidence': DEFAULT_CONFIDENCE
        }

    # Sort categories by score (descending)
    sorted_categories = sorted(scores.keys(), key=lambda k: scores[k]['score'], reverse=True)

    # Get all categories with at least 1 match (limited to top 3)
    matched_categories = sorted_categories[:3]

    # Calculate confidence based on top category's dominance
    best_category = sorted_categories[0]
    best_score = scores[best_category]['score']
    total_score = sum(s['score'] for s in scores.values())
    confidence = min(0.95, 0.5 + (best_score / total_score) * 0.45)

    # Create comma-separated category string
    category_string = ', '.join(matched_categories)

    logger.debug(
        f'Rule-based: "{query[:50]}" -> {matched_categories} '
        f'(confidence: {confidence:.2f})'
    )

    return {
        'category': category_string,
        'categories': matched_categories,
        'confidence': round(confidence, 2),
        'matched_keywords': scores[best_category]['matched'][:5],
    }


def spacy_categorize(query: str) -> Dict[str, any]:
    """
    Use spaCy NER and text classification for categorization.

    This is a simple implementation that looks at named entities
    and tries to map them to categories.
    """
    if not nlp:
        return {'category': DEFAULT_CATEGORY, 'confidence': DEFAULT_CONFIDENCE}

    try:
        doc = nlp(query)

        # Entity-to-category mapping
        entity_category_map = {
            'ORG': 'Work',
            'MONEY': 'Finance',
            'PRODUCT': 'Shopping',
            'GPE': 'Travel',  # Geo-political entity (countries, cities)
            'LOC': 'Travel',
            'PERSON': 'Social',
            'WORK_OF_ART': 'Entertainment',
            'EVENT': 'News',
        }

        # Count entity types
        entity_counts = {}
        for ent in doc.ents:
            if ent.label_ in entity_category_map:
                category = entity_category_map[ent.label_]
                entity_counts[category] = entity_counts.get(category, 0) + 1

        if entity_counts:
            best_category = max(entity_counts, key=entity_counts.get)
            confidence = min(0.85, 0.5 + entity_counts[best_category] * 0.1)

            logger.debug(f'spaCy: "{query[:50]}" -> {best_category} (confidence: {confidence:.2f})')

            return {
                'category': best_category,
                'confidence': round(confidence, 2),
            }

        # Fallback: analyze tokens for tech/coding terms
        tech_indicators = {'code', 'function', 'error', 'bug', 'api', 'server', 'database'}
        if any(token.text.lower() in tech_indicators for token in doc):
            return {'category': 'Coding', 'confidence': 0.6}

    except Exception as e:
        logger.error(f'spaCy categorization error: {e}')

    return {'category': DEFAULT_CATEGORY, 'confidence': DEFAULT_CONFIDENCE}


def tfidf_categorize(query: str) -> Dict[str, any]:
    """
    Simple TF-IDF based categorization using scikit-learn.

    This trains a small classifier on the category keywords
    and uses it to classify new queries.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        import numpy as np

        # Build training data from category keywords
        texts = []
        labels = []
        for category, keywords in CATEGORIES.items():
            # Create synthetic training examples
            for keyword in keywords:
                texts.append(keyword)
                labels.append(category)
                # Add some variations
                texts.append(f'how to {keyword}')
                labels.append(category)
                texts.append(f'{keyword} help')
                labels.append(category)

        # Train a simple classifier
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000)
        X = vectorizer.fit_transform(texts)
        clf = MultinomialNB()
        clf.fit(X, labels)

        # Classify the query
        query_vec = vectorizer.transform([query])
        predicted = clf.predict(query_vec)[0]
        probabilities = clf.predict_proba(query_vec)[0]
        confidence = float(np.max(probabilities))

        if confidence > 0.3:  # Only return if reasonably confident
            logger.debug(f'TF-IDF: "{query[:50]}" -> {predicted} (confidence: {confidence:.2f})')
            return {
                'category': predicted,
                'confidence': round(confidence, 2),
            }

    except ImportError:
        logger.warning('scikit-learn not installed. TF-IDF fallback unavailable.')
    except Exception as e:
        logger.error(f'TF-IDF categorization error: {e}')

    return {'category': DEFAULT_CATEGORY, 'confidence': DEFAULT_CONFIDENCE}


def get_category_keywords(category: str) -> list:
    """Get keywords for a specific category."""
    return CATEGORIES.get(category, [])


def get_all_categories() -> list:
    """Get list of all category names."""
    return list(CATEGORIES.keys()) + [DEFAULT_CATEGORY]


def add_category_keyword(category: str, keyword: str) -> bool:
    """
    Add a keyword to a category.

    Note: This only affects the runtime CATEGORIES dict.
    For permanent changes, edit config.py.
    """
    if category not in CATEGORIES:
        return False

    keyword_lower = keyword.lower()
    if keyword_lower not in CATEGORIES[category]:
        CATEGORIES[category].append(keyword_lower)
        logger.info(f'Added keyword "{keyword}" to category "{category}"')
        return True

    return False


if __name__ == '__main__':
    # Test the categorizer
    test_queries = [
        'python pandas dataframe tutorial',
        'best laptop deals amazon',
        'how to make pizza dough',
        'latest news about climate change',
        'facebook login',
        'stock market today',
        'yoga exercises for beginners',
        'flight tickets to paris',
        'random gibberish query xyz123',
    ]

    print('Testing categorizer:')
    print('-' * 60)

    for query in test_queries:
        result = categorize(query)
        print(f'Query: "{query}"')
        print(f'  -> Category: {result["category"]} (confidence: {result["confidence"]})')
        if 'matched_keywords' in result:
            print(f'     Matched: {result["matched_keywords"]}')
        print()
