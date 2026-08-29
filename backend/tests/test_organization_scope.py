import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException

from app.core.exceptions import ValidationException
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.organization.organization import Organization
from app.services.organization_scope_service import AccessScope, OrganizationScopeService
from app.services.user.user_service import UserService


def assignment(scope, permission="user.view", *, active=True, role_active=True):
    permission_obj = SimpleNamespace(permission_code=permission, is_active=True)
    mapping = SimpleNamespace(is_active=True, permission=permission_obj)
    role = SimpleNamespace(is_active=role_active, role_permissions=[mapping])
    return SimpleNamespace(is_active=active, role=role, access_scope=scope)


def user(scope="ORGANIZATION", permission="user.view", **overrides):
    values = dict(
        id=uuid4(), organization_id=uuid4(), business_unit_id=uuid4(),
        division_id=uuid4(), department_id=uuid4(), designation_id=uuid4(),
        user_roles=[assignment(scope, permission)],
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class OrganizationScopeTests(unittest.TestCase):
    def setUp(self):
        self.service = OrganizationScopeService()
        self.actor = user()

    def target(self, **changes):
        values = dict(
            id=uuid4(), organization_id=self.actor.organization_id,
            business_unit_id=self.actor.business_unit_id,
            division_id=self.actor.division_id,
            department_id=self.actor.department_id,
            designation_id=uuid4(),
        )
        values.update(changes)
        return SimpleNamespace(**values)

    def test_organization_scope_allows_same_organization(self):
        self.assertTrue(self.service.can_access_user(self.actor, self.target(), "user.view"))

    def test_organization_scope_denies_other_organization(self):
        self.assertFalse(self.service.can_access_user(self.actor, self.target(organization_id=uuid4()), "user.view"))

    def test_business_unit_scope_allows_descendants_and_denies_other_bu(self):
        self.actor.user_roles = [assignment("BUSINESS_UNIT")]
        self.assertTrue(self.service.can_access_user(self.actor, self.target(division_id=uuid4(), department_id=uuid4()), "user.view"))
        self.assertFalse(self.service.can_access_user(self.actor, self.target(business_unit_id=uuid4()), "user.view"))

    def test_division_scope_allows_child_department_and_denies_other_division(self):
        self.actor.user_roles = [assignment("DIVISION")]
        self.assertTrue(self.service.can_access_user(self.actor, self.target(department_id=uuid4()), "user.view"))
        self.assertFalse(self.service.can_access_user(self.actor, self.target(division_id=uuid4()), "user.view"))

    def test_department_scope_allows_only_own_department(self):
        self.actor.user_roles = [assignment("DEPARTMENT")]
        self.assertTrue(self.service.can_access_user(self.actor, self.target(), "user.view"))
        self.assertFalse(self.service.can_access_user(self.actor, self.target(department_id=uuid4()), "user.view"))

    def test_self_scope_allows_only_self(self):
        self.actor.user_roles = [assignment("SELF")]
        self.assertTrue(self.service.can_access_user(self.actor, self.actor, "user.view"))
        self.assertFalse(self.service.can_access_user(self.actor, self.target(), "user.view"))

    def test_designation_is_not_access_boundary(self):
        self.actor.user_roles = [assignment("DEPARTMENT")]
        self.assertTrue(self.service.can_access_user(self.actor, self.target(designation_id=uuid4()), "user.view"))

    def test_scope_is_permission_specific(self):
        self.actor.user_roles = [assignment("ORGANIZATION", "other.permission"), assignment("DEPARTMENT", "user.view")]
        self.assertEqual(self.service.resolve_scope(self.actor, "user.view"), AccessScope.DEPARTMENT)

    def test_multi_role_uses_broadest_scope_for_same_permission(self):
        self.actor.user_roles = [assignment("DEPARTMENT"), assignment("DIVISION")]
        self.assertEqual(self.service.resolve_scope(self.actor, "user.view"), AccessScope.DIVISION)

    def test_inactive_assignment_and_role_do_not_grant_scope(self):
        self.actor.user_roles = [assignment("ORGANIZATION", active=False), assignment("BUSINESS_UNIT", role_active=False)]
        with self.assertRaises(HTTPException):
            self.service.resolve_scope(self.actor, "user.view")

    def test_scope_alone_does_not_grant_permission(self):
        self.actor.user_roles = [assignment("ORGANIZATION", "user.view")]
        with self.assertRaises(HTTPException):
            self.service.resolve_scope(self.actor, "user.update")

    def test_scope_escalation_is_rejected(self):
        self.actor.user_roles = [assignment("DEPARTMENT", "user.update")]
        with self.assertRaises(HTTPException):
            self.service.ensure_scope_not_escalated(self.actor, "user.update", "ORGANIZATION")

    def test_invalid_scope_is_rejected(self):
        with self.assertRaises(ValidationException):
            self.service.ensure_scope_not_escalated(self.actor, "user.view", "GLOBAL")

    def test_direct_user_lookup_enforces_scope_without_uuid_bypass(self):
        target = self.target(organization_id=uuid4())
        user_service = UserService()
        user_service.repository = Mock()
        user_service.repository.get.return_value = target
        with self.assertRaises(HTTPException) as error:
            user_service.get_scoped(Mock(), target.id, self.actor, "user.view")
        self.assertEqual(error.exception.status_code, 404)

    def test_user_list_is_filtered_at_query_level(self):
        self.actor.user_roles = [assignment("DEPARTMENT")]
        query = Mock()
        db = Mock()
        db.query.return_value = query
        query.filter.return_value = query
        self.service.filter_users(db, self.actor, "user.view")
        query.filter.assert_called_once()


class HierarchyValidationTests(unittest.TestCase):
    def make_db(self, *, mismatch=False):
        org = SimpleNamespace(id=uuid4())
        bu = SimpleNamespace(id=uuid4(), organization_id=uuid4() if mismatch else org.id)
        div = SimpleNamespace(id=uuid4(), business_unit_id=bu.id)
        dept = SimpleNamespace(id=uuid4(), division_id=div.id)
        desig = SimpleNamespace(id=uuid4(), department_id=dept.id)
        objects = {Organization: org, BusinessUnit: bu, Division: div, Department: dept, Designation: desig}
        db = Mock()
        db.query.side_effect = lambda model: SimpleNamespace(
            filter=lambda *args: SimpleNamespace(first=lambda: objects[model])
        )
        return db, org, bu, div, dept, desig

    def test_valid_hierarchy_is_accepted(self):
        db, org, bu, div, dept, desig = self.make_db()
        OrganizationScopeService().validate_hierarchy(
            db, organization_id=org.id, business_unit_id=bu.id,
            division_id=div.id, department_id=dept.id, designation_id=desig.id,
        )

    def test_mismatched_hierarchy_is_rejected(self):
        db, org, bu, div, dept, desig = self.make_db(mismatch=True)
        with self.assertRaises(ValidationException):
            OrganizationScopeService().validate_hierarchy(
                db, organization_id=org.id, business_unit_id=bu.id,
                division_id=div.id, department_id=dept.id, designation_id=desig.id,
            )


if __name__ == "__main__":
    unittest.main()
