"""LogBull Python client library for sending logs to LogBull server."""

from .core import LogBullLogger
from .handlers import LogBullHandler, LoguruSink, StructlogProcessor


__version__ = "0.1.0"

# Main exports
__all__ = [
    "LogBullLogger",
    "LogBullHandler",
    "LoguruSink",
    "StructlogProcessor",
]
