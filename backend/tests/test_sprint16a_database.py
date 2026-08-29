"""Focused PostgreSQL integration tests for Sprint 16A.

These tests use isolated transactions and always roll them back.
"""

import unittest
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import VersionConflictException
from app.database.session import engine
from app.models.business import Location, Manufacturer, Material
from app.models.organization.organization import Organization
from app.services.business.manufacturer_service import ManufacturerService


class Sprint16DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:12].upper()
        self.organization = Organization(
            organization_code=f"S16A{suffix}", organization_name="Sprint 16A Test Organization"
        )
        self.db.add(self.organization)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def _expect_integrity_error(self, record) -> None:
        savepoint = self.db.begin_nested()
        self.db.add(record)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        savepoint.rollback()

    def test_duplicate_code_in_one_organization_is_rejected(self):
        self.db.add(Manufacturer(
            organization_id=self.organization.id, code="ACME", name="First"
        ))
        self.db.flush()
        self._expect_integrity_error(Manufacturer(
            organization_id=self.organization.id, code="ACME", name="Second"
        ))

    def test_same_code_in_different_organizations_is_allowed(self):
        other = Organization(
            organization_code=f"S16B{uuid4().hex[:12].upper()}", organization_name="Other"
        )
        self.db.add(other)
        self.db.flush()
        self.db.add_all([
            Manufacturer(organization_id=self.organization.id, code="SHARED", name="First"),
            Manufacturer(organization_id=other.id, code="SHARED", name="Second"),
        ])
        self.db.flush()

    def test_database_rejects_invalid_location_and_material_types(self):
        self._expect_integrity_error(Location(
            organization_id=self.organization.id, code="BAD-L", name="Bad", location_type="INVALID"
        ))
        self._expect_integrity_error(Material(
            organization_id=self.organization.id, code="BAD-M", name="Bad", material_type="INVALID"
        ))

    def test_database_rejects_foreign_organization_parent(self):
        other = Organization(
            organization_code=f"S16C{uuid4().hex[:12].upper()}", organization_name="Other"
        )
        parent = Location(
            organization_id=self.organization.id, code="PARENT", name="Parent", location_type="SITE"
        )
        self.db.add_all([other, parent])
        self.db.flush()
        self._expect_integrity_error(Location(
            organization_id=other.id, parent_location_id=parent.id,
            code="CHILD", name="Child", location_type="ROOM",
        ))

    def test_atomic_update_increments_version_and_stale_write_changes_nothing(self):
        service = ManufacturerService()
        record = service.create(
            self.db, self.organization.id, code=" versioned ", name="Original"
        )
        self.db.flush()
        updated = service.update(
            self.db, self.organization.id, record.id, 1, name="Updated"
        )
        self.assertEqual(updated.version, 2)
        with self.assertRaisesRegex(VersionConflictException, "Refresh and try again"):
            service.update(self.db, self.organization.id, record.id, 1, name="Stale")
        self.assertEqual(
            self.db.get(Manufacturer, record.id).name,
            "Updated",
        )


if __name__ == "__main__":
    unittest.main()
