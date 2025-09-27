"""Input validation utilities for LogBull."""

import re
from typing import Any, Dict, Optional, Set
from urllib.parse import urlparse


VALID_LOG_LEVELS: Set[str] = {
    "DEBUG",
    "INFO",
    "WARNING",
    "WARN",
    "ERROR",
    "CRITICAL",
    "FATAL",
    "PANIC",
}

DEFAULT_MAX_MESSAGE_LENGTH: int = 10_000

UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

API_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{10,}$")


class LogValidator:
    def __init__(
        self,
        max_message_length: Optional[int] = None,
        max_fields_count: int = 100,
        max_field_key_length: int = 100,
    ):
        self.max_message_length = max_message_length or DEFAULT_MAX_MESSAGE_LENGTH
        self.max_fields_count = max_fields_count
        self.max_field_key_length = max_field_key_length

    def validate_log_level(self, level: str) -> str:
        level_upper = level.strip().upper()

        if not level_upper:
            raise ValueError("Log level cannot be empty")

        if level_upper not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level '{level}'. Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
            )

        return self._normalize_log_level(level_upper)

    def validate_project_id(self, project_id: str) -> str:
        project_id = project_id.strip()

        if not project_id:
            raise ValueError("Project ID cannot be empty")

        if not UUID_PATTERN.match(project_id):
            raise ValueError(
                f"Invalid project ID format '{project_id}'. Must be a valid UUID format: "
                "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        return project_id

    def validate_api_key(self, api_key: Optional[str]) -> Optional[str]:
        if api_key is None:
            return None

        api_key = api_key.strip()

        if not api_key:
            return None

        if len(api_key) < 10:
            raise ValueError("API key must be at least 10 characters long")

        if not API_KEY_PATTERN.match(api_key):
            raise ValueError(
                "Invalid API key format. API key must contain only alphanumeric "
                "characters, underscores, hyphens, and dots"
            )

        return api_key

    def validate_log_message(
        self, message: Any, max_length: Optional[int] = None
    ) -> str:
        if message is None:
            raise ValueError("Log message cannot be None")

        message_str: str
        if isinstance(message, str):
            message_str = message
        else:
            message_str = str(message)

        message_str = message_str.strip()

        if not message_str:
            raise ValueError("Log message cannot be empty")

        effective_max_length = max_length or self.max_message_length
        if len(message_str) > effective_max_length:
            raise ValueError(
                f"Log message too long ({len(message_str)} chars). Maximum allowed: {effective_max_length}"
            )

        return message_str

    def validate_log_fields(
        self, fields: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if fields is None:
            return None

        if len(fields) > self.max_fields_count:
            raise ValueError(
                f"Too many fields ({len(fields)}). Maximum allowed: {self.max_fields_count}"
            )

        validated_fields = {}
        for key, value in fields.items():
            key = key.strip()
            if not key:
                raise ValueError("Field key cannot be empty")

            if len(key) > self.max_field_key_length:
                raise ValueError(
                    f"Field key too long ({len(key)} chars). Maximum: {self.max_field_key_length}"
                )

            validated_fields[key] = value

        return validated_fields

    def validate_log_entry(
        self,
        level: str,
        message: Any,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        validated_level = self.validate_log_level(level)
        validated_message = self.validate_log_message(message)
        validated_fields = self.validate_log_fields(fields)

        return {
            "level": validated_level,
            "message": validated_message,
            "fields": validated_fields or {},
        }

    def validate_config(
        self,
        project_id: str,
        host: str,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "project_id": self.validate_project_id(project_id),
            "host": self._validate_host_url(host),
            "api_key": self.validate_api_key(api_key),
            "batch_size": 1000,
        }

    def _is_valid_url(self, url: str) -> bool:
        if not url.strip():
            return False

        try:
            parsed = urlparse(url.strip())
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _validate_host_url(self, host: str) -> str:
        host = host.strip()

        if not host:
            raise ValueError("Host URL cannot be empty")

        if not self._is_valid_url(host):
            raise ValueError(f"Invalid host URL format: '{host}'")

        parsed = urlparse(host)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(
                f"Host URL must use http or https scheme, got: {parsed.scheme}"
            )

        return host

    def _normalize_log_level(self, level: str) -> str:
        if level in ("FATAL", "CRITICAL", "PANIC"):
            return "CRITICAL"

        return level
