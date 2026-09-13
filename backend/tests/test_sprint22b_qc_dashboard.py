"""Focused Sprint 22B QC operational dashboard query and security tests."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.dependencies.database import get_db
from app.main import app
from app.models.business.qc_method import Test as QCTest
from app.models.business.sample import SampleTest
from app.models.business.sample_test_assignment import SampleTestAssignment
from app.models.business.sample_test_result import SampleTestResult
from app.services.business.qc_dashboard_service import QCDashboardService
from tests import test_sprint21b_result_api as sprint21b_support


class Sprint22BQCDashboardTests(unittest.TestCase):
    tearDown = sprint21b_support.Sprint21BResultAPITests.tearDown
    _basis = sprint21b_support.Sprint21BResultAPITests._basis
    _user = sprint21b_support.Sprint21BResultAPITests._user
    actor = sprint21b_support.Sprint21BResultAPITests.actor

    def setUp(self):
        session_factory = lambda bind: Session(
            bind=bind, join_transaction_mode="create_savepoint"
        )
        fixture = sprint21b_support.sample_test_support
        with patch.object(fixture, "Session", session_factory):
            sprint21b_support.Sprint21BResultAPITests.setUp(self)
        self.dashboard = QCDashboardService()
        self.specification_version_id = self.sample.specification_version_id

    def new_test(self, *, owner=None, test_status="PENDING",
                 sample_status="REGISTERED", due_at=None, priority="NORMAL"):
        owner = owner or self.user_a
        sample = self.samples.create(self.db, self.org.id, {
            "sample_number": f"DASH-{uuid4().hex[:8]}",
            "material_id": self.material.id,
            "specification_version_id": self.specification_version_id,
            "due_at": due_at, "priority": priority,
        })
        sample.business_unit_id = owner.business_unit_id
        sample.division_id = owner.division_id
        sample.department_id = owner.department_id
        sample.status = sample_status
        test = self.sample_tests.generate(self.db, self.org.id, sample.id)[0]
        test.status = test_status
        self.db.flush()
        return sample, test

    def add_result(self, test, status, *, entered_at=None, reviewed_at=None,
                   finalized_at=None, actor=None):
        actor = actor or self.user_a
        result = SampleTestResult(
            sample_test_id=test.id, sequence_number=1, status=status,
            entered_at=entered_at,
            entered_by_user_id=actor.id if entered_at else None,
            reviewed_at=reviewed_at,
            reviewed_by_user_id=actor.id if reviewed_at else None,
            finalized_at=finalized_at,
            finalized_by_user_id=actor.id if finalized_at else None,
        )
        self.db.add(result); self.db.flush()
        return result

    def assign(self, test, user=None, active=True):
        row = SampleTestAssignment(
            sample_test_id=test.id, assigned_user_id=(user or self.user_a).id,
            assigned_at=datetime.now(timezone.utc), is_active=active,
        )
        self.db.add(row); self.db.flush()
        return row

    def test_summary_classifies_only_scoped_current_operational_state(self):
        self.sample.status = "CANCELLED"
        self.sample_test.status = "CANCELLED"
        self.new_test(test_status="PENDING")
        self.new_test(test_status="ASSIGNED")
        self.new_test(test_status="IN_PROGRESS")
        self.new_test(test_status="FINALIZED", sample_status="FINALIZED")
        _, review_test = self.new_test(test_status="RESULT_ENTERED")
        self.add_result(review_test, "ENTERED")
        _, mismatched = self.new_test(test_status="RESULT_ENTERED")
        self.add_result(mismatched, "DRAFT")
        _, finalize_test = self.new_test(test_status="REVIEWED")
        self.add_result(finalize_test, "REVIEWED")

        actor = self.actor(
            "sample.view", extras=(("sample_test_result.review", "ORGANIZATION"),
                                   ("sample_test_result.finalize", "ORGANIZATION")),
        )
        summary = self.dashboard.summary(self.db, actor)
        self.assertEqual(summary, {
            "active_samples": 6, "pending_tests": 1,
            "assigned_or_in_progress_tests": 2, "awaiting_review": 1,
            "awaiting_finalization": 1, "finalized_tests": 1,
        })
        no_workflow = self.dashboard.summary(self.db, self.actor("sample.view"))
        self.assertEqual((no_workflow["awaiting_review"],
                          no_workflow["awaiting_finalization"]), (0, 0))

    def test_work_queue_context_filters_and_stable_order(self):
        now = datetime.now(timezone.utc)
        first_sample, first = self.new_test(
            test_status="ASSIGNED", due_at=now, priority="HIGH"
        )
        second_sample, second = self.new_test(
            test_status="IN_PROGRESS", due_at=now + timedelta(days=1)
        )
        assignment = self.assign(first)
        result = self.add_result(first, "DRAFT")
        actor = self.actor("sample.view")
        rows = self.dashboard.work_queue(self.db, actor)
        ids = [row["sample_test_id"] for row in rows]
        self.assertLess(ids.index(first.id), ids.index(second.id))
        row = next(item for item in rows if item["sample_test_id"] == first.id)
        self.assertEqual(row["material"]["id"], self.material.id)
        self.assertEqual(row["test"]["id"], first.test_id)
        self.assertEqual(row["method_version"]["id"], first.method_version_id)
        self.assertEqual(row["active_assignment"]["assignment_id"], assignment.id)
        self.assertEqual(row["result"]["result_id"], result.id)
        filtered = self.dashboard.work_queue(
            self.db, actor, assigned_user_id=self.user_a.id,
            business_unit_id=self.user_a.business_unit_id,
            division_id=self.user_a.division_id,
            department_id=self.user_a.department_id,
            sample_status=first_sample.status, sample_test_status=first.status,
            due_from=now - timedelta(minutes=1), due_to=now + timedelta(minutes=1),
        )
        self.assertEqual([item["sample_test_id"] for item in filtered], [first.id])
        outside = self.dashboard.work_queue(
            self.db, self.actor("sample.view", "DEPARTMENT", user=self.user_b),
            business_unit_id=self.user_a.business_unit_id,
        )
        self.assertEqual(outside, [])

    def test_hierarchy_self_history_reassignment_and_cross_org_scope(self):
        _, owned = self.new_test(owner=self.user_a, test_status="ASSIGNED")
        _, other = self.new_test(owner=self.user_b, test_status="ASSIGNED")
        for scope in ("ORGANIZATION", "BUSINESS_UNIT", "DIVISION", "DEPARTMENT"):
            rows = self.dashboard.work_queue(
                self.db, self.actor("sample.view", scope),
            )
            self.assertIn(owned.id, {row["sample_test_id"] for row in rows})
            if scope != "ORGANIZATION":
                self.assertNotIn(other.id, {row["sample_test_id"] for row in rows})
        department_rows = self.dashboard.work_queue(
            self.db, self.actor("sample.view", "DEPARTMENT")
        )
        self.assertNotIn(other.id, {row["sample_test_id"] for row in department_rows})

        historical = self.assign(owned, active=False)
        self_actor = self.actor("sample.view", "SELF")
        self.assertEqual(self.dashboard.work_queue(self.db, self_actor), [])
        historical.is_active = True; self.db.flush()
        self.assertEqual(
            {row["sample_test_id"] for row in self.dashboard.work_queue(self.db, self_actor)},
            {owned.id},
        )
        historical.is_active = False
        self.assign(owned, self.user_b, active=True); self.db.flush()
        self.assertEqual(self.dashboard.work_queue(self.db, self_actor), [])
        other_version = self._basis(self.other_org, self.other_material)[0]
        other_sample = self.samples.create(self.db, self.other_org.id, {
            "sample_number": f"CROSS-{uuid4().hex[:8]}",
            "material_id": self.other_material.id,
            "specification_version_id": other_version.id,
        })
        other_org_test = self.sample_tests.generate(
            self.db, self.other_org.id, other_sample.id
        )[0]
        visible_ids = {row["sample_test_id"] for row in self.dashboard.work_queue(
            self.db, self.actor("sample.view", user=self.user_a)
        )}
        self.assertNotIn(other_org_test.id, visible_ids)

    def test_review_queue_composes_exact_permissions_and_scope(self):
        now = datetime.now(timezone.utc)
        _, review_test = self.new_test(test_status="RESULT_ENTERED")
        review_result = self.add_result(review_test, "ENTERED", entered_at=now)
        self.assign(review_test)
        _, final_test = self.new_test(test_status="REVIEWED")
        final_result = self.add_result(
            final_test, "REVIEWED", entered_at=now - timedelta(hours=1),
            reviewed_at=now,
        )
        self.assign(final_test)
        review_rows = self.dashboard.review_queue(
            self.db, self.actor("sample_test_result.review")
        )
        self.assertEqual([(row["queue_stage"], row["result_id"]) for row in review_rows],
                         [("REVIEW", review_result.id)])
        final_rows = self.dashboard.review_queue(
            self.db, self.actor("sample_test_result.finalize")
        )
        self.assertEqual([(row["queue_stage"], row["result_id"]) for row in final_rows],
                         [("FINALIZE", final_result.id)])
        both = self.actor(
            "sample_test_result.review",
            extras=(("sample_test_result.finalize", "ORGANIZATION"),),
        )
        self.assertEqual({row["queue_stage"] for row in self.dashboard.review_queue(self.db, both)},
                         {"REVIEW", "FINALIZE"})
        with self.assertRaises(Exception) as denied:
            self.dashboard.review_queue(self.db, self.actor("sample.view"))
        self.assertEqual(denied.exception.status_code, 403)

    def test_review_queue_self_is_active_assignment_derived_not_result_actor(self):
        now = datetime.now(timezone.utc)
        _, test = self.new_test(test_status="RESULT_ENTERED")
        self.add_result(test, "ENTERED", entered_at=now, actor=self.user_a)
        actor = self.actor("sample_test_result.review", "SELF")
        # No active assignment: result actor identity grants nothing.
        self.assertEqual(self.dashboard.review_queue(self.db, actor), [])
        assignment = self.assign(test)
        self.assertEqual(len(self.dashboard.review_queue(self.db, actor)), 1)
        assignment.is_active = False; self.db.flush()
        self.assertEqual(self.dashboard.review_queue(self.db, actor), [])

    def test_recent_activity_maps_timestamps_limit_and_self_scope(self):
        now = datetime.now(timezone.utc)
        _, test = self.new_test(test_status="FINALIZED")
        result = self.add_result(
            test, "FINALIZED", entered_at=now - timedelta(hours=2),
            reviewed_at=now - timedelta(hours=1), finalized_at=now,
        )
        self.assign(test)
        activities = self.dashboard.recent_activity(
            self.db, self.actor("sample.view"), 2
        )
        qc_test = self.db.get(QCTest, test.test_id)
        self.assertEqual([row["activity_type"] for row in activities],
                         ["FINALIZED", "REVIEWED"])
        self.assertTrue(all(row["result_id"] == result.id for row in activities))
        self.assertEqual(activities[0]["test"], {
            "id": test.test_id,
            "code": qc_test.test_code,
            "name": qc_test.test_name,
        })
        self.assertTrue(all(not {"test_id", "test_code", "test_name"}
                            .intersection(row) for row in activities))

        actor = self.actor("sample.view")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        response = TestClient(app).get("/qc-dashboard/recent-activity?limit=2")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual([row["activity_type"] for row in payload],
                         ["FINALIZED", "REVIEWED"])
        self.assertEqual(payload[0]["test"], {
            "id": str(test.test_id),
            "code": qc_test.test_code,
            "name": qc_test.test_name,
        })
        self.assertTrue(all(not {"test_id", "test_code", "test_name"}
                            .intersection(row) for row in payload))

        _, active_test = self.new_test(test_status="REVIEWED")
        active_result = self.add_result(
            active_test, "REVIEWED", entered_at=now - timedelta(minutes=30),
            reviewed_at=now - timedelta(minutes=15),
        )
        self.assign(active_test)
        self_activities = self.dashboard.recent_activity(
            self.db, self.actor("sample.view", "SELF"), 20
        )
        self.assertEqual({row["activity_type"] for row in self_activities},
                         {"SUBMITTED", "REVIEWED"})
        self.assertTrue(all(row["result_id"] == active_result.id
                            for row in self_activities))

    def test_routes_permissions_filter_validation_and_openapi_contract(self):
        actor = self.actor("sample.view")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        client = TestClient(app)
        self.assertEqual(client.get("/qc-dashboard/summary").status_code, 200)
        self.assertEqual(client.get("/qc-dashboard/work-queue").status_code, 200)
        self.assertEqual(client.get("/qc-dashboard/recent-activity").status_code, 200)
        self.assertEqual(client.get("/qc-dashboard/recent-activity?limit=101").status_code, 422)
        self.assertEqual(client.get("/qc-dashboard/review-queue").status_code, 403)
        actor.user_roles = self.actor("sample_test_result.review").user_roles
        self.assertEqual(client.get("/qc-dashboard/review-queue").status_code, 200)
        schema = app.openapi()
        paths = {path for path in schema["paths"] if path.startswith("/qc-dashboard")}
        self.assertEqual(paths, {
            "/qc-dashboard/summary", "/qc-dashboard/work-queue",
            "/qc-dashboard/review-queue", "/qc-dashboard/recent-activity",
        })
        operation_ids = [operation["operationId"] for path in schema["paths"].values()
                         for operation in path.values() if isinstance(operation, dict)
                         and "operationId" in operation]
        self.assertEqual(len(operation_ids), len(set(operation_ids)))


if __name__ == "__main__":
    unittest.main()
