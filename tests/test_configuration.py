"""Tests for LogBull configuration validation and error handling."""

from typing import Generator
from unittest.mock import Mock, patch

import pytest

from logbull import LogBullHandler, LogBullLogger
from logbull.handlers import LoguruSink, StructlogProcessor


class TestConfigurationValidation:
    """Test configuration validation across all LogBull components."""

    @pytest.fixture
    def mock_sender(self) -> Generator[Mock, None, None]:
        """Mock LogSender to avoid network calls."""
        with patch("logbull.core.logger.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance
            yield mock_sender_instance

    def test_valid_project_id_formats(self, mock_sender: Mock) -> None:
        """Test that valid project ID formats are accepted."""
        valid_uuids = [
            "12345678-1234-1234-1234-123456789012",
            "abcdef12-3456-7890-abcd-ef1234567890",
            "ABCDEF12-3456-7890-ABCD-EF1234567890",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]

        for project_id in valid_uuids:
            logger = LogBullLogger(project_id=project_id, host="http://localhost:4005")
            assert logger is not None

    def test_invalid_project_id_formats(self, mock_sender: Mock) -> None:
        """Test that invalid project ID formats raise ValueError."""
        invalid_uuids = [
            "",  # Empty
            "not-a-uuid",  # Not UUID format
            "12345678-1234-1234-1234",  # Too short
            "12345678-1234-1234-1234-123456789012-extra",  # Too long
            "12345678_1234_1234_1234_123456789012",  # Wrong separators
            "12345678-1234-1234-1234-12345678901g",  # Invalid character
            "12345678-1234-1234-123456789012",  # Missing section
        ]

        for project_id in invalid_uuids:
            with pytest.raises(
                ValueError, match="Project ID cannot be empty|Invalid project ID format"
            ):
                LogBullLogger(project_id=project_id, host="http://localhost:4005")

    def test_valid_host_urls(self, mock_sender: Mock) -> None:
        """Test that valid host URLs are accepted."""
        valid_hosts = [
            "http://localhost:4005",
            "https://logbull.example.com",
            "http://192.168.1.100:8080",
            "https://my-logbull.company.com:443",
            "http://logbull:4005",
            "https://logbull.local",
        ]

        for host in valid_hosts:
            logger = LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012", host=host
            )
            assert logger is not None

    def test_invalid_host_urls(self, mock_sender: Mock) -> None:
        """Test that invalid host URLs raise ValueError."""
        invalid_hosts = [
            "",  # Empty
            "not-a-url",  # No protocol
            "ftp://example.com",  # Wrong protocol
            "http://",  # No host
            "://localhost:4005",  # No scheme
            "localhost:4005",  # No scheme
        ]

        for host in invalid_hosts:
            # Test each host individually to see which ones actually raise errors
            try:
                LogBullLogger(
                    project_id="12345678-1234-1234-1234-123456789012", host=host
                )
                # If we get here, the host was accepted (should not happen for invalid hosts)
                pytest.fail(f"Host '{host}' was incorrectly accepted as valid")
            except ValueError:
                # This is expected for invalid hosts
                pass
            except Exception as e:
                # Unexpected error type
                pytest.fail(
                    f"Host '{host}' raised unexpected error: {type(e).__name__}: {e}"
                )

    def test_valid_api_keys(self, mock_sender: Mock) -> None:
        """Test that valid API keys are accepted."""
        valid_api_keys = [
            "test_api_key_123",
            "abcdefghij1234567890",
            "API.KEY-WITH_DOTS.AND-HYPHENS",
            "a" * 50,  # Long key
            None,  # None should be valid (optional)
        ]

        for api_key in valid_api_keys:
            logger = LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012",
                host="http://localhost:4005",
                api_key=api_key,
            )
            assert logger is not None

    def test_invalid_api_keys(self, mock_sender: Mock) -> None:
        """Test that invalid API keys raise ValueError."""
        # Note: Empty string is valid (gets converted to None) since API key is optional
        invalid_api_keys = [
            "short",  # Too short
            "key with spaces",  # Spaces not allowed
            "key@with#special$chars",  # Invalid characters
            "key/with/slashes",  # Slashes not allowed
        ]

        for api_key in invalid_api_keys:
            with pytest.raises(
                ValueError,
                match="API key must be at least 10 characters|Invalid API key format",
            ):
                LogBullLogger(
                    project_id="12345678-1234-1234-1234-123456789012",
                    host="http://localhost:4005",
                    api_key=api_key,
                )

    def test_valid_log_levels(self, mock_sender: Mock) -> None:
        """Test that valid log levels are accepted."""
        valid_levels = [
            "DEBUG",
            "debug",
            "Debug",
            "INFO",
            "info",
            "Info",
            "WARNING",
            "warning",
            "Warning",
            "WARN",
            "warn",
            "Warn",
            "ERROR",
            "error",
            "Error",
            "CRITICAL",
            "critical",
            "Critical",
            "FATAL",
            "fatal",
            "Fatal",
        ]

        for level in valid_levels:
            logger = LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012",
                host="http://localhost:4005",
                log_level=level,
            )
            assert logger is not None

    def test_invalid_log_levels(self, mock_sender: Mock) -> None:
        """Test that invalid log levels raise ValueError."""
        invalid_levels = [
            "",
            "INVALID",
            "TRACE",
            "VERBOSE",
            "123",
            None,  # None should raise error for log_level
        ]

        for level in invalid_levels:
            with pytest.raises((ValueError, AttributeError)):
                if level is None:
                    # Test with None log_level - this will cause an AttributeError
                    LogBullLogger(
                        project_id="12345678-1234-1234-1234-123456789012",
                        host="http://localhost:4005",
                        log_level=level,  # type: ignore[arg-type]
                    )
                else:
                    LogBullLogger(
                        project_id="12345678-1234-1234-1234-123456789012",
                        host="http://localhost:4005",
                        log_level=level,
                    )

    def test_configuration_validation_across_components(self) -> None:
        """Test that all components validate configuration consistently."""
        project_id = "12345678-1234-1234-1234-123456789012"
        host = "http://localhost:4005"
        api_key = "valid_api_key"

        with patch("logbull.core.logger.LogSender"), patch(
            "logbull.handlers.standard.LogSender"
        ), patch("logbull.handlers.loguru.LogSender"), patch(
            "logbull.handlers.structlog.LogSender"
        ):
            # All components should accept the same valid configuration
            logger = LogBullLogger(project_id=project_id, host=host, api_key=api_key)
            handler = LogBullHandler(project_id=project_id, host=host, api_key=api_key)
            sink = LoguruSink(project_id=project_id, host=host, api_key=api_key)
            processor = StructlogProcessor(
                project_id=project_id, host=host, api_key=api_key
            )

            assert all([logger, handler, sink, processor])

    def test_configuration_validation_error_consistency(self) -> None:
        """Test that all components raise the same errors for invalid configuration."""
        invalid_project_id = "invalid-uuid"
        valid_host = "http://localhost:4005"

        component_classes = [
            LogBullLogger,
            LogBullHandler,
            LoguruSink,
            StructlogProcessor,
        ]

        with patch("logbull.core.logger.LogSender"), patch(
            "logbull.handlers.standard.LogSender"
        ), patch("logbull.handlers.loguru.LogSender"), patch(
            "logbull.handlers.structlog.LogSender"
        ):
            for component_class in component_classes:
                with pytest.raises(ValueError, match="Invalid project ID format"):
                    component_class(project_id=invalid_project_id, host=valid_host)

    def test_whitespace_handling_in_config(self, mock_sender: Mock) -> None:
        """Test that configuration handles whitespace correctly."""
        # Should trim whitespace and accept
        logger = LogBullLogger(
            project_id="  12345678-1234-1234-1234-123456789012  ",
            host="  http://localhost:4005  ",
            api_key="  valid_api_key_123  ",
        )
        assert logger is not None

    def test_case_insensitive_log_levels(self, mock_sender: Mock) -> None:
        """Test that log levels are case-insensitive."""
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            log_level="info",
        )
        assert logger.log_level == "INFO"

    def test_log_level_normalization(self, mock_sender: Mock) -> None:
        """Test that log levels are normalized correctly."""
        test_cases = [
            ("FATAL", "CRITICAL"),
            ("CRITICAL", "CRITICAL"),
            ("WARN", "WARN"),  # WARN stays as WARN
            ("WARNING", "WARNING"),
        ]

        for input_level, expected_level in test_cases:
            logger = LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012",
                host="http://localhost:4005",
                log_level=input_level,
            )
            assert logger.log_level == expected_level

    def test_context_validation(self, mock_sender: Mock) -> None:
        """Test validation of context parameter."""
        valid_contexts = [
            None,
            {},
            {"key": "value"},
            {"multiple": "values", "with": "different", "types": 123},
        ]

        for context in valid_contexts:
            logger = LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012",
                host="http://localhost:4005",
                context=context,
            )
            assert logger is not None

    def test_required_parameters(self) -> None:
        """Test that missing parameters result in console-only mode."""
        # Missing project_id - should work in console-only mode
        logger = LogBullLogger(host="http://localhost:4005")
        assert logger is not None
        assert logger.console_only_mode is True
        assert logger.sender is None

        # Missing host - should work in console-only mode
        logger = LogBullLogger(project_id="12345678-1234-1234-1234-123456789012")
        assert logger is not None
        assert logger.console_only_mode is True
        assert logger.sender is None

        # Missing both - should work in console-only mode
        logger = LogBullLogger()
        assert logger is not None
        assert logger.console_only_mode is True
        assert logger.sender is None

    def test_none_values_for_required_params(self) -> None:
        """Test that None values for parameters result in console-only mode."""
        # project_id=None - should work in console-only mode
        logger = LogBullLogger(project_id=None, host="http://localhost:4005")
        assert logger is not None
        assert logger.console_only_mode is True
        assert logger.sender is None

        # host=None - should work in console-only mode
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012", host=None
        )
        assert logger is not None
        assert logger.console_only_mode is True
        assert logger.sender is None
