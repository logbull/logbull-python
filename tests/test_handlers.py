"""Tests for LogBull logging handlers."""

import logging
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from logbull import LogBullHandler


class TestLogBullHandler:
    """Test LogBullHandler for Python logging integration."""

    @pytest.fixture
    def mock_sender(self) -> Generator[Mock, None, None]:
        """Mock the LogSender to avoid network calls."""
        with patch("logbull.handlers.standard.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance
            yield mock_sender_instance

    @pytest.fixture
    def handler(self, mock_sender: Mock) -> LogBullHandler:
        """Create a test handler instance."""
        return LogBullHandler(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

    @pytest.fixture
    def logger_with_handler(self, handler: LogBullHandler) -> logging.Logger:
        """Create a Python logger with LogBull handler."""
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        # Clear any existing handlers
        logger.handlers.clear()
        logger.addHandler(handler)
        # Prevent propagation to avoid interference with other tests
        logger.propagate = False
        return logger

    def test_handler_initialization(self, mock_sender: Mock) -> None:
        """Test basic handler initialization."""
        handler = LogBullHandler(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
        )
        assert handler is not None
        assert isinstance(handler, logging.Handler)

    def test_invalid_config_raises_error(self) -> None:
        """Test that invalid configuration raises appropriate errors."""
        with pytest.raises(ValueError):
            LogBullHandler(project_id="invalid-uuid", host="http://localhost:4005")

    def test_basic_logging(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test basic logging through Python logging."""
        logger_with_handler.info("Test info message")

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert "Test info message" in call_args["message"]
        assert "timestamp" in call_args

    def test_logging_with_extra(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test logging with extra fields."""
        extra_data = {"user_id": "123", "action": "test"}
        logger_with_handler.info("User action", extra=extra_data)

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert call_args["fields"]["user_id"] == "123"
        assert call_args["fields"]["action"] == "test"

    def test_all_log_levels(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test all Python logging levels."""
        test_cases = [
            (logging.DEBUG, "debug", "DEBUG"),
            (logging.INFO, "info", "INFO"),
            (logging.WARNING, "warning", "WARNING"),
            (logging.ERROR, "error", "ERROR"),
            (logging.CRITICAL, "critical", "CRITICAL"),
        ]

        for _log_level, method_name, expected_level in test_cases:
            mock_sender.reset_mock()
            method = getattr(logger_with_handler, method_name)
            method("Test message")

            call_args = mock_sender.add_log_to_queue.call_args[0][0]
            assert call_args["level"] == expected_level

    def test_exception_logging(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test logging with exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger_with_handler.error("An error occurred", exc_info=True)

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert "exception" in call_args["fields"]
        assert "ValueError" in call_args["fields"]["exception"]
        assert "Test exception" in call_args["fields"]["exception"]

    def test_structured_fields_extraction(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test that handler extracts standard fields from log records."""
        logger_with_handler.info("Test message")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        fields = call_args["fields"]

        # Should include standard logging fields
        expected_fields = ["logger_name", "filename", "line_number", "function_name"]
        for field in expected_fields:
            assert field in fields

    def test_message_formatting(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test message formatting with parameters."""
        logger_with_handler.info("User %s performed %s", "john", "login")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        assert "User john performed login" in call_args["message"]

    def test_handler_level_filtering(self, mock_sender: Mock) -> None:
        """Test that handler respects its own level setting."""
        handler = LogBullHandler(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            level=logging.WARNING,
        )

        logger = logging.getLogger("test_filter")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False

        # INFO should be filtered out
        logger.info("Info message")
        mock_sender.add_log_to_queue.assert_not_called()

        # WARNING should pass through
        logger.warning("Warning message")
        mock_sender.add_log_to_queue.assert_called_once()

    def test_flush(self, handler: LogBullHandler, mock_sender: Mock) -> None:
        """Test flush method."""
        handler.flush()
        mock_sender.flush.assert_called_once()

    def test_close(self, handler: LogBullHandler, mock_sender: Mock) -> None:
        """Test close method."""
        handler.close()
        mock_sender.shutdown.assert_called_once()

    def test_handler_with_custom_formatter(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test handler with custom log formatter."""
        formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
        logger_with_handler.handlers[0].setFormatter(formatter)

        logger_with_handler.info("Test message")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        # Message should be formatted according to the custom formatter
        assert "INFO - test_logger - Test message" in call_args["message"]

    def test_multiple_extra_fields(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test logging with multiple extra fields of different types."""
        extra = {
            "string_field": "text",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"nested": "value"},
        }

        logger_with_handler.info("Complex data", extra=extra)

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        fields = call_args["fields"]

        assert fields["string_field"] == "text"
        assert fields["int_field"] == 42
        assert fields["float_field"] == 3.14
        assert fields["bool_field"] is True
        assert fields["list_field"] == [1, 2, 3]
        assert fields["dict_field"] == {"nested": "value"}

    def test_thread_and_process_info(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test that thread and process information is captured."""
        logger_with_handler.info("Test message")

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        fields = call_args["fields"]

        assert "thread_id" in fields
        assert "process_id" in fields
        assert isinstance(fields["thread_id"], int)
        assert isinstance(fields["process_id"], int)

    def test_error_handling_in_emit(
        self, handler: LogBullHandler, mock_sender: Mock
    ) -> None:
        """Test error handling when emit fails."""
        # Make the sender raise an exception
        mock_sender.add_log_to_queue.side_effect = Exception("Network error")

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # This should not raise an exception but handle it gracefully
        try:
            handler.emit(record)
        except Exception:
            pytest.fail("Handler should handle errors gracefully")

    def test_filter_internal_fields(
        self, logger_with_handler: logging.Logger, mock_sender: Mock
    ) -> None:
        """Test that internal logging fields are not included in the output."""
        # Add some extra data that should be included
        logger_with_handler.info("Test", extra={"custom_field": "value"})

        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        fields = call_args["fields"]

        # Should include custom field
        assert fields["custom_field"] == "value"

        # Should NOT include internal Python logging fields
        internal_fields = [
            "msg",
            "args",
            "levelno",
            "pathname",
            "module",
            "created",
            "msecs",
            "relativeCreated",
            "exc_text",
        ]
        for field in internal_fields:
            assert field not in fields
