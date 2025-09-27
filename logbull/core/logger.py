import atexit
from datetime import datetime
from typing import Any, Dict, Optional

from ..utils import LogFormatter, LogValidator
from .sender import LogSender
from .types import LogBullConfig, LogEntry


class LogBullLogger:
    LOG_LEVEL_PRIORITY = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "WARN": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "FATAL": 50,
        "PANIC": 50,
    }

    def __init__(
        self,
        *,
        project_id: str,
        host: str,
        api_key: Optional[str] = None,
        log_level: str = "INFO",
        context: Optional[Dict[str, Any]] = None,
    ):
        self.validator = LogValidator()
        self.formatter = LogFormatter()

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

        self.log_level = self.validator.validate_log_level(str(log_level))
        self.min_level_priority = self.LOG_LEVEL_PRIORITY[self.log_level]

        self.context = self.formatter.ensure_fields(context) if context else {}

        self.sender = LogSender(self.config)

        atexit.register(self._cleanup)

    def log(
        self, level: str, message: str, fields: Optional[Dict[str, Any]] = None
    ) -> None:
        self._log(level, message, fields)

    def debug(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self._log("DEBUG", message, fields)

    def info(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self._log("INFO", message, fields)

    def warning(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self._log("WARNING", message, fields)

    def warn(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self.warning(message, fields)

    def error(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self._log("ERROR", message, fields)

    def critical(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self._log("CRITICAL", message, fields)

    def fatal(self, message: str, fields: Optional[Dict[str, Any]] = None) -> None:
        self.critical(message, fields)

    def with_context(self, context: Dict[str, Any]) -> "LogBullLogger":
        merged_context = self.formatter.merge_context_fields(self.context, context)

        new_logger = LogBullLogger(
            project_id=self.config["project_id"],
            host=self.config["host"],
            api_key=self.config.get("api_key"),
            log_level=self.log_level,
            context=merged_context,
        )

        return new_logger

    def flush(self) -> None:
        self.sender.flush()

    def shutdown(self) -> None:
        self.sender.shutdown()

    def _log(
        self, level: str, message: str, fields: Optional[Dict[str, Any]] = None
    ) -> None:
        try:
            level_priority = self.LOG_LEVEL_PRIORITY.get(level.upper(), 0)
            if level_priority < self.min_level_priority:
                return

            validated = self.validator.validate_log_entry(level, message, fields)

            merged_fields = self.formatter.merge_context_fields(
                self.context, validated["fields"]
            )

            formatted_entry = self.formatter.format_log_entry(
                level=validated["level"],
                message=validated["message"],
                fields=merged_fields,
                timestamp=datetime.now(),
            )
            log_entry: LogEntry = {
                "level": formatted_entry["level"],
                "message": formatted_entry["message"],
                "timestamp": formatted_entry["timestamp"],
                "fields": formatted_entry["fields"],
            }

            self._print_to_console(log_entry)

            self.sender.add_log_to_queue(log_entry)

        except Exception as e:
            print(f"LogBull logging error: {e}")

    def _print_to_console(self, log_entry: LogEntry) -> None:
        level = log_entry["level"]
        message = log_entry["message"]
        timestamp = log_entry["timestamp"]
        fields = log_entry["fields"]

        console_parts = [f"[{timestamp}]", f"[{level}]", message]

        if fields:
            fields_str = ", ".join(f"{k}={v}" for k, v in fields.items())
            console_parts.append(f"({fields_str})")

        console_message = " ".join(console_parts)
        print(console_message)

    def _cleanup(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass
