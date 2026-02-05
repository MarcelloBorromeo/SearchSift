"""
SearchSift Configuration

All settings for the backend server. Copy to config_local.py
and modify for your environment (config_local.py is gitignored).
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.absolute()

# Server settings
HOST = '127.0.0.1'  # Bind to localhost only for security
PORT = 5000
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# API Key for extension authentication
# Generate with: python scripts/generate_api_key.py
API_KEY = os.getenv('SEARCHSIFT_API_KEY', '')  # Set via environment variable or .env file

# CORS settings - allowed extension origins
# Add your extension ID after loading it in Chrome
ALLOWED_ORIGINS = [
    'chrome-extension://*',  # Allow all Chrome extensions (tighten in production)
    'moz-extension://*',     # Allow all Firefox extensions
    # 'chrome-extension://your-actual-extension-id-here',
]

# Database
DATABASE_PATH = BASE_DIR / 'data' / 'searchsift.db'

# Logging
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'searchsift.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Reports
REPORTS_DIR = BASE_DIR / 'reports'

# Categorization settings
ENABLE_SPACY = os.getenv('ENABLE_SPACY', 'False').lower() == 'true'
SPACY_MODEL = 'en_core_web_sm'

# Fallback categorization (when spaCy is disabled)
USE_TFIDF_FALLBACK = False  # Use simple keyword matching instead

# Batching settings (for extension)
BATCH_SIZE = 20
BATCH_TIMEOUT_SECONDS = 10

# Rate limiting
MAX_REQUESTS_PER_SECOND = 10  # Per client
REQUEST_WINDOW_SECONDS = 1

# Deduplication
DEDUPE_WINDOW_SECONDS = 5  # Ignore duplicate query+url within this window

# Event validation
MAX_EVENT_AGE_SECONDS = 10  # Reject events older than this (idle detection)

# Category definitions for rule-based categorization
CATEGORIES = {
    'Work': [
        'meeting', 'schedule', 'calendar', 'email', 'slack', 'teams',
        'project', 'deadline', 'report', 'presentation', 'spreadsheet',
        'invoice', 'client', 'contract', 'proposal', 'office', 'zoom',
        'linkedin', 'resume', 'job', 'interview', 'salary', 'hr',
        'career', 'hire', 'hiring', 'recruit', 'employee', 'manager',
        'workplace', 'remote work', 'wfh', 'business', 'corporate',
    ],
    'Coding': [
        'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
        'node', 'npm', 'pip', 'github', 'gitlab', 'stackoverflow',
        'api', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'debug', 'error', 'exception', 'bug', 'fix', 'code',
        'function', 'class', 'import', 'library', 'framework',
        'database', 'sql', 'mongodb', 'redis', 'postgres', 'mysql',
        'git', 'commit', 'merge', 'branch', 'pull request', 'pr',
        'programming', 'developer', 'software', 'engineer', 'coding',
        'algorithm', 'data structure', 'leetcode', 'hackerrank',
        'frontend', 'backend', 'fullstack', 'devops', 'cli', 'terminal',
        'json', 'xml', 'html', 'css', 'sass', 'webpack', 'vite',
        'rust', 'golang', 'java', 'swift', 'kotlin', 'c++', 'ruby',
    ],
    'AI': [
        'ai', 'artificial intelligence', 'machine learning', 'ml',
        'chatgpt', 'openai', 'claude', 'anthropic', 'gpt', 'llm',
        'deep learning', 'neural network', 'nlp', 'computer vision',
        'midjourney', 'stable diffusion', 'dall-e', 'generative',
        'prompt', 'transformer', 'model', 'training', 'fine-tune',
        'huggingface', 'pytorch', 'tensorflow', 'langchain',
        'copilot', 'gemini', 'bard', 'perplexity', 'automation',
    ],
    'Research': [
        'research', 'study', 'paper', 'journal', 'academic', 'scholar',
        'university', 'thesis', 'dissertation', 'citation', 'reference',
        'wikipedia', 'wiki', 'definition', 'meaning', 'explain',
        'how to', 'what is', 'why does', 'tutorial', 'guide', 'learn',
        'course', 'education', 'class', 'lecture', 'professor',
        'science', 'scientific', 'experiment', 'theory', 'hypothesis',
    ],
    'Shopping': [
        'buy', 'purchase', 'price', 'cheap', 'deal', 'discount',
        'amazon', 'ebay', 'walmart', 'target', 'best buy', 'costco',
        'shop', 'store', 'order', 'shipping', 'delivery', 'cart',
        'review', 'rating', 'compare', 'vs', 'alternative',
        'coupon', 'promo', 'sale', 'black friday', 'cyber monday',
        'product', 'brand', 'warranty', 'return', 'refund',
    ],
    'Social': [
        'facebook', 'twitter', 'instagram', 'tiktok', 'snapchat',
        'reddit', 'discord', 'whatsapp', 'telegram', 'messenger',
        'friend', 'follow', 'like', 'share', 'post', 'comment',
        'profile', 'social media', 'viral', 'trending', 'meme',
        'dating', 'tinder', 'bumble', 'hinge', 'relationship',
    ],
    'News': [
        'news', 'breaking', 'headline', 'article', 'journalist',
        'cnn', 'bbc', 'nytimes', 'washington post', 'reuters',
        'politics', 'election', 'president', 'congress', 'senate',
        'economy', 'stock', 'market', 'inflation', 'recession',
        'weather', 'forecast', 'storm', 'earthquake', 'disaster',
        'update', 'latest', 'today', 'current events', 'world',
    ],
    'Entertainment': [
        'movie', 'film', 'netflix', 'hulu', 'disney', 'hbo', 'prime video',
        'tv show', 'series', 'episode', 'season', 'streaming',
        'music', 'spotify', 'youtube', 'song', 'album', 'artist', 'concert',
        'game', 'gaming', 'playstation', 'xbox', 'nintendo', 'steam',
        'funny', 'comedy', 'laugh', 'joke', 'humor',
        'anime', 'manga', 'comic', 'superhero', 'marvel', 'dc',
        'celebrity', 'actor', 'actress', 'singer', 'band',
        'podcast', 'twitch', 'streamer', 'esports',
    ],
    'Finance': [
        'bank', 'banking', 'account', 'credit card', 'debit',
        'loan', 'mortgage', 'interest', 'rate', 'apr',
        'invest', 'stock', 'crypto', 'bitcoin', 'ethereum',
        'budget', 'savings', 'retirement', '401k', 'ira',
        'tax', 'irs', 'refund', 'deduction', 'accountant',
        'paypal', 'venmo', 'transfer', 'wire', 'payment',
        'trading', 'forex', 'etf', 'dividend', 'portfolio',
    ],
    'Health': [
        'health', 'medical', 'doctor', 'hospital', 'clinic',
        'symptom', 'disease', 'illness', 'treatment', 'medicine',
        'pharmacy', 'prescription', 'drug', 'vaccine', 'covid',
        'fitness', 'workout', 'exercise', 'gym', 'yoga', 'diet',
        'nutrition', 'vitamin', 'supplement', 'weight', 'calories',
        'mental health', 'anxiety', 'depression', 'therapy', 'counseling',
        'sleep', 'wellness', 'mindfulness', 'meditation', 'stress',
    ],
    'Travel': [
        'travel', 'flight', 'airline', 'airport', 'booking',
        'hotel', 'airbnb', 'vacation', 'trip', 'destination',
        'passport', 'visa', 'immigration', 'customs',
        'car rental', 'uber', 'lyft', 'taxi', 'transportation',
        'restaurant', 'food', 'cuisine', 'menu', 'reservation',
        'beach', 'mountain', 'cruise', 'tour', 'sightseeing',
    ],
    'Sports': [
        'sports', 'football', 'basketball', 'baseball', 'soccer',
        'nfl', 'nba', 'mlb', 'nhl', 'fifa', 'espn',
        'score', 'game', 'match', 'team', 'player', 'coach',
        'championship', 'playoff', 'tournament', 'league',
        'running', 'marathon', 'cycling', 'swimming', 'tennis', 'golf',
    ],
}

# Default category when no rules match
DEFAULT_CATEGORY = 'Other'
DEFAULT_CONFIDENCE = 0.5


# Try to load local config overrides
try:
    from backend.config_local import *  # noqa: F401, F403
except ImportError:
    pass
