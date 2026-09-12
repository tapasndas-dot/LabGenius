"""Focused Sprint 21D.2 Result review and finalization workflow tests."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.exceptions import (ResourceNotFoundException, ValidationException,
                                 VersionConflictException)
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business.sample_test_assignment import SampleTestAssignment
from app.models.business.sample_test_result import SampleTestResult
from tests.test_sprint19b_sample_api import assignment
from tests import test_sprint21b_result_api as sprint21b_support


class Sprint21D2ResultReviewTests(unittest.TestCase):
    """Reuse the established Sprint 21B database fixture without inheriting its tests."""

    _basis = sprint21b_support.Sprint21BResultAPITests._basis
    tearDown = sprint21b_support.Sprint21BResultAPITests.tearDown
    _user = sprint21b_support.Sprint21BResultAPITests._user
    actor = sprint21b_support.Sprint21BResultAPITests.actor
    create = sprint21b_support.Sprint21BResultAPITests.create
    typed_values = staticmethod(sprint21b_support.Sprint21BResultAPITests.typed_values)
    add_all_parameters = sprint21b_support.Sprint21BResultAPITests.add_all_parameters

    def setUp(self):
        session_factory = lambda bind: Session(
            bind=bind, join_transaction_mode="create_savepoint"
        )
        sample_fixture = sprint21b_support.sample_test_support
        with patch.object(sample_fixture, "Session", session_factory):
            sprint21b_support.Sprint21BResultAPITests.setUp(self)

    def submitted(self, sample_test_status="ASSIGNED"):
        self.sample_test.status = sample_test_status
        result = self.create()
        self.add_all_parameters(result["id"])
        current = self.api.results.result_repository.get(self.db, result["id"])
        return self.api.submit(
            self.db, self.actor("sample_test_result.submit"), self.sample.id,
            self.sample_test.id, result["id"], current.version,
        )

    def reviewed(self):
        entered = self.submitted()
        return self.api.review(
            self.db, self.actor("sample_test_result.review"), self.sample.id,
            self.sample_test.id, entered["id"], entered["version"],
        )

    def test_happy_path_synchronizes_result_and_sample_test(self):
        entered = self.submitted("IN_PROGRESS")
        self.assertEqual((entered["status"], self.sample_test.status),
                         ("ENTERED", "RESULT_ENTERED"))
        reviewed = self.api.review(
            self.db, self.actor("sample_test_result.review"), self.sample.id,
            self.sample_test.id, entered["id"], entered["version"],
        )
        self.assertEqual((reviewed["status"], self.sample_test.status),
                         ("REVIEWED", "REVIEWED"))
        self.assertIsNotNone(reviewed["reviewed_at"])
        self.assertEqual(reviewed["reviewed_by"]["id"], self.user_a.id)
        finalized = self.api.finalize(
            self.db, self.actor("sample_test_result.finalize"), self.sample.id,
            self.sample_test.id, reviewed["id"], reviewed["version"],
        )
        self.assertEqual((finalized["status"], self.sample_test.status),
                         ("FINALIZED", "FINALIZED"))
        self.assertIsNotNone(finalized["finalized_at"])
        self.assertEqual(finalized["finalized_by"]["id"], self.user_a.id)
        self.assertEqual(self.sample.status, "REGISTERED")
        actions = {row.action for row in self.db.query(AuditEvent).filter(
            AuditEvent.entity_id == entered["id"]
        )}
        self.assertTrue({"SUBMIT", "REVIEW", "FINALIZE"}.issubset(actions))

    def test_invalid_result_and_parent_transitions_are_rejected(self):
        draft = self.create()
        with self.assertRaises(ValidationException):
            self.api.results.review(
                self.db, self.db.get(SampleTestResult, draft["id"]),
                self.user_a.id, draft["version"],
            )
        self.add_all_parameters(draft["id"])
        self.sample_test.status = "PENDING"; self.db.commit()
        with self.assertRaises(ValidationException):
            self.api.results.submit(
                self.db, self.org.id, self.db.get(SampleTestResult, draft["id"]),
                self.user_a.id, draft["version"],
            )
        self.sample_test.status = "ASSIGNED"; self.db.commit()
        entered = self.api.submit(self.db, self.actor("sample_test_result.submit"),
                                  self.sample.id, self.sample_test.id, draft["id"], draft["version"])
        with self.assertRaises(ValidationException):
            self.api.results.finalize(
                self.db, self.db.get(SampleTestResult, entered["id"]),
                self.user_a.id, entered["version"],
            )
        reviewed = self.api.review(self.db, self.actor("sample_test_result.review"),
                                   self.sample.id, self.sample_test.id, entered["id"], entered["version"])
        with self.assertRaises(ValidationException):
            self.api.results.review(
                self.db, self.db.get(SampleTestResult, reviewed["id"]),
                self.user_a.id, reviewed["version"],
            )
        finalized = self.api.finalize(self.db, self.actor("sample_test_result.finalize"),
                                      self.sample.id, self.sample_test.id, reviewed["id"], reviewed["version"])
        with self.assertRaises(ValidationException):
            self.api.results.finalize(
                self.db, self.db.get(SampleTestResult, finalized["id"]),
                self.user_a.id, finalized["version"],
            )

    def test_routes_require_distinct_permissions_and_conceal_wrong_chain(self):
        entered = self.submitted()
        actor = self.actor("sample_test_result.review")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        client = TestClient(app)
        base = f"/samples/{self.sample.id}/tests/{self.sample_test.id}/results/{entered['id']}"
        self.assertEqual(client.post(f"{base}/finalize", json={"version": entered["version"]}).status_code, 403)
        reviewed = client.post(f"{base}/review", json={"version": entered["version"]})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        actor.user_roles = [assignment("sample_test_result.finalize", "ORGANIZATION")]
        self.assertEqual(client.post(
            f"/samples/{uuid4()}/tests/{self.sample_test.id}/results/{entered['id']}/finalize",
            json={"version": reviewed.json()["version"]},
        ).status_code, 404)
        self.assertEqual(client.post(
            f"/samples/{self.sample.id}/tests/{uuid4()}/results/{entered['id']}/finalize",
            json={"version": reviewed.json()["version"]},
        ).status_code, 404)
        self.assertEqual(client.post(
            f"/samples/{self.sample.id}/tests/{self.sample_test.id}/results/{uuid4()}/finalize",
            json={"version": reviewed.json()["version"]},
        ).status_code, 404)

    def test_scope_including_self_remains_assignment_only(self):
        entered = self.submitted()
        for scope in ("ORGANIZATION", "BUSINESS_UNIT", "DIVISION", "DEPARTMENT"):
            # The same centralized filter is exercised through a read-only lookup.
            self.api._result(self.db, self.actor("sample_test_result.review", scope),
                             self.sample.id, self.sample_test.id, entered["id"],
                             "sample_test_result.review")
        self_actor = self.actor("sample_test_result.review", "SELF")
        with self.assertRaises(ResourceNotFoundException):
            self.api._result(self.db, self_actor, self.sample.id, self.sample_test.id,
                             entered["id"], "sample_test_result.review")
        assignment_row = SampleTestAssignment(
            sample_test_id=self.sample_test.id, assigned_user_id=self.user_a.id,
            assigned_at=datetime.now(timezone.utc), is_active=True,
        )
        self.db.add(assignment_row); self.db.commit()
        self.api._result(self.db, self_actor, self.sample.id, self.sample_test.id,
                         entered["id"], "sample_test_result.review")
        assignment_row.is_active = False
        result = self.db.get(SampleTestResult, entered["id"])
        result.reviewed_by_user_id = self.user_a.id
        result.finalized_by_user_id = self.user_a.id
        self.db.commit()
        with self.assertRaises(ResourceNotFoundException):
            self.api._result(self.db, self_actor, self.sample.id, self.sample_test.id,
                             entered["id"], "sample_test_result.review")

    def test_stale_versions_and_atomic_parent_failure_roll_back(self):
        entered = self.submitted()
        with self.assertRaises(VersionConflictException):
            self.api.results.review(
                self.db, self.db.get(SampleTestResult, entered["id"]),
                self.user_a.id, entered["version"] + 1,
            )
        reviewed = self.api.review(self.db, self.actor("sample_test_result.review"),
                                   self.sample.id, self.sample_test.id, entered["id"], entered["version"])
        with self.assertRaises(VersionConflictException):
            self.api.results.finalize(
                self.db, self.db.get(SampleTestResult, reviewed["id"]),
                self.user_a.id, reviewed["version"] + 1,
            )
        result_before = self.db.get(SampleTestResult, reviewed["id"])
        test_before = self.db.get(type(self.sample_test), self.sample_test.id)
        result_id = result_before.id
        result_version = result_before.version
        result_status = result_before.status
        sample_test_id = test_before.id
        sample_test_version = test_before.version
        sample_test_status = test_before.status
        repository = self.api.results.sample_test_repository
        with patch.object(repository, "transition_status", return_value=None):
            with self.assertRaises(VersionConflictException):
                self.api.finalize(
                    self.db, self.actor("sample_test_result.finalize"),
                    self.sample.id, sample_test_id, result_id, result_version,
                )
        self.db.expire_all()
        result_after = self.db.get(SampleTestResult, result_id)
        test_after = self.db.get(type(self.sample_test), sample_test_id)
        self.assertEqual(result_after.status, result_status)
        self.assertEqual(result_after.version, result_version)
        self.assertIsNone(result_after.finalized_at)
        self.assertIsNone(result_after.finalized_by_user_id)
        self.assertEqual(test_after.status, sample_test_status)
        self.assertEqual(test_after.version, sample_test_version)
        self.assertEqual(self.db.query(AuditEvent).filter(
            AuditEvent.entity_id == result_id,
            AuditEvent.action == "FINALIZE",
        ).count(), 0)

    def test_audit_failure_rolls_back_both_transitions_and_content_stays_immutable(self):
        entered = self.submitted()
        with self.assertRaises(ValidationException):
            self.api.results.update_draft_result(
                self.db, self.db.get(SampleTestResult, entered["id"]),
                entered["version"], {"notes": "late"},
            )
        with self.assertRaises(ValidationException):
            self.create()
        result_before = self.db.get(SampleTestResult, entered["id"])
        test_before = self.db.get(type(self.sample_test), self.sample_test.id)
        result_id = result_before.id
        result_version = result_before.version
        result_status = result_before.status
        sample_test_id = test_before.id
        sample_test_version = test_before.version
        sample_test_status = test_before.status
        with patch.object(
            self.api.audit, "record_update",
            side_effect=RuntimeError("forced audit failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.api.review(
                    self.db, self.actor("sample_test_result.review"),
                    self.sample.id, sample_test_id, result_id, result_version,
                )
        self.db.expire_all()
        result_after = self.db.get(SampleTestResult, result_id)
        test_after = self.db.get(type(self.sample_test), sample_test_id)
        self.assertEqual(result_after.status, result_status)
        self.assertEqual(result_after.version, result_version)
        self.assertIsNone(result_after.reviewed_at)
        self.assertIsNone(result_after.reviewed_by_user_id)
        self.assertEqual(test_after.status, sample_test_status)
        self.assertEqual(test_after.version, sample_test_version)
        self.assertEqual(self.db.query(AuditEvent).filter(
            AuditEvent.entity_id == result_id,
            AuditEvent.action == "REVIEW",
        ).count(), 0)


if __name__ == "__main__":
    unittest.main()
