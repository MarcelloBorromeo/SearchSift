"""
SearchSift Flask Backend

Local-first API server for receiving and storing search events.
"""

import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from sqlalchemy import func
from dateutil import parser as date_parser

from backend.config import (
    HOST, PORT, DEBUG, API_KEY, ALLOWED_ORIGINS,
    LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
    REPORTS_DIR, DEDUPE_WINDOW_SECONDS, MAX_EVENT_AGE_SECONDS,
)
from backend.models import init_db, get_session, close_session, SearchRecord, DailySummary
from backend.categorizer import categorize

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=Path(__file__).parent / 'ui' / 'templates',
    static_folder=Path(__file__).parent / 'ui' / 'static',
)

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ----- Logging Setup -----

def setup_logging():
    """Configure application logging."""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, LOG_LEVEL))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


# ----- Database Setup -----

@app.before_request
def before_request():
    """Ensure database session is available."""
    pass


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Clean up database session after each request."""
    close_session()


# Initialize database on startup
with app.app_context():
    init_db()


# ----- Authentication & CORS -----

def check_api_key(f):
    """Decorator to verify API key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            logger.warning(f'Missing API key from {request.remote_addr}')
            return jsonify({'error': 'API key required'}), 401

        if api_key != API_KEY:
            logger.warning(f'Invalid API key from {request.remote_addr}')
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)
    return decorated


def check_origin(f):
    """Decorator to verify request origin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        origin = request.headers.get('Origin', '')

        # Check if origin matches any allowed pattern
        allowed = False
        for pattern in ALLOWED_ORIGINS:
            if pattern.endswith('*'):
                # Wildcard match
                if origin.startswith(pattern[:-1]):
                    allowed = True
                    break
            elif origin == pattern:
                allowed = True
                break

        if not allowed and origin:
            logger.warning(f'Blocked request from origin: {origin}')
            return jsonify({'error': 'Origin not allowed'}), 403

        return f(*args, **kwargs)
    return decorated


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to response."""
    origin = request.headers.get('Origin', '')

    for pattern in ALLOWED_ORIGINS:
        if pattern.endswith('*'):
            if origin.startswith(pattern[:-1]):
                response.headers['Access-Control-Allow-Origin'] = origin
                break
        elif origin == pattern:
            response.headers['Access-Control-Allow-Origin'] = origin
            break

    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'

    return response


@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle CORS preflight requests."""
    return '', 204


# ----- API Endpoints -----

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    session = get_session()
    try:
        # Check database connection
        from sqlalchemy import text
        session.execute(text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'error: {str(e)}'
    finally:
        session.close()

    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat(),
    })


@app.route('/ingest', methods=['POST'])
@check_api_key
@check_origin
def ingest():
    """
    Receive search events from the browser extension.

    Expected JSON body:
    {
        "events": [
            {
                "type": "search" | "click",
                "query": "search query",
                "url": "https://...",
                "engine": "google",
                "timestamp": "ISO8601",
                "tabId": 123,
                "windowId": 456
            },
            ...
        ]
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON body'}), 400

    events = data.get('events', [])
    if not events:
        # Support single event format
        if 'query' in data:
            events = [data]
        else:
            return jsonify({'error': 'No events provided'}), 400

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
                timestamp = date_parser.parse(timestamp_str) if timestamp_str else datetime.utcnow()
            except (ValueError, TypeError):
                timestamp = datetime.utcnow()

            # Validate timestamp (idle detection)
            # Remove timezone info for comparison
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()
            if age_seconds > MAX_EVENT_AGE_SECONDS:
                logger.debug(f'Skipping stale event: {age_seconds:.1f}s old')
                skipped += 1
                continue

            # Check for duplicates
            url = event.get('url', '')
            dedupe_cutoff = timestamp - timedelta(seconds=DEDUPE_WINDOW_SECONDS)

            existing = session.query(SearchRecord).filter(
                SearchRecord.query == query,
                SearchRecord.url == url,
                SearchRecord.timestamp_utc >= dedupe_cutoff,
            ).first()

            if existing:
                logger.debug(f'Skipping duplicate: {query[:30]}...')
                skipped += 1
                continue

            # Categorize the query
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
                tab_id=event.get('tabId'),
                window_id=event.get('windowId'),
                raw_json=json.dumps(event),
            )

            session.add(record)
            inserted += 1

        session.commit()

        logger.info(f'Ingested {inserted} events, skipped {skipped}')

        return jsonify({
            'status': 'ok',
            'inserted': inserted,
            'skipped': skipped,
        })

    except Exception as e:
        session.rollback()
        logger.error(f'Ingest error: {e}')
        return jsonify({'error': str(e)}), 500

    finally:
        session.close()


@app.route('/api/summary', methods=['GET'])
@check_api_key
def api_summary():
    """
    Get aggregated statistics for a date range.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    try:
        start_date = date_parser.parse(start_str).date() if start_str else datetime.utcnow().date()
        end_date = date_parser.parse(end_str).date() if end_str else start_date
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400

    session = get_session()

    try:
        # Date range filter
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Total counts
        total_searches = session.query(SearchRecord).filter(
            SearchRecord.event_type == 'search',
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).count()

        total_clicks = session.query(SearchRecord).filter(
            SearchRecord.event_type == 'click',
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).count()

        # Counts by category
        category_counts = session.query(
            SearchRecord.category,
            func.count(SearchRecord.id).label('count')
        ).filter(
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).group_by(SearchRecord.category).all()

        # Counts by engine
        engine_counts = session.query(
            SearchRecord.engine,
            func.count(SearchRecord.id).label('count')
        ).filter(
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).group_by(SearchRecord.engine).all()

        # Top queries
        top_queries = session.query(
            SearchRecord.query,
            func.count(SearchRecord.id).label('count')
        ).filter(
            SearchRecord.event_type == 'search',
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).group_by(SearchRecord.query).order_by(
            func.count(SearchRecord.id).desc()
        ).limit(10).all()

        return jsonify({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_searches': total_searches,
            'total_clicks': total_clicks,
            'by_category': {c: count for c, count in category_counts},
            'by_engine': {e: count for e, count in engine_counts},
            'top_queries': [{'query': q, 'count': c} for q, c in top_queries],
        })

    finally:
        session.close()


@app.route('/api/records', methods=['GET'])
@check_api_key
def api_records():
    """
    Get individual search records with filtering.

    Query params:
        start: Start date
        end: End date
        category: Filter by category
        engine: Filter by engine
        type: Filter by event type (search/click)
        limit: Max results (default 100)
        offset: Pagination offset
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    category = request.args.get('category')
    engine = request.args.get('engine')
    event_type = request.args.get('type')
    limit = min(int(request.args.get('limit', 100)), 1000)
    offset = int(request.args.get('offset', 0))

    session = get_session()

    try:
        query = session.query(SearchRecord)

        # Apply filters
        if start_str:
            start_dt = date_parser.parse(start_str)
            query = query.filter(SearchRecord.timestamp_utc >= start_dt)

        if end_str:
            end_dt = date_parser.parse(end_str)
            query = query.filter(SearchRecord.timestamp_utc <= end_dt)

        if category:
            query = query.filter(SearchRecord.category == category)

        if engine:
            query = query.filter(SearchRecord.engine == engine)

        if event_type:
            query = query.filter(SearchRecord.event_type == event_type)

        # Get total count
        total = query.count()

        # Get paginated results
        records = query.order_by(SearchRecord.timestamp_utc.desc())\
            .offset(offset).limit(limit).all()

        return jsonify({
            'total': total,
            'limit': limit,
            'offset': offset,
            'records': [r.to_dict() for r in records],
        })

    finally:
        session.close()


@app.route('/api/category-trend', methods=['GET'])
@check_api_key
def api_category_trend():
    """
    Get search frequency by category over time.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        bucket: Time bucket ('hour' or 'day', default: auto-detect based on range)
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    bucket = request.args.get('bucket')

    try:
        start_date = date_parser.parse(start_str).date() if start_str else datetime.utcnow().date()
        end_date = date_parser.parse(end_str).date() if end_str else start_date
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400

    # Auto-detect bucket size based on date range
    day_diff = (end_date - start_date).days
    if not bucket:
        bucket = 'hour' if day_diff <= 1 else 'day'

    session = get_session()

    try:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Get all records in range
        records = session.query(SearchRecord).filter(
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).all()

        # Group by time bucket and category
        from collections import defaultdict
        trend_data = defaultdict(lambda: defaultdict(int))

        for record in records:
            if bucket == 'hour':
                time_key = record.timestamp_utc.strftime('%H:00')
            else:
                time_key = record.timestamp_utc.strftime('%Y-%m-%d')

            trend_data[time_key][record.category] += 1

        # Get all unique categories and times
        all_categories = set()
        for time_key in trend_data:
            all_categories.update(trend_data[time_key].keys())

        # Sort time keys
        if bucket == 'hour':
            # Generate all hours for consistent x-axis
            time_keys = [f'{h:02d}:00' for h in range(24)]
        else:
            time_keys = sorted(trend_data.keys())

        # Build response data
        result = []
        for time_key in time_keys:
            entry = {'time': time_key}
            for cat in all_categories:
                entry[cat] = trend_data[time_key].get(cat, 0)
            result.append(entry)

        return jsonify({
            'bucket': bucket,
            'categories': list(all_categories),
            'data': result,
        })

    finally:
        session.close()


@app.route('/report/daily', methods=['GET'])
@check_api_key
def report_daily():
    """
    Get HTML report for a specific date.

    Query params:
        date: Date in YYYY-MM-DD format (default: yesterday)
    """
    date_str = request.args.get('date')

    try:
        if date_str:
            report_date = date_parser.parse(date_str).date()
        else:
            report_date = (datetime.utcnow() - timedelta(days=1)).date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400

    # Check for pre-generated report file
    report_file = REPORTS_DIR / f'{report_date.isoformat()}.html'
    if report_file.exists():
        return send_from_directory(REPORTS_DIR, f'{report_date.isoformat()}.html')

    # Generate report on the fly
    session = get_session()

    try:
        start_dt = datetime.combine(report_date, datetime.min.time())
        end_dt = datetime.combine(report_date, datetime.max.time())

        # Get records for the day
        records = session.query(SearchRecord).filter(
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).order_by(SearchRecord.timestamp_utc.desc()).all()

        # Calculate statistics
        total_searches = sum(1 for r in records if r.event_type == 'search')
        total_clicks = sum(1 for r in records if r.event_type == 'click')

        category_counts = {}
        engine_counts = {}
        hourly_by_category = {}

        for r in records:
            category_counts[r.category] = category_counts.get(r.category, 0) + 1
            engine_counts[r.engine] = engine_counts.get(r.engine, 0) + 1

            # Build hourly data by category
            if r.timestamp_utc:
                hour = r.timestamp_utc.hour
                if r.category not in hourly_by_category:
                    hourly_by_category[r.category] = [0] * 24
                hourly_by_category[r.category][hour] += 1

        return render_template(
            'report.html',
            date=report_date,
            records=records,
            total_searches=total_searches,
            total_clicks=total_clicks,
            category_counts=category_counts,
            engine_counts=engine_counts,
            hourly_by_category=hourly_by_category,
        )

    finally:
        session.close()


@app.route('/report/csv', methods=['GET'])
@check_api_key
def report_csv():
    """
    Export records as CSV.

    Query params:
        date: Single date or start date
        end: End date (optional)
    """
    import csv
    from io import StringIO

    date_str = request.args.get('date')
    end_str = request.args.get('end')

    try:
        if date_str:
            start_date = date_parser.parse(date_str).date()
        else:
            start_date = (datetime.utcnow() - timedelta(days=1)).date()

        end_date = date_parser.parse(end_str).date() if end_str else start_date
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400

    # Check for pre-generated CSV file
    if start_date == end_date:
        csv_file = REPORTS_DIR / f'{start_date.isoformat()}.csv'
        if csv_file.exists():
            return send_from_directory(
                REPORTS_DIR,
                f'{start_date.isoformat()}.csv',
                mimetype='text/csv',
                as_attachment=True,
            )

    session = get_session()

    try:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        records = session.query(SearchRecord).filter(
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).order_by(SearchRecord.timestamp_utc.desc()).all()

        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'id', 'event_type', 'query', 'url', 'engine',
            'timestamp_utc', 'category', 'confidence'
        ])

        # Data rows
        for r in records:
            writer.writerow([
                r.id, r.event_type, r.query, r.url, r.engine,
                r.timestamp_utc.isoformat(), r.category, r.confidence
            ])

        response = app.response_class(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=searchsift_{start_date}_{end_date}.csv'
            }
        )

        return response

    finally:
        session.close()


# ----- UI Routes -----

@app.route('/')
def dashboard():
    """Main dashboard UI."""
    return render_template('dashboard.html')


@app.route('/help')
def help_page():
    """Help page."""
    return render_template('help.html')


# ----- Error Handlers -----

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f'Server error: {e}')
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('error.html', error='Server error'), 500


# ----- Main -----

if __name__ == '__main__':
    logger.info(f'Starting SearchSift backend on {HOST}:{PORT}')
    app.run(host=HOST, port=PORT, debug=DEBUG)
