from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_effective_permission_codes
from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business.sample import SamplePriority, SampleStatus
from app.models.business.stability import (
    StabilityProtocolCondition, StabilityProtocolTimepoint, StabilityProtocolVersion,
    StabilityPull, StabilityPullStatus, StabilityStudy, StabilityStudyCondition, StabilityStudyStatus,
)
from app.repositories.business.stability_repository import (
    StabilityProtocolConditionRepository, StabilityProtocolRepository,
    StabilityProtocolTimepointRepository, StabilityProtocolVersionRepository,
    StabilityPullRepository, StabilityStudyConditionRepository, StabilityStudyRepository,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.business.sample_service import SampleService, SampleTestService
from app.services.business.normalization import normalize_optional
from app.services.business.organization_master_service import VERSION_CONFLICT_MESSAGE
from app.services.organization_scope_service import OrganizationScopeService
from .stability_service import (
    StabilityProtocolConditionService, StabilityProtocolService,
    StabilityProtocolTimepointService, StabilityProtocolVersionService,
    StabilityStudyConditionService, StabilityStudyService,
)


class _Transactions:
    @staticmethod
    def _commit(db, mutation, *, duplicate_message="A conflicting record already exists."):
        try:
            record = mutation()
            db.commit()
            if record is not None:
                db.refresh(record)
            return record
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(duplicate_message) from exc
        except Exception:
            db.rollback()
            raise


class StabilityProtocolAPIService(_Transactions):
    def __init__(self):
        self.domain = StabilityProtocolService()
        self.repository = StabilityProtocolRepository()
        self.scope = OrganizationScopeService()

    def list(self, db, actor, permission, *, limit=100, offset=0):
        query = self.scope.filter_shared_masters(self.repository.query(db), actor, permission, self.repository.model)
        return query.order_by(self.repository.model.protocol_code, self.repository.model.id).offset(offset).limit(limit).all()

    def get(self, db, actor, protocol_id, permission):
        record = self.repository.get(db, actor.organization_id, protocol_id)
        if record is None:
            raise ResourceNotFoundException("Stability Protocol not found.")
        self.scope.ensure_can_access_shared_master(actor, record, permission, resource_name="Stability Protocol")
        return record

    def create(self, db, actor, permission, values):
        self.scope.ensure_can_create_shared_master(actor, permission)
        return self._commit(db, lambda: self.domain.create(db, actor, values), duplicate_message="A Stability Protocol with this code already exists.")

    def update(self, db, actor, protocol_id, expected, permission, values):
        self.get(db, actor, protocol_id, permission)
        return self._commit(db, lambda: self.domain.update(db, actor, protocol_id, expected, values), duplicate_message="A Stability Protocol with this code already exists.")

    def set_active(self, db, actor, protocol_id, expected, permission, active):
        self.get(db, actor, protocol_id, permission)
        return self._commit(db, lambda: self.domain.set_active(db, actor, protocol_id, expected, active))

    def delete(self, db, actor, protocol_id, expected, permission):
        self.get(db, actor, protocol_id, permission)
        self._commit(db, lambda: self.domain.delete(db, actor, protocol_id, expected), duplicate_message="This Stability Protocol is referenced and cannot be deleted.")


class StabilityProtocolTreeAPIService(_Transactions):
    def __init__(self, protocols=None):
        self.protocols = protocols or StabilityProtocolAPIService()
        self.versions = StabilityProtocolVersionRepository()
        self.conditions = StabilityProtocolConditionRepository()
        self.timepoints = StabilityProtocolTimepointRepository()
        self.version_domain = StabilityProtocolVersionService()
        self.condition_domain = StabilityProtocolConditionService()
        self.timepoint_domain = StabilityProtocolTimepointService()
        self.scope = OrganizationScopeService()

    @staticmethod
    def _match(record, field, expected):
        if record is None or getattr(record, field) != expected:
            raise ResourceNotFoundException("Nested Stability record not found.")
        return record

    def version(self, db, actor, protocol_id, version_id, permission):
        self.protocols.get(db, actor, protocol_id, permission)
        return self._match(self.versions.get(db, actor.organization_id, version_id), "stability_protocol_id", protocol_id)

    def list_versions(self, db, actor, protocol_id, permission):
        self.protocols.get(db, actor, protocol_id, permission)
        return db.query(StabilityProtocolVersion).filter_by(stability_protocol_id=protocol_id).order_by(StabilityProtocolVersion.version_number).all()

    def create_version(self, db, actor, protocol_id, permission, values):
        self.protocols.get(db, actor, protocol_id, permission)
        self.scope.ensure_can_create_shared_master(actor, permission)
        return self._commit(db, lambda: self.version_domain.create(db, actor, protocol_id, values))

    def update_version(self, db, actor, protocol_id, version_id, expected, permission, values):
        self.version(db, actor, protocol_id, version_id, permission)
        return self._commit(db, lambda: self.version_domain.update(db, actor, version_id, expected, values))

    def lifecycle(self, db, actor, protocol_id, version_id, expected, permission, target):
        self.version(db, actor, protocol_id, version_id, permission)
        return self._commit(db, lambda: self.version_domain.transition(db, actor, version_id, expected, target))

    def condition(self, db, actor, protocol_id, version_id, condition_id, permission):
        self.version(db, actor, protocol_id, version_id, permission)
        return self._match(self.conditions.get(db, actor.organization_id, condition_id), "stability_protocol_version_id", version_id)

    def list_conditions(self, db, actor, protocol_id, version_id, permission):
        self.version(db, actor, protocol_id, version_id, permission)
        return db.query(StabilityProtocolCondition).filter_by(stability_protocol_version_id=version_id).order_by(StabilityProtocolCondition.sequence_number).all()

    def create_condition(self, db, actor, protocol_id, version_id, permission, values):
        self.version(db, actor, protocol_id, version_id, permission)
        self.scope.ensure_can_create_shared_master(actor, permission)
        return self._commit(db, lambda: self.condition_domain.create(db, actor, version_id, values))

    def update_condition(self, db, actor, protocol_id, version_id, condition_id, expected, permission, values):
        self.condition(db, actor, protocol_id, version_id, condition_id, permission)
        return self._commit(db, lambda: self.condition_domain.update(db, actor, condition_id, expected, values))

    def delete_condition(self, db, actor, protocol_id, version_id, condition_id, expected, permission):
        self.condition(db, actor, protocol_id, version_id, condition_id, permission)
        self._commit(db, lambda: self.condition_domain.delete(db, actor, condition_id, expected))

    def timepoint(self, db, actor, protocol_id, version_id, condition_id, timepoint_id, permission):
        self.condition(db, actor, protocol_id, version_id, condition_id, permission)
        return self._match(self.timepoints.get(db, actor.organization_id, timepoint_id), "stability_protocol_condition_id", condition_id)

    def list_timepoints(self, db, actor, protocol_id, version_id, condition_id, permission):
        self.condition(db, actor, protocol_id, version_id, condition_id, permission)
        return db.query(StabilityProtocolTimepoint).filter_by(stability_protocol_condition_id=condition_id).order_by(StabilityProtocolTimepoint.sequence_number).all()

    def create_timepoint(self, db, actor, protocol_id, version_id, condition_id, permission, values):
        self.condition(db, actor, protocol_id, version_id, condition_id, permission)
        self.scope.ensure_can_create_shared_master(actor, permission)
        return self._commit(db, lambda: self.timepoint_domain.create(db, actor, condition_id, values))

    def update_timepoint(self, db, actor, protocol_id, version_id, condition_id, timepoint_id, expected, permission, values):
        self.timepoint(db, actor, protocol_id, version_id, condition_id, timepoint_id, permission)
        return self._commit(db, lambda: self.timepoint_domain.update(db, actor, timepoint_id, expected, values))

    def delete_timepoint(self, db, actor, protocol_id, version_id, condition_id, timepoint_id, expected, permission):
        self.timepoint(db, actor, protocol_id, version_id, condition_id, timepoint_id, permission)
        self._commit(db, lambda: self.timepoint_domain.delete(db, actor, timepoint_id, expected))


class StabilityStudyAPIService(_Transactions):
    def __init__(self):
        self.domain = StabilityStudyService()
        self.repository = StabilityStudyRepository()
        self.conditions = StabilityStudyConditionRepository()
        self.condition_domain = StabilityStudyConditionService()
        self.scope = OrganizationScopeService()

    def list(self, db, actor, permission, *, limit=100, offset=0):
        return self.domain.scoped_query(db, actor, permission).order_by(self.repository.model.study_number, self.repository.model.id).offset(offset).limit(limit).all()

    def get(self, db, actor, study_id, permission):
        record = self.domain.scoped_query(db, actor, permission).filter(self.repository.model.id == study_id).first()
        if record is None:
            raise ResourceNotFoundException("Stability Study not found.")
        return record

    def _ensure_placement(self, db, actor, permission, values):
        if not self.scope.can_place_stability_study(db, actor, permission, values):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The Stability Study hierarchy is outside the permitted scope.")

    def create(self, db, actor, permission, values):
        self._ensure_placement(db, actor, permission, values)
        return self._commit(db, lambda: self.domain.create(db, actor, values), duplicate_message="A Stability Study with this number already exists.")

    def update(self, db, actor, study_id, expected, permission, values):
        current = self.get(db, actor, study_id, permission)
        placement = {field: values.get(field, getattr(current, field)) for field in ("business_unit_id", "division_id", "department_id")}
        self._ensure_placement(db, actor, permission, placement)
        return self._commit(db, lambda: self.domain.update(db, actor, study_id, expected, values))

    def transition(self, db, actor, study_id, expected, permission, target):
        self.get(db, actor, study_id, permission)
        return self._commit(db, lambda: self.domain.transition(db, actor, study_id, expected, target))

    def study_condition(self, db, actor, study_id, study_condition_id, permission):
        self.get(db, actor, study_id, permission)
        record = self.conditions.get(db, actor.organization_id, study_condition_id)
        if record is None or record.stability_study_id != study_id:
            raise ResourceNotFoundException("Stability Study Condition not found.")
        return record

    def list_conditions(self, db, actor, study_id, permission):
        self.get(db, actor, study_id, permission)
        return db.query(StabilityStudyCondition).filter_by(stability_study_id=study_id).order_by(StabilityStudyCondition.created_at, StabilityStudyCondition.id).all()

    def create_condition(self, db, actor, study_id, permission, values):
        self.get(db, actor, study_id, permission)
        return self._commit(db, lambda: self.condition_domain.create(db, actor, study_id, values))

    def update_condition(self, db, actor, study_id, study_condition_id, expected, permission, values):
        self.study_condition(db, actor, study_id, study_condition_id, permission)
        return self._commit(db, lambda: self.condition_domain.update(db, actor, study_condition_id, expected, values))

    def delete_condition(self, db, actor, study_id, study_condition_id, expected, permission):
        self.study_condition(db, actor, study_id, study_condition_id, permission)
        self._commit(db, lambda: self.condition_domain.delete(db, actor, study_condition_id, expected))


class StabilityPullAPIService(_Transactions):
    def __init__(self):
        self.repository = StabilityPullRepository()
        self.scope = OrganizationScopeService()
        self.samples = SampleService()
        self.sample_tests = SampleTestService(self.samples.repository)
        self.audit = AuditService()

    def _query(self, db, actor, permission):
        return self.scope.filter_stability_pulls(
            self.repository.query(db), actor, permission
        )

    def _get(self, db, actor, study_id, pull_id, permission):
        record = self._query(db, actor, permission).filter(
            StabilityPull.id == pull_id,
            StabilityPull.stability_study_id == study_id,
        ).first()
        if record is None:
            raise ResourceNotFoundException("Stability Pull not found.")
        return record

    @staticmethod
    def _response(record):
        study_condition = record.study_condition
        condition = study_condition.protocol_condition if study_condition else None
        instrument = study_condition.instrument if study_condition else None
        timepoint = record.timepoint
        sample = record.qc_sample
        return {
            **record.__dict__,
            "protocol_condition": ({"id": condition.id, "code": condition.condition_code,
                                     "name": condition.condition_name} if condition else None),
            "timepoint": ({"id": timepoint.id, "label": timepoint.label,
                           "sequence_number": timepoint.sequence_number,
                           "is_initial": timepoint.is_initial} if timepoint else None),
            "assigned_instrument": ({"id": instrument.id, "code": instrument.instrument_code,
                                     "name": instrument.instrument_name,
                                     "status": instrument.status} if instrument else None),
            "qc_sample": ({"id": sample.id, "sample_number": sample.sample_number,
                           "status": sample.status} if sample else None),
        }

    def list(self, db, actor, study_id, permission, *, limit=100, offset=0, **filters):
        # The parent check and row filtering both use the Pull permission's Study scope.
        query = self._query(db, actor, permission).filter(
            StabilityPull.stability_study_id == study_id
        )
        query = self.repository.apply_filters(query, **filters)
        records = query.order_by(
            StabilityPull.scheduled_date, StabilityPull.id
        ).offset(offset).limit(limit).all()
        if not records:
            scoped_study = self.scope.filter_stability_studies(
                db.query(StabilityStudy), actor, permission
            ).filter_by(id=study_id).first()
            if scoped_study is None:
                raise ResourceNotFoundException("Stability Study not found.")
        return [self._response(record) for record in records]

    def get(self, db, actor, study_id, pull_id, permission):
        return self._response(self._get(db, actor, study_id, pull_id, permission))

    @staticmethod
    def _validate_active(record):
        if record.study.status != StabilityStudyStatus.ACTIVE:
            raise ValidationException("Stability Pull actions require an ACTIVE Study.")

    @staticmethod
    def _validate_expected(record, expected):
        if record.version != expected:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)

    def mark_pulled(self, db, actor, study_id, pull_id, expected, pulled_at, notes, *, notes_supplied):
        record = self._get(db, actor, study_id, pull_id, "stability_pull.execute")
        self._validate_expected(record, expected)
        self._validate_active(record)
        if record.status != StabilityPullStatus.SCHEDULED:
            raise ValidationException("Only a SCHEDULED Stability Pull may be marked pulled.")
        before = self.audit.snapshot(record)
        values = {"status": StabilityPullStatus.PULLED.value, "pulled_at": pulled_at}
        if notes_supplied:
            values["notes"] = normalize_optional(notes)
        def mutation():
            updated = self.repository.update_expected(db, pull_id, expected, values)
            if updated is None:
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit.record_update(db, entity=updated, actor=actor, before=before, owner=record.study)
            return updated
        return self._response(self._commit(db, mutation))

    def cancel(self, db, actor, study_id, pull_id, expected):
        record = self._get(db, actor, study_id, pull_id, "stability_pull.execute")
        self._validate_expected(record, expected)
        self._validate_active(record)
        if record.status != StabilityPullStatus.SCHEDULED:
            raise ValidationException("Only a SCHEDULED Stability Pull may be cancelled.")
        before = self.audit.snapshot(record)
        def mutation():
            updated = self.repository.update_expected(
                db, pull_id, expected, {"status": StabilityPullStatus.CANCELLED.value}
            )
            if updated is None:
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit.record_update(db, entity=updated, actor=actor, before=before,
                                     owner=record.study, action=AuditAction.CANCEL)
            return updated
        return self._response(self._commit(db, mutation))

    def create_sample(self, db, actor, study_id, pull_id, expected, sample_number):
        record = self._get(db, actor, study_id, pull_id, "stability_pull.execute")
        if "sample.create" not in get_effective_permission_codes(actor):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Permission 'sample.create' is required.")
        self._validate_expected(record, expected)
        self._validate_active(record)
        if record.status != StabilityPullStatus.PULLED or record.qc_sample_id is not None or record.pulled_at is None:
            raise ValidationException("Only a pulled Stability Pull without a QC Sample may create a Sample.")
        study = record.study
        values = {
            "business_unit_id": study.business_unit_id,
            "division_id": study.division_id,
            "department_id": study.department_id,
            "sample_number": sample_number,
            "material_id": study.material_id,
            "specification_version_id": record.specification_version_id,
            "sampled_at": record.pulled_at,
            "status": SampleStatus.REGISTERED.value,
            "priority": SamplePriority.NORMAL.value,
        }
        normalized = self.samples.normalize(values)
        if not self.scope.can_place_sample(db, actor, "sample.create", normalized):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Target Sample hierarchy is outside the authorized scope.")
        before = self.audit.snapshot(record)
        def mutation():
            sample = self.samples.create(db, actor.organization_id, normalized)
            self.audit.record_create(db, entity=sample, actor=actor)
            existing = self.sample_tests.repository.existing_source_ids(db, sample.id)
            tests = self.sample_tests.generate(db, actor.organization_id, sample.id)
            for sample_test in tests:
                if sample_test.specification_test_id not in existing:
                    self.audit.record_create(db, entity=sample_test, actor=actor, owner=sample)
            updated = self.repository.update_expected(db, pull_id, expected, {
                "status": StabilityPullStatus.SAMPLE_CREATED.value,
                "qc_sample_id": sample.id,
            })
            if updated is None:
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit.record_update(db, entity=updated, actor=actor, before=before, owner=study)
            return updated
        return self._response(self._commit(
            db, mutation, duplicate_message="A Sample with this number already exists."
        ))


stability_protocol_api_service = StabilityProtocolAPIService()
stability_protocol_tree_api_service = StabilityProtocolTreeAPIService(stability_protocol_api_service)
stability_study_api_service = StabilityStudyAPIService()
stability_pull_api_service = StabilityPullAPIService()
