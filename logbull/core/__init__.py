"""LogBull core module."""

from .logger import LogBullLogger
from .registry import register_sender
from .sender import LogSender
from .types import (
    ContextManager,
    LogBatch,
    LogBullConfig,
    LogBullResponse,
    LogEntry,
    LogProcessor,
    RejectedLog,
)
from .types import (
    LogSender as LogSenderProtocol,
)


__all__ = [
    "LogBullLogger",
    "LogSender",
    "LogEntry",
    "LogBatch",
    "LogBullConfig",
    "LogBullResponse",
    "RejectedLog",
    "LogSenderProtocol",
    "LogProcessor",
    "ContextManager",
    "register_sender",
]
