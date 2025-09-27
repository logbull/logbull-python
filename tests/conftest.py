"""Shared test fixtures for LogBull tests."""

from typing import Any, Dict, Generator
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_http_requests() -> Generator[Mock, None, None]:
    """Mock HTTP requests to avoid network calls during tests."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda self, *args: None

        mock_urlopen.return_value = mock_response
        yield mock_urlopen


@pytest.fixture
def valid_config() -> Dict[str, str]:
    """Provide valid configuration for testing."""
    return {
        "project_id": "12345678-1234-1234-1234-123456789012",
        "host": "http://localhost:4005",
        "api_key": "test_api_key_123",
    }


@pytest.fixture
def sample_log_entry() -> Dict[str, Any]:
    """Provide a sample log entry for testing."""
    return {
        "level": "INFO",
        "message": "Test message",
        "timestamp": "2023-12-01T10:00:00.000000Z",
        "fields": {"key": "value"},
    }
