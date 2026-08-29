import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.dependencies.database import get_db
from app.main import app
from app.routers import instrument_type, location, manufacturer, material
from app.services.business.manufacturer_service import ManufacturerService
from app.services.organization_scope_service import AccessScope, OrganizationScopeService


def permission_actor(permission: str, scope: str = "ORGANIZATION", organization_id=None):
    permission_obj = SimpleNamespace(permission_code=permission, is_active=True)
    mapping = SimpleNamespace(is_active=True, permission=permission_obj)
    role = SimpleNamespace(is_active=True, role_permissions=[mapping])
    assignment = SimpleNamespace(is_active=True, role=role, access_scope=scope)
    return SimpleNamespace(
        id=uuid4(), organization_id=organization_id or uuid4(), user_roles=[assignment],
        force_password_change=False,
    )


def response_record(**values):
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid4(), organization_id=uuid4(), code="CODE", name="Name",
        description=None, is_active=True, version=1, created_at=now, updated_at=now,
    )
    defaults.update(values)
    return SimpleNamespace(**defaults)


class SharedMasterScopeTests(unittest.TestCase):
    def setUp(self):
        self.scope = OrganizationScopeService()
        self.organization_id = uuid4()
        self.target = SimpleNamespace(organization_id=self.organization_id)

    def test_organization_and_hierarchy_scopes_access_same_organization(self):
        for level in ("ORGANIZATION", "BUSINESS_UNIT", "DIVISION", "DEPARTMENT"):
            actor = permission_actor("material.view", level, self.organization_id)
            self.scope.ensure_can_access_shared_master(actor, self.target, "material.view")

    def test_self_has_no_rows_or_direct_access(self):
        actor = permission_actor("material.view", "SELF", self.organization_id)
        query = Mock()
        query.filter.return_value = query
        self.assertIs(self.scope.filter_shared_masters(query, actor, "material.view", Mock()), query)
        query.filter.assert_called_once()
        with self.assertRaisesRegex(Exception, "not found"):
            self.scope.ensure_can_access_shared_master(actor, self.target, "material.view")

    def test_unrelated_organization_role_does_not_broaden_requested_permission(self):
        actor = permission_actor("material.view", "SELF", self.organization_id)
        other = permission_actor("user.view", "ORGANIZATION", self.organization_id).user_roles[0]
        actor.user_roles.append(other)
        self.assertEqual(self.scope.resolve_scope(actor, "material.view"), AccessScope.SELF)

    def test_cross_organization_direct_access_is_concealed(self):
        actor = permission_actor("material.view", "ORGANIZATION", uuid4())
        with self.assertRaisesRegex(Exception, "not found"):
            self.scope.ensure_can_access_shared_master(actor, self.target, "material.view")


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: Mock()
        self.original_services = {
            location: location.service, manufacturer: manufacturer.service,
            instrument_type: instrument_type.service, material: material.service,
        }
        location.service = Mock()
        manufacturer.service = Mock()
        instrument_type.service = Mock()
        material.service = Mock()
        location.service.list_scoped.return_value = []
        manufacturer.service.list_scoped.return_value = []
        instrument_type.service.list_scoped.return_value = []
        material.service.list_scoped.return_value = []

    def tearDown(self):
        for module, service in self.original_services.items():
            module.service = service
        app.dependency_overrides.clear()

    def _authorize(self, permission):
        app.dependency_overrides[get_current_user] = lambda: permission_actor(permission)

    def test_unauthenticated_requests_are_denied(self):
        for path in ("/locations", "/manufacturers", "/instrument-types", "/materials"):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_view_permission_allows_list_and_create_requires_create(self):
        self._authorize("manufacturer.view")
        self.assertEqual(self.client.get("/manufacturers").status_code, 200)
        response = self.client.post("/manufacturers", json={"code": "M", "name": "Maker"})
        self.assertEqual(response.status_code, 403)

    def test_location_list_filters_are_forwarded(self):
        self._authorize("location.view")
        parent_id = uuid4()
        response = self.client.get(
            f"/locations?limit=20&offset=4&search=lab&is_active=true&parent_location_id={parent_id}&location_type=ROOM"
        )
        self.assertEqual(response.status_code, 200)
        kwargs = location.service.list_scoped.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (20, 4))
        self.assertEqual(kwargs["parent_location_id"], parent_id)
        self.assertEqual(kwargs["location_type"], "ROOM")

    def test_material_type_filter_is_forwarded(self):
        self._authorize("material.view")
        self.assertEqual(self.client.get("/materials?material_type=REAGENT").status_code, 200)
        self.assertEqual(material.service.list_scoped.call_args.kwargs["material_type"], "REAGENT")

    def test_create_payload_cannot_select_organization(self):
        self._authorize("manufacturer.create")
        response = self.client.post("/manufacturers", json={
            "organization_id": str(uuid4()), "code": "M", "name": "Maker"
        })
        self.assertEqual(response.status_code, 422)

    def test_update_status_and_delete_require_versions_and_permissions(self):
        record_id = uuid4()
        cases = (
            (manufacturer, "manufacturer.update", "put", f"/manufacturers/{record_id}", {"version": 2, "name": "New"}, "update_for_actor"),
            (manufacturer, "manufacturer.update", "put", f"/manufacturers/{record_id}/deactivate", {"version": 2}, "set_active_scoped"),
            (manufacturer, "manufacturer.delete", "delete", f"/manufacturers/{record_id}", {"version": 2}, "delete_scoped"),
        )
        manufacturer.service.update_for_actor.return_value = response_record(organization_id=uuid4(), version=3, website=None)
        manufacturer.service.set_active_scoped.return_value = response_record(organization_id=uuid4(), version=3, website=None, is_active=False)
        for module, permission, method, path, body, called in cases:
            self._authorize(permission)
            response = self.client.request(method.upper(), path, json=body)
            self.assertIn(response.status_code, (200, 204))
            self.assertTrue(getattr(module.service, called).called)

    def test_all_requested_paths_and_methods_are_in_openapi(self):
        paths = app.openapi()["paths"]
        resources = {
            "/locations": "location_id", "/manufacturers": "manufacturer_id",
            "/instrument-types": "instrument_type_id", "/materials": "material_id",
        }
        for root, identifier in resources.items():
            self.assertEqual(set(paths[root]), {"get", "post"})
            self.assertEqual(set(paths[f"{root}/{{{identifier}}}"]), {"get", "put", "delete"})
            self.assertEqual(set(paths[f"{root}/{{{identifier}}}/activate"]), {"put"})
            self.assertEqual(set(paths[f"{root}/{{{identifier}}}/deactivate"]), {"put"})


class TransactionAtomicityTests(unittest.TestCase):
    def test_audit_failure_rolls_back_business_update(self):
        repository = Mock()
        from app.models.business.manufacturer import Manufacturer
        repository.model = Manufacturer
        actor = permission_actor("manufacturer.update")
        record = response_record(organization_id=actor.organization_id, website=None)
        repository.get.return_value = record
        repository.update_expected.return_value = record
        service = ManufacturerService(repository)
        service.audit_service = Mock()
        service.audit_service.snapshot.return_value = {"name": "Before"}
        service.audit_service.record_update.side_effect = RuntimeError("audit unavailable")
        db = Mock()
        with self.assertRaises(RuntimeError):
            service.update_for_actor(db, actor, record.id, 1, {"name": "After"})
        db.rollback.assert_called_once()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
