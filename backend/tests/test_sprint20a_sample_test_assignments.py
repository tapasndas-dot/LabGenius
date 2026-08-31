"""Focused PostgreSQL/domain tests for Sprint 20A SampleTest assignments."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business.sample import Sample, SampleTest, SampleTestStatus
from app.models.business.sample_test_assignment import SampleTestAssignment
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.user.user import User
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.sample_test_assignment_service import SampleTestAssignmentService
from app.services.organization_scope_service import OrganizationScopeService
from tests.test_sprint19a_samples import Sprint19ADatabaseTests


def scope_assignment(permission: str = "sample.view"):
    mapping = SimpleNamespace(
        is_active=True,
        permission=SimpleNamespace(is_active=True, permission_code=permission),
    )
    role = SimpleNamespace(is_active=True, role_permissions=[mapping])
    return SimpleNamespace(is_active=True, role=role, access_scope="SELF")


class Sprint20AAssignmentTests(Sprint19ADatabaseTests):
    def setUp(self):
        super().setUp()
        self.assignments = SampleTestAssignmentService()
        self.scope = OrganizationScopeService()
        self.user_a = self._user(self.org, "A", active=True)
        self.user_b = self._user(self.org, "B", active=True)
        self.inactive_user = self._user(self.org, "I", active=False)
        self.other_user = self._user(self.other_org, "X", active=True)
        version = self._basis()[0]
        self.sample = self.samples.create(self.db, self.org.id, {
            "sample_number": f"ASSIGN-{uuid4().hex[:6]}",
            "material_id": self.material.id,
            "specification_version_id": version.id,
        })
        self.sample_test = self.sample_tests.generate(self.db, self.org.id, self.sample.id)[0]

    def _user(self, organization, marker: str, *, active: bool) -> User:
        suffix = uuid4().hex[:8]
        bu = BusinessUnit(
            organization_id=organization.id,
            business_unit_code=f"B{marker}{suffix}", business_unit_name="Laboratory",
        )
        self.db.add(bu); self.db.flush()
        division = Division(
            business_unit_id=bu.id,
            division_code=f"D{marker}{suffix}", division_name="Quality",
        )
        self.db.add(division); self.db.flush()
        department = Department(
            division_id=division.id,
            department_code=f"P{marker}{suffix}", department_name="QC",
        )
        self.db.add(department); self.db.flush()
        designation = Designation(
            department_id=department.id,
            designation_code=f"G{marker}{suffix}", designation_name="Scientist",
        )
        self.db.add(designation); self.db.flush()
        user = User(
            organization_id=organization.id,
            business_unit_id=bu.id,
            division_id=division.id,
            department_id=department.id,
            designation_id=designation.id,
            employee_code=f"E{marker}{suffix}", first_name="Test", last_name=marker,
            display_name=f"Test {marker}", email=f"{marker.lower()}{suffix}@example.invalid",
            username=f"{marker.lower()}{suffix}", password_hash="not-a-real-password-hash",
            account_status="ACTIVE", is_active=active,
        )
        self.db.add(user); self.db.flush()
        return user

    def _actor(self, user: User):
        return SimpleNamespace(
            id=user.id, organization_id=user.organization_id,
            business_unit_id=user.business_unit_id, division_id=user.division_id,
            department_id=user.department_id, user_roles=[scope_assignment()],
        )

    def test_initial_assignment_validates_user_and_transitions_status(self):
        with self.assertRaises(ValidationException):
            self.assignments.assign(self.db, self.org.id, self.sample_test.id, self.inactive_user.id)
        with self.assertRaises(ValidationException):
            self.assignments.assign(self.db, self.org.id, self.sample_test.id, self.other_user.id)
        assignment = self.assignments.assign(
            self.db, self.org.id, self.sample_test.id, self.user_a.id, self.user_b.id, "Primary"
        )
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.assigned_user_id, self.user_a.id)
        self.assertEqual(self.sample_test.status, SampleTestStatus.ASSIGNED)

    def test_reassign_and_unassign_preserve_history_and_enforce_versions(self):
        first = self.assignments.assign(
            self.db, self.org.id, self.sample_test.id, self.user_a.id
        )
        with self.assertRaises(VersionConflictException):
            self.assignments.reassign(
                self.db, self.org.id, self.sample_test.id, self.user_b.id, first.version + 1
            )
        second = self.assignments.reassign(
            self.db, self.org.id, self.sample_test.id, self.user_b.id, first.version
        )
        self.db.refresh(first)
        self.assertFalse(first.is_active)
        self.assertIsNotNone(first.unassigned_at)
        self.assertTrue(second.is_active)
        self.assertEqual(self.sample_test.status, SampleTestStatus.ASSIGNED)
        history = self.assignments.list_assignment_history(self.db, self.sample_test.id)
        self.assertEqual(len(history), 2)
        with self.assertRaises(VersionConflictException):
            self.assignments.unassign(self.db, self.org.id, self.sample_test.id, second.version + 1)
        ended = self.assignments.unassign(
            self.db, self.org.id, self.sample_test.id, second.version
        )
        self.assertFalse(ended.is_active)
        self.assertEqual(self.sample_test.status, SampleTestStatus.PENDING)
        self.assertEqual(len(self.assignments.list_assignment_history(self.db, self.sample_test.id)), 2)

    def test_database_prevents_two_active_assignments(self):
        self.assignments.assign(self.db, self.org.id, self.sample_test.id, self.user_a.id)
        nested = self.db.begin_nested()
        self.db.add(SampleTestAssignment(
            sample_test_id=self.sample_test.id,
            assigned_user_id=self.user_b.id,
            assigned_at=self.sample_test.created_at,
            is_active=True,
        ))
        with self.assertRaises(IntegrityError):
            self.db.flush()
        nested.rollback()
        self.assertEqual(
            self.db.query(SampleTestAssignment).filter_by(
                sample_test_id=self.sample_test.id, is_active=True
            ).count(), 1,
        )

    def test_invalid_states_cancelled_parent_and_cross_org_are_rejected(self):
        self.sample_test.status = SampleTestStatus.FINALIZED
        with self.assertRaises(ValidationException):
            self.assignments.assign(self.db, self.org.id, self.sample_test.id, self.user_a.id)
        self.sample_test.status = SampleTestStatus.PENDING
        self.sample.status = "CANCELLED"
        with self.assertRaises(ValidationException):
            self.assignments.assign(self.db, self.org.id, self.sample_test.id, self.user_a.id)
        self.sample.status = "REGISTERED"
        with self.assertRaises(ResourceNotFoundException):
            self.assignments.assign(self.db, self.other_org.id, self.sample_test.id, self.other_user.id)

    def test_self_scope_tracks_only_active_assignments_without_duplicate_samples(self):
        first = self.assignments.assign(self.db, self.org.id, self.sample_test.id, self.user_a.id)
        actor_a, actor_b = self._actor(self.user_a), self._actor(self.user_b)
        self.assertEqual(
            [row.id for row in self.scope.filter_sample_tests(
                self.db.query(SampleTest), actor_a, "sample.view"
            ).all()], [self.sample_test.id],
        )
        self.assertEqual(
            [row.id for row in self.scope.filter_samples(
                self.db.query(Sample), actor_a, "sample.view"
            ).all()], [self.sample.id],
        )
        self.assertEqual(self.scope.filter_samples(
            self.db.query(Sample), actor_b, "sample.view"
        ).count(), 0)
        second = self.assignments.reassign(
            self.db, self.org.id, self.sample_test.id, self.user_b.id, first.version
        )
        self.assertEqual(self.scope.filter_sample_tests(
            self.db.query(SampleTest), actor_a, "sample.view"
        ).count(), 0)
        self.assertEqual(self.scope.filter_sample_tests(
            self.db.query(SampleTest), actor_b, "sample.view"
        ).count(), 1)
        version, source, _, _ = self._basis(code="SECOND")
        other_test = SampleTest(
            sample_id=self.sample.id, specification_test_id=source.id,
            test_id=source.test_id, method_version_id=source.method_version_id,
            sequence_number=2,
        )
        self.db.add(other_test); self.db.flush()
        self.assignments.assign(self.db, self.org.id, other_test.id, self.user_a.id)
        self.assertEqual(self.scope.filter_samples(
            self.db.query(Sample), actor_a, "sample.view"
        ).count(), 1)
        self.assignments.unassign(self.db, self.org.id, other_test.id, 1)
        self.assertEqual(self.scope.filter_samples(
            self.db.query(Sample), actor_a, "sample.view"
        ).count(), 0)
        self.assertEqual(second.assigned_user_id, self.user_b.id)

    def test_reassignment_is_rollback_safe(self):
        first = self.assignments.assign(
            self.db, self.org.id, self.sample_test.id, self.user_a.id
        )
        nested = self.db.begin_nested()
        with patch.object(self.assignments.repository, "create", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                self.assignments.reassign(
                    self.db, self.org.id, self.sample_test.id, self.user_b.id, first.version
                )
        nested.rollback()
        active = self.assignments.get_active_assignment(self.db, self.sample_test.id)
        self.assertEqual(active.assigned_user_id, self.user_a.id)
        self.assertTrue(active.is_active)


class Sprint20APermissionContractTests(unittest.TestCase):
    def test_exact_assignment_permission(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual(codes.count("sample.assign"), 1)
        self.assertFalse(any(code.startswith("assignment.") for code in codes))
        self.assertNotIn("sample_test.assign", codes)
        self.assertNotIn("sample.unassign", codes)


if __name__ == "__main__":
    unittest.main()
