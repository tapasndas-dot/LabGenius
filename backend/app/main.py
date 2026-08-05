from fastapi import FastAPI

from app.core.config import settings
from app.routers import database
from app.routers import health
from app.routers import root

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

app.include_router(
    root.router,
    tags=["Root"]
)

app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

app.include_router(
    database.router,
    prefix="/database",
    tags=["Database"]
)