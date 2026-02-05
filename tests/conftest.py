"""
Pytest fixtures for SearchSift tests.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test configuration before importing app
os.environ['SEARCHSIFT_API_KEY'] = 'test-api-key-12345'


@pytest.fixture(scope='session')
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        yield db_path


@pytest.fixture(scope='function')
def app(temp_db, monkeypatch):
    """Create a Flask test application."""
    # Patch database path before importing
    from backend import config
    monkeypatch.setattr(config, 'DATABASE_PATH', temp_db)

    from backend.app import app as flask_app
    from backend.models import init_db, engine, Base

    # Create tables
    Base.metadata.create_all(engine)

    flask_app.config['TESTING'] = True

    yield flask_app

    # Cleanup
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def api_headers():
    """Headers with API key for authenticated requests."""
    return {
        'Content-Type': 'application/json',
        'X-API-Key': 'test-api-key-12345',
    }


@pytest.fixture
def sample_event():
    """A sample search event."""
    return {
        'type': 'search',
        'query': 'python tutorial',
        'url': 'https://www.google.com/search?q=python+tutorial',
        'engine': 'google',
        'timestamp': '2024-01-15T10:00:00Z',
        'tabId': 123,
        'windowId': 1,
    }


@pytest.fixture
def sample_click_event():
    """A sample click event."""
    return {
        'type': 'click',
        'query': 'python tutorial',
        'url': 'https://docs.python.org/3/tutorial/',
        'engine': 'google',
        'timestamp': '2024-01-15T10:01:00Z',
        'tabId': 123,
        'windowId': 1,
    }
