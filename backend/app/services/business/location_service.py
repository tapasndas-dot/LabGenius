from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.business.location import Location, LocationType
from app.repositories.business.location_repository import LocationRepository
from .organization_master_service import OrganizationMasterService


class LocationService(OrganizationMasterService[Location]):
    def __init__(self, repository: LocationRepository | None = None):
        super().__init__(repository or LocationRepository(), "location")

    @staticmethod
    def _validate_type(value: str) -> str:
        try:
            return LocationType(value).value
        except ValueError as exc:
            raise ValidationException("Invalid location type.") from exc

    def _validate_parent(
        self, db: Session, organization_id: UUID, parent_id: UUID | None,
        record_id: UUID | None = None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == record_id:
            raise ValidationException("A location cannot be its own parent.")
        visited: set[UUID] = set()
        current_id: UUID | None = parent_id
        while current_id is not None:
            if current_id in visited or current_id == record_id:
                raise ValidationException("Location hierarchy cannot contain a circular relationship.")
            visited.add(current_id)
            current = self.repository.get(db, organization_id, current_id)
            if current is None:
                raise ResourceNotFoundException("Parent location not found.")
            current_id = current.parent_location_id

    def create(self, db: Session, organization_id: UUID, **values) -> Location:
        values = self._normalize_common(values)
        values["location_type"] = self._validate_type(values["location_type"])
        self._validate_parent(db, organization_id, values.get("parent_location_id"))
        return self.repository.add(db, Location(organization_id=organization_id, **values))

    def update(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, **values) -> Location:
        values = self._normalize_common(values)
        if "location_type" in values:
            values["location_type"] = self._validate_type(values["location_type"])
        if "parent_location_id" in values:
            self._validate_parent(db, organization_id, values["parent_location_id"], record_id)
        return self._mutate(db, organization_id, record_id, expected_version, values)

    def create_scoped(self, db: Session, actor, values: dict) -> Location:
        self.scope_service.ensure_can_create_shared_master(actor, "location.create")
        normalized = self._normalize_common(values)
        normalized["location_type"] = self._validate_type(normalized["location_type"])
        self._validate_parent(db, actor.organization_id, normalized.get("parent_location_id"))
        if self.repository.get_by_code(db, actor.organization_id, normalized["code"]):
            from app.core.exceptions import DuplicateResourceException
            raise DuplicateResourceException(self._duplicate_message())
        record = Location(organization_id=actor.organization_id, **normalized)
        return self._add_and_commit_create(db, record, actor)

    def update_for_actor(self, db: Session, actor, record_id: UUID, expected_version: int, values: dict):
        values = self._normalize_common(values)
        if "location_type" in values:
            values["location_type"] = self._validate_type(values["location_type"])
        if "parent_location_id" in values:
            self._validate_parent(db, actor.organization_id, values["parent_location_id"], record_id)
        return self.update_scoped(db, actor, record_id, expected_version, values, "location.update")
