"""Focused secured Stability Chamber Profile API tests."""
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, VersionConflictException
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business.instrument import StabilityChamberProfile
from tests.test_sprint17b_instrument_api import Sprint17BTests, assignment


class Sprint23CChamberProfileTests(Sprint17BTests):
    def test_profile_get_routes_authorize_parent_and_missing_is_404(self):
        self.enable_instruments(); record = self.instrument("PROFILE-GET", department_id=self.department.id)
        profile = StabilityChamberProfile(instrument_id=record.id, temperature_setpoint=25, temperature_unit=" C ")
        self.db.add(profile); self.db.flush()
        client = TestClient(app); actor = self.actor("instrument.view", "DEPARTMENT")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        response = client.get(f"/instruments/{record.id}/chamber-profile")
        self.assertEqual(response.status_code, 200); self.assertEqual(response.json()["id"], str(profile.id))
        missing = self.instrument("PROFILE-MISSING", department_id=self.department.id)
        self.assertEqual(client.get(f"/instruments/{missing.id}/chamber-profile").status_code, 404)
        hidden = self.instrument("PROFILE-HIDDEN", department_id=self.other_department.id)
        self.db.add(StabilityChamberProfile(instrument_id=hidden.id)); self.db.flush()
        self.assertEqual(client.get(f"/instruments/{hidden.id}/chamber-profile").status_code, 404)

    def test_profile_create_update_audit_and_profile_version_concurrency(self):
        record = self.instrument("PROFILE-WRITE", department_id=self.department.id); instrument_version = record.version
        actor = self.actor("instrument.update", "DEPARTMENT")
        profile = self.service.create_chamber_profile_scoped(self.db, actor, record.id, {"temperature_setpoint": 25, "temperature_unit": " C ", "humidity_setpoint": 60, "humidity_unit": " RH ", "description": " Chamber "})
        self.assertEqual((profile.version, profile.temperature_unit, profile.description), (1, "C", "Chamber"))
        self.assertEqual(record.version, instrument_version)
        profile = self.service.update_chamber_profile_scoped(self.db, actor, record.id, profile.version, {"temperature_setpoint": 30})
        self.assertEqual(profile.version, 2); self.assertEqual(record.version, instrument_version)
        events = self.db.query(AuditEvent).filter(AuditEvent.entity_id == profile.id).order_by(AuditEvent.occurred_at).all()
        self.assertEqual([event.action for event in events], ["CREATE", "UPDATE"])
        self.assertTrue(all(event.organization_id == self.org.id for event in events))
        with self.assertRaises(VersionConflictException): self.service.update_chamber_profile_scoped(self.db, actor, record.id, 1, {"temperature_setpoint": 35})

    def test_duplicate_profile_creation_is_rejected(self):
        record = self.instrument("PROFILE-DUPLICATE")
        actor = self.actor("instrument.update", "ORGANIZATION")
        self.service.create_chamber_profile_scoped(self.db, actor, record.id, {})
        with self.assertRaises(DuplicateResourceException):
            self.service.create_chamber_profile_scoped(self.db, actor, record.id, {})

    def test_profile_http_permissions_update_payload_and_out_of_scope_concealment(self):
        self.enable_instruments(); record = self.instrument("PROFILE-HTTP", department_id=self.department.id)
        profile = StabilityChamberProfile(instrument_id=record.id, temperature_setpoint=20, version=4)
        self.db.add(profile); self.db.flush()
        client = TestClient(app); actor = self.actor("instrument.view", "DEPARTMENT")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        self.assertEqual(client.post(f"/instruments/{record.id}/chamber-profile", json={}).status_code, 403)
        actor.user_roles = [assignment("instrument.update", "DEPARTMENT")]
        response = client.put(f"/instruments/{record.id}/chamber-profile", json={"version": 4, "humidity_setpoint": 55})
        self.assertEqual(response.status_code, 200); self.assertEqual(response.json()["version"], 5)
        hidden = self.instrument("PROFILE-HTTP-HIDDEN", department_id=self.other_department.id)
        self.db.add(StabilityChamberProfile(instrument_id=hidden.id)); self.db.flush()
        self.assertEqual(client.put(f"/instruments/{hidden.id}/chamber-profile", json={"version": 1, "description": "hidden"}).status_code, 404)
        self.assertEqual(client.put(f"/instruments/{record.id}/chamber-profile", json={"version": 4, "humidity_setpoint": 50}).status_code, 409)


if __name__ == "__main__":
    import unittest
    unittest.main()
