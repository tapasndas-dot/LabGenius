import re

from app.core.config import settings
from app.core.exceptions import ValidationException


class PasswordPolicy:
    """Centralized, configurable password-policy validation."""

    @staticmethod
    def validate(password: str) -> None:
        errors: list[str] = []

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long."
            )
        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")
        if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit.")
        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(
            r"[^A-Za-z0-9]", password
        ):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise ValidationException(" ".join(errors))
