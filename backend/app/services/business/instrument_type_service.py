from uuid import UUID

from sqlalchemy.orm import Session

from app.models.business.instrument_type import InstrumentType
from app.repositories.business.instrument_type_repository import InstrumentTypeRepository
from .organization_master_service import OrganizationMasterService


class InstrumentTypeService(OrganizationMasterService[InstrumentType]):
    def __init__(self, repository: InstrumentTypeRepository | None = None):
        super().__init__(repository or InstrumentTypeRepository(), "instrument type")

    def create(self, db: Session, organization_id: UUID, **values) -> InstrumentType:
        values = self._normalize_common(values)
        return self.repository.add(db, InstrumentType(organization_id=organization_id, **values))

    def update(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, **values) -> InstrumentType:
        return self._mutate(db, organization_id, record_id, expected_version, self._normalize_common(values))

    def create_scoped(self, db: Session, actor, values: dict) -> InstrumentType:
        self.scope_service.ensure_can_create_shared_master(actor, "instrument_type.create")
        normalized = self._normalize_common(values)
        if self.repository.get_by_code(db, actor.organization_id, normalized["code"]):
            from app.core.exceptions import DuplicateResourceException
            raise DuplicateResourceException(self._duplicate_message())
        record = InstrumentType(organization_id=actor.organization_id, **normalized)
        return self._add_and_commit_create(db, record, actor)

    def update_for_actor(self, db: Session, actor, record_id: UUID, expected_version: int, values: dict):
        return self.update_scoped(db, actor, record_id, expected_version, self._normalize_common(values), "instrument_type.update")
