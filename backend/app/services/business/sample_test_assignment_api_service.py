from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, VersionConflictException
from app.models.business.sample import Sample, SampleTest
from app.services.audit_service import AuditAction, AuditService
from app.services.organization_scope_service import AccessScope, OrganizationScopeService
from .sample_service import SampleService, SampleTestService
from .sample_test_assignment_service import SampleTestAssignmentService


class SampleTestAssignmentAPIService:
    """Secured transaction boundary for SampleTest assignment operations."""

    def __init__(self):
        self.samples = SampleService()
        self.sample_tests = SampleTestService(self.samples.repository)
        self.assignments = SampleTestAssignmentService(
            sample_repository=self.samples.repository,
            sample_test_repository=self.sample_tests.repository,
        )
        self.scope = OrganizationScopeService()
        self.audit = AuditService()

    def _read_test(
        self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
        permission: str = "sample.view",
    ) -> tuple[Sample, SampleTest]:
        sample = self.samples.scoped_query(db, actor, permission).filter(
            Sample.id == sample_id
        ).first()
        if sample is None:
            raise ResourceNotFoundException("Sample not found.")
        test = self.scope.filter_sample_tests(
            self.sample_tests.repository.query(db), actor, permission
        ).filter(
            SampleTest.sample_id == sample.id,
            SampleTest.id == sample_test_id,
        ).first()
        if test is None:
            raise ResourceNotFoundException("Sample Test not found.")
        return sample, test

    def _mutation_test(
        self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
    ) -> tuple[Sample, SampleTest]:
        # SELF is operational access, never assignment-management authority.
        if self.scope.resolve_scope(actor, "sample.assign") == AccessScope.SELF:
            raise ResourceNotFoundException("Sample not found.")
        sample = self.samples.repository.get(db, actor.organization_id, sample_id)
        if sample is None or not self.scope.can_place_sample(
            db, actor, "sample.assign", {
                "business_unit_id": sample.business_unit_id,
                "division_id": sample.division_id,
                "department_id": sample.department_id,
            },
        ):
            raise ResourceNotFoundException("Sample not found.")
        test = self.sample_tests.repository.get_for_sample(db, sample.id, sample_test_id)
        if test is None:
            raise ResourceNotFoundException("Sample Test not found.")
        return sample, test

    @staticmethod
    def _response(test: SampleTest, assignment):
        return {"sample_test": test, "assignment": assignment}

    @staticmethod
    def _audit_context(sample: Sample, test: SampleTest, assignment) -> dict:
        return {
            "sample_id": sample.id,
            "sample_number": sample.sample_number,
            "sample_test_id": test.id,
            "assignment_id": assignment.id,
            "assigned_user_id": assignment.assigned_user_id,
            "assignment_version": assignment.version,
        }

    def assign(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID, values: dict):
        sample, test = self._mutation_test(db, actor, sample_id, sample_test_id)
        try:
            assignment = self.assignments.assign(
                db, actor.organization_id, test.id, values["assigned_user_id"],
                actor.id, values.get("notes"), values["expected_sample_test_version"],
            )
            self.audit.record_action(
                db, action=AuditAction.ASSIGN,
                entity_type=type(assignment).__name__, entity_id=assignment.id,
                actor=actor, owner=sample,
                changes={"assigned": self._audit_context(sample, test, assignment)},
            )
            db.commit(); db.refresh(test); db.refresh(assignment)
            return self._response(test, assignment)
        except IntegrityError as exc:
            db.rollback()
            raise VersionConflictException(
                "SampleTest assignment changed concurrently. Refresh and try again."
            ) from exc
        except Exception:
            db.rollback(); raise

    def reassign(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID, values: dict):
        sample, test = self._mutation_test(db, actor, sample_id, sample_test_id)
        current = self.assignments.get_active_assignment(db, test.id)
        if current is None:
            raise VersionConflictException("SampleTest has no active assignment to replace.")
        old_context = self._audit_context(sample, test, current)
        try:
            assignment = self.assignments.reassign(
                db, actor.organization_id, test.id, values["assigned_user_id"],
                values["expected_assignment_version"], actor.id, values.get("notes"),
                values["expected_sample_test_version"],
            )
            self.audit.record_action(
                db, action=AuditAction.UNASSIGN,
                entity_type=type(current).__name__, entity_id=current.id,
                actor=actor, owner=sample,
                changes={"unassigned": old_context},
            )
            self.audit.record_action(
                db, action=AuditAction.ASSIGN,
                entity_type=type(assignment).__name__, entity_id=assignment.id,
                actor=actor, owner=sample,
                changes={
                    "assigned": self._audit_context(sample, test, assignment),
                    "previous_assigned_user_id": current.assigned_user_id,
                },
            )
            db.commit(); db.refresh(test); db.refresh(assignment)
            return self._response(test, assignment)
        except IntegrityError as exc:
            db.rollback()
            raise VersionConflictException(
                "SampleTest assignment changed concurrently. Refresh and try again."
            ) from exc
        except Exception:
            db.rollback(); raise

    def unassign(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID, values: dict):
        sample, test = self._mutation_test(db, actor, sample_id, sample_test_id)
        current = self.assignments.get_active_assignment(db, test.id)
        if current is None:
            raise VersionConflictException("SampleTest has no active assignment.")
        old_context = self._audit_context(sample, test, current)
        try:
            ended = self.assignments.unassign(
                db, actor.organization_id, test.id,
                values["expected_assignment_version"], actor.id,
                values["expected_sample_test_version"],
            )
            self.audit.record_action(
                db, action=AuditAction.UNASSIGN,
                entity_type=type(ended).__name__, entity_id=ended.id,
                actor=actor, owner=sample,
                changes={"unassigned": old_context},
            )
            db.commit(); db.refresh(test)
            return self._response(test, None)
        except Exception:
            db.rollback(); raise

    def current(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID):
        _, test = self._read_test(db, actor, sample_id, sample_test_id)
        assignment = self.assignments.get_active_assignment(db, test.id)
        if assignment is None:
            raise ResourceNotFoundException("Active Sample Test assignment not found.")
        return assignment

    def history(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID):
        _, test = self._read_test(db, actor, sample_id, sample_test_id)
        return self.assignments.list_assignment_history(db, test.id)


sample_test_assignment_api_service = SampleTestAssignmentAPIService()
