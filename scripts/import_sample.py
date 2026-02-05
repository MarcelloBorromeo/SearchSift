#!/usr/bin/env python3
"""
Import sample data into the SearchSift database for testing.

Usage:
    python scripts/import_sample.py

This will:
1. Read sample data from data/sample_data.json
2. Categorize each event
3. Insert records into the database
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.models import init_db, get_session, close_session, SearchRecord
from backend.categorizer import categorize
from backend.config import BASE_DIR


def load_sample_data() -> dict:
    """Load sample data from JSON file."""
    sample_file = BASE_DIR / 'data' / 'sample_data.json'

    if not sample_file.exists():
        print(f"Error: Sample data file not found: {sample_file}")
        sys.exit(1)

    with open(sample_file, 'r') as f:
        return json.load(f)


def import_events(events: list) -> tuple:
    """
    Import events into the database.

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    session = get_session()
    inserted = 0
    skipped = 0

    try:
        for event in events:
            query = event.get('query', '').strip()
            if not query:
                skipped += 1
                continue

            # Parse timestamp
            timestamp_str = event.get('timestamp')
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Convert to naive UTC for storage
                timestamp = timestamp.replace(tzinfo=None)
            except (ValueError, TypeError, AttributeError):
                timestamp = datetime.utcnow()

            # Categorize the query
            url = event.get('url', '')
            cat_result = categorize(query, url)

            # Create record
            record = SearchRecord(
                event_type=event.get('type', 'search'),
                query=query,
                url=url,
                engine=event.get('engine', 'unknown'),
                timestamp_utc=timestamp,
                category=cat_result['category'],
                confidence=cat_result['confidence'],
                raw_json=json.dumps(event),
            )

            session.add(record)
            inserted += 1

        session.commit()
        return inserted, skipped

    except Exception as e:
        session.rollback()
        raise e

    finally:
        close_session()


def main():
    print("\n" + "=" * 60)
    print("SearchSift Sample Data Importer")
    print("=" * 60)

    # Initialize database
    print("\nInitializing database...")
    init_db()

    # Load sample data
    print("Loading sample data...")
    data = load_sample_data()

    events = data.get('events', [])
    sample_date = data.get('date', 'unknown')

    print(f"Found {len(events)} events for date: {sample_date}")

    # Import events
    print("\nImporting events...")
    inserted, skipped = import_events(events)

    print(f"\nResults:")
    print(f"  - Inserted: {inserted}")
    print(f"  - Skipped:  {skipped}")

    # Show category breakdown
    session = get_session()
    try:
        from sqlalchemy import func
        category_counts = session.query(
            SearchRecord.category,
            func.count(SearchRecord.id)
        ).group_by(SearchRecord.category).all()

        print(f"\nCategory breakdown:")
        for category, count in sorted(category_counts, key=lambda x: -x[1]):
            print(f"  - {category}: {count}")

    finally:
        close_session()

    print("\n" + "=" * 60)
    print("Import complete!")
    print("\nNext steps:")
    print(f"  1. Generate report: python backend/tasks.py --run-once --date {sample_date}")
    print("  2. Start backend:   flask run --host=127.0.0.1")
    print("  3. View dashboard:  http://127.0.0.1:5000/")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
