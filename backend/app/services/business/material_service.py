from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.models.business.material import Material, MaterialType
from app.repositories.business.material_repository import MaterialRepository
from .organization_master_service import OrganizationMasterService


class MaterialService(OrganizationMasterService[Material]):
    def __init__(self, repository: MaterialRepository | None = None):
        super().__init__(repository or MaterialRepository())

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
