"""Permission-aware read service for QC operational dashboard projections."""

from fastapi import HTTPException

from app.auth.dependencies import get_effective_permission_codes
from app.models.business.sample import Sample, SampleTest
from app.repositories.business.qc_dashboard_repository import QCDashboardRepository
from app.services.organization_scope_service import OrganizationScopeService


class QCDashboardService:
    def __init__(self):
        self.repository = QCDashboardRepository()
        self.scope = OrganizationScopeService()

    def _tests(self, db, actor, permission):
        return self.scope.filter_sample_tests(db.query(SampleTest), actor, permission)

    @staticmethod
    def _reference(row, prefix):
        return {"id": getattr(row, f"{prefix}_id"),
                "code": getattr(row, f"{prefix}_code"),
                "name": getattr(row, f"{prefix}_name")}

    def summary(self, db, actor):
        permissions = set(get_effective_permission_codes(actor))
        samples = self.scope.filter_samples(db.query(Sample), actor, "sample.view")
        tests = self._tests(db, actor, "sample.view")
        return {
            "active_samples": self.repository.count_samples(samples.filter(
                Sample.status.notin_(("CANCELLED", "FINALIZED"))
            )),
            "pending_tests": self.repository.count_tests(tests.filter(
                SampleTest.status == "PENDING"
            )),
            "assigned_or_in_progress_tests": self.repository.count_tests(tests.filter(
                SampleTest.status.in_(("ASSIGNED", "IN_PROGRESS"))
            )),
            "awaiting_review": self.repository.count_result_stage(
                self._tests(db, actor, "sample_test_result.review"),
                "RESULT_ENTERED", "ENTERED",
            ) if "sample_test_result.review" in permissions else 0,
            "awaiting_finalization": self.repository.count_result_stage(
                self._tests(db, actor, "sample_test_result.finalize"),
                "REVIEWED", "REVIEWED",
            ) if "sample_test_result.finalize" in permissions else 0,
            "finalized_tests": self.repository.count_tests(tests.filter(
                SampleTest.status == "FINALIZED"
            )),
        }

    def work_queue(self, db, actor, **filters):
        rows = self.repository.work_queue(
            self._tests(db, actor, "sample.view"), **filters
        )
        return [self._work_row(row) for row in rows]

    def _work_row(self, row):
        method = None if row.method_version_id is None else {
            "id": row.method_version_id, "code": row.method_code,
            "name": row.method_name, "version_number": row.version_number,
        }
        assignment = None if row.assignment_id is None else {
            "assignment_id": row.assignment_id,
            "assigned_user_id": row.assigned_user_id,
            "assigned_user_display_name": row.assigned_user_display_name,
            "assigned_at": row.assigned_at,
        }
        result = None if row.result_id is None else {
            "result_id": row.result_id, "status": row.result_status,
            "sequence_number": row.sequence_number, "entered_at": row.entered_at,
            "reviewed_at": row.reviewed_at, "finalized_at": row.finalized_at,
        }
        return {
            "sample_id": row.sample_id, "sample_number": row.sample_number,
            "sample_status": row.sample_status, "sample_test_id": row.sample_test_id,
            "sample_test_status": row.sample_test_status, "priority": row.priority,
            "due_at": row.due_at, "material": self._reference(row, "material"),
            "test": self._reference(row, "test"), "method_version": method,
            "active_assignment": assignment, "result": result,
        }

    def review_queue(self, db, actor):
        permissions = set(get_effective_permission_codes(actor))
        stages = []
        for stage, permission in (
            ("REVIEW", "sample_test_result.review"),
            ("FINALIZE", "sample_test_result.finalize"),
        ):
            if permission not in permissions:
                continue
            rows = self.repository.review_queue(
                self._tests(db, actor, permission), stage=stage
            )
            stages.extend(self._review_row(row, stage) for row in rows)
        if not stages and not permissions.intersection({
            "sample_test_result.review", "sample_test_result.finalize"
        }):
            raise HTTPException(status_code=403, detail="Result workflow permission is required.")
        return sorted(stages, key=lambda row: (
            row["due_at"] is None,
            row["due_at"].isoformat() if row["due_at"] is not None else "",
            row["sample_number"], str(row["sample_test_id"]), row["queue_stage"],
        ))

    def _review_row(self, row, stage):
        method = None if row.method_version_id is None else {
            "id": row.method_version_id, "code": row.method_code,
            "name": row.method_name, "version_number": row.version_number,
        }
        return {
            "queue_stage": stage, "sample_id": row.sample_id,
            "sample_number": row.sample_number, "sample_test_id": row.sample_test_id,
            "sample_test_status": row.sample_test_status, "result_id": row.result_id,
            "result_status": row.result_status, "result_version": row.result_version,
            "test": self._reference(row, "test"), "method_version": method,
            "assigned_user_display_name": row.assigned_user_display_name,
            "entered_at": row.entered_at,
            "entered_by_display_name": row.entered_by_display_name,
            "reviewed_at": row.reviewed_at,
            "reviewed_by_display_name": row.reviewed_by_display_name,
            "due_at": row.due_at, "priority": row.priority,
        }

    def recent_activity(self, db, actor, limit):
        return [dict(row) for row in self.repository.recent_activity(
            db, self._tests(db, actor, "sample.view"), limit
        )]


qc_dashboard_service = QCDashboardService()
