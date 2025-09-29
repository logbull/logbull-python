"""LogBull sender registry for cleanup on app shutdown."""

import atexit
import weakref
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .sender import LogSender

# Global registry of active senders for cleanup
_active_senders: "weakref.WeakSet[LogSender]" = weakref.WeakSet()


def _cleanup_all_senders() -> None:
    """Flush and shutdown all active senders on application exit."""
    for sender in list(_active_senders):
        try:
            sender.shutdown()
        except Exception:
            pass


def register_sender(sender: "LogSender") -> None:
    """Register a sender for automatic cleanup on app shutdown."""
    _active_senders.add(sender)


# Register the cleanup function to run on exit
atexit.register(_cleanup_all_senders)


__all__ = ["register_sender"]
