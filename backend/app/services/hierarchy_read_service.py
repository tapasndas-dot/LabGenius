from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.services.organization_scope_service import OrganizationScopeService


class HierarchyReadService:
    """Scoped hierarchy reads; mutation behavior remains with the existing services."""

    def __init__(self, model, hierarchy_key: str, permission_code: str):
        self.model = model
        self.hierarchy_key = hierarchy_key
        self.permission_code = permission_code
        self.scope_service = OrganizationScopeService()

    def query(self, db: Session, actor):
        return self.scope_service.hierarchy_queries(
            db, actor, self.permission_code
        )[self.hierarchy_key]

    def list(self, db: Session, actor, **filters):
        query = self.query(db, actor)
        for field, value in filters.items():
            query = query.filter(getattr(self.model, field) == value)
        return query.all()

    def get(self, db: Session, actor, record_id):
        record = self.query(db, actor).filter(self.model.id == record_id).first()
        if record is None:
            raise ResourceNotFoundException(f"{self.model.__name__} not found.")
        return record
