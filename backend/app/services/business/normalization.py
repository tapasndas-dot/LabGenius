from app.core.exceptions import ValidationException


def normalize_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValidationException("Code must not be blank.")
    return normalized


def normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationException("Name must not be blank.")
    return normalized


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
