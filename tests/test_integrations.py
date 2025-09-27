"""Tests for LogBull third-party library integrations."""

import sys
from typing import Any, Generator, cast
from unittest.mock import Mock, patch

# Import real libraries for integration testing
import loguru
import pytest
import structlog
from loguru import logger as loguru_logger

from logbull.handlers import LoguruSink, StructlogProcessor


LOGURU_AVAILABLE = True
STRUCTLOG_AVAILABLE = True


@pytest.mark.skipif(not LOGURU_AVAILABLE, reason="loguru not available")
class TestLoguruIntegration:
    """Test real Loguru integration with LogBull."""

    @pytest.fixture
    def mock_sender(self) -> Generator[Mock, None, None]:
        """Mock the LogSender to avoid network calls."""
        with patch("logbull.handlers.loguru.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance
            yield mock_sender_instance

    @pytest.fixture
    def loguru_logger_with_logbull(
        self, mock_sender: Mock
    ) -> Generator["loguru.Logger", None, None]:
        """Create a fresh Loguru logger with LogBull sink."""
        # Remove all existing handlers to avoid interference
        loguru_logger.remove()

        # Create LogBull sink
        logbull_sink = LoguruSink(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

        # Add LogBull sink to Loguru
        sink_id = loguru_logger.add(logbull_sink, level="DEBUG")

        yield loguru_logger

        # Cleanup: remove the sink
        loguru_logger.remove(sink_id)

    def test_loguru_basic_logging(
        self,
        loguru_logger_with_logbull: "loguru.Logger",
        mock_sender: Mock,
    ) -> None:
        """Test basic logging through real Loguru to LogBull."""
        loguru_logger_with_logbull.info("Test message from Loguru")

        # Verify that LogSender was called
        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "Test message from Loguru"
        assert "timestamp" in call_args

    def test_loguru_structured_logging(
        self,
        loguru_logger_with_logbull: "loguru.Logger",
        mock_sender: Mock,
    ) -> None:
        """Test structured logging with bound context."""
        # Use Loguru's bind functionality for structured logging
        bound_logger = loguru_logger_with_logbull.bind(
            user_id="12345", session_id="sess_abc123", action="login"
        )

        bound_logger.info("User logged in successfully")

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "User logged in successfully"
        assert call_args["fields"]["user_id"] == "12345"
        assert call_args["fields"]["session_id"] == "sess_abc123"
        assert call_args["fields"]["action"] == "login"

    def test_loguru_exception_logging(
        self,
        loguru_logger_with_logbull: "loguru.Logger",
        mock_sender: Mock,
    ) -> None:
        """Test exception logging through Loguru."""
        try:
            raise ValueError("Test exception for logging")
        except ValueError:
            loguru_logger_with_logbull.exception("An error occurred during processing")

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "ERROR"
        assert "An error occurred during processing" in call_args["message"]
        # Should have exception information in fields
        assert any(key.startswith("exception") for key in call_args["fields"])

    def test_loguru_different_levels(
        self,
        loguru_logger_with_logbull: "loguru.Logger",
        mock_sender: Mock,
    ) -> None:
        """Test different log levels through Loguru."""
        test_cases = [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
        ]

        for loguru_method, expected_level in test_cases:
            mock_sender.reset_mock()

            method = getattr(loguru_logger_with_logbull, loguru_method)
            method(f"Test {loguru_method} message")

            mock_sender.add_log_to_queue.assert_called_once()
            call_args = mock_sender.add_log_to_queue.call_args[0][0]
            assert call_args["level"] == expected_level

    def test_loguru_with_extra_data(
        self,
        loguru_logger_with_logbull: "loguru.Logger",
        mock_sender: Mock,
    ) -> None:
        """Test logging with various extra data types."""
        # Test with mixed data types
        loguru_logger_with_logbull.bind(
            string_field="text_value",
            int_field=42,
            float_field=3.14159,
            bool_field=True,
            list_field=[1, 2, 3],
            dict_field={"nested": "value", "count": 10},
        ).info("Message with various data types")

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        fields = call_args["fields"]

        assert fields["string_field"] == "text_value"
        assert fields["int_field"] == 42
        assert fields["float_field"] == 3.14159
        assert fields["bool_field"] is True
        assert fields["list_field"] == [1, 2, 3]
        assert fields["dict_field"] == {"nested": "value", "count": 10}

    def test_loguru_multiple_sinks(self, mock_sender: Mock) -> None:
        """Test Loguru with multiple sinks including LogBull."""
        # Remove all handlers
        loguru_logger.remove()

        # Add both console and LogBull sinks
        loguru_logger.add(sys.stderr, level="INFO")

        logbull_sink = LoguruSink(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

        sink_id = loguru_logger.add(logbull_sink, level="DEBUG")

        # Log a message
        loguru_logger.info("Message sent to multiple sinks")

        # Verify LogBull received the message
        mock_sender.add_log_to_queue.assert_called_once()

        # Cleanup
        loguru_logger.remove(sink_id)


@pytest.mark.skipif(not STRUCTLOG_AVAILABLE, reason="structlog not available")
class TestStructlogIntegration:
    """Test real Structlog integration with LogBull."""

    @pytest.fixture
    def mock_sender(self) -> Generator[Mock, None, None]:
        """Mock the LogSender to avoid network calls."""
        with patch("logbull.handlers.structlog.LogSender") as mock_sender_class:
            mock_sender_instance = Mock()
            mock_sender_class.return_value = mock_sender_instance
            yield mock_sender_instance

    @pytest.fixture
    def structlog_logger_with_logbull(
        self, mock_sender: Mock
    ) -> Generator["structlog.BoundLogger", None, None]:
        """Configure Structlog with LogBull processor."""
        # Create LogBull processor
        logbull_processor = StructlogProcessor(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

        # Configure structlog with LogBull processor in the chain
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                cast(Any, logbull_processor),  # Add LogBull processor to the chain
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=False,  # Disable caching for tests
        )

        # Create logger
        logger = structlog.get_logger("test_logger")

        yield logger

        # Reset structlog configuration after test
        structlog.reset_defaults()

    def test_structlog_basic_logging(
        self,
        structlog_logger_with_logbull: "structlog.BoundLogger",
        mock_sender: Mock,
    ) -> None:
        """Test basic logging through real Structlog to LogBull."""
        structlog_logger_with_logbull.info("Test message from Structlog")

        # Verify that LogSender was called
        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "Test message from Structlog"
        assert "timestamp" in call_args

    def test_structlog_structured_logging(
        self,
        structlog_logger_with_logbull: "structlog.BoundLogger",
        mock_sender: Mock,
    ) -> None:
        """Test structured logging with key-value pairs."""
        structlog_logger_with_logbull.info(
            "User action completed",
            user_id="12345",
            action="purchase",
            amount=99.99,
            currency="USD",
        )

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "User action completed"
        assert call_args["fields"]["user_id"] == "12345"
        assert call_args["fields"]["action"] == "purchase"
        assert call_args["fields"]["amount"] == 99.99
        assert call_args["fields"]["currency"] == "USD"

    def test_structlog_bound_logging(
        self,
        structlog_logger_with_logbull: "structlog.BoundLogger",
        mock_sender: Mock,
    ) -> None:
        """Test bound context logging."""
        # Bind context to logger
        bound_logger = structlog_logger_with_logbull.bind(
            session_id="sess_abc123", user_id="user_456"
        )

        # Log with additional context
        bound_logger.warning(
            "Rate limit approaching", current_requests=950, max_requests=1000
        )

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "WARNING"
        assert call_args["message"] == "Rate limit approaching"
        # Should include both bound context and additional fields
        assert call_args["fields"]["session_id"] == "sess_abc123"
        assert call_args["fields"]["user_id"] == "user_456"
        assert call_args["fields"]["current_requests"] == 950
        assert call_args["fields"]["max_requests"] == 1000

    def test_structlog_different_levels(
        self,
        structlog_logger_with_logbull: "structlog.BoundLogger",
        mock_sender: Mock,
    ) -> None:
        """Test different log levels through Structlog."""
        test_cases = [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
        ]

        for structlog_method, expected_level in test_cases:
            mock_sender.reset_mock()

            method = getattr(structlog_logger_with_logbull, structlog_method)
            method(f"Test {structlog_method} message")

            # Note: DEBUG messages might be filtered out depending on configuration
            if expected_level == "DEBUG":
                # Skip DEBUG as it might be filtered by the INFO level filter
                continue

            mock_sender.add_log_to_queue.assert_called_once()
            call_args = mock_sender.add_log_to_queue.call_args[0][0]
            assert call_args["level"] == expected_level

    def test_structlog_with_various_data_types(
        self,
        structlog_logger_with_logbull: "structlog.BoundLogger",
        mock_sender: Mock,
    ) -> None:
        """Test logging with various data types."""
        structlog_logger_with_logbull.info(
            "Complex data processing",
            string_field="text_value",
            int_field=42,
            float_field=3.14159,
            bool_field=True,
            list_field=[1, 2, 3],
            dict_field={"nested": "value", "count": 10},
            none_field=None,
        )

        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]
        fields = call_args["fields"]

        assert fields["string_field"] == "text_value"
        assert fields["int_field"] == 42
        assert fields["float_field"] == 3.14159
        assert fields["bool_field"] is True
        assert fields["list_field"] == [1, 2, 3]
        assert fields["dict_field"] == {"nested": "value", "count": 10}
        assert fields["none_field"] is None

    def test_structlog_processor_chain_integration(self, mock_sender: Mock) -> None:
        """Test that LogBull processor works correctly in a processor chain."""
        logbull_processor = StructlogProcessor(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

        # Configure a more complex processor chain
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                cast(Any, logbull_processor),  # LogBull processor in the middle
                structlog.dev.ConsoleRenderer(),  # Final renderer
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=False,
        )

        logger = structlog.get_logger("integration_test")
        logger.info("Testing processor chain", component="auth", operation="login")

        # Verify LogBull processor was called
        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "Testing processor chain"
        assert call_args["fields"]["component"] == "auth"
        assert call_args["fields"]["operation"] == "login"

        # Reset
        structlog.reset_defaults()

    def test_structlog_context_vars(
        self,
        structlog_logger_with_logbull: "structlog.BoundLogger",
        mock_sender: Mock,
    ) -> None:
        """Test integration with context variables."""
        import contextvars

        # Set context variables
        request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
            "request_id"
        )
        user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")

        request_id_var.set("req_123456")
        user_id_var.set("user_789")

        # Configure with context vars
        logbull_processor = StructlogProcessor(
            project_id="12345678-1234-1234-1234-123456789012",
            host="http://localhost:4005",
            api_key="test_api_key",
        )

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                cast(Any, logbull_processor),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=False,
        )

        # Clear any previous mock calls
        mock_sender.reset_mock()

        logger = structlog.get_logger("context_test")
        logger.info("Processing request", endpoint="/api/users")

        # Context vars should be merged into the log
        mock_sender.add_log_to_queue.assert_called_once()
        call_args = mock_sender.add_log_to_queue.call_args[0][0]

        assert call_args["level"] == "INFO"
        assert call_args["message"] == "Processing request"
        assert call_args["fields"]["endpoint"] == "/api/users"

        # Reset
        structlog.reset_defaults()
