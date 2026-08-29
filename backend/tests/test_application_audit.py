import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.request_context import RequestContext, reset_request_context, set_request_context
from app.core.sanitization import sanitize
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.routers import audit
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.audit_service import AuditAction, AuditService


class SanitizationTests(unittest.TestCase):
    def test_recursive_sensitive_values_are_removed(self):
        result = sanitize({
            "safe": "kept", "password": "gone", "password_hash": "gone",
            "current_password": "gone", "new_password": "gone",
            "nested": [{"Authorization": "gone", "access_token": "gone", "ok": True}],
            "credentials": {"api_key": "gone"},
        })
        self.assertEqual(result, {"safe": "kept", "nested": [{"ok": True}]})

    def test_common_types_are_json_safe(self):
        identifier = uuid4()
        timestamp = datetime.now(timezone.utc)
        result = sanitize({"id": identifier, "at": timestamp, "action": AuditAction.CREATE})
        self.assertEqual(result["id"], str(identifier))
        self.assertEqual(result["at"], timestamp.isoformat())
        self.assertEqual(result["action"], "CREATE")


class AuditServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AuditService()
        self.service.repository = Mock()
        self.service.repository.add.side_effect = lambda _db, event: event
        self.actor = SimpleNamespace(
            id=uuid4(), organization_id=uuid4(), business_unit_id=uuid4(),
            division_id=uuid4(), department_id=uuid4(),
        )

    def test_update_records_only_changed_fields(self):
        entity = SimpleNamespace(id=uuid4(), name="after", enabled=True)
        event = self.service.record_update(
            Mock(), entity=entity, actor=self.actor,
            before={"id": entity.id, "name": "before", "enabled": True},
        )
        self.assertEqual(event.action, "UPDATE")
        self.assertEqual(event.changes, {"name": {"before": "before", "after": "after"}})

    def test_create_captures_actor_entity_and_ownership(self):
        entity = SimpleNamespace(id=uuid4(), name="created")
        event = self.service.record_create(Mock(), entity=entity, actor=self.actor, owner=self.actor)
        self.assertEqual(event.actor_user_id, self.actor.id)
        self.assertEqual(event.entity_type, "SimpleNamespace")
        self.assertEqual(event.entity_id, entity.id)
        self.assertEqual(event.organization_id, self.actor.organization_id)
        self.assertIn("created", event.changes)

    def test_delete_preserves_safe_snapshot(self):
        entity = SimpleNamespace(id=uuid4(), name="removed")
        event = self.service.record_delete(
            Mock(), entity=entity, actor=self.actor,
            before={"name": "removed", "password_hash": "never"}, owner=self.actor,
        )
        self.assertEqual(event.action, "DELETE")
        self.assertEqual(event.changes, {"deleted": {"name": "removed"}})

    def test_reason_is_supported(self):
        event = self.service.record_action(
            Mock(), action="OVERRIDE", entity_type="Result", actor=self.actor,
            reason="Documented correction",
        )
        self.assertEqual(event.reason, "Documented correction")
        self.assertEqual(event.action, "OVERRIDE")

    def test_request_context_is_captured(self):
        request_id = str(uuid4())
        token = set_request_context(RequestContext(request_id=request_id, source_ip="127.0.0.1"))
        try:
            event = self.service.record_action(
                Mock(), action="CREATE", entity_type="Sample", actor=self.actor
            )
        finally:
            reset_request_context(token)
        self.assertEqual(event.request_id, UUID(request_id))
        self.assertEqual(event.source_ip, "127.0.0.1")

    def test_model_has_no_mutability_columns(self):
        columns = set(AuditEvent.__table__.columns.keys())
        self.assertNotIn("is_active", columns)
        self.assertNotIn("version", columns)
        self.assertNotIn("updated_at", columns)


class AuditApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_service = audit.service
        audit.service = Mock()
        audit.service.list.return_value = []
        app.dependency_overrides[get_db] = lambda: Mock()

    def tearDown(self):
        audit.service = self.original_service
        app.dependency_overrides.clear()

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/audit/events").status_code, 401)

    def test_requires_dedicated_permission(self):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            user_roles=[], force_password_change=False
        )
        response = self.client.get("/audit/events", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 403)

    def test_pagination_and_filters_are_forwarded(self):
        actor = SimpleNamespace(id=uuid4())
        app.dependency_overrides[audit.can_view_audit] = lambda: actor
        entity_id = uuid4()
        response = self.client.get(
            f"/audit/events?entity_type=User&entity_id={entity_id}&action=create&limit=25&offset=10"
        )
        self.assertEqual(response.status_code, 200)
        kwargs = audit.service.list.call_args.kwargs
        self.assertEqual(kwargs["entity_type"], "User")
        self.assertEqual(kwargs["entity_id"], entity_id)
        self.assertEqual(kwargs["limit"], 25)
        self.assertEqual(kwargs["offset"], 10)

    def test_maximum_page_size_is_enforced(self):
        app.dependency_overrides[audit.can_view_audit] = lambda: SimpleNamespace(id=uuid4())
        self.assertEqual(self.client.get("/audit/events?limit=501").status_code, 422)

    def test_request_id_header_is_server_uuid(self):
        app.dependency_overrides[audit.can_view_audit] = lambda: SimpleNamespace(id=uuid4())
        response = self.client.get("/audit/events", headers={"X-Request-ID": "attacker-value"})
        self.assertEqual(response.status_code, 200)
        UUID(response.headers["X-Request-ID"])
        self.assertNotEqual(response.headers["X-Request-ID"], "attacker-value")

    def test_no_mutation_routes_exist(self):
        paths = app.openapi()["paths"]
        self.assertEqual(set(paths["/audit/events"]), {"get"})
        self.assertEqual(set(paths["/audit/events/{event_id}"]), {"get"})


class PermissionSeedTests(unittest.TestCase):
    def test_audit_permission_is_unique(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual(codes.count("audit.view"), 1)
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
