"""SQL projections and aggregates for the QC operational dashboard."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, literal, select, union_all
from sqlalchemy.orm import Session, aliased

from app.models.business.material import Material
from app.models.business.qc_method import Method, MethodVersion, Test
from app.models.business.sample import Sample, SampleTest
from app.models.business.sample_test_assignment import SampleTestAssignment
from app.models.business.sample_test_result import SampleTestResult
from app.models.user.user import User


class QCDashboardRepository:
    @staticmethod
    def count_samples(query) -> int:
        return query.with_entities(func.count(Sample.id)).scalar() or 0

    @staticmethod
    def count_tests(query) -> int:
        return query.with_entities(func.count(SampleTest.id)).scalar() or 0

    @staticmethod
    def count_result_stage(query, sample_test_status: str,
                           result_status: str) -> int:
        return query.join(
            SampleTestResult, SampleTestResult.sample_test_id == SampleTest.id
        ).filter(
            SampleTest.status == sample_test_status,
            SampleTestResult.status == result_status,
        ).with_entities(func.count(SampleTestResult.id)).scalar() or 0

    @staticmethod
    def _filtered(query, *, business_unit_id=None, division_id=None,
                  department_id=None, sample_status=None,
                  sample_test_status=None, assigned_user_id=None,
                  due_from=None, due_to=None):
        query = query.join(Sample, SampleTest.sample_id == Sample.id)
        if business_unit_id is not None:
            query = query.filter(Sample.business_unit_id == business_unit_id)
        if division_id is not None:
            query = query.filter(Sample.division_id == division_id)
        if department_id is not None:
            query = query.filter(Sample.department_id == department_id)
        if sample_status is not None:
            query = query.filter(Sample.status == sample_status)
        if sample_test_status is not None:
            query = query.filter(SampleTest.status == sample_test_status)
        if assigned_user_id is not None:
            query = query.filter(SampleTest.assignments.any(
                and_(SampleTestAssignment.is_active.is_(True),
                     SampleTestAssignment.assigned_user_id == assigned_user_id),
            ))
        if due_from is not None:
            query = query.filter(Sample.due_at >= due_from)
        if due_to is not None:
            query = query.filter(Sample.due_at <= due_to)
        return query

    def work_queue(self, query, **filters):
        assignment = aliased(SampleTestAssignment)
        assignee = aliased(User)
        result = aliased(SampleTestResult)
        query = self._filtered(query, **filters)
        return query.join(Material, Material.id == Sample.material_id).join(
            Test, Test.id == SampleTest.test_id
        ).outerjoin(
            MethodVersion, MethodVersion.id == SampleTest.method_version_id
        ).outerjoin(Method, Method.id == MethodVersion.method_id).outerjoin(
            assignment,
            (assignment.sample_test_id == SampleTest.id)
            & assignment.is_active.is_(True),
        ).outerjoin(assignee, assignee.id == assignment.assigned_user_id).outerjoin(
            result, result.sample_test_id == SampleTest.id
        ).with_entities(
            Sample.id.label("sample_id"), Sample.sample_number,
            Sample.status.label("sample_status"), SampleTest.id.label("sample_test_id"),
            SampleTest.status.label("sample_test_status"), Sample.priority, Sample.due_at,
            Material.id.label("material_id"), Material.code.label("material_code"),
            Material.name.label("material_name"), Test.id.label("test_id"),
            Test.test_code, Test.test_name, MethodVersion.id.label("method_version_id"),
            Method.method_code, Method.method_name, MethodVersion.version_number,
            assignment.id.label("assignment_id"), assignment.assigned_user_id,
            assignee.display_name.label("assigned_user_display_name"), assignment.assigned_at,
            result.id.label("result_id"), result.status.label("result_status"),
            result.sequence_number, result.entered_at, result.reviewed_at, result.finalized_at,
        ).order_by(
            Sample.due_at.asc().nullslast(), Sample.sample_number, SampleTest.id
        ).all()

    def review_queue(self, query, *, stage: str):
        assignment = aliased(SampleTestAssignment)
        assignee = aliased(User)
        entered_by = aliased(User)
        reviewed_by = aliased(User)
        test_status = "RESULT_ENTERED" if stage == "REVIEW" else "REVIEWED"
        return query.join(Sample, SampleTest.sample_id == Sample.id).join(
            SampleTestResult, SampleTestResult.sample_test_id == SampleTest.id
        ).join(Test, Test.id == SampleTest.test_id).outerjoin(
            MethodVersion, MethodVersion.id == SampleTest.method_version_id
        ).outerjoin(Method, Method.id == MethodVersion.method_id).outerjoin(
            assignment,
            (assignment.sample_test_id == SampleTest.id)
            & assignment.is_active.is_(True),
        ).outerjoin(assignee, assignee.id == assignment.assigned_user_id).outerjoin(
            entered_by, entered_by.id == SampleTestResult.entered_by_user_id
        ).outerjoin(
            reviewed_by, reviewed_by.id == SampleTestResult.reviewed_by_user_id
        ).filter(
            SampleTest.status == test_status,
            SampleTestResult.status == ("ENTERED" if stage == "REVIEW" else "REVIEWED"),
        ).with_entities(
            Sample.id.label("sample_id"), Sample.sample_number,
            SampleTest.id.label("sample_test_id"),
            SampleTest.status.label("sample_test_status"),
            SampleTestResult.id.label("result_id"),
            SampleTestResult.status.label("result_status"),
            SampleTestResult.version.label("result_version"),
            Test.id.label("test_id"), Test.test_code, Test.test_name,
            MethodVersion.id.label("method_version_id"), Method.method_code,
            Method.method_name, MethodVersion.version_number,
            assignee.display_name.label("assigned_user_display_name"),
            SampleTestResult.entered_at,
            entered_by.display_name.label("entered_by_display_name"),
            SampleTestResult.reviewed_at,
            reviewed_by.display_name.label("reviewed_by_display_name"),
            Sample.due_at, Sample.priority,
        ).order_by(Sample.due_at.asc().nullslast(), Sample.sample_number,
                   SampleTest.id, SampleTestResult.id).all()

    @staticmethod
    def recent_activity(db: Session, query, limit: int):
        visible = query.with_entities(SampleTest.id).subquery()

        def activity(timestamp_column, actor_column, activity_type):
            actor = aliased(User)
            return select(
                timestamp_column.label("occurred_at"),
                Sample.id.label("sample_id"), Sample.sample_number,
                SampleTest.id.label("sample_test_id"),
                SampleTestResult.id.label("result_id"), Test.id.label("test_id"),
                Test.test_code, Test.test_name,
                actor.display_name.label("actor_display_name"),
                literal(activity_type).label("activity_type"),
            ).select_from(visible).join(
                SampleTest, SampleTest.id == visible.c.id
            ).join(Sample, Sample.id == SampleTest.sample_id).join(
                SampleTestResult, SampleTestResult.sample_test_id == SampleTest.id
            ).join(Test, Test.id == SampleTest.test_id).outerjoin(
                actor, actor.id == actor_column
            ).where(timestamp_column.is_not(None))

        combined = union_all(
            activity(SampleTestResult.entered_at,
                     SampleTestResult.entered_by_user_id, "SUBMITTED"),
            activity(SampleTestResult.reviewed_at,
                     SampleTestResult.reviewed_by_user_id, "REVIEWED"),
            activity(SampleTestResult.finalized_at,
                     SampleTestResult.finalized_by_user_id, "FINALIZED"),
        ).subquery()
        return db.execute(select(combined).order_by(
            combined.c.occurred_at.desc(), combined.c.result_id,
            combined.c.activity_type,
        ).limit(limit)).mappings().all()
