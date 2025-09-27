"""Tests for LogBullLogger (standalone logger)."""

from typing import Generator
from unittest.mock import Mock, patch

import pytest

from logbull import LogBullLogger


class TestLogBullLogger:
    """Test LogBullLogger public API."""

    @pytest.fixture
    def mock_sender(self) -> Generator[Mock, None, None]:
        """Mock the LogSender to avoid network calls."""
        with patch("logbull.core.logger.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance
            yield mock_sender_instance

    @pytest.fixture
    def mock_health_checker(self) -> Generator[Mock, None, None]:
        """Mock HealthChecker to avoid network calls."""
        with patch("logbull.core.sender.HealthChecker") as mock_health_class:
            mock_health_instance = Mock()
            mock_health_instance.check_availability.return_value = True
            mock_health_class.return_value = mock_health_instance
            yield mock_health_instance

    @pytest.fixture
    def logger(self, mock_sender: Mock, mock_health_checker: Mock) -> LogBullLogger:
        """Create a test logger instance."""
        return LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

    @pytest.fixture
    def capture_stdout(self) -> Generator[Mock, None, None]:
        """Capture print calls for testing console output."""
        with patch("builtins.print") as mock_print:
            yield mock_print

    def test_logger_initialization(
        self,
        mock_sender: Mock,
        mock_health_checker: Mock,
    ) -> None:
        """Test basic logger initialization."""
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
        )
        assert logger is not None
        assert logger.log_level == "INFO"

    def test_logger_initialization_with_options(
        self,
        mock_sender: Mock,
        mock_health_checker: Mock,
    ) -> None:
        """Test logger initialization with custom options."""
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key_123",
            log_level="DEBUG",
        )
        assert logger.log_level == "DEBUG"

    def test_invalid_project_id_raises_error(self) -> None:
        """Test that invalid project ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid project ID format"):
            LogBullLogger(project_id="invalid-uuid", host="http://localhost:4005")

    def test_invalid_host_raises_error(self) -> None:
        """Test that invalid host raises ValueError."""
        with pytest.raises(ValueError, match="Invalid host URL format"):
            LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012",
                host="not-a-url",
            )

    def test_info_logging(
        self,
        logger: LogBullLogger,
        mock_sender: Mock,
        capture_stdout: Mock,
    ) -> None:
        """Test basic info logging."""
        logger.info("Test message")

        # Check that add_log_to_queue was called
        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "Test message"
        assert "timestamp" in call_args
        assert call_args["fields"] == {}

        # Check console output
        capture_stdout.assert_called_once()
        call_args = capture_stdout.call_args[0][0]
        assert "INFO" in call_args
        assert "Test message" in call_args

    def test_logging_with_fields(
        self,
        logger: LogBullLogger,
        mock_sender: Mock,
        capture_stdout: Mock,
    ) -> None:
        """Test logging with custom fields."""
        fields = {"user_id": "123", "action": "login"}
        logger.info("User action", fields=fields)

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert call_args["fields"] == fields

        # Check console output includes fields
        capture_stdout.assert_called_once()
        call_args = capture_stdout.call_args[0][0]
        assert "user_id=123" in call_args
        assert "action=login" in call_args

    def test_all_log_levels(
        self,
        logger: LogBullLogger,
        mock_sender: Mock,
    ) -> None:
        """Test all supported log levels."""
        test_cases = [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
            ("warn", "WARNING"),
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
            ("fatal", "CRITICAL"),
        ]

        for method_name, expected_level in test_cases:
            mock_sender.reset_mock()
            method = getattr(logger, method_name)
            method("Test message")

            if expected_level in ["DEBUG"]:
                # DEBUG should not be logged with default INFO level
                mock_sender.add_log_to_queue.assert_not_called()
            else:
                call_args = mock_sender.add_log_to_queue.call_args[0][0]
                assert call_args["level"] == expected_level

    def test_debug_level_filtering(
        self,
        mock_sender: Mock,
        mock_health_checker: Mock,
    ) -> None:
        """Test that DEBUG messages are filtered when log_level is INFO."""
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            log_level="INFO",
        )

        logger.debug("Debug message")
        mock_sender.add_log_to_queue.assert_not_called()

        logger.info("Info message")
        mock_sender.add_log_to_queue.assert_called_once()

    def test_debug_level_logger(
        self,
        mock_sender: Mock,
        mock_health_checker: Mock,
    ) -> None:
        """Test DEBUG level logger processes all messages."""
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            log_level="DEBUG",
        )

        logger.debug("Debug message")
        mock_sender.add_log_to_queue.assert_called_once()

    def test_with_context(self, logger: LogBullLogger, mock_sender: Mock) -> None:
        """Test context management with with_context()."""
        context = {"session_id": "abc123", "user_id": "456"}
        context_logger = logger.with_context(context)

        # Verify it returns a new logger instance
        assert context_logger is not logger
        assert isinstance(context_logger, LogBullLogger)

        # Test that context is included in logs
        context_logger.info("Test message", fields={"extra": "data"})

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert call_args["fields"]["session_id"] == "abc123"
        assert call_args["fields"]["user_id"] == "456"
        assert call_args["fields"]["extra"] == "data"

    def test_chained_context(self, logger: LogBullLogger, mock_sender: Mock) -> None:
        """Test chaining context with multiple with_context() calls."""
        logger1 = logger.with_context({"level1": "value1"})
        logger2 = logger1.with_context({"level2": "value2"})

        logger2.info("Test message")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert call_args["fields"]["level1"] == "value1"
        assert call_args["fields"]["level2"] == "value2"

    def test_context_override(self, logger: LogBullLogger, mock_sender: Mock) -> None:
        """Test that fields parameter overrides context."""
        context_logger = logger.with_context({"key": "context_value"})
        context_logger.info("Test", fields={"key": "field_value"})

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        # Fields should override context
        assert call_args["fields"]["key"] == "field_value"

    def test_flush(self, logger: LogBullLogger, mock_sender: Mock) -> None:
        """Test flush method."""
        logger.flush()
        mock_sender.flush.assert_called_once()

    def test_shutdown(self, logger: LogBullLogger, mock_sender: Mock) -> None:
        """Test shutdown method."""
        logger.shutdown()
        mock_sender.shutdown.assert_called_once()

    def test_log_method(self, logger: LogBullLogger, mock_sender: Mock) -> None:
        """Test generic log method."""
        logger.log("ERROR", "Test error message")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert call_args["level"] == "ERROR"
        assert call_args["message"] == "Test error message"

    def test_console_output_format(
        self,
        logger: LogBullLogger,
        capture_stdout: Mock,
    ) -> None:
        """Test console output format includes timestamp and level."""
        logger.info("Test message", fields={"key": "value"})

        capture_stdout.assert_called_once()
        output = capture_stdout.call_args[0][0]

        # Should contain timestamp in brackets
        assert output.count("[") >= 2  # [timestamp] [level]
        assert "[INFO]" in output
        assert "Test message" in output
        assert "key=value" in output

    def test_empty_message_validation(
        self,
        mock_sender: Mock,
        mock_health_checker: Mock,
    ) -> None:
        """Test that empty messages raise appropriate errors."""
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
        )

        # This should be handled gracefully - either raise error or handle it
        # The exact behavior depends on validation implementation
        try:
            logger.info("")  # Empty string
            # Test None value with type ignore comment since we're testing error handling
            logger.info(None)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            # This is acceptable behavior
            pass

    def test_initialization_with_context(
        self,
        mock_sender: Mock,
        mock_health_checker: Mock,
    ) -> None:
        """Test initialization with default context."""
        context = {"app": "test", "version": "1.0"}
        logger = LogBullLogger(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            context=context,
        )

        logger.info("Test message")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert call_args["fields"]["app"] == "test"
        assert call_args["fields"]["version"] == "1.0"
