from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import CapabilityConflictException, ResourceNotFoundException, VersionConflictException
from app.models.module import Module, OrganizationModule
from app.repositories.module_repository import ModuleRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.business.organization_master_service import VERSION_CONFLICT_MESSAGE

MODULE_CATALOG = (
    {"code": "PLATFORM", "name": "Platform", "description": "Authentication, security, organization hierarchy, audit, and common services.", "capability_class": "PLATFORM", "is_core": True},
    {"code": "CORE_LAB", "name": "Core Lab", "description": "Shared laboratory masters and common testing foundation.", "capability_class": "CORE_LAB", "is_core": True},
    {"code": "INSTRUMENTS", "name": "Instrument / Asset Registry", "description": "Shared instrument and asset registry capability.", "capability_class": "OPTIONAL_SHARED", "is_core": False},
    {"code": "STABILITY", "name": "Stability", "description": "Stability protocol, study, chamber, and pull capability.", "capability_class": "OPTIONAL_DOMAIN", "is_core": False},
    {"code": "CALIBRATION", "name": "Calibration", "description": "Instrument calibration capability.", "capability_class": "OPTIONAL_DOMAIN", "is_core": False},
    {"code": "MAINTENANCE", "name": "Maintenance", "description": "Instrument maintenance capability.", "capability_class": "OPTIONAL_DOMAIN", "is_core": False},
    {"code": "QUALIFICATION", "name": "Qualification", "description": "Instrument qualification capability.", "capability_class": "OPTIONAL_DOMAIN", "is_core": False},
    {"code": "INVENTORY", "name": "Inventory", "description": "Independent laboratory inventory capability.", "capability_class": "OPTIONAL_DOMAIN", "is_core": False},
    {"code": "CONTRACT_TESTING", "name": "Contract Testing", "description": "Contract laboratory submission and reporting extension.", "capability_class": "OPTIONAL_DOMAIN", "is_core": False},
)
MODULE_DEPENDENCIES = {
    "STABILITY": ("CORE_LAB", "INSTRUMENTS"), "CALIBRATION": ("INSTRUMENTS",),
    "MAINTENANCE": ("INSTRUMENTS",), "QUALIFICATION": ("INSTRUMENTS",),
    "CONTRACT_TESTING": ("CORE_LAB",),
}


class ModuleService:
    def __init__(self):
        self.repository = ModuleRepository(); self.audit_service = AuditService()

    def list_modules(self, db: Session):
        return self.repository.list_modules(db)

    def is_enabled(self, db: Session, organization_id: UUID, code: str) -> bool:
        module = self.repository.get_module(db, code)
        if module is None or not module.is_active:
            return False
        if module.is_core:
            return True
        assignment = self.repository.assignment(db, organization_id, module.id)
        return bool(assignment and assignment.is_active and assignment.is_enabled)

    def states(self, db: Session, organization_id: UUID):
        assignments = {item.module_id: item for item in self.repository.assignments(db, organization_id)}
        return [{"module": module, "is_enabled": True if module.is_core else bool(assignments.get(module.id) and assignments[module.id].is_enabled),
                 "version": assignments[module.id].version if module.id in assignments else 0,
                 "dependencies": list(MODULE_DEPENDENCIES.get(module.code, ())) }
                for module in self.repository.list_modules(db)]

    def _module(self, db: Session, code: str) -> Module:
        module = self.repository.get_module(db, code.upper())
        if module is None or not module.is_active:
            raise ResourceNotFoundException("Capability not found.")
        return module

    def enable(self, db: Session, actor, code: str, expected_version: int | None):
        module = self._module(db, code)
        if module.is_core:
            raise CapabilityConflictException("Core capabilities are always enabled.")
        missing = [dependency for dependency in MODULE_DEPENDENCIES.get(module.code, ()) if not self.is_enabled(db, actor.organization_id, dependency)]
        if missing:
            raise CapabilityConflictException(f"Enable required capabilities first: {', '.join(missing)}.")
        assignment = self.repository.assignment(db, actor.organization_id, module.id)
        now = datetime.now(timezone.utc)
        try:
            if assignment is None:
                if expected_version not in (None, 0):
                    raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
                assignment = OrganizationModule(organization_id=actor.organization_id, module_id=module.id, is_enabled=True, enabled_at=now)
                db.add(assignment); db.flush()
            else:
                if expected_version is None:
                    raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
                assignment = self.repository.update_expected(db, assignment, expected_version, {"is_enabled": True, "enabled_at": now, "disabled_at": None})
                if assignment is None:
                    raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit_service.record_update(db, entity=assignment, actor=actor, owner=assignment, before={"is_enabled": False}, action=AuditAction.ACTIVATE)
            db.commit(); db.refresh(assignment); return assignment
        except Exception:
            db.rollback(); raise

    def disable(self, db: Session, actor, code: str, expected_version: int):
        module = self._module(db, code)
        if module.is_core:
            raise CapabilityConflictException("Core capabilities cannot be disabled.")
        blockers = [candidate.code for candidate in self.repository.list_modules(db)
                    if module.code in MODULE_DEPENDENCIES.get(candidate.code, ()) and self.is_enabled(db, actor.organization_id, candidate.code)]
        if blockers:
            raise CapabilityConflictException(f"Disable dependent capabilities first: {', '.join(blockers)}.")
        assignment = self.repository.assignment(db, actor.organization_id, module.id)
        if assignment is None or not assignment.is_enabled:
            raise CapabilityConflictException("Capability is not enabled.")
        before = self.audit_service.snapshot(assignment)
        try:
            updated = self.repository.update_expected(db, assignment, expected_version, {"is_enabled": False, "disabled_at": datetime.now(timezone.utc)})
            if updated is None:
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit_service.record_update(db, entity=updated, actor=actor, owner=updated, before=before, action=AuditAction.DEACTIVATE)
            db.commit(); db.refresh(updated); return updated
        except Exception:
            db.rollback(); raise

    def require_enabled(self, db: Session, actor, code: str):
        if not self.is_enabled(db, actor.organization_id, code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Required capability is not enabled for this organization.")
        return actor
