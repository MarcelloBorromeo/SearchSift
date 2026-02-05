"""
Tests for the /ingest endpoint.
"""

import json
import pytest
from datetime import datetime, timedelta


class TestIngestEndpoint:
    """Tests for POST /ingest endpoint."""

    def test_ingest_single_event(self, client, api_headers, sample_event):
        """Test ingesting a single search event."""
        response = client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['inserted'] == 1
        assert data['skipped'] == 0

    def test_ingest_multiple_events(self, client, api_headers, sample_event, sample_click_event):
        """Test ingesting multiple events at once."""
        events = [sample_event, sample_click_event]

        response = client.post(
            '/ingest',
            data=json.dumps({'events': events}),
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['inserted'] == 2

    def test_ingest_without_api_key(self, client, sample_event):
        """Test that requests without API key are rejected."""
        response = client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers={'Content-Type': 'application/json'},
        )

        assert response.status_code == 401

    def test_ingest_with_invalid_api_key(self, client, sample_event):
        """Test that requests with invalid API key are rejected."""
        response = client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'wrong-key',
            },
        )

        assert response.status_code == 403

    def test_ingest_empty_query_skipped(self, client, api_headers):
        """Test that events with empty queries are skipped."""
        event = {
            'type': 'search',
            'query': '',
            'url': 'https://www.google.com/',
            'engine': 'google',
        }

        response = client.post(
            '/ingest',
            data=json.dumps({'events': [event]}),
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['inserted'] == 0
        assert data['skipped'] == 1

    def test_ingest_no_events(self, client, api_headers):
        """Test request with no events."""
        response = client.post(
            '/ingest',
            data=json.dumps({'events': []}),
            headers=api_headers,
        )

        assert response.status_code == 400

    def test_ingest_no_json_body(self, client, api_headers):
        """Test request with no JSON body."""
        response = client.post(
            '/ingest',
            headers=api_headers,
        )

        assert response.status_code == 400

    def test_ingest_single_event_format(self, client, api_headers, sample_event):
        """Test that single event format (not wrapped in events array) works."""
        response = client.post(
            '/ingest',
            data=json.dumps(sample_event),
            headers=api_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['inserted'] == 1


class TestDeduplication:
    """Tests for event deduplication."""

    def test_duplicate_events_deduplicated(self, client, api_headers, sample_event):
        """Test that identical events within dedupe window are skipped."""
        # First request
        response1 = client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers=api_headers,
        )
        assert response1.status_code == 200
        assert response1.get_json()['inserted'] == 1

        # Second request with same event
        response2 = client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers=api_headers,
        )
        assert response2.status_code == 200
        # Should be skipped as duplicate
        assert response2.get_json()['skipped'] == 1

    def test_different_queries_not_deduplicated(self, client, api_headers, sample_event):
        """Test that different queries are not deduplicated."""
        event2 = {**sample_event, 'query': 'different query'}

        # First event
        client.post(
            '/ingest',
            data=json.dumps({'events': [sample_event]}),
            headers=api_headers,
        )

        # Second event with different query
        response = client.post(
            '/ingest',
            data=json.dumps({'events': [event2]}),
            headers=api_headers,
        )

        assert response.status_code == 200
        assert response.get_json()['inserted'] == 1


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'version' in data
        assert 'database' in data
