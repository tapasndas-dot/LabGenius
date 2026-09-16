import pytest
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import app


REQUIRED_SETTINGS = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_KEY": "test-key",
    "DATABASE_URL": "postgresql://user:password@localhost/labgenius_test",
    "JWT_SECRET_KEY": "test-secret-not-used-for-authentication",
}


def make_settings(cors_origins: str) -> Settings:
    return Settings(
        _env_file=None,
        CORS_ALLOWED_ORIGINS=cors_origins,
        **REQUIRED_SETTINGS,
    )


def test_application_version_default_matches_release_baseline() -> None:
    assert Settings.model_fields["APP_VERSION"].default == "0.28.0"


def test_cors_origins_parse_multiple_explicit_values() -> None:
    configured = make_settings(
        " https://demo.example.com/, https://admin.example.com "
    )

    assert configured.CORS_ALLOWED_ORIGINS == [
        "https://demo.example.com",
        "https://admin.example.com",
    ]


def test_cors_origins_ignore_empty_and_whitespace_entries() -> None:
    configured = make_settings("https://demo.example.com, ,  ,")

    assert configured.CORS_ALLOWED_ORIGINS == ["https://demo.example.com"]


def test_cors_origins_reject_wildcard() -> None:
    with pytest.raises(ValidationError, match="explicit origins"):
        make_settings("https://demo.example.com,*")


def test_application_cors_middleware_uses_configured_origins() -> None:
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origins"] == settings.CORS_ALLOWED_ORIGINS
    assert "*" not in cors_middleware.kwargs["allow_origins"]
    assert cors_middleware.kwargs["allow_credentials"] is True
    assert cors_middleware.kwargs["allow_methods"] == ["*"]
    assert cors_middleware.kwargs["allow_headers"] == ["*"]
