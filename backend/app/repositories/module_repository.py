from uuid import UUID
from sqlalchemy import func, update
from sqlalchemy.orm import Session
from app.models.module import Module, OrganizationModule


class ModuleRepository:
    def list_modules(self, db: Session):
        return db.query(Module).order_by(Module.capability_class, Module.code).all()

    def get_module(self, db: Session, code: str):
        return db.query(Module).filter(Module.code == code).first()

    def assignments(self, db: Session, organization_id: UUID):
        return db.query(OrganizationModule).filter(OrganizationModule.organization_id == organization_id).all()

    def assignment(self, db: Session, organization_id: UUID, module_id: UUID):
        return db.query(OrganizationModule).filter(
            OrganizationModule.organization_id == organization_id,
            OrganizationModule.module_id == module_id,
        ).first()

    def update_expected(self, db: Session, assignment: OrganizationModule, expected_version: int, values: dict):
        changed = db.execute(update(OrganizationModule).where(
            OrganizationModule.id == assignment.id,
            OrganizationModule.organization_id == assignment.organization_id,
            OrganizationModule.version == expected_version,
        ).values(**values, version=OrganizationModule.version + 1, updated_at=func.now()).returning(OrganizationModule.id)).scalar_one_or_none()
        if changed is None:
            return None
        return self.assignment(db, assignment.organization_id, assignment.module_id)
