from uuid import UUID

from sqlalchemy import delete, func, or_, update
from sqlalchemy.orm import Session

from app.models.business.specification import Specification, SpecificationLimit, SpecificationTest, SpecificationVersion
from .organization_master_repository import OrganizationMasterRepository


class SpecificationRepository(OrganizationMasterRepository):
    def __init__(self):
        super().__init__(Specification)

    def get_by_code(self, db: Session, organization_id: UUID, code: str):
        return db.query(Specification).filter(
            Specification.organization_id == organization_id,
            Specification.specification_code == code,
        ).first()

    def list(self, db: Session, organization_id: UUID):
        return db.query(Specification).filter(
            Specification.organization_id == organization_id
        ).order_by(Specification.specification_code).all()

    def apply_list_filters(self, query, *, search=None, is_active=None, material_id=None, **filters):
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(
                Specification.specification_code.ilike(pattern),
                Specification.specification_name.ilike(pattern),
            ))
        if is_active is not None:
            query = query.filter(Specification.is_active == is_active)
        if material_id is not None:
            query = query.filter(Specification.material_id == material_id)
        return query


class _VersionedRepository:
    model = None

    def update_expected(self, db, record_id, expected_version, values):
        updated_id = db.execute(update(self.model).where(
            self.model.id == record_id,
            self.model.version == expected_version,
        ).values(
            **values, version=self.model.version + 1, updated_at=func.now()
        ).returning(self.model.id)).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(self.model, updated_id)

    def delete_expected(self, db, record_id, expected_version):
        return db.execute(delete(self.model).where(
            self.model.id == record_id,
            self.model.version == expected_version,
        )).rowcount == 1


class SpecificationVersionRepository(_VersionedRepository):
    model = SpecificationVersion

    def get(self, db, organization_id, record_id):
        return db.query(SpecificationVersion).join(Specification).filter(
            Specification.organization_id == organization_id,
            SpecificationVersion.id == record_id,
        ).first()

    def get_by_number(self, db, organization_id, specification_id, number):
        return db.query(SpecificationVersion).join(Specification).filter(
            Specification.organization_id == organization_id,
            SpecificationVersion.specification_id == specification_id,
            SpecificationVersion.version_number == number,
        ).first()


class SpecificationTestRepository(_VersionedRepository):
    model = SpecificationTest

    def get(self, db, organization_id, record_id):
        return db.query(SpecificationTest).join(SpecificationVersion).join(Specification).filter(
            Specification.organization_id == organization_id,
            SpecificationTest.id == record_id,
        ).first()

    def duplicate(self, db, specification_version_id, test_id):
        return db.query(SpecificationTest).filter(
            SpecificationTest.specification_version_id == specification_version_id,
            SpecificationTest.test_id == test_id,
        ).first()


class SpecificationLimitRepository(_VersionedRepository):
    model = SpecificationLimit

    def get(self, db, organization_id, record_id):
        return db.query(SpecificationLimit).join(SpecificationTest).join(
            SpecificationVersion
        ).join(Specification).filter(
            Specification.organization_id == organization_id,
            SpecificationLimit.id == record_id,
        ).first()
