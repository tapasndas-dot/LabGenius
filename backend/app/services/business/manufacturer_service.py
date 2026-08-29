from uuid import UUID

from sqlalchemy.orm import Session

from app.models.business.manufacturer import Manufacturer
from app.repositories.business.manufacturer_repository import ManufacturerRepository
from .organization_master_service import OrganizationMasterService


class ManufacturerService(OrganizationMasterService[Manufacturer]):
    def __init__(self, repository: ManufacturerRepository | None = None):
        super().__init__(repository or ManufacturerRepository(), "manufacturer")

    def create(self, db: Session, organization_id: UUID, **values) -> Manufacturer:
        values = self._normalize_common(values)
        return self.repository.add(db, Manufacturer(organization_id=organization_id, **values))

    def update(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, **values) -> Manufacturer:
        return self._mutate(db, organization_id, record_id, expected_version, self._normalize_common(values))

    def create_scoped(self, db: Session, actor, values: dict) -> Manufacturer:
        self.scope_service.ensure_can_create_shared_master(actor, "manufacturer.create")
        normalized = self._normalize_common(values)
        if self.repository.get_by_code(db, actor.organization_id, normalized["code"]):
            from app.core.exceptions import DuplicateResourceException
            raise DuplicateResourceException(self._duplicate_message())
        record = Manufacturer(organization_id=actor.organization_id, **normalized)
        return self._add_and_commit_create(db, record, actor)

    def update_for_actor(self, db: Session, actor, record_id: UUID, expected_version: int, values: dict):
        return self.update_scoped(db, actor, record_id, expected_version, self._normalize_common(values), "manufacturer.update")
