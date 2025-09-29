"""Structlog integration processor for LogBull."""

from typing import Any, Dict, Optional

from ..core.logger import _generate_unique_nanosecond_timestamp
from ..core.sender import LogSender
from ..core.types import LogBullConfig, LogEntry
from ..utils import LogFormatter, LogValidator


class StructlogProcessor:
    """Structlog processor that sends logs to LogBull server."""

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

    def __call__(
        self, logger: Any, name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a Structlog event and send to LogBull."""
        try:
            # Extract information from event_dict
            level = event_dict.get("level", "info").upper()
            message = str(event_dict.get("event", ""))

            # Extract fields (everything except reserved keys)
            reserved_keys = {"level", "event", "timestamp"}
            fields = {
                key: value
                for key, value in event_dict.items()
                if key not in reserved_keys
            }

            # Add logger name if available
            if name:
                fields["logger_name"] = name

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

        except Exception as e:
            # Print error instead of raising to avoid breaking Structlog pipeline
            print(f"LogBull: Error processing Structlog event: {e}")

        # Return the original event_dict to continue the processor chain
        return event_dict

    def flush(self) -> None:
        """Flush any pending log records."""
        try:
            self.sender.flush()
        except Exception:
            pass

    def close(self) -> None:
        """Close the processor and cleanup resources."""
        try:
            self.sender.shutdown()
        except Exception:
            pass
