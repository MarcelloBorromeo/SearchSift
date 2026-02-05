"""
Tests for the daily aggregation tasks.
"""

import json
import pytest
import sys
import tempfile
from datetime import datetime, date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDailyReportGeneration:
    """Tests for daily report generation."""

    @pytest.fixture
    def populated_db(self, app, api_headers, client):
        """Populate database with test data."""
        events = [
            {
                'type': 'search',
                'query': 'python tutorial',
                'url': 'https://google.com/search?q=python',
                'engine': 'google',
                'timestamp': '2024-01-15T10:00:00Z',
            },
            {
                'type': 'click',
                'query': 'python tutorial',
                'url': 'https://python.org',
                'engine': 'google',
                'timestamp': '2024-01-15T10:01:00Z',
            },
            {
                'type': 'search',
                'query': 'amazon laptop',
                'url': 'https://google.com/search?q=amazon',
                'engine': 'google',
                'timestamp': '2024-01-15T11:00:00Z',
            },
            {
                'type': 'search',
                'query': 'netflix movies',
                'url': 'https://bing.com/search?q=netflix',
                'engine': 'bing',
                'timestamp': '2024-01-15T12:00:00Z',
            },
        ]

        for event in events:
            client.post(
                '/ingest',
                data=json.dumps({'events': [event]}),
                headers=api_headers,
            )

        return date(2024, 1, 15)

    def test_generate_daily_report(self, app, populated_db):
        """Test that daily report generates correct data."""
        from backend.tasks import generate_daily_report

        report_data = generate_daily_report(populated_db)

        assert report_data is not None
        assert report_data['date'] == '2024-01-15'
        assert report_data['summary']['total_events'] == 4
        assert report_data['summary']['total_searches'] == 3
        assert report_data['summary']['total_clicks'] == 1

    def test_report_category_breakdown(self, app, populated_db):
        """Test category breakdown in report."""
        from backend.tasks import generate_daily_report

        report_data = generate_daily_report(populated_db)

        categories = report_data['by_category']
        assert 'Coding' in categories
        assert 'Shopping' in categories
        assert 'Entertainment' in categories

    def test_report_engine_breakdown(self, app, populated_db):
        """Test engine breakdown in report."""
        from backend.tasks import generate_daily_report

        report_data = generate_daily_report(populated_db)

        engines = report_data['by_engine']
        assert 'google' in engines
        assert 'bing' in engines
        assert engines['google'] == 3
        assert engines['bing'] == 1

    def test_report_top_queries(self, app, populated_db):
        """Test top queries in report."""
        from backend.tasks import generate_daily_report

        report_data = generate_daily_report(populated_db)

        top_queries = report_data['top_queries']
        assert len(top_queries) > 0
        assert any(q['query'] == 'python tutorial' for q in top_queries)

    def test_empty_date_returns_none(self, app):
        """Test that empty date returns None."""
        from backend.tasks import generate_daily_report

        result = generate_daily_report(date(2000, 1, 1))  # Date with no data
        assert result is None

    def test_write_html_report(self, app, populated_db):
        """Test writing HTML report file."""
        from backend.tasks import generate_daily_report, write_html_report

        report_data = generate_daily_report(populated_db)

        with tempfile.TemporaryDirectory() as tmpdir:
            from backend import config
            original_reports_dir = config.REPORTS_DIR
            config.REPORTS_DIR = Path(tmpdir)

            try:
                output_path = write_html_report(populated_db, report_data)

                assert output_path.exists()
                assert output_path.suffix == '.html'

                content = output_path.read_text()
                assert 'SearchSift' in content
                assert '2024-01-15' in content
            finally:
                config.REPORTS_DIR = original_reports_dir

    def test_write_csv_report(self, app, populated_db):
        """Test writing CSV report file."""
        from backend.tasks import generate_daily_report, write_csv_report

        report_data = generate_daily_report(populated_db)

        with tempfile.TemporaryDirectory() as tmpdir:
            from backend import config
            original_reports_dir = config.REPORTS_DIR
            config.REPORTS_DIR = Path(tmpdir)

            try:
                output_path = write_csv_report(populated_db, report_data)

                assert output_path.exists()
                assert output_path.suffix == '.csv'

                content = output_path.read_text()
                lines = content.strip().split('\n')
                assert len(lines) == 5  # Header + 4 records
                assert 'query' in lines[0].lower()
                assert 'category' in lines[0].lower()
            finally:
                config.REPORTS_DIR = original_reports_dir


class TestDomainExtraction:
    """Tests for domain extraction utility."""

    def test_get_domain(self):
        """Test domain extraction from URLs."""
        from backend.tasks import get_domain

        assert get_domain('https://www.google.com/search?q=test') == 'google.com'
        assert get_domain('https://docs.python.org/3/') == 'docs.python.org'
        assert get_domain('http://example.com') == 'example.com'
        assert get_domain('invalid-url') == 'unknown'
        assert get_domain('') == 'unknown'


class TestSummaryEndpoint:
    """Tests for /api/summary endpoint."""

    def test_summary_endpoint(self, client, api_headers, sample_event):
        """Test summary API endpoint."""
        # Add some data
        client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers=api_headers,
        )

        # Get summary
        response = client.get(
            '/api/summary?start=2024-01-15&end=2024-01-15',
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'total_searches' in data
        assert 'total_clicks' in data
        assert 'by_category' in data
        assert 'by_engine' in data

    def test_summary_invalid_date(self, client, api_headers):
        """Test summary with invalid date format."""
        response = client.get(
            '/api/summary?start=invalid-date',
            headers=api_headers,
        )

        assert response.status_code == 400

    def test_summary_requires_auth(self, client):
        """Test that summary endpoint requires authentication."""
        response = client.get('/api/summary?start=2024-01-15&end=2024-01-15')
        assert response.status_code == 401
