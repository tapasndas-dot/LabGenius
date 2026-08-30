from uuid import UUID

from sqlalchemy import delete, func, or_, update
from sqlalchemy.orm import Session

from app.models.business.qc_method import Method, MethodParameter, MethodVersion, Test
from .organization_master_repository import OrganizationMasterRepository


class _NamedCodeRepository(OrganizationMasterRepository):
    code_field: str
    name_field: str

    def get_by_code(self, db: Session, organization_id: UUID, code: str):
        return db.query(self.model).filter(
            self.model.organization_id == organization_id,
            getattr(self.model, self.code_field) == code,
        ).first()

    def list(self, db: Session, organization_id: UUID):
        return db.query(self.model).filter(
            self.model.organization_id == organization_id
        ).order_by(getattr(self.model, self.code_field)).all()

    def apply_list_filters(
        self, query, *, search: str | None = None,
        is_active: bool | None = None, **filters,
    ):
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(
                getattr(self.model, self.code_field).ilike(pattern),
                getattr(self.model, self.name_field).ilike(pattern),
            ))
        if is_active is not None:
            query = query.filter(self.model.is_active == is_active)
        for field, value in filters.items():
            if value is not None:
                query = query.filter(getattr(self.model, field) == value)
        return query


class TestRepository(_NamedCodeRepository):
    code_field = "test_code"
    name_field = "test_name"

    def __init__(self):
        super().__init__(Test)


class MethodRepository(_NamedCodeRepository):
    code_field = "method_code"
    name_field = "method_name"

    def __init__(self):
        super().__init__(Method)


class MethodVersionRepository:
    def get(self, db: Session, organization_id: UUID, record_id: UUID):
        return db.query(MethodVersion).join(Method).filter(Method.organization_id == organization_id, MethodVersion.id == record_id).first()

    def get_by_number(self, db: Session, organization_id: UUID, method_id: UUID, version_number: int):
        return db.query(MethodVersion).join(Method).filter(Method.organization_id == organization_id, MethodVersion.method_id == method_id, MethodVersion.version_number == version_number).first()

    def update_expected(self, db: Session, record_id: UUID, expected_version: int, values: dict):
        updated_id = db.execute(update(MethodVersion).where(MethodVersion.id == record_id, MethodVersion.version == expected_version).values(**values, version=MethodVersion.version + 1, updated_at=func.now()).returning(MethodVersion.id)).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(MethodVersion, updated_id)

    def delete_expected(self, db: Session, record_id: UUID, expected_version: int):
        return db.execute(delete(MethodVersion).where(MethodVersion.id == record_id, MethodVersion.version == expected_version)).rowcount == 1


class MethodParameterRepository:
    def get(self, db: Session, organization_id: UUID, record_id: UUID):
        return db.query(MethodParameter).join(MethodVersion).join(Method).filter(Method.organization_id == organization_id, MethodParameter.id == record_id).first()

    def get_by_code(self, db: Session, method_version_id: UUID, parameter_code: str):
        return db.query(MethodParameter).filter(MethodParameter.method_version_id == method_version_id, MethodParameter.parameter_code == parameter_code).first()

    def update_expected(self, db: Session, record_id: UUID, expected_version: int, values: dict):
        updated_id = db.execute(update(MethodParameter).where(MethodParameter.id == record_id, MethodParameter.version == expected_version).values(**values, version=MethodParameter.version + 1, updated_at=func.now()).returning(MethodParameter.id)).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(MethodParameter, updated_id)

    def delete_expected(self, db: Session, record_id: UUID, expected_version: int):
        return db.execute(delete(MethodParameter).where(MethodParameter.id == record_id, MethodParameter.version == expected_version)).rowcount == 1
