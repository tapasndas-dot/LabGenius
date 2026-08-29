from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID


SENSITIVE_KEY_PARTS = (
    "password", "token", "jwt", "authorization", "api_key", "apikey",
    "secret", "credential", "database_password",
)


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_").replace(" ", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize(value: Any) -> Any:
    """Recursively remove secrets and convert common values to JSON-safe data."""
    if isinstance(value, dict):
        return {
            str(key): sanitize(item)
            for key, item in value.items()
            if not is_sensitive_key(key)
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return sanitize(value.value)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "model_dump"):
        return sanitize(value.model_dump())
    return str(value)
