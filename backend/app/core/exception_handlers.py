from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
    SecurityConflictException,
    ValidationException,
)


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(ResourceNotFoundException)
    async def resource_not_found_handler(
        request: Request,
        exc: ResourceNotFoundException,
    ):
        return JSONResponse(
            status_code=404,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(DuplicateResourceException)
    async def duplicate_handler(
        request: Request,
        exc: DuplicateResourceException,
    ):
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(ValidationException)
    async def validation_handler(
        request: Request,
        exc: ValidationException,
    ):
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(SecurityConflictException)
    async def security_conflict_handler(
        request: Request,
        exc: SecurityConflictException,
    ):
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )
