"""Standard Python logging handler for LogBull."""

import logging
from typing import Any, Dict, Optional

from ..core.logger import _generate_unique_nanosecond_timestamp
from ..core.sender import LogSender
from ..core.types import LogBullConfig, LogEntry
from ..utils import LogFormatter, LogValidator


class LogBullHandler(logging.Handler):
    """Python logging handler that sends logs to LogBull server."""

    def __init__(
        self,
        *,
        project_id: str,
        host: str,
        api_key: Optional[str] = None,
        level: int = logging.NOTSET,
    ):
        super().__init__(level)

        self.validator = LogValidator()
        self.formatter_util = LogFormatter()

        # Validate configuration
        validated_config = self.validator.validate_config(
            project_id=project_id,
            host=host,
            api_key=api_key,
        )

        self.config: LogBullConfig = {
            "project_id": validated_config["project_id"],
            "host": validated_config["host"],
            "api_key": validated_config["api_key"],
            "batch_size": validated_config["batch_size"],
        }

        self.sender = LogSender(self.config)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to LogBull."""
        try:
            # Extract message
            message = self.format(record)

            # Extract fields from record extras
            fields = self._extract_fields(record)

            # Convert log level
            level = self._convert_log_level(record.levelname)

            # Validate log entry
            validated = self.validator.validate_log_entry(level, message, fields)

            # Generate unique timestamp with nanosecond precision
            timestamp_ns = _generate_unique_nanosecond_timestamp()

            # Format log entry
            formatted_entry = self.formatter_util.format_log_entry(
                level=validated["level"],
                message=validated["message"],
                fields=validated["fields"],
                timestamp_ns=timestamp_ns,
            )

            log_entry: LogEntry = {
                "level": formatted_entry["level"],
                "message": formatted_entry["message"],
                "timestamp": formatted_entry["timestamp"],
                "fields": formatted_entry["fields"],
            }

            self.sender.add_log_to_queue(log_entry)

        except Exception:
            # Use handleError to report issues with the handler itself
            self.handleError(record)

    def flush(self) -> None:
        """Flush any pending log records."""
        try:
            self.sender.flush()
        except Exception:
            pass

    def close(self) -> None:
        """Close the handler and cleanup resources."""
        try:
            self.sender.shutdown()
        except Exception:
            pass
        finally:
            super().close()

    def _extract_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract custom fields from log record."""
        fields = {}

        # Standard fields that might be useful
        standard_fields = {
            "logger_name": record.name,
            "filename": record.filename,
            "line_number": record.lineno,
            "function_name": record.funcName,
            "process_id": record.process,
            "thread_id": record.thread,
            "thread_name": record.threadName,
        }

        # Add standard fields if they have meaningful values
        for key, value in standard_fields.items():
            if value and value != "":
                fields[key] = value

        # Add exception info if present
        if record.exc_info:
            import traceback

            fields["exception"] = "".join(traceback.format_exception(*record.exc_info))

        # Add extra fields from the record
        # These come from logger.info("msg", extra={"key": "value"})
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
            }:
                fields[key] = value

        return self.formatter_util.ensure_fields(fields)

    def _convert_log_level(self, level_name: str) -> str:
        """Convert Python logging level to LogBull level."""
        level_mapping = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "WARN": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL",
            "FATAL": "CRITICAL",
        }

        return level_mapping.get(level_name.upper(), "INFO")
