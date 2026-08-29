from uuid import UUID

from sqlalchemy.orm import Session

from app.models.business.manufacturer import Manufacturer
from app.repositories.business.manufacturer_repository import ManufacturerRepository
from .organization_master_service import OrganizationMasterService


class ManufacturerService(OrganizationMasterService[Manufacturer]):
    def __init__(self, repository: ManufacturerRepository | None = None):
        super().__init__(repository or ManufacturerRepository())

    def create(self, db: Session, organization_id: UUID, **values) -> Manufacturer:
        values = self._normalize_common(values)
        return self.repository.add(db, Manufacturer(organization_id=organization_id, **values))

    def update(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, **values) -> Manufacturer:
        return self._mutate(db, organization_id, record_id, expected_version, self._normalize_common(values))
