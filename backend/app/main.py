from fastapi import FastAPI
from app.core.exception_handlers import register_exception_handlers

from app.routers import organization
from app.routers import business_unit
from app.routers import division
from app.routers import department
from app.routers import designation
from app.routers.user import router as user_router
from app.routers.auth import router as auth_router

from app.core.config import settings
from app.routers import database
from app.routers import health
from app.routers import root


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

register_exception_handlers(app)


app.include_router(
    organization.router,
    prefix="/organizations",
    tags=["Organizations"],
)

app.include_router(
    business_unit.router,
    prefix="/business-units",
    tags=["Business Units"]
)

app.include_router(
    division.router,
    prefix="/divisions",
    tags=["Divisions"],
)

app.include_router(
    department.router,
    prefix="/departments",
    tags=["Departments"],
)

app.include_router(
    designation.router,
    prefix="/designations",
    tags=["Designations"],
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

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)
app.include_router(
    user_router,
    prefix="/users",
    tags=["Users"]
)
