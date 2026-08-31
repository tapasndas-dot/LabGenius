from uuid import UUID

from datetime import datetime

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models.business.sample_test_assignment import SampleTestAssignment


class SampleTestAssignmentRepository:
    """
    Repository for SampleTestAssignment operational history.
    """

    def get_active(
        self, db: Session, sample_test_id: UUID, *, for_update: bool = False
    ) -> SampleTestAssignment | None:
        """Get the currently active assignment for a SampleTest, if any."""
        query = db.query(SampleTestAssignment).filter(
            SampleTestAssignment.sample_test_id == sample_test_id,
            SampleTestAssignment.is_active.is_(True)
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def list_history(self, db: Session, sample_test_id: UUID) -> list[SampleTestAssignment]:
        """Get all assignments for a SampleTest in reverse chronological order."""
        return db.query(SampleTestAssignment).filter(
            SampleTestAssignment.sample_test_id == sample_test_id
        ).order_by(
            SampleTestAssignment.assigned_at,
            SampleTestAssignment.id,
        ).all()

    def create(self, db: Session, sample_test_id: UUID, assigned_user_id: UUID,
               assigned_by_user_id: UUID | None, assigned_at: datetime,
               notes: str | None = None) -> SampleTestAssignment:
        """Create a new assignment record."""
        record = SampleTestAssignment(
            sample_test_id=sample_test_id,
            assigned_user_id=assigned_user_id,
            assigned_by_user_id=assigned_by_user_id,
            assigned_at=assigned_at,
            is_active=True,
            notes=notes
        )
        db.add(record)
        db.flush()
        return record

    def deactivate_expected(
        self, db: Session, assignment_id: UUID, expected_version: int,
        unassigned_at: datetime, unassigned_by_user_id: UUID | None = None,
    ) -> SampleTestAssignment | None:
        """Deactivate only the active assignment at the caller's expected version."""
        updated_id = db.execute(
            update(SampleTestAssignment).where(
                SampleTestAssignment.id == assignment_id,
                SampleTestAssignment.is_active.is_(True),
                SampleTestAssignment.version == expected_version,
            ).values(
                is_active=False,
                unassigned_at=unassigned_at,
                unassigned_by_user_id=unassigned_by_user_id,
                version=SampleTestAssignment.version + 1,
                updated_at=func.now(),
            ).returning(SampleTestAssignment.id)
        ).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(SampleTestAssignment, updated_id)
