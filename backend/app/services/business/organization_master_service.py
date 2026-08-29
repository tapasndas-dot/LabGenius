from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, VersionConflictException
from app.database.base_entities import MasterEntity
from app.repositories.business.organization_master_repository import OrganizationMasterRepository
from .normalization import normalize_code, normalize_name, normalize_optional

MasterType = TypeVar("MasterType", bound=MasterEntity)
VERSION_CONFLICT_MESSAGE = "Record has been modified by another user. Refresh and try again."


class OrganizationMasterService(Generic[MasterType]):
    """Shared mechanics only; each business master retains its own public service."""

    def __init__(self, repository: OrganizationMasterRepository[MasterType]):
        self.repository = repository

    def _normalize_common(self, values: dict) -> dict:
        normalized = dict(values)
        if "code" in normalized:
            normalized["code"] = normalize_code(normalized["code"])
        if "name" in normalized:
            normalized["name"] = normalize_name(normalized["name"])
        for field in ("description", "website", "default_unit_of_measure"):
            if field in normalized:
                normalized[field] = normalize_optional(normalized[field])
        return normalized

    def _mutate(
        self, db: Session, organization_id: UUID, record_id: UUID,
        expected_version: int, values: dict,
    ) -> MasterType:
        updated = self.repository.update_expected(
            db, organization_id, record_id, expected_version, values
        )
        if updated is not None:
            return updated
        if self.repository.get(db, organization_id, record_id) is None:
            raise ResourceNotFoundException("Record not found.")
        raise VersionConflictException(VERSION_CONFLICT_MESSAGE)

    def set_active(
        self, db: Session, organization_id: UUID, record_id: UUID,
        expected_version: int, is_active: bool,
    ) -> MasterType:
        return self._mutate(db, organization_id, record_id, expected_version, {"is_active": is_active})

    def delete(
        self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int
    ) -> None:
        if self.repository.delete_expected(db, organization_id, record_id, expected_version):
            return
        if self.repository.get(db, organization_id, record_id) is None:
            raise ResourceNotFoundException("Record not found.")
        raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
