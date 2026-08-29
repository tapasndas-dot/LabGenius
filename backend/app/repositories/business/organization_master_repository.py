from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, or_, update
from sqlalchemy.orm import Session

from app.database.base_entities import MasterEntity

MasterType = TypeVar("MasterType", bound=MasterEntity)


class OrganizationMasterRepository(Generic[MasterType]):
    """Organization-scoped persistence and atomic expected-version mutations."""

    def __init__(self, model: type[MasterType]):
        self.model = model

    def get(self, db: Session, organization_id: UUID, record_id: UUID) -> MasterType | None:
        return db.query(self.model).filter(
            self.model.organization_id == organization_id,
            self.model.id == record_id,
        ).first()

    def get_by_code(self, db: Session, organization_id: UUID, code: str) -> MasterType | None:
        return db.query(self.model).filter(
            self.model.organization_id == organization_id,
            self.model.code == code,
        ).first()

    def list(self, db: Session, organization_id: UUID) -> list[MasterType]:
        return db.query(self.model).filter(
            self.model.organization_id == organization_id
        ).order_by(self.model.code).all()

    def query(self, db: Session):
        return db.query(self.model)

    def apply_list_filters(
        self, query, *, search: str | None = None, is_active: bool | None = None,
        **filters,
    ):
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(
                self.model.code.ilike(pattern), self.model.name.ilike(pattern)
            ))
        if is_active is not None:
            query = query.filter(self.model.is_active == is_active)
        for field, value in filters.items():
            if value is not None:
                query = query.filter(getattr(self.model, field) == value)
        return query

    def add(self, db: Session, record: MasterType) -> MasterType:
        db.add(record)
        db.flush()
        return record

    def update_expected(
        self,
        db: Session,
        organization_id: UUID,
        record_id: UUID,
        expected_version: int,
        values: dict,
    ) -> MasterType | None:
        statement = (
            update(self.model)
            .where(
                self.model.organization_id == organization_id,
                self.model.id == record_id,
                self.model.version == expected_version,
            )
            .values(**values, version=self.model.version + 1, updated_at=func.now())
            .returning(self.model.id)
        )
        updated_id = db.execute(statement).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return self.get(db, organization_id, updated_id)

    def delete_expected(
        self,
        db: Session,
        organization_id: UUID,
        record_id: UUID,
        expected_version: int,
    ) -> bool:
        result = db.execute(
            delete(self.model).where(
                self.model.organization_id == organization_id,
                self.model.id == record_id,
                self.model.version == expected_version,
            )
        )
        return result.rowcount == 1
