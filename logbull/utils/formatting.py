"""Log formatting utilities for LogBull."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class LogFormatter:
    def __init__(self, max_message_length: Optional[int] = None):
        self.max_message_length = max_message_length

    def format_timestamp(self, timestamp: Optional[datetime] = None) -> str:
        """Format timestamp to UTC ISO format with microseconds."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

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
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return {
            "level": level.upper(),
            "message": self.format_message(message),
            "timestamp": self.format_timestamp(timestamp),
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
