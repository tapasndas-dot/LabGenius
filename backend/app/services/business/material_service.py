from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.models.business.material import Material, MaterialType
from app.repositories.business.material_repository import MaterialRepository
from .organization_master_service import OrganizationMasterService


class MaterialService(OrganizationMasterService[Material]):
    def __init__(self, repository: MaterialRepository | None = None):
        super().__init__(repository or MaterialRepository(), "material")

    @staticmethod
    def _validate_type(value: str) -> str:
        try:
            return MaterialType(value).value
        except ValueError as exc:
            raise ValidationException("Invalid material type.") from exc

    def create(self, db: Session, organization_id: UUID, **values) -> Material:
        values = self._normalize_common(values)
        values["material_type"] = self._validate_type(values["material_type"])
        return self.repository.add(db, Material(organization_id=organization_id, **values))

    def update(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, **values) -> Material:
        values = self._normalize_common(values)
        if "material_type" in values:
            values["material_type"] = self._validate_type(values["material_type"])
        return self._mutate(db, organization_id, record_id, expected_version, values)

    def create_scoped(self, db: Session, actor, values: dict) -> Material:
        self.scope_service.ensure_can_create_shared_master(actor, "material.create")
        normalized = self._normalize_common(values)
        normalized["material_type"] = self._validate_type(normalized["material_type"])
        if self.repository.get_by_code(db, actor.organization_id, normalized["code"]):
            from app.core.exceptions import DuplicateResourceException
            raise DuplicateResourceException(self._duplicate_message())
        record = Material(organization_id=actor.organization_id, **normalized)
        return self._add_and_commit_create(db, record, actor)

    def update_for_actor(self, db: Session, actor, record_id: UUID, expected_version: int, values: dict):
        values = self._normalize_common(values)
        if "material_type" in values:
            values["material_type"] = self._validate_type(values["material_type"])
        return self.update_scoped(db, actor, record_id, expected_version, values, "material.update")
