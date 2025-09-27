"""Loguru integration handler for LogBull."""

from datetime import datetime
from typing import Any, Dict, Optional

from ..core.sender import LogSender
from ..core.types import LogBullConfig, LogEntry
from ..utils import LogFormatter, LogValidator


class LoguruSink:
    """Loguru sink that sends logs to LogBull server."""

    def __init__(
        self,
        *,
        project_id: str,
        host: str,
        api_key: Optional[str] = None,
    ):
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

    def __call__(self, message: Any) -> None:
        """Process a Loguru log message."""
        try:
            # Extract information directly from the loguru Message object
            record = message.record

            level = record["level"].name
            text = record["message"]  # The raw message text
            time = record["time"]

            # Parse timestamp
            timestamp = None
            if time:
                if hasattr(time, "timestamp"):
                    timestamp = datetime.fromtimestamp(time.timestamp())
                else:
                    timestamp = datetime.now()

            # Extract fields from the record
            fields = self._extract_fields_from_record(record)

            # Validate log entry
            validated = self.validator.validate_log_entry(level, text, fields)

            # Format log entry
            formatted_entry = self.formatter_util.format_log_entry(
                level=validated["level"],
                message=validated["message"],
                fields=validated["fields"],
                timestamp=timestamp,
            )

            log_entry: LogEntry = {
                "level": formatted_entry["level"],
                "message": formatted_entry["message"],
                "timestamp": formatted_entry["timestamp"],
                "fields": formatted_entry["fields"],
            }

            self.sender.add_log_to_queue(log_entry)

        except Exception as e:
            # Print error instead of raising to avoid breaking Loguru
            print(f"LogBull: Error processing Loguru log: {e}")

    def flush(self) -> None:
        """Flush any pending log records."""
        try:
            self.sender.flush()
        except Exception:
            pass

    def close(self) -> None:
        """Close the sink and cleanup resources."""
        try:
            self.sender.shutdown()
        except Exception:
            pass

    def _extract_fields_from_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract custom fields from Loguru record dictionary."""
        fields = {}

        # Add basic record information
        if "name" in record:
            fields["logger_name"] = record["name"]

        if "file" in record:
            file_info = record["file"]
            if hasattr(file_info, "name"):
                fields["filename"] = file_info.name
            if hasattr(file_info, "path"):
                fields["filepath"] = str(file_info.path)

        if "line" in record:
            fields["line_number"] = record["line"]

        if "function" in record:
            fields["function_name"] = record["function"]

        if "process" in record:
            process_info = record["process"]
            if hasattr(process_info, "id"):
                fields["process_id"] = process_info.id
            if hasattr(process_info, "name"):
                fields["process_name"] = process_info.name

        if "thread" in record:
            thread_info = record["thread"]
            if hasattr(thread_info, "id"):
                fields["thread_id"] = thread_info.id
            if hasattr(thread_info, "name"):
                fields["thread_name"] = thread_info.name

        # Add exception info if present
        if "exception" in record and record["exception"]:
            exception_info = record["exception"]
            if hasattr(exception_info, "type") and hasattr(exception_info, "value"):
                fields["exception_type"] = exception_info.type.__name__
                fields["exception_message"] = str(exception_info.value)
            if hasattr(exception_info, "traceback"):
                fields["exception_traceback"] = str(exception_info.traceback)

        # Add extra fields from bound context
        # Loguru stores bound data in record["extra"]
        if "extra" in record:
            extra_data = record["extra"]
            if isinstance(extra_data, dict):
                for key, value in extra_data.items():
                    # Skip internal Loguru fields
                    if not key.startswith("_"):
                        fields[key] = value

        return self.formatter_util.ensure_fields(fields)
