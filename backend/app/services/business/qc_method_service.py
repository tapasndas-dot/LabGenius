from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business.qc_method import Method, MethodParameter, MethodParameterValueType, MethodVersion, MethodVersionStatus, Test
from app.repositories.business.qc_method_repository import MethodParameterRepository, MethodRepository, MethodVersionRepository, TestRepository
from .normalization import normalize_code, normalize_name, normalize_optional
from .organization_master_service import VERSION_CONFLICT_MESSAGE


IMMUTABLE_VERSION_MESSAGE = "Only DRAFT Method Versions may be structurally modified."


class _HeaderService:
    model = None
    code_field = ""
    name_field = ""
    optional_fields: tuple[str, ...] = ()
    resource_name = "record"

    def __init__(self, repository):
        self.repository = repository

    def normalize(self, values: dict) -> dict:
        result = dict(values)
        if self.code_field in result:
            result[self.code_field] = normalize_code(result[self.code_field])
        if self.name_field in result:
            result[self.name_field] = normalize_name(result[self.name_field])
        for field in self.optional_fields:
            if field in result:
                result[field] = normalize_optional(result[field])
        return result

    def create(self, db: Session, organization_id: UUID, values: dict):
        values = self.normalize(values)
        if self.code_field not in values or self.name_field not in values:
            raise ValidationException(f"{self.resource_name.title()} code and name are required.")
        if self.repository.get_by_code(db, organization_id, values[self.code_field]):
            raise DuplicateResourceException(f"A {self.resource_name} with this code already exists.")
        record = self.model(organization_id=organization_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_expected(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, values: dict):
        values = self.normalize(values)
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException(f"{self.resource_name.title()} not found.")
        if self.code_field in values:
            duplicate = self.repository.get_by_code(db, organization_id, values[self.code_field])
            if duplicate is not None and duplicate.id != record_id:
                raise DuplicateResourceException(f"A {self.resource_name} with this code already exists.")
        updated = self.repository.update_expected(db, organization_id, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated


class TestService(_HeaderService):
    model = Test
    code_field = "test_code"
    name_field = "test_name"
    optional_fields = ("description", "test_category", "default_unit")
    resource_name = "test"

    def __init__(self, repository: TestRepository | None = None):
        super().__init__(repository or TestRepository())


class MethodService(_HeaderService):
    model = Method
    code_field = "method_code"
    name_field = "method_name"
    optional_fields = ("description",)
    resource_name = "method"

    def __init__(self, repository: MethodRepository | None = None):
        super().__init__(repository or MethodRepository())


class MethodVersionService:
    _TRANSITIONS = {
        MethodVersionStatus.DRAFT: {MethodVersionStatus.APPROVED, MethodVersionStatus.RETIRED},
        MethodVersionStatus.APPROVED: {MethodVersionStatus.RETIRED, MethodVersionStatus.SUPERSEDED},
        MethodVersionStatus.RETIRED: set(),
        MethodVersionStatus.SUPERSEDED: set(),
    }

    def __init__(self, repository: MethodVersionRepository | None = None, method_repository: MethodRepository | None = None):
        self.repository = repository or MethodVersionRepository()
        self.method_repository = method_repository or MethodRepository()

    @staticmethod
    def _normalize(values: dict) -> dict:
        result = dict(values)
        for field in ("version_label", "source_reference", "description"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if "status" in result:
            try:
                result["status"] = MethodVersionStatus(result["status"]).value
            except ValueError as exc:
                raise ValidationException("Invalid Method Version status.") from exc
        return result

    @staticmethod
    def _validate_effectivity(effective_from: datetime | None, effective_to: datetime | None):
        for value in (effective_from, effective_to):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValidationException("Method Version effectivity must be timezone-aware.")
        if effective_from is not None and effective_to is not None and effective_to < effective_from:
            raise ValidationException("effective_to must be on or after effective_from.")

    def create(self, db: Session, organization_id: UUID, method_id: UUID, values: dict):
        method = self.method_repository.get(db, organization_id, method_id)
        if method is None or not method.is_active:
            raise ResourceNotFoundException("Method not found.")
        values = self._normalize(values)
        status = MethodVersionStatus(values.get("status", MethodVersionStatus.DRAFT))
        if status != MethodVersionStatus.DRAFT:
            raise ValidationException("New Method Versions must start in DRAFT status.")
        version_number = values.get("version_number")
        if not isinstance(version_number, int) or version_number <= 0:
            raise ValidationException("Method Version number must be positive.")
        self._validate_effectivity(values.get("effective_from"), values.get("effective_to"))
        if self.repository.get_by_number(db, organization_id, method_id, version_number):
            raise DuplicateResourceException("This Method version number already exists.")
        record = MethodVersion(method_id=method_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_draft(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, values: dict):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Method Version not found.")
        if current.status != MethodVersionStatus.DRAFT:
            raise ValidationException(IMMUTABLE_VERSION_MESSAGE)
        values = self._normalize(values)
        if "status" in values and values["status"] != MethodVersionStatus.DRAFT:
            raise ValidationException("Use the controlled status transition operation.")
        effective_from = values.get("effective_from", current.effective_from)
        effective_to = values.get("effective_to", current.effective_to)
        self._validate_effectivity(effective_from, effective_to)
        updated = self.repository.update_expected(db, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def transition_status(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, target_status: str):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Method Version not found.")
        try:
            target = MethodVersionStatus(target_status)
            source = MethodVersionStatus(current.status)
        except ValueError as exc:
            raise ValidationException("Invalid Method Version status.") from exc
        if target not in self._TRANSITIONS[source]:
            raise ValidationException(f"Method Version cannot transition from {source} to {target}.")
        updated = self.repository.update_expected(db, record_id, expected_version, {"status": target.value})
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def delete_draft(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Method Version not found.")
        if current.status != MethodVersionStatus.DRAFT:
            raise ValidationException(IMMUTABLE_VERSION_MESSAGE)
        if not self.repository.delete_expected(db, record_id, expected_version):
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)


class MethodParameterService:
    def __init__(self, repository: MethodParameterRepository | None = None, version_repository: MethodVersionRepository | None = None):
        self.repository = repository or MethodParameterRepository()
        self.version_repository = version_repository or MethodVersionRepository()

    @staticmethod
    def _normalize(values: dict) -> dict:
        result = dict(values)
        if "parameter_code" in result:
            result["parameter_code"] = normalize_code(result["parameter_code"])
        if "parameter_name" in result:
            result["parameter_name"] = normalize_name(result["parameter_name"])
        for field in ("unit", "default_value", "description"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if "value_type" in result:
            try:
                result["value_type"] = MethodParameterValueType(result["value_type"]).value
            except ValueError as exc:
                raise ValidationException("Invalid Method Parameter value type.") from exc
        if result.get("sequence_number") is not None and result["sequence_number"] <= 0:
            raise ValidationException("Method Parameter sequence number must be positive.")
        return result

    def _draft(self, db: Session, organization_id: UUID, method_version_id: UUID):
        version = self.version_repository.get(db, organization_id, method_version_id)
        if version is None:
            raise ResourceNotFoundException("Method Version not found.")
        if version.status != MethodVersionStatus.DRAFT:
            raise ValidationException(IMMUTABLE_VERSION_MESSAGE)
        return version

    def create(self, db: Session, organization_id: UUID, method_version_id: UUID, values: dict):
        self._draft(db, organization_id, method_version_id)
        values = self._normalize(values)
        if not all(field in values for field in ("parameter_code", "parameter_name", "value_type")):
            raise ValidationException("Method Parameter code, name, and value type are required.")
        if self.repository.get_by_code(db, method_version_id, values["parameter_code"]):
            raise DuplicateResourceException("This Method Parameter code already exists for the version.")
        record = MethodParameter(method_version_id=method_version_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_draft(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int, values: dict):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Method Parameter not found.")
        self._draft(db, organization_id, current.method_version_id)
        values = self._normalize(values)
        if "parameter_code" in values:
            duplicate = self.repository.get_by_code(db, current.method_version_id, values["parameter_code"])
            if duplicate is not None and duplicate.id != record_id:
                raise DuplicateResourceException("This Method Parameter code already exists for the version.")
        updated = self.repository.update_expected(db, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def delete_draft(self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Method Parameter not found.")
        self._draft(db, organization_id, current.method_version_id)
        if not self.repository.delete_expected(db, record_id, expected_version):
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
