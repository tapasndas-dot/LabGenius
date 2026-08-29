from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user, require_permission
from app.dependencies.database import get_db
from app.schemas.module import ModuleResponse, ModuleStateResponse, ModuleVersionRequest
from app.services.module_service import ModuleService

router = APIRouter(); service = ModuleService()

@router.get("", response_model=list[ModuleResponse])
def list_modules(db: Session = Depends(get_db), actor=Depends(require_permission("module.view"))):
    return service.list_modules(db)

@router.get("/organization", response_model=list[ModuleStateResponse])
def organization_modules(db: Session = Depends(get_db), actor=Depends(require_permission("module.view"))):
    return service.states(db, actor.organization_id)

@router.get("/enabled", response_model=list[str])
def enabled_modules(db: Session = Depends(get_db), actor=Depends(get_current_user)):
    return [item["module"].code for item in service.states(db, actor.organization_id) if item["is_enabled"] and item["module"].is_active]

@router.put("/{code}/enable", response_model=ModuleStateResponse)
def enable_module(code: str, payload: ModuleVersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("module.manage"))):
    service.enable(db, actor, code, payload.version)
    return next(item for item in service.states(db, actor.organization_id) if item["module"].code == code.upper())

@router.put("/{code}/disable", response_model=ModuleStateResponse)
def disable_module(code: str, payload: ModuleVersionRequest, db: Session = Depends(get_db), actor=Depends(require_permission("module.manage"))):
    if payload.version is None:
        from app.core.exceptions import VersionConflictException
        raise VersionConflictException("Record has been modified by another user. Refresh and try again.")
    service.disable(db, actor, code, payload.version)
    return next(item for item in service.states(db, actor.organization_id) if item["module"].code == code.upper())
