from uuid import UUID

from sqlalchemy.orm import Session

from app.models.business.instrument_type import InstrumentType
from app.repositories.business.instrument_type_repository import InstrumentTypeRepository
from .organization_master_service import OrganizationMasterService


class InstrumentTypeService(OrganizationMasterService[InstrumentType]):
    def __init__(self, repository: InstrumentTypeRepository | None = None):
        super().__init__(repository or InstrumentTypeRepository())

    def create(self, db: Session, organization_id: UUID, **values) -> InstrumentType:
        values = self._normalize_common(values)
        return self.repository.add(db, InstrumentType(organization_id=organization_id, **values))

    def update(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, **values) -> InstrumentType:
        return self._mutate(db, organization_id, record_id, expected_version, self._normalize_common(values))
