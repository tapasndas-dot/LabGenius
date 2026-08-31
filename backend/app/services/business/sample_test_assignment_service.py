from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business.sample import Sample, SampleTest, SampleTestStatus
from app.models.user.user import User
from app.repositories.business.sample_repository import SampleRepository, SampleTestRepository
from app.repositories.business.sample_test_assignment_repository import SampleTestAssignmentRepository


class SampleTestAssignmentService:
    """
    Service for managing SampleTest assignments.
    
    Assignment history is preserved and queryable.
    At most one active assignment per SampleTest at a time.
    """

    def __init__(self, repository=None, sample_repository=None, sample_test_repository=None):
        self.repository = repository or SampleTestAssignmentRepository()
        self.sample_repository = sample_repository or SampleRepository()
        self.sample_test_repository = sample_test_repository or SampleTestRepository()

    def _validate_assignable_state(self, db: Session, sample_test: SampleTest) -> None:
        """Check whether a SampleTest is eligible for assignment."""
        if sample_test.status not in (SampleTestStatus.PENDING, SampleTestStatus.ASSIGNED):
            raise ValidationException(f"Cannot assign SampleTest with status {sample_test.status}.")
        
        sample = db.get(Sample, sample_test.sample_id)
        if sample is None:
            raise ResourceNotFoundException("Parent Sample not found.")
        if sample.status in ("CANCELLED", "FINALIZED"):
            raise ValidationException(f"Cannot assign SampleTest: parent Sample is {sample.status}.")

    def _validate_target_user(self, db: Session, organization_id: UUID, target_user_id: UUID) -> User:
        """Validate that the target user exists, is active, and belongs to the organization."""
        user = db.get(User, target_user_id)
        if user is None:
            raise ResourceNotFoundException("Target user not found.")
        if user.organization_id != organization_id:
            raise ValidationException("Target user must belong to the same organization.")
        if not user.is_active:
            raise ValidationException("Target user is not active.")
        return user

    def _get_owned_test_for_update(
        self, db: Session, organization_id: UUID, sample_test_id: UUID
    ) -> tuple[SampleTest, Sample]:
        sample_test = db.query(SampleTest).filter(
            SampleTest.id == sample_test_id
        ).with_for_update().first()
        if sample_test is None:
            raise ResourceNotFoundException("SampleTest not found.")
        sample = db.get(Sample, sample_test.sample_id)
        if sample is None or sample.organization_id != organization_id:
            raise ResourceNotFoundException("SampleTest not found in this organization.")
        return sample_test, sample

    def assign(self, db: Session, organization_id: UUID, sample_test_id: UUID, 
               target_user_id: UUID, assigned_by_user_id: UUID | None = None,
               notes: str | None = None,
               expected_sample_test_version: int | None = None):
        """
        Assign a SampleTest to a user.
        
        Initial assignment transitions PENDING -> ASSIGNED.
        Subsequent assignments through reassign().
        """
        sample_test, _ = self._get_owned_test_for_update(db, organization_id, sample_test_id)
        if (
            expected_sample_test_version is not None
            and sample_test.version != expected_sample_test_version
        ):
            raise VersionConflictException("SampleTest has changed. Refresh and try again.")
        self._validate_assignable_state(db, sample_test)
        if sample_test.status != SampleTestStatus.PENDING:
            raise ValidationException("Only a PENDING SampleTest may be initially assigned.")
        self._validate_target_user(db, organization_id, target_user_id)

        # Check for existing active assignment
        existing = self.repository.get_active(db, sample_test_id)
        if existing is not None:
            raise VersionConflictException("SampleTest already has an active assignment.")

        # Create active assignment
        now = datetime.now(timezone.utc)
        assignment = self.repository.create(
            db, sample_test_id, target_user_id, assigned_by_user_id, now, notes
        )

        # Transition SampleTest to ASSIGNED if currently PENDING
        if sample_test.status == SampleTestStatus.PENDING:
            sample_test.status = SampleTestStatus.ASSIGNED
            sample_test.version = (sample_test.version or 0) + 1
            db.flush()

        return assignment

    def reassign(self, db: Session, organization_id: UUID, sample_test_id: UUID,
                 target_user_id: UUID, expected_assignment_version: int,
                 assigned_by_user_id: UUID | None = None,
                 notes: str | None = None,
                 expected_sample_test_version: int | None = None):
        """
        Reassign a SampleTest to a different user.
        
        Deactivates current assignment, creates new active assignment.
        Atomic operation: both succeed or both fail.
        SampleTest remains ASSIGNED.
        """
        sample_test, _ = self._get_owned_test_for_update(db, organization_id, sample_test_id)
        if (
            expected_sample_test_version is not None
            and sample_test.version != expected_sample_test_version
        ):
            raise VersionConflictException("SampleTest has changed. Refresh and try again.")
        self._validate_assignable_state(db, sample_test)
        if sample_test.status != SampleTestStatus.ASSIGNED:
            raise ValidationException("Only an ASSIGNED SampleTest may be reassigned.")
        self._validate_target_user(db, organization_id, target_user_id)

        # Get current active assignment
        current = self.repository.get_active(db, sample_test_id, for_update=True)
        if current is None:
            raise VersionConflictException("SampleTest has no active assignment to replace.")
        if current.version != expected_assignment_version:
            raise VersionConflictException("SampleTest assignment has changed. Refresh and try again.")

        # Atomic: deactivate old, create new
        now = datetime.now(timezone.utc)
        if self.repository.deactivate_expected(
            db, current.id, expected_assignment_version, now, assigned_by_user_id
        ) is None:
            raise VersionConflictException("SampleTest assignment has changed. Refresh and try again.")
        assignment = self.repository.create(
            db, sample_test_id, target_user_id, assigned_by_user_id, now, notes
        )

        # SampleTest remains ASSIGNED
        return assignment

    def unassign(self, db: Session, organization_id: UUID, sample_test_id: UUID,
                 expected_assignment_version: int,
                 unassigned_by_user_id: UUID | None = None,
                 expected_sample_test_version: int | None = None):
        """
        Unassign a SampleTest.
        
        Deactivates active assignment.
        SampleTest returns to PENDING.
        """
        sample_test, _ = self._get_owned_test_for_update(db, organization_id, sample_test_id)
        if (
            expected_sample_test_version is not None
            and sample_test.version != expected_sample_test_version
        ):
            raise VersionConflictException("SampleTest has changed. Refresh and try again.")
        self._validate_assignable_state(db, sample_test)
        if sample_test.status != SampleTestStatus.ASSIGNED:
            raise ValidationException("Only an ASSIGNED SampleTest may be unassigned.")

        # Get current active assignment
        current = self.repository.get_active(db, sample_test_id, for_update=True)
        if current is None:
            raise VersionConflictException("SampleTest has no active assignment.")
        if current.version != expected_assignment_version:
            raise VersionConflictException("SampleTest assignment has changed. Refresh and try again.")

        # Deactivate
        now = datetime.now(timezone.utc)
        deactivated = self.repository.deactivate_expected(
            db, current.id, expected_assignment_version, now, unassigned_by_user_id
        )
        if deactivated is None:
            raise VersionConflictException("SampleTest assignment has changed. Refresh and try again.")

        # Return to PENDING
        sample_test.status = SampleTestStatus.PENDING
        sample_test.version = (sample_test.version or 0) + 1
        db.flush()

        return deactivated

    def get_active_assignment(self, db: Session, sample_test_id: UUID):
        """Get the active assignment for a SampleTest."""
        return self.repository.get_active(db, sample_test_id)

    def list_assignment_history(self, db: Session, sample_test_id: UUID):
        """Get all assignments for a SampleTest."""
        return self.repository.list_history(db, sample_test_id)
