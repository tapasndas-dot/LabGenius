from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business.instrument import Instrument, InstrumentStatus, StabilityChamberProfile
from app.models.business.material import Material
from app.models.business.specification import Specification, SpecificationVersion, SpecificationVersionStatus
from app.models.business.stability import StabilityProtocol, StabilityProtocolCondition, StabilityProtocolTimepoint, StabilityProtocolVersion, StabilityProtocolVersionStatus, StabilityStudy, StabilityStudyCondition, StabilityStudyStatus
from app.repositories.business.stability_repository import StabilityProtocolConditionRepository, StabilityProtocolRepository, StabilityProtocolTimepointRepository, StabilityProtocolVersionRepository, StabilityStudyConditionRepository, StabilityStudyRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.organization_scope_service import AccessScope, OrganizationScopeService
from .normalization import normalize_code, normalize_name, normalize_optional
from .organization_master_service import VERSION_CONFLICT_MESSAGE
from .sample_service import SampleService


IMMUTABLE_PROTOCOL_MESSAGE = "Only DRAFT Stability Protocol Versions may be structurally modified."


class _AuditedService:
    def __init__(self):
        self.audit = AuditService()

    def _create_audit(self, db, actor, entity, owner=None):
        self.audit.record_create(db, entity=entity, actor=actor, owner=owner or entity)

    def _update_audit(self, db, actor, entity, before, owner=None, action=AuditAction.UPDATE):
        self.audit.record_update(db, entity=entity, actor=actor, owner=owner or entity, before=before, action=action)


class StabilityProtocolService(_AuditedService):
    def __init__(self, repository=None):
        super().__init__()
        self.repository = repository or StabilityProtocolRepository()

    @staticmethod
    def normalize(values):
        result = dict(values)
        if "protocol_code" in result:
            result["protocol_code"] = normalize_code(result["protocol_code"])
        if "protocol_name" in result:
            result["protocol_name"] = normalize_name(result["protocol_name"])
        if "description" in result:
            result["description"] = normalize_optional(result["description"])
        return result

    def create(self, db: Session, actor, values: dict):
        values = self.normalize(values)
        if not values.get("protocol_code") or not values.get("protocol_name"):
            raise ValidationException("Stability Protocol code and name are required.")
        if self.repository.get_by_code(db, actor.organization_id, values["protocol_code"]):
            raise DuplicateResourceException("A Stability Protocol with this code already exists.")
        record = StabilityProtocol(organization_id=actor.organization_id, **values)
        db.add(record); db.flush()
        self._create_audit(db, actor, record)
        return record

    def update(self, db, actor, protocol_id, expected_version, values):
        current = self.repository.get(db, actor.organization_id, protocol_id)
        if current is None:
            raise ResourceNotFoundException("Stability Protocol not found.")
        before = self.audit.snapshot(current)
        values = self.normalize(values)
        duplicate = self.repository.get_by_code(db, actor.organization_id, values.get("protocol_code")) if values.get("protocol_code") else None
        if duplicate is not None and duplicate.id != protocol_id:
            raise DuplicateResourceException("A Stability Protocol with this code already exists.")
        updated = self.repository.update_expected(db, protocol_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._update_audit(db, actor, updated, before)
        return updated

    def set_active(self, db, actor, protocol_id, expected_version, is_active):
        current = self.repository.get(db, actor.organization_id, protocol_id)
        if current is None:
            raise ResourceNotFoundException("Stability Protocol not found.")
        before = self.audit.snapshot(current)
        updated = self.repository.update_expected(db, protocol_id, expected_version, {"is_active": is_active})
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        self._update_audit(db, actor, updated, before, action=action)
        return updated

    def delete(self, db, actor, protocol_id, expected_version):
        current = self.repository.get(db, actor.organization_id, protocol_id)
        if current is None:
            raise ResourceNotFoundException("Stability Protocol not found.")
        before = self.audit.snapshot(current)
        if not self.repository.delete_expected(db, protocol_id, expected_version):
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self.audit.record_delete(db, entity=current, actor=actor, owner=current, before=before)


class StabilityProtocolVersionService(_AuditedService):
    TRANSITIONS = {
        StabilityProtocolVersionStatus.DRAFT: {StabilityProtocolVersionStatus.APPROVED},
        StabilityProtocolVersionStatus.APPROVED: {StabilityProtocolVersionStatus.RETIRED, StabilityProtocolVersionStatus.SUPERSEDED},
        StabilityProtocolVersionStatus.RETIRED: set(),
        StabilityProtocolVersionStatus.SUPERSEDED: set(),
    }

    def __init__(self, repository=None, protocol_repository=None):
        super().__init__()
        self.repository = repository or StabilityProtocolVersionRepository()
        self.protocol_repository = protocol_repository or StabilityProtocolRepository()

    def draft(self, db, organization_id, version_id):
        record = self.repository.get(db, organization_id, version_id)
        if record is None:
            raise ResourceNotFoundException("Stability Protocol Version not found.")
        if record.status != StabilityProtocolVersionStatus.DRAFT:
            raise ValidationException(IMMUTABLE_PROTOCOL_MESSAGE)
        return record

    @staticmethod
    def normalize(values):
        result = dict(values)
        for field in ("version_label", "description"):
            if field in result:
                result[field] = normalize_optional(result[field])
        return result

    @staticmethod
    def validate_effectivity(start, end):
        if any(value is not None and (value.tzinfo is None or value.utcoffset() is None) for value in (start, end)):
            raise ValidationException("Protocol Version effectivity must be timezone-aware.")
        if start is not None and end is not None and end < start:
            raise ValidationException("effective_to must be on or after effective_from.")

    def create(self, db, actor, protocol_id, values):
        protocol = self.protocol_repository.get(db, actor.organization_id, protocol_id)
        if protocol is None or not protocol.is_active:
            raise ResourceNotFoundException("Stability Protocol not found.")
        values = self.normalize(values)
        number = values.get("version_number")
        if not isinstance(number, int) or number <= 0:
            raise ValidationException("Protocol Version number must be positive.")
        if values.pop("status", "DRAFT") != "DRAFT":
            raise ValidationException("New Protocol Versions must start in DRAFT status.")
        self.validate_effectivity(values.get("effective_from"), values.get("effective_to"))
        duplicate = self.repository.query(db).filter_by(stability_protocol_id=protocol_id, version_number=number).first()
        if duplicate:
            raise DuplicateResourceException("This Protocol version number already exists.")
        record = StabilityProtocolVersion(stability_protocol_id=protocol_id, **values)
        db.add(record); db.flush(); self._create_audit(db, actor, record, protocol)
        return record

    def update(self, db, actor, version_id, expected_version, values):
        current = self.draft(db, actor.organization_id, version_id)
        values = self.normalize(values)
        if "status" in values:
            raise ValidationException("Use the controlled status transition operation.")
        self.validate_effectivity(values.get("effective_from", current.effective_from), values.get("effective_to", current.effective_to))
        before = self.audit.snapshot(current)
        updated = self.repository.update_expected(db, version_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._update_audit(db, actor, updated, before, current.protocol)
        return updated

    def transition(self, db, actor, version_id, expected_version, target_status):
        current = self.repository.get(db, actor.organization_id, version_id)
        if current is None:
            raise ResourceNotFoundException("Stability Protocol Version not found.")
        try:
            source, target = StabilityProtocolVersionStatus(current.status), StabilityProtocolVersionStatus(target_status)
        except ValueError as exc:
            raise ValidationException("Invalid Stability Protocol Version status.") from exc
        if target not in self.TRANSITIONS[source]:
            raise ValidationException(f"Protocol Version cannot transition from {source.value} to {target.value}.")
        before = self.audit.snapshot(current)
        updated = self.repository.update_expected(db, version_id, expected_version, {"status": target.value})
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        action = {StabilityProtocolVersionStatus.APPROVED: AuditAction.APPROVE, StabilityProtocolVersionStatus.RETIRED: AuditAction.RETIRE, StabilityProtocolVersionStatus.SUPERSEDED: AuditAction.SUPERSEDE}[target]
        self._update_audit(db, actor, updated, before, current.protocol, action)
        return updated


class StabilityProtocolConditionService(_AuditedService):
    def __init__(self):
        super().__init__(); self.repository = StabilityProtocolConditionRepository(); self.versions = StabilityProtocolVersionService()

    @staticmethod
    def normalize(values):
        result = dict(values)
        if "condition_code" in result: result["condition_code"] = normalize_code(result["condition_code"])
        if "condition_name" in result: result["condition_name"] = normalize_name(result["condition_name"])
        for field in ("temperature_unit", "humidity_unit", "description"):
            if field in result: result[field] = normalize_optional(result[field])
        if result.get("sequence_number") is not None and result["sequence_number"] <= 0:
            raise ValidationException("Condition sequence number must be positive.")
        return result

    def create(self, db, actor, protocol_version_id, values):
        version = self.versions.draft(db, actor.organization_id, protocol_version_id); values = self.normalize(values)
        if not all(values.get(field) for field in ("sequence_number", "condition_code", "condition_name")):
            raise ValidationException("Condition sequence, code, and name are required.")
        record = StabilityProtocolCondition(stability_protocol_version_id=protocol_version_id, **values)
        db.add(record); db.flush(); self._create_audit(db, actor, record, version.protocol); return record

    def update(self, db, actor, condition_id, expected_version, values):
        current = self.repository.get(db, actor.organization_id, condition_id)
        if current is None: raise ResourceNotFoundException("Stability Protocol Condition not found.")
        self.versions.draft(db, actor.organization_id, current.stability_protocol_version_id); before = self.audit.snapshot(current)
        updated = self.repository.update_expected(db, condition_id, expected_version, self.normalize(values))
        if updated is None: raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._update_audit(db, actor, updated, before, current.protocol_version.protocol); return updated

    def delete(self, db, actor, condition_id, expected_version):
        current = self.repository.get(db, actor.organization_id, condition_id)
        if current is None: raise ResourceNotFoundException("Stability Protocol Condition not found.")
        self.versions.draft(db, actor.organization_id, current.stability_protocol_version_id); before = self.audit.snapshot(current); owner = current.protocol_version.protocol
        if not self.repository.delete_expected(db, condition_id, expected_version): raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self.audit.record_delete(db, entity=current, actor=actor, owner=owner, before=before)


class StabilityProtocolTimepointService(_AuditedService):
    def __init__(self):
        super().__init__(); self.repository = StabilityProtocolTimepointRepository(); self.conditions = StabilityProtocolConditionRepository(); self.versions = StabilityProtocolVersionService()

    @staticmethod
    def normalize(values):
        result = dict(values)
        for field in ("label", "interval_unit", "description"):
            if field in result: result[field] = normalize_optional(result[field])
        if result.get("interval_unit") is not None: result["interval_unit"] = result["interval_unit"].upper()
        return result

    @staticmethod
    def validate_interval(values):
        initial, amount, unit = values.get("is_initial", False), values.get("interval_value"), values.get("interval_unit")
        if initial and (amount is not None or unit is not None): raise ValidationException("Initial timepoints cannot have an interval.")
        if not initial and (not isinstance(amount, int) or amount <= 0 or unit not in {"DAY", "WEEK", "MONTH", "YEAR"}): raise ValidationException("Non-initial timepoints require a positive interval and valid unit.")

    @staticmethod
    def validate_specification(db, organization_id, specification_version_id):
        version = db.query(SpecificationVersion).join(Specification).filter(SpecificationVersion.id == specification_version_id, Specification.organization_id == organization_id).first()
        if version is None or version.status != SpecificationVersionStatus.APPROVED:
            raise ValidationException("Timepoints require an APPROVED Specification Version in the same organization.")

    def create(self, db, actor, condition_id, values):
        condition = self.conditions.get(db, actor.organization_id, condition_id)
        if condition is None: raise ResourceNotFoundException("Stability Protocol Condition not found.")
        self.versions.draft(db, actor.organization_id, condition.stability_protocol_version_id); values = self.normalize(values)
        if not values.get("sequence_number") or not values.get("label") or not values.get("specification_version_id"): raise ValidationException("Timepoint sequence, label, and Specification Version are required.")
        self.validate_interval(values); self.validate_specification(db, actor.organization_id, values["specification_version_id"])
        if values.get("is_initial") and self.repository.query(db).filter_by(stability_protocol_condition_id=condition_id, is_initial=True).first(): raise DuplicateResourceException("Only one initial timepoint is allowed per condition.")
        record = StabilityProtocolTimepoint(stability_protocol_condition_id=condition_id, **values)
        db.add(record); db.flush(); self._create_audit(db, actor, record, condition.protocol_version.protocol); return record

    def update(self, db, actor, timepoint_id, expected_version, values):
        current = self.repository.get(db, actor.organization_id, timepoint_id)
        if current is None: raise ResourceNotFoundException("Stability Protocol Timepoint not found.")
        self.versions.draft(db, actor.organization_id, current.condition.stability_protocol_version_id); values = self.normalize(values)
        merged = {field: values.get(field, getattr(current, field)) for field in ("is_initial", "interval_value", "interval_unit")}; self.validate_interval(merged)
        if "specification_version_id" in values: self.validate_specification(db, actor.organization_id, values["specification_version_id"])
        if merged["is_initial"]:
            duplicate = self.repository.query(db).filter(StabilityProtocolTimepoint.stability_protocol_condition_id == current.stability_protocol_condition_id, StabilityProtocolTimepoint.is_initial.is_(True), StabilityProtocolTimepoint.id != timepoint_id).first()
            if duplicate: raise DuplicateResourceException("Only one initial timepoint is allowed per condition.")
        before = self.audit.snapshot(current); updated = self.repository.update_expected(db, timepoint_id, expected_version, values)
        if updated is None: raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._update_audit(db, actor, updated, before, current.condition.protocol_version.protocol); return updated

    def delete(self, db, actor, timepoint_id, expected_version):
        current = self.repository.get(db, actor.organization_id, timepoint_id)
        if current is None: raise ResourceNotFoundException("Stability Protocol Timepoint not found.")
        self.versions.draft(db, actor.organization_id, current.condition.stability_protocol_version_id); before = self.audit.snapshot(current); owner = current.condition.protocol_version.protocol
        if not self.repository.delete_expected(db, timepoint_id, expected_version): raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self.audit.record_delete(db, entity=current, actor=actor, owner=owner, before=before)


class StabilityStudyService(_AuditedService):
    MUTABLE = {"business_unit_id", "division_id", "department_id", "study_name", "batch_number", "lot_number", "start_date", "notes"}

    def __init__(self):
        super().__init__(); self.repository = StabilityStudyRepository(); self.protocol_versions = StabilityProtocolVersionRepository(); self.scope = OrganizationScopeService()

    def scoped_query(self, db, actor, permission): return self.scope.filter_stability_studies(self.repository.query(db), actor, permission)

    @staticmethod
    def _validate_timepoint_materials(db, study):
        mismatch = db.query(StabilityProtocolTimepoint.id).join(StabilityProtocolCondition).join(
            SpecificationVersion,
            StabilityProtocolTimepoint.specification_version_id == SpecificationVersion.id,
        ).join(Specification).filter(
            StabilityProtocolCondition.stability_protocol_version_id == study.stability_protocol_version_id,
            Specification.material_id != study.material_id,
        ).first()
        if mismatch is not None:
            raise ValidationException("Study Material must match every Timepoint Specification Material.")

    @staticmethod
    def normalize(values):
        result = dict(values)
        if "study_number" in result: result["study_number"] = normalize_code(result["study_number"])
        if "study_name" in result: result["study_name"] = normalize_name(result["study_name"])
        for field in ("batch_number", "lot_number", "notes"):
            if field in result: result[field] = normalize_optional(result[field])
        return result

    @staticmethod
    def validate_references(db, organization_id, values):
        SampleService.validate_hierarchy(db, organization_id, values)
        material = db.get(Material, values.get("material_id"))
        if material is None or material.organization_id != organization_id: raise ValidationException("Material must belong to the Study organization.")
        version = db.query(StabilityProtocolVersion).join(StabilityProtocol).filter(StabilityProtocolVersion.id == values.get("stability_protocol_version_id"), StabilityProtocol.organization_id == organization_id).first()
        if version is None: raise ValidationException("Protocol Version must belong to the Study organization.")
        return version

    def create(self, db, actor, values):
        values = self.normalize(values)
        if values.pop("status", "DRAFT") != "DRAFT": raise ValidationException("New Stability Studies must start in DRAFT status.")
        if not all(values.get(field) for field in ("study_number", "study_name", "material_id", "stability_protocol_version_id")): raise ValidationException("Study number, name, Material, and Protocol Version are required.")
        self.validate_references(db, actor.organization_id, values)
        if self.repository.get_by_number(db, actor.organization_id, values["study_number"]): raise DuplicateResourceException("A Stability Study with this number already exists.")
        record = StabilityStudy(organization_id=actor.organization_id, **values); db.add(record); db.flush(); self._create_audit(db, actor, record); return record

    def update(self, db, actor, study_id, expected_version, values):
        current = self.repository.get(db, actor.organization_id, study_id)
        if current is None: raise ResourceNotFoundException("Stability Study not found.")
        if current.status != StabilityStudyStatus.DRAFT: raise ValidationException("Only DRAFT Stability Studies may be edited.")
        values = self.normalize({key: value for key, value in values.items() if key in self.MUTABLE})
        hierarchy = {field: values.get(field, getattr(current, field)) for field in ("business_unit_id", "division_id", "department_id")}; SampleService.validate_hierarchy(db, actor.organization_id, hierarchy)
        before = self.audit.snapshot(current); updated = self.repository.update_expected(db, study_id, expected_version, values)
        if updated is None: raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._update_audit(db, actor, updated, before); return updated

    def transition(self, db, actor, study_id, expected_version, target_status):
        current = self.repository.get(db, actor.organization_id, study_id)
        if current is None: raise ResourceNotFoundException("Stability Study not found.")
        allowed = {StabilityStudyStatus.DRAFT: {StabilityStudyStatus.ACTIVE, StabilityStudyStatus.CANCELLED}, StabilityStudyStatus.ACTIVE: {StabilityStudyStatus.COMPLETED, StabilityStudyStatus.CANCELLED}, StabilityStudyStatus.COMPLETED: set(), StabilityStudyStatus.CANCELLED: set()}
        try: source, target = StabilityStudyStatus(current.status), StabilityStudyStatus(target_status)
        except ValueError as exc: raise ValidationException("Invalid Stability Study status.") from exc
        if target not in allowed[source]: raise ValidationException(f"Study cannot transition from {source.value} to {target.value}.")
        protocol_version = self.protocol_versions.get(db, actor.organization_id, current.stability_protocol_version_id)
        if target == StabilityStudyStatus.ACTIVE:
            if protocol_version.status != StabilityProtocolVersionStatus.APPROVED: raise ValidationException("Study activation requires an APPROVED Protocol Version.")
            self._validate_timepoint_materials(db, current)
        before = self.audit.snapshot(current); updated = self.repository.update_expected(db, study_id, expected_version, {"status": target.value})
        if updated is None: raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        action = AuditAction.CANCEL if target == StabilityStudyStatus.CANCELLED else AuditAction.UPDATE
        self._update_audit(db, actor, updated, before, action=action); return updated


class StabilityStudyConditionService(_AuditedService):
    def __init__(self):
        super().__init__(); self.repository = StabilityStudyConditionRepository(); self.studies = StabilityStudyRepository(); self.conditions = StabilityProtocolConditionRepository()

    @staticmethod
    def validate_times(assigned_at, ended_at):
        if any(value is not None and (value.tzinfo is None or value.utcoffset() is None) for value in (assigned_at, ended_at)): raise ValidationException("Study Condition timestamps must be timezone-aware.")
        if assigned_at and ended_at and ended_at < assigned_at: raise ValidationException("ended_at must be on or after assigned_at.")

    def validate_references(self, db, organization_id, study, condition_id, instrument_id):
        condition = self.conditions.get(db, organization_id, condition_id)
        if condition is None or condition.stability_protocol_version_id != study.stability_protocol_version_id: raise ValidationException("Study Condition must belong to the Study's frozen Protocol Version.")
        instrument = db.get(Instrument, instrument_id)
        if instrument is None or instrument.organization_id != organization_id: raise ValidationException("Instrument must belong to the Study organization.")
        if instrument.status in {InstrumentStatus.RETIRED, InstrumentStatus.OUT_OF_SERVICE}: raise ValidationException("The chamber Instrument is unavailable for assignment.")
        if db.query(StabilityChamberProfile).filter_by(instrument_id=instrument_id).first() is None: raise ValidationException("Instrument must have a Stability Chamber Profile.")

    @staticmethod
    def validate_mutation_allowed(study, *, deleting=False):
        status = StabilityStudyStatus(study.status)
        if deleting:
            if status != StabilityStudyStatus.DRAFT:
                raise ValidationException("Study Conditions may be deleted only while the Stability Study is DRAFT.")
            return
        if status not in {StabilityStudyStatus.DRAFT, StabilityStudyStatus.ACTIVE}:
            raise ValidationException("Study Conditions may be created or updated only while the Stability Study is DRAFT or ACTIVE.")

    def create(self, db, actor, study_id, values):
        study = self.studies.get(db, actor.organization_id, study_id)
        if study is None: raise ResourceNotFoundException("Stability Study not found.")
        self.validate_mutation_allowed(study)
        self.validate_references(db, actor.organization_id, study, values.get("stability_protocol_condition_id"), values.get("instrument_id")); self.validate_times(values.get("assigned_at"), values.get("ended_at"))
        record = StabilityStudyCondition(stability_study_id=study_id, **values); db.add(record); db.flush(); self._create_audit(db, actor, record, study); return record

    def update(self, db, actor, study_condition_id, expected_version, values):
        current = self.repository.get(db, actor.organization_id, study_condition_id)
        if current is None: raise ResourceNotFoundException("Stability Study Condition not found.")
        study = current.study; self.validate_mutation_allowed(study); condition_id = values.get("stability_protocol_condition_id", current.stability_protocol_condition_id); instrument_id = values.get("instrument_id", current.instrument_id)
        self.validate_references(db, actor.organization_id, study, condition_id, instrument_id); self.validate_times(values.get("assigned_at", current.assigned_at), values.get("ended_at", current.ended_at))
        before = self.audit.snapshot(current); updated = self.repository.update_expected(db, study_condition_id, expected_version, values)
        if updated is None: raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._update_audit(db, actor, updated, before, study); return updated

    def delete(self, db, actor, study_condition_id, expected_version):
        current = self.repository.get(db, actor.organization_id, study_condition_id)
        if current is None: raise ResourceNotFoundException("Stability Study Condition not found.")
        self.validate_mutation_allowed(current.study, deleting=True)
        before = self.audit.snapshot(current); owner = current.study
        if not self.repository.delete_expected(db, study_condition_id, expected_version): raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self.audit.record_delete(db, entity=current, actor=actor, owner=owner, before=before)
