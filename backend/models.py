"""
SearchSift Database Models

SQLite schema using SQLAlchemy ORM.
"""

import json
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    DateTime, Index, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from backend.config import DATABASE_PATH

# Ensure data directory exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Database engine
engine = create_engine(
    f'sqlite:///{DATABASE_PATH}',
    connect_args={'check_same_thread': False},
    echo=False,
)

# Session factory
Session = scoped_session(sessionmaker(bind=engine))

# Base class for models
Base = declarative_base()


class SearchRecord(Base):
    """
    Individual search query or click event.

    Attributes:
        id: Primary key
        event_type: 'search' or 'click'
        query: The search query text
        url: The URL (search page for searches, clicked link for clicks)
        engine: Search engine name (google, bing, etc.)
        timestamp_utc: When the event occurred (UTC)
        category: Assigned category (Work, Shopping, etc.)
        confidence: Confidence score for the category (0.0 - 1.0)
        tab_id: Browser tab ID (for deduplication)
        window_id: Browser window ID
        raw_json: Original JSON payload from extension
        created_at: When the record was inserted
    """
    __tablename__ = 'search_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(20), nullable=False, default='search')
    query = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    engine = Column(String(50), nullable=False)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    category = Column(String(50), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    tab_id = Column(Integer, nullable=True)
    window_id = Column(Integer, nullable=True)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for common queries
    __table_args__ = (
        Index('idx_timestamp_category', 'timestamp_utc', 'category'),
        Index('idx_query_url_timestamp', 'query', 'url', 'timestamp_utc'),
    )

    def __repr__(self):
        return f'<SearchRecord {self.id}: {self.query[:30]}... ({self.engine})>'

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'query': self.query,
            'url': self.url,
            'engine': self.engine,
            'timestamp_utc': self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            'category': self.category,
            'confidence': self.confidence,
            'tab_id': self.tab_id,
            'window_id': self.window_id,
        }


class DailySummary(Base):
    """
    Pre-computed daily summary for fast report generation.

    Attributes:
        id: Primary key
        date: The date this summary covers (YYYY-MM-DD)
        generated_at: When the summary was generated
        summary_json: JSON blob with aggregated statistics
    """
    __tablename__ = 'daily_summary'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, unique=True, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    summary_json = Column(Text, nullable=False)

    def __repr__(self):
        return f'<DailySummary {self.date}>'

    @property
    def summary(self):
        """Parse and return the summary JSON."""
        return json.loads(self.summary_json) if self.summary_json else {}

    @summary.setter
    def summary(self, value):
        """Set summary from a dictionary."""
        self.summary_json = json.dumps(value)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)
    print(f'Database initialized at: {DATABASE_PATH}')


def get_session():
    """Get a database session."""
    return Session()


def close_session():
    """Close the current session."""
    Session.remove()


# Enable foreign keys for SQLite
@event.listens_for(engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.execute('PRAGMA journal_mode=WAL')  # Better concurrent access
    cursor.close()


if __name__ == '__main__':
    init_db()
