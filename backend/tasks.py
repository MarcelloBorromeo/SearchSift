"""
SearchSift Daily Tasks

Generates daily HTML and CSV reports from search data.
Can be run manually, via cron, or with APScheduler.
"""

import argparse
import csv
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func

from backend.config import REPORTS_DIR, BASE_DIR
from backend.models import init_db, get_session, close_session, SearchRecord, DailySummary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Jinja2 environment for report templates
template_dir = BASE_DIR / 'backend' / 'ui' / 'templates'
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain or 'unknown'
    except Exception:
        return 'unknown'


def generate_daily_report(date: datetime.date) -> dict:
    """
    Generate report data for a specific date.

    Args:
        date: The date to generate report for

    Returns:
        Dictionary with report data
    """
    session = get_session()

    try:
        start_dt = datetime.combine(date, datetime.min.time())
        end_dt = datetime.combine(date, datetime.max.time())

        # Get all records for the day
        records = session.query(SearchRecord).filter(
            SearchRecord.timestamp_utc >= start_dt,
            SearchRecord.timestamp_utc <= end_dt,
        ).order_by(SearchRecord.timestamp_utc).all()

        if not records:
            logger.info(f'No records found for {date}')
            return None

        # Calculate statistics
        total_events = len(records)
        searches = [r for r in records if r.event_type == 'search']
        clicks = [r for r in records if r.event_type == 'click']

        # Category breakdown
        category_counts = Counter(r.category for r in records)
        category_searches = Counter(r.category for r in searches)
        category_clicks = Counter(r.category for r in clicks)

        # Engine breakdown
        engine_counts = Counter(r.engine for r in records)

        # Top queries
        query_counts = Counter(r.query for r in searches)
        top_queries = query_counts.most_common(20)

        # Top domains (from clicks)
        domain_counts = Counter(get_domain(r.url) for r in clicks if r.url)
        top_domains = domain_counts.most_common(20)

        # Hourly distribution
        hourly_counts = Counter(r.timestamp_utc.hour for r in records)
        hourly_data = [hourly_counts.get(h, 0) for h in range(24)]

        # Average confidence by category
        category_confidence = {}
        for cat in set(r.category for r in records):
            cat_records = [r for r in records if r.category == cat and r.confidence]
            if cat_records:
                avg_conf = sum(r.confidence for r in cat_records) / len(cat_records)
                category_confidence[cat] = round(avg_conf, 2)

        # Build report data
        report_data = {
            'date': date.isoformat(),
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_events': total_events,
                'total_searches': len(searches),
                'total_clicks': len(clicks),
                'unique_queries': len(set(r.query for r in searches)),
                'unique_domains': len(set(get_domain(r.url) for r in clicks if r.url)),
            },
            'by_category': dict(category_counts),
            'by_engine': dict(engine_counts),
            'top_queries': [{'query': q, 'count': c} for q, c in top_queries],
            'top_domains': [{'domain': d, 'count': c} for d, c in top_domains],
            'hourly_distribution': hourly_data,
            'category_confidence': category_confidence,
            'records': [r.to_dict() for r in records],
        }

        # Store summary in database
        existing_summary = session.query(DailySummary).filter(
            DailySummary.date == date.isoformat()
        ).first()

        if existing_summary:
            existing_summary.summary_json = json.dumps(report_data)
            existing_summary.generated_at = datetime.utcnow()
        else:
            summary = DailySummary(
                date=date.isoformat(),
                summary_json=json.dumps(report_data),
            )
            session.add(summary)

        session.commit()

        logger.info(f'Generated report for {date}: {total_events} events')

        return report_data

    except Exception as e:
        session.rollback()
        logger.error(f'Error generating report for {date}: {e}')
        raise

    finally:
        session.close()


def write_html_report(date: datetime.date, report_data: dict) -> Path:
    """
    Write HTML report file.

    Args:
        date: Report date
        report_data: Report data dictionary

    Returns:
        Path to generated HTML file
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    template = jinja_env.get_template('report.html')

    html_content = template.render(
        date=date,
        data=report_data,
        records=report_data.get('records', []),
        total_searches=report_data['summary']['total_searches'],
        total_clicks=report_data['summary']['total_clicks'],
        category_counts=report_data['by_category'],
        engine_counts=report_data['by_engine'],
        top_queries=report_data['top_queries'],
        top_domains=report_data['top_domains'],
        hourly_distribution=report_data['hourly_distribution'],
    )

    output_path = REPORTS_DIR / f'{date.isoformat()}.html'
    output_path.write_text(html_content, encoding='utf-8')

    logger.info(f'Wrote HTML report: {output_path}')

    return output_path


def write_csv_report(date: datetime.date, report_data: dict) -> Path:
    """
    Write CSV report file.

    Args:
        date: Report date
        report_data: Report data dictionary

    Returns:
        Path to generated CSV file
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORTS_DIR / f'{date.isoformat()}.csv'

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'id', 'event_type', 'query', 'url', 'engine',
            'timestamp_utc', 'category', 'confidence'
        ])

        # Data rows
        for record in report_data.get('records', []):
            writer.writerow([
                record.get('id'),
                record.get('event_type'),
                record.get('query'),
                record.get('url'),
                record.get('engine'),
                record.get('timestamp_utc'),
                record.get('category'),
                record.get('confidence'),
            ])

    logger.info(f'Wrote CSV report: {output_path}')

    return output_path


def run_daily_task(date: datetime.date = None):
    """
    Run the full daily report generation task.

    Args:
        date: Date to generate report for (default: yesterday)
    """
    if date is None:
        date = (datetime.utcnow() - timedelta(days=1)).date()

    logger.info(f'Running daily task for {date}')

    # Generate report data
    report_data = generate_daily_report(date)

    if report_data:
        # Write HTML report
        write_html_report(date, report_data)

        # Write CSV report
        write_csv_report(date, report_data)

        logger.info(f'Daily task completed for {date}')
    else:
        logger.info(f'No data to report for {date}')


def run_scheduler():
    """
    Run with APScheduler for automatic daily reports.
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error('APScheduler not installed. Run: pip install apscheduler')
        return

    scheduler = BlockingScheduler()

    # Run at 1 AM every day
    scheduler.add_job(
        run_daily_task,
        CronTrigger(hour=1, minute=0),
        id='daily_report',
        name='Generate daily report',
    )

    logger.info('Scheduler started. Press Ctrl+C to exit.')

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Scheduler stopped.')


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='SearchSift Daily Tasks')

    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run the daily task once and exit'
    )

    parser.add_argument(
        '--date',
        type=str,
        help='Date to generate report for (YYYY-MM-DD). Default: yesterday'
    )

    parser.add_argument(
        '--scheduler',
        action='store_true',
        help='Run with APScheduler for automatic daily reports'
    )

    args = parser.parse_args()

    # Initialize database
    init_db()

    if args.scheduler:
        run_scheduler()
    elif args.run_once:
        date = None
        if args.date:
            try:
                date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except ValueError:
                logger.error(f'Invalid date format: {args.date}. Use YYYY-MM-DD')
                return

        run_daily_task(date)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
