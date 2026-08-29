from fastapi import Depends
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.dependencies.database import get_db
from app.services.module_service import ModuleService

service = ModuleService()

def require_capability(code: str):
    def checker(db: Session = Depends(get_db), actor=Depends(get_current_user)):
        return service.require_enabled(db, actor, code)
    return checker
