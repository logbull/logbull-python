"""Type definitions and protocols for LogBull core functionality."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Protocol, TypedDict


LogLevel = Literal["DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"]
LogFields = Dict[str, Any]
ConfigDict = Dict[str, Any]


class LogEntry(TypedDict, total=False):
    level: str
    message: str
    timestamp: str
    fields: LogFields


class LogBatch(TypedDict):
    logs: List[LogEntry]


class LogBullResponse(TypedDict, total=False):
    accepted: int
    rejected: int
    message: str
    errors: Optional[List[Dict[str, Any]]]


class RejectedLog(TypedDict):
    index: int
    reason: str
    log: LogEntry


class LogBullConfig(TypedDict, total=False):
    project_id: str
    host: str
    api_key: Optional[str]
    batch_size: int
    log_level: Optional[LogLevel]


class LogSender(Protocol):
    """Protocol for log sending implementations."""

    def send_logs(self, logs: List[LogEntry]) -> LogBullResponse:
        """Send logs to LogBull server."""
        ...


class LogProcessor(Protocol):
    """Protocol for log processing implementations."""

    def process_log(
        self,
        level: str,
        message: str,
        fields: Optional[LogFields] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Process a single log entry."""
        ...

    def flush(self) -> None:
        """Flush all pending logs."""
        ...

    def shutdown(self) -> None:
        """Shutdown the processor and cleanup resources."""
        ...


class ContextManager(Protocol):
    """Protocol for context management in loggers."""

    def with_context(self, context: LogFields) -> "ContextManager":
        """Create a new logger instance with additional context."""
        ...
