from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
    ValidationException,
    VersionConflictException,
)
from app.models.business.material import Material
from app.models.business.qc_method import Method, MethodVersion, MethodVersionStatus, Test
from app.models.business.specification import (
    Specification,
    SpecificationCriterionType,
    SpecificationLimit,
    SpecificationTest,
    SpecificationVersion,
    SpecificationVersionStatus,
)
from app.repositories.business import (
    MaterialRepository,
    SpecificationLimitRepository,
    SpecificationRepository,
    SpecificationTestRepository,
    SpecificationVersionRepository,
)
from .normalization import normalize_code, normalize_name, normalize_optional
from .organization_master_service import VERSION_CONFLICT_MESSAGE


IMMUTABLE_SPECIFICATION_MESSAGE = "Only DRAFT Specification Versions may be structurally modified."


class SpecificationService:
    def __init__(self, repository=None, material_repository=None):
        self.repository = repository or SpecificationRepository()
        self.material_repository = material_repository or MaterialRepository()

    @staticmethod
    def _normalize(values):
        result = dict(values)
        if "specification_code" in result:
            result["specification_code"] = normalize_code(result["specification_code"])
        if "specification_name" in result:
            result["specification_name"] = normalize_name(result["specification_name"])
        if "description" in result:
            result["description"] = normalize_optional(result["description"])
        return result

    def _material(self, db, organization_id, material_id):
        material = self.material_repository.get(db, organization_id, material_id)
        if material is None:
            raise ValidationException("Material must belong to the Specification organization.")
        return material

    def create(self, db: Session, organization_id: UUID, values: dict):
        values = self._normalize(values)
        if not all(values.get(field) for field in ("material_id", "specification_code", "specification_name")):
            raise ValidationException("Material, Specification code, and name are required.")
        self._material(db, organization_id, values["material_id"])
        if self.repository.get_by_code(db, organization_id, values["specification_code"]):
            raise DuplicateResourceException("A Specification with this code already exists.")
        record = Specification(organization_id=organization_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_expected(self, db, organization_id, record_id, expected_version, values):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Specification not found.")
        values = self._normalize(values)
        if "material_id" in values:
            self._material(db, organization_id, values["material_id"])
        if "specification_code" in values:
            duplicate = self.repository.get_by_code(db, organization_id, values["specification_code"])
            if duplicate is not None and duplicate.id != record_id:
                raise DuplicateResourceException("A Specification with this code already exists.")
        updated = self.repository.update_expected(db, organization_id, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated


class SpecificationVersionService:
    _TRANSITIONS = {
        SpecificationVersionStatus.DRAFT: {SpecificationVersionStatus.APPROVED, SpecificationVersionStatus.RETIRED},
        SpecificationVersionStatus.APPROVED: {SpecificationVersionStatus.RETIRED, SpecificationVersionStatus.SUPERSEDED},
        SpecificationVersionStatus.RETIRED: set(),
        SpecificationVersionStatus.SUPERSEDED: set(),
    }

    def __init__(self, repository=None, specification_repository=None):
        self.repository = repository or SpecificationVersionRepository()
        self.specification_repository = specification_repository or SpecificationRepository()

    @staticmethod
    def _normalize(values):
        result = dict(values)
        for field in ("version_label", "description"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if "status" in result:
            try:
                result["status"] = SpecificationVersionStatus(result["status"]).value
            except ValueError as exc:
                raise ValidationException("Invalid Specification Version status.") from exc
        return result

    @staticmethod
    def _validate_effectivity(start: datetime | None, end: datetime | None):
        for value in (start, end):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValidationException("Specification Version effectivity must be timezone-aware.")
        if start is not None and end is not None and end < start:
            raise ValidationException("effective_to must be on or after effective_from.")

    def _draft(self, db, organization_id, record_id):
        record = self.repository.get(db, organization_id, record_id)
        if record is None:
            raise ResourceNotFoundException("Specification Version not found.")
        if record.status != SpecificationVersionStatus.DRAFT:
            raise ValidationException(IMMUTABLE_SPECIFICATION_MESSAGE)
        return record

    def create(self, db, organization_id, specification_id, values):
        specification = self.specification_repository.get(db, organization_id, specification_id)
        if specification is None or not specification.is_active:
            raise ResourceNotFoundException("Specification not found.")
        values = self._normalize(values)
        if SpecificationVersionStatus(values.get("status", "DRAFT")) != SpecificationVersionStatus.DRAFT:
            raise ValidationException("New Specification Versions must start in DRAFT status.")
        number = values.get("version_number")
        if not isinstance(number, int) or number <= 0:
            raise ValidationException("Specification Version number must be positive.")
        self._validate_effectivity(values.get("effective_from"), values.get("effective_to"))
        if self.repository.get_by_number(db, organization_id, specification_id, number):
            raise DuplicateResourceException("This Specification version number already exists.")
        record = SpecificationVersion(specification_id=specification_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_draft(self, db, organization_id, record_id, expected_version, values):
        current = self._draft(db, organization_id, record_id)
        values = self._normalize(values)
        if "status" in values and values["status"] != SpecificationVersionStatus.DRAFT:
            raise ValidationException("Use the controlled status transition operation.")
        self._validate_effectivity(values.get("effective_from", current.effective_from), values.get("effective_to", current.effective_to))
        updated = self.repository.update_expected(db, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def validate_approval_ready(self, db, organization_id, record_id):
        version = self.repository.get(db, organization_id, record_id)
        if version is None:
            raise ResourceNotFoundException("Specification Version not found.")
        specification = version.specification
        if not specification.is_active:
            raise ValidationException("The parent Specification must be active.")
        if not version.specification_tests:
            raise ValidationException("An approval-ready Specification Version requires at least one Test.")
        for item in version.specification_tests:
            test = db.get(Test, item.test_id)
            if test is None or not test.is_active or test.organization_id != organization_id:
                raise ValidationException("Every referenced Test must be active and in the same organization.")
            if item.is_required and item.method_version_id is None:
                raise ValidationException("Required Specification Tests need an approved Method Version.")
            if item.method_version_id is not None:
                method_version = db.get(MethodVersion, item.method_version_id)
                method = db.get(Method, method_version.method_id) if method_version else None
                if method is None or method.organization_id != organization_id or method_version.status != MethodVersionStatus.APPROVED:
                    raise ValidationException("Assigned Method Versions must be APPROVED and in the same organization.")
            if not item.limits:
                raise ValidationException("Every Specification Test requires at least one complete limit.")
            for limit in item.limits:
                SpecificationLimitService.validate_criterion(limit.__dict__)
        return True

    def transition_status(self, db, organization_id, record_id, expected_version, target_status):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Specification Version not found.")
        try:
            source = SpecificationVersionStatus(current.status)
            target = SpecificationVersionStatus(target_status)
        except ValueError as exc:
            raise ValidationException("Invalid Specification Version status.") from exc
        if target not in self._TRANSITIONS[source]:
            raise ValidationException(f"Specification Version cannot transition from {source} to {target}.")
        if target == SpecificationVersionStatus.APPROVED:
            self.validate_approval_ready(db, organization_id, record_id)
        updated = self.repository.update_expected(db, record_id, expected_version, {"status": target.value})
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def delete_draft(self, db, organization_id, record_id, expected_version):
        self._draft(db, organization_id, record_id)
        if not self.repository.delete_expected(db, record_id, expected_version):
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)


class SpecificationTestService:
    def __init__(self, repository=None, version_service=None):
        self.repository = repository or SpecificationTestRepository()
        self.version_service = version_service or SpecificationVersionService()

    @staticmethod
    def _normalize(values):
        result = dict(values)
        for field in ("display_name", "instructions"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if result.get("sequence_number") is not None and result["sequence_number"] <= 0:
            raise ValidationException("Specification Test sequence number must be positive.")
        return result

    @staticmethod
    def _references(db, organization_id, test_id, method_version_id):
        test = db.get(Test, test_id)
        if test is None or not test.is_active or test.organization_id != organization_id:
            raise ValidationException("Test must belong to the Specification organization.")
        if method_version_id is not None:
            method_version = db.get(MethodVersion, method_version_id)
            method = db.get(Method, method_version.method_id) if method_version else None
            if method is None or method.organization_id != organization_id:
                raise ValidationException("Method Version must belong to the Specification organization.")

    def create(self, db, organization_id, specification_version_id, values):
        self.version_service._draft(db, organization_id, specification_version_id)
        values = self._normalize(values)
        if not all(field in values for field in ("test_id", "sequence_number")):
            raise ValidationException("Test and sequence number are required.")
        self._references(db, organization_id, values["test_id"], values.get("method_version_id"))
        if self.repository.duplicate(db, specification_version_id, values["test_id"]):
            raise DuplicateResourceException("This Test already exists in the Specification Version.")
        record = SpecificationTest(specification_version_id=specification_version_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_draft(self, db, organization_id, record_id, expected_version, values):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Specification Test not found.")
        self.version_service._draft(db, organization_id, current.specification_version_id)
        values = self._normalize(values)
        test_id = values.get("test_id", current.test_id)
        method_version_id = values.get("method_version_id", current.method_version_id)
        self._references(db, organization_id, test_id, method_version_id)
        duplicate = self.repository.duplicate(db, current.specification_version_id, test_id)
        if duplicate is not None and duplicate.id != record_id:
            raise DuplicateResourceException("This Test already exists in the Specification Version.")
        updated = self.repository.update_expected(db, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def delete_draft(self, db, organization_id, record_id, expected_version):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Specification Test not found.")
        self.version_service._draft(db, organization_id, current.specification_version_id)
        if not self.repository.delete_expected(db, record_id, expected_version):
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)


class SpecificationLimitService:
    _FIELDS = ("lower_limit", "upper_limit", "target_value", "text_value", "boolean_value")

    def __init__(self, repository=None, test_repository=None, version_service=None):
        self.repository = repository or SpecificationLimitRepository()
        self.test_repository = test_repository or SpecificationTestRepository()
        self.version_service = version_service or SpecificationVersionService()

    @classmethod
    def validate_criterion(cls, values):
        try:
            criterion = SpecificationCriterionType(values.get("criterion_type"))
        except (ValueError, TypeError) as exc:
            raise ValidationException("Invalid Specification Limit criterion type.") from exc
        present = {field for field in cls._FIELDS if values.get(field) is not None}
        required = {
            SpecificationCriterionType.BETWEEN: {"lower_limit", "upper_limit"},
            SpecificationCriterionType.MINIMUM: {"lower_limit"},
            SpecificationCriterionType.MAXIMUM: {"upper_limit"},
            SpecificationCriterionType.EQUAL: {"target_value"},
            SpecificationCriterionType.TEXT_MATCH: {"text_value"},
            SpecificationCriterionType.BOOLEAN: {"boolean_value"},
            SpecificationCriterionType.INFORMATIONAL: set(),
        }[criterion]
        if present != required:
            raise ValidationException(f"{criterion.value} requires exactly: {', '.join(sorted(required)) or 'no acceptance values'}.")
        if criterion == SpecificationCriterionType.BETWEEN and values["lower_limit"] > values["upper_limit"]:
            raise ValidationException("BETWEEN lower_limit must not exceed upper_limit.")
        if criterion == SpecificationCriterionType.TEXT_MATCH and not str(values["text_value"]).strip():
            raise ValidationException("TEXT_MATCH text_value must not be blank.")

    @classmethod
    def _normalize(cls, values):
        result = dict(values)
        for field in ("parameter_name", "text_value", "unit", "description"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if "criterion_type" in result:
            try:
                result["criterion_type"] = SpecificationCriterionType(result["criterion_type"]).value
            except ValueError as exc:
                raise ValidationException("Invalid Specification Limit criterion type.") from exc
        if result.get("sequence_number") is not None and result["sequence_number"] <= 0:
            raise ValidationException("Specification Limit sequence number must be positive.")
        return result

    def _draft_for_test(self, db, organization_id, test_id):
        item = self.test_repository.get(db, organization_id, test_id)
        if item is None:
            raise ResourceNotFoundException("Specification Test not found.")
        self.version_service._draft(db, organization_id, item.specification_version_id)
        return item

    def create(self, db, organization_id, specification_test_id, values):
        self._draft_for_test(db, organization_id, specification_test_id)
        values = self._normalize(values)
        self.validate_criterion(values)
        record = SpecificationLimit(specification_test_id=specification_test_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_draft(self, db, organization_id, record_id, expected_version, values):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Specification Limit not found.")
        self._draft_for_test(db, organization_id, current.specification_test_id)
        values = self._normalize(values)
        merged = {field: getattr(current, field) for field in ("criterion_type", *self._FIELDS)}
        merged.update(values)
        self.validate_criterion(merged)
        updated = self.repository.update_expected(db, record_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def delete_draft(self, db, organization_id, record_id, expected_version):
        current = self.repository.get(db, organization_id, record_id)
        if current is None:
            raise ResourceNotFoundException("Specification Limit not found.")
        self._draft_for_test(db, organization_id, current.specification_test_id)
        if not self.repository.delete_expected(db, record_id, expected_version):
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
