from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException
from app.models.business.stability import (
    StabilityProtocolCondition, StabilityProtocolTimepoint, StabilityProtocolVersion,
    StabilityStudyCondition,
)
from app.repositories.business.stability_repository import (
    StabilityProtocolConditionRepository, StabilityProtocolRepository,
    StabilityProtocolTimepointRepository, StabilityProtocolVersionRepository,
    StabilityStudyConditionRepository, StabilityStudyRepository,
)
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


stability_protocol_api_service = StabilityProtocolAPIService()
stability_protocol_tree_api_service = StabilityProtocolTreeAPIService(stability_protocol_api_service)
stability_study_api_service = StabilityStudyAPIService()
