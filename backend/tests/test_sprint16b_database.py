"""Rollback-isolated PostgreSQL integration tests for Sprint 16B services."""

import unittest
from collections import Counter
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException
from app.database.session import engine
from app.models.audit_event import AuditEvent
from app.models.organization.organization import Organization
from app.services.business.instrument_type_service import InstrumentTypeService
from app.services.business.location_service import LocationService
from app.services.business.manufacturer_service import ManufacturerService
from app.services.business.material_service import MaterialService


def actor_with_permissions(organization_id, *permissions, scope="ORGANIZATION"):
    mappings = [SimpleNamespace(
        is_active=True,
        permission=SimpleNamespace(is_active=True, permission_code=code),
    ) for code in permissions]
    role = SimpleNamespace(is_active=True, role_permissions=mappings)
    assignment = SimpleNamespace(is_active=True, role=role, access_scope=scope)
    return SimpleNamespace(
        id=None, organization_id=organization_id, user_roles=[assignment],
        business_unit_id=None, division_id=None, department_id=None,
    )


class Sprint16BDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        self.organization = Organization(
            organization_code=f"S16B{uuid4().hex[:12].upper()}",
            organization_name="Sprint 16B Test Organization",
        )
        self.other_organization = Organization(
            organization_code=f"S16X{uuid4().hex[:12].upper()}",
            organization_name="Other Test Organization",
        )
        self.db.add_all([self.organization, self.other_organization])
        self.db.flush()

    def tearDown(self):
        self.db.close()
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()

    def test_manufacturer_crud_concurrency_and_audit_actions(self):
        service = ManufacturerService()
        actor = actor_with_permissions(
            self.organization.id, "manufacturer.create", "manufacturer.view",
            "manufacturer.update", "manufacturer.delete",
        )
        record = service.create_scoped(self.db, actor, {"code": " maker ", "name": "Maker"})
        self.assertEqual((record.code, record.version), ("MAKER", 1))
        record = service.update_for_actor(
            self.db, actor, record.id, 1, {"name": "Updated Maker"}
        )
        self.assertEqual(record.version, 2)
        record = service.set_active_scoped(
            self.db, actor, record.id, 2, False, "manufacturer.update"
        )
        self.assertEqual((record.is_active, record.version), (False, 3))
        record = service.set_active_scoped(
            self.db, actor, record.id, 3, True, "manufacturer.update"
        )
        service.delete_scoped(
            self.db, actor, record.id, 4, "manufacturer.delete"
        )
        actions = [row.action for row in self.db.query(AuditEvent).filter(
            AuditEvent.entity_id == record.id
        ).all()]
        self.assertEqual(Counter(actions), Counter(
            ["CREATE", "UPDATE", "DEACTIVATE", "ACTIVATE", "DELETE"]
        ))

    def test_duplicate_safe_error_search_filters_pagination_and_isolation(self):
        service = MaterialService()
        actor = actor_with_permissions(self.organization.id, "material.create", "material.view")
        other_actor = actor_with_permissions(self.other_organization.id, "material.create", "material.view")
        first = service.create_scoped(self.db, actor, {
            "code": "MAT-02", "name": "Second Reagent", "material_type": "REAGENT"
        })
        service.create_scoped(self.db, actor, {
            "code": "MAT-01", "name": "First Raw", "material_type": "RAW_MATERIAL"
        })
        service.create_scoped(self.db, other_actor, {
            "code": "MAT-02", "name": "Other Organization", "material_type": "REAGENT"
        })
        with self.assertRaisesRegex(DuplicateResourceException, "material with this code"):
            service.create_scoped(self.db, actor, {
                "code": "mat-02", "name": "Duplicate", "material_type": "OTHER"
            })
        rows = service.list_scoped(
            self.db, actor, "material.view", search="reagent", material_type="REAGENT",
            is_active=True, limit=1, offset=0,
        )
        self.assertEqual([row.id for row in rows], [first.id])
        with self.assertRaises(ResourceNotFoundException):
            service.get_scoped(self.db, first.id, other_actor, "material.view")

    def test_self_scope_has_no_rows_and_hierarchy_scope_is_organization_wide(self):
        service = InstrumentTypeService()
        creator = actor_with_permissions(self.organization.id, "instrument_type.create")
        service.create_scoped(self.db, creator, {"code": "HPLC", "name": "HPLC"})
        self_actor = actor_with_permissions(self.organization.id, "instrument_type.view", scope="SELF")
        division_actor = actor_with_permissions(self.organization.id, "instrument_type.view", scope="DIVISION")
        self.assertEqual(service.list_scoped(self.db, self_actor, "instrument_type.view"), [])
        self.assertEqual(len(service.list_scoped(self.db, division_actor, "instrument_type.view")), 1)

    def test_location_parent_filters_and_foreign_parent_concealment(self):
        service = LocationService()
        actor = actor_with_permissions(self.organization.id, "location.create", "location.view")
        parent = service.create_scoped(self.db, actor, {
            "code": "SITE", "name": "Site", "location_type": "SITE"
        })
        child = service.create_scoped(self.db, actor, {
            "code": "LAB", "name": "Laboratory", "location_type": "LABORATORY",
            "parent_location_id": parent.id,
        })
        rows = service.list_scoped(
            self.db, actor, "location.view", parent_location_id=parent.id,
            location_type="LABORATORY",
        )
        self.assertEqual([row.id for row in rows], [child.id])
        other_actor = actor_with_permissions(self.other_organization.id, "location.create")
        with self.assertRaises(ResourceNotFoundException):
            service.create_scoped(self.db, other_actor, {
                "code": "FOREIGN", "name": "Foreign", "location_type": "ROOM",
                "parent_location_id": parent.id,
            })


if __name__ == "__main__":
    unittest.main()
