"""Log formatting utilities for LogBull."""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class LogFormatter:
    def __init__(self, max_message_length: Optional[int] = None):
        self.max_message_length = max_message_length

    def format_timestamp(self, timestamp_ns: Optional[int] = None) -> str:
        """Format timestamp to RFC3339Nano format with nanosecond precision."""
        if timestamp_ns is None:
            timestamp_ns = time.time_ns()

        # Split into seconds and nanoseconds
        seconds = timestamp_ns // 1_000_000_000
        nanoseconds = timestamp_ns % 1_000_000_000

        # Create datetime from seconds and format to RFC3339Nano
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        base_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")

        return f"{base_timestamp}.{nanoseconds:09d}Z"

    def format_message(self, message: str, max_length: Optional[int] = None) -> str:
        message = message.strip()
        effective_max_length = max_length or self.max_message_length

        if effective_max_length and len(message) > effective_max_length:
            message = message[: effective_max_length - 3] + "..."

        return message

    def ensure_fields(self, fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if fields is None:
            return {}

        formatted_fields = {}
        for key, value in fields.items():
            if isinstance(key, str) and key.strip():
                formatted_key = key.strip()
                try:
                    json.dumps(value)
                    formatted_fields[formatted_key] = value
                except (TypeError, ValueError):
                    formatted_fields[formatted_key] = str(value)

        return formatted_fields

    def format_log_entry(
        self,
        level: str,
        message: str,
        fields: Optional[Dict[str, Any]] = None,
        timestamp_ns: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "level": level.upper(),
            "message": self.format_message(message),
            "timestamp": self.format_timestamp(timestamp_ns),
            "fields": self.ensure_fields(fields),
        }

    def format_batch(
        self, log_entries: list[Dict[str, Any]]
    ) -> Dict[str, list[Dict[str, Any]]]:
        return {"logs": log_entries}

    def merge_context_fields(
        self,
        base_fields: Optional[Dict[str, Any]],
        context_fields: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        result = self.ensure_fields(base_fields)
        context = self.ensure_fields(context_fields)
        result.update(context)
        return result

    def _sanitize_field_name(self, name: str) -> str:
        name = name.strip()

        sanitized = ""
        for char in name:
            if char.isalnum() or char in ["_", "-", "."]:
                sanitized += char
            else:
                sanitized += "_"

        if sanitized and sanitized[0].isdigit():
            sanitized = "_" + sanitized

        if not sanitized:
            sanitized = "field"

        return sanitized
