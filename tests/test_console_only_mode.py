"""Tests for console-only mode (no credentials)."""

from typing import Generator
from unittest.mock import Mock, patch

import pytest

from logbull import LogBullHandler, LogBullLogger, LoguruSink, StructlogProcessor


class TestConsoleOnlyMode:
    """Test LogBull components in console-only mode."""

    @pytest.fixture
    def capture_stdout(self) -> Generator[Mock, None, None]:
        """Capture print calls for testing console output."""
        with patch("builtins.print") as mock_print:
            yield mock_print

    def test_logger_without_credentials(self, capture_stdout: Mock) -> None:
        """Test LogBullLogger without credentials works in console-only mode."""
        logger = LogBullLogger()

        assert logger is not None
        assert logger.console_only_mode is True
        assert logger.sender is None

        # Should print notification about console-only mode
        notification_call = capture_stdout.call_args_list[0]
        assert "console-only mode" in notification_call[0][0].lower()

        # Reset mock for next test
        capture_stdout.reset_mock()

        # Logging should still work, just to console
        logger.info("Test message")

        # Should print to console
        assert capture_stdout.called
        console_output = capture_stdout.call_args[0][0]
        assert "Test message" in console_output
        assert "[INFO]" in console_output

    def test_logger_with_partial_credentials(self, capture_stdout: Mock) -> None:
        """Test logger with only project_id or only host."""
        # Only project_id provided
        logger1 = LogBullLogger(project_id="12345678-1234-1234-1234-123456789012")
        assert logger1.console_only_mode is True
        assert logger1.sender is None

        capture_stdout.reset_mock()

        # Only host provided
        logger2 = LogBullLogger(host="http://localhost:4005")
        assert logger2.console_only_mode is True
        assert logger2.sender is None

    def test_logger_console_only_still_logs_to_console(
        self, capture_stdout: Mock
    ) -> None:
        """Test that console-only mode still prints logs to console."""
        logger = LogBullLogger()

        capture_stdout.reset_mock()

        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Should have multiple console outputs (one for each level that's above INFO)
        assert capture_stdout.call_count >= 3  # INFO, WARNING, ERROR

    def test_logger_console_only_with_context(self, capture_stdout: Mock) -> None:
        """Test that context works in console-only mode."""
        logger = LogBullLogger()
        context_logger = logger.with_context({"user": "john_doe"})

        capture_stdout.reset_mock()

        context_logger.info("User action")

        # Should include context in console output
        console_output = capture_stdout.call_args[0][0]
        assert "user=john_doe" in console_output

    def test_logger_console_only_flush_and_shutdown(self) -> None:
        """Test that flush and shutdown don't fail in console-only mode."""
        logger = LogBullLogger()

        # These should not raise exceptions
        logger.flush()
        logger.shutdown()

    def test_handler_without_credentials(self, capture_stdout: Mock) -> None:
        """Test LogBullHandler without credentials is disabled."""
        handler = LogBullHandler()

        assert handler is not None
        assert handler.disabled is True
        assert handler.sender is None

        # Should print notification
        notification_call = capture_stdout.call_args_list[0]
        assert "disabled" in notification_call[0][0].lower()

    def test_handler_disabled_doesnt_process_logs(self, capture_stdout: Mock) -> None:
        """Test that disabled handler doesn't process logs."""
        import logging

        handler = LogBullHandler()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        capture_stdout.reset_mock()

        # Emit should return early and do nothing
        handler.emit(record)

        # Should not have called print (except the initial notification)
        # Reset was called, so no new calls should be made
        assert capture_stdout.call_count == 0

    def test_handler_disabled_flush_and_close(self) -> None:
        """Test that flush and close work on disabled handler."""
        handler = LogBullHandler()

        # These should not raise exceptions
        handler.flush()
        handler.close()

    def test_loguru_sink_without_credentials(self, capture_stdout: Mock) -> None:
        """Test LoguruSink without credentials is disabled."""
        sink = LoguruSink()

        assert sink is not None
        assert sink.disabled is True
        assert sink.sender is None

        # Should print notification
        notification_call = capture_stdout.call_args_list[0]
        assert "disabled" in notification_call[0][0].lower()

    def test_loguru_sink_disabled_flush_and_close(self) -> None:
        """Test that flush and close work on disabled sink."""
        sink = LoguruSink()

        # These should not raise exceptions
        sink.flush()
        sink.close()

    def test_structlog_processor_without_credentials(
        self, capture_stdout: Mock
    ) -> None:
        """Test StructlogProcessor without credentials is disabled."""
        processor = StructlogProcessor()

        assert processor is not None
        assert processor.disabled is True
        assert processor.sender is None

        # Should print notification
        notification_call = capture_stdout.call_args_list[0]
        assert "disabled" in notification_call[0][0].lower()

    def test_structlog_processor_disabled_passes_through(self) -> None:
        """Test that disabled processor passes event through unchanged."""
        processor = StructlogProcessor()

        # Mock event dict
        event_dict = {
            "event": "Test message",
            "level": "info",
            "custom_field": "value",
        }

        # Processor should return the event_dict unchanged
        result = processor(None, "test_logger", event_dict)
        assert result == event_dict

    def test_structlog_processor_disabled_flush_and_close(self) -> None:
        """Test that flush and close work on disabled processor."""
        processor = StructlogProcessor()

        # These should not raise exceptions
        processor.flush()
        processor.close()

    def test_logger_with_full_credentials_not_console_only(self) -> None:
        """Test that logger with full credentials is not in console-only mode."""
        with patch("logbull.core.logger.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance

            logger = LogBullLogger(
                project_id="12345678-1234-1234-1234-123456789012",
                host="http://localhost:4005",
                api_key="test_api_key",
            )

            assert logger.console_only_mode is False
            assert logger.sender is not None

    def test_handler_with_full_credentials_not_disabled(self) -> None:
        """Test that handler with full credentials is not disabled."""
        with patch("logbull.handlers.standard.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance

            handler = LogBullHandler(
                project_id="12345678-1234-1234-1234-123456789012",
                host="http://localhost:4005",
                api_key="test_api_key",
            )

            assert handler.disabled is False
            assert handler.sender is not None
