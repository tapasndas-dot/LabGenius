from uuid import uuid4

from fastapi import FastAPI, Request

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers

from app.routers import business_unit
from app.routers import database
from app.routers import department
from app.routers import designation
from app.routers import role
from app.routers import role_permission
from app.routers import division
from app.routers import health
from app.routers import organization
from app.routers import permission
from app.routers import root
from app.routers import user_role
from app.routers import security_history
from app.routers import audit
from app.core.request_context import RequestContext, reset_request_context, set_request_context
from app.routers.user import security as user_security_router
from app.routers.auth import router as auth_router
from app.routers.user import router as user_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


register_exception_handlers(app)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid4())
    token = set_request_context(RequestContext(
        request_id=request_id,
        source_ip=request.client.host if request.client else None,
    ))
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        reset_request_context(token)


app.include_router(
    organization.router,
    prefix="/organizations",
    tags=["Organizations"],
)


app.include_router(
    business_unit.router,
    prefix="/business-units",
    tags=["Business Units"],
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
    role.router,
    prefix="/roles",
    tags=["Roles"],
)

app.include_router(
    role_permission.router,
    tags=["Role Permissions"],
)

app.include_router(
    permission.router,
    prefix="/permissions",
    tags=["Permissions"],
)


app.include_router(
    root.router,
    tags=["Root"],
)


app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)


app.include_router(
    database.router,
    prefix="/database",
    tags=["Database"],
)


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)


app.include_router(
    user_router,
    prefix="/users",
    tags=["Users"],
)

app.include_router(
    user_security_router.router,
    prefix="/users",
    tags=["User Security"],
)

app.include_router(
    user_role.router,
    tags=["User Roles"]
)

app.include_router(
    security_history.router,
    prefix="/security",
    tags=["Security History"],
)

app.include_router(audit.router, prefix="/audit", tags=["Audit"])
