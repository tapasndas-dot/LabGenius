"""Focused Sprint 20B assignment API, scope, concurrency, and audit tests."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, VersionConflictException
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business.sample import Sample, SampleTest
from app.models.business.sample_test_assignment import SampleTestAssignment
from app.services.business.sample_test_assignment_api_service import SampleTestAssignmentAPIService
from tests.test_sprint19b_sample_api import assignment
from tests.test_sprint20a_sample_test_assignments import Sprint20AAssignmentTests


class Sprint20BAssignmentAPITests(Sprint20AAssignmentTests):
    def setUp(self):
        super().setUp()
        self.api = SampleTestAssignmentAPIService()
        self.sample.business_unit_id = self.user_a.business_unit_id
        self.sample.division_id = self.user_a.division_id
        self.sample.department_id = self.user_a.department_id
        self.db.flush()

    def tearDown(self):
        app.dependency_overrides.clear()
        super().tearDown()

    def actor(self, permission: str, scope="ORGANIZATION", user=None, extras=()):
        user = user or self.user_a
        roles = [assignment(permission, scope)]
        roles.extend(assignment(code, extra_scope) for code, extra_scope in extras)
        return SimpleNamespace(
            id=user.id, organization_id=user.organization_id,
            business_unit_id=user.business_unit_id, division_id=user.division_id,
            department_id=user.department_id, force_password_change=False,
            user_roles=roles,
        )

    def assign_values(self, user=None, **changes):
        values = {
            "assigned_user_id": (user or self.user_a).id,
            "expected_sample_test_version": self.sample_test.version,
            "notes": "Primary assignment",
        }
        values.update(changes)
        return values

    def test_assign_read_history_reassign_and_unassign_with_audit(self):
        manager = self.actor("sample.assign")
        first_response = self.api.assign(
            self.db, manager, self.sample.id, self.sample_test.id, self.assign_values()
        )
        first = first_response["assignment"]
        self.assertEqual(first_response["sample_test"].status, "ASSIGNED")
        viewer = self.actor("sample.view")
        self.assertEqual(
            self.api.current(self.db, viewer, self.sample.id, self.sample_test.id).id,
            first.id,
        )
        self.assertEqual([row.id for row in self.api.history(
            self.db, viewer, self.sample.id, self.sample_test.id
        )], [first.id])
        second_response = self.api.reassign(self.db, manager, self.sample.id, self.sample_test.id, {
            "assigned_user_id": self.user_b.id,
            "expected_assignment_version": first.version,
            "expected_sample_test_version": first_response["sample_test"].version,
            "notes": "Coverage change",
        })
        second = second_response["assignment"]
        history = self.api.history(self.db, viewer, self.sample.id, self.sample_test.id)
        self.assertEqual([row.id for row in history], [first.id, second.id])
        ended = self.api.unassign(self.db, manager, self.sample.id, self.sample_test.id, {
            "expected_assignment_version": second.version,
            "expected_sample_test_version": second_response["sample_test"].version,
        })
        self.assertEqual(ended["sample_test"].status, "PENDING")
        self.assertIsNone(ended["assignment"])
        actions = [row.action for row in self.db.query(AuditEvent).filter(
            AuditEvent.entity_id.in_([first.id, second.id])
        ).order_by(AuditEvent.occurred_at, AuditEvent.id)]
        self.assertEqual(actions.count("ASSIGN"), 2)
        self.assertEqual(actions.count("UNASSIGN"), 2)

    def test_routes_permissions_contract_and_wrong_parent_chain(self):
        manager = self.actor("sample.assign")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: manager
        client = TestClient(app)
        sample_test_id = self.sample_test.id
        route = f"/samples/{self.sample.id}/tests/{sample_test_id}"
        payload = {
            "assigned_user_id": str(self.user_a.id),
            "expected_sample_test_version": self.sample_test.version,
            "notes": "API",
        }
        response = client.post(f"{route}/assign", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        assignment_version = response.json()["assignment"]["version"]
        test_version = response.json()["sample_test"]["version"]
        manager.user_roles = [assignment("sample.view", "ORGANIZATION")]
        self.assertEqual(client.get(f"{route}/assignment").status_code, 200)
        self.assertEqual(client.get(f"{route}/assignment-history").status_code, 200)
        self.assertEqual(client.post(f"{route}/reassign", json={
            "assigned_user_id": str(self.user_b.id),
            "expected_assignment_version": assignment_version,
            "expected_sample_test_version": test_version,
        }).status_code, 403)
        manager.user_roles = [assignment("sample.assign", "ORGANIZATION")]
        hidden = f"/samples/{uuid4()}/tests/{sample_test_id}"
        manager.user_roles = [assignment("sample.view", "ORGANIZATION")]
        self.assertEqual(client.get(f"{hidden}/assignment").status_code, 404)
        self.assertEqual(client.get(f"{hidden}/assignment-history").status_code, 404)
        manager.user_roles = [assignment("sample.assign", "ORGANIZATION")]
        self.assertEqual(client.post(
            f"/samples/{uuid4()}/tests/{sample_test_id}/unassign",
            json={
                "expected_assignment_version": assignment_version,
                "expected_sample_test_version": test_version,
            },
        ).status_code, 404)
        self.assertEqual(client.post(f"{route}/reassign", json={
            "assigned_user_id": str(self.user_b.id),
            "expected_assignment_version": assignment_version + 1,
            "expected_sample_test_version": test_version,
        }).status_code, 409)

    def test_hierarchy_scope_is_permission_specific_and_self_cannot_mutate(self):
        for scope in ("ORGANIZATION", "BUSINESS_UNIT", "DIVISION", "DEPARTMENT"):
            sample, test = self.api._mutation_test(
                self.db, self.actor("sample.assign", scope),
                self.sample.id, self.sample_test.id,
            )
            self.assertEqual((sample.id, test.id), (self.sample.id, self.sample_test.id))
        outside = self.actor(
            "sample.assign", "DEPARTMENT", user=self.user_b,
            extras=(("sample.view", "ORGANIZATION"),),
        )
        with self.assertRaises(ResourceNotFoundException):
            self.api._mutation_test(
                self.db, outside, self.sample.id, self.sample_test.id
            )
        self_only = self.actor("sample.assign", "SELF")
        with self.assertRaises(ResourceNotFoundException):
            self.api.assign(
                self.db, self_only, self.sample.id, self.sample_test.id,
                self.assign_values(),
            )
        first = self.assignments.assign(
            self.db, self.org.id, self.sample_test.id, self.user_a.id,
            expected_sample_test_version=self.sample_test.version,
        )
        with self.assertRaises(ResourceNotFoundException):
            self.api.reassign(self.db, self_only, self.sample.id, self.sample_test.id, {
                "assigned_user_id": self.user_b.id,
                "expected_assignment_version": first.version,
                "expected_sample_test_version": self.sample_test.version,
                "notes": None,
            })
        with self.assertRaises(ResourceNotFoundException):
            self.api.unassign(self.db, self_only, self.sample.id, self.sample_test.id, {
                "expected_assignment_version": first.version,
                "expected_sample_test_version": self.sample_test.version,
            })

    def test_self_view_union_exact_test_filter_and_cancellation_safety(self):
        first = self.assignments.assign(
            self.db, self.org.id, self.sample_test.id, self.user_a.id,
            expected_sample_test_version=self.sample_test.version,
        )
        _, source, _, _ = self._basis(code="UNASSIGNED")
        unassigned = SampleTest(
            sample_id=self.sample.id, specification_test_id=source.id,
            test_id=source.test_id, method_version_id=source.method_version_id,
            sequence_number=2,
        )
        self.db.add(unassigned); self.db.flush()
        self_actor = self.actor("sample.view", "SELF")
        self.assertEqual([row.id for row in self.api.samples.scoped_query(
            self.db, self_actor, "sample.view"
        ).all()], [self.sample.id])
        self.assertEqual([row.id for row in self.api.scope.filter_sample_tests(
            self.db.query(SampleTest), self_actor, "sample.view"
        ).all()], [self.sample_test.id])
        union_actor = self.actor(
            "sample.view", "SELF", extras=(("sample.view", "DEPARTMENT"),)
        )
        self.assertEqual(self.api.scope.filter_sample_tests(
            self.db.query(SampleTest), union_actor, "sample.view"
        ).count(), 2)
        self.sample.status = "CANCELLED"; self.db.flush()
        self.assertEqual(self.api.samples.scoped_query(
            self.db, self_actor, "sample.view"
        ).count(), 0)
        self.assertEqual(self.api.scope.filter_sample_tests(
            self.db.query(SampleTest), self_actor, "sample.view"
        ).count(), 0)
        self.assertEqual(self.db.query(SampleTestAssignment).filter_by(id=first.id).count(), 1)

    def test_stale_sample_test_version_is_conflict(self):
        manager = self.actor("sample.assign")
        with self.assertRaises(VersionConflictException):
            self.api.assign(self.db, manager, self.sample.id, self.sample_test.id,
                            self.assign_values(expected_sample_test_version=999))

    def test_database_race_is_clean_conflict(self):
        manager = self.actor("sample.assign")
        with patch.object(
            self.api.assignments.repository, "create",
            side_effect=IntegrityError("duplicate", {}, Exception("race")),
        ):
            with self.assertRaises(VersionConflictException):
                self.api.assign(
                    self.db, manager, self.sample.id, self.sample_test.id,
                    self.assign_values(),
                )

    def test_audit_failure_rolls_back_assignment(self):
        manager = self.actor("sample.assign")
        sample_test_id = self.sample_test.id
        self.api.audit = Mock()
        self.api.audit.record_action.side_effect = RuntimeError("audit failed")
        with self.assertRaises(RuntimeError):
            self.api.assign(
                self.db, manager, self.sample.id, self.sample_test.id,
                self.assign_values(),
            )
        self.assertEqual(self.db.query(SampleTestAssignment).filter_by(
            sample_test_id=sample_test_id
        ).count(), 0)


if __name__ == "__main__":
    unittest.main()
