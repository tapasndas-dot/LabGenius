"""Focused Sprint 17A Instrument Registry tests."""

import unittest
from uuid import uuid4

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
    ValidationException,
    VersionConflictException,
)
from app.database.session import engine
from app.models.business import (
    Instrument,
    InstrumentType,
    Location,
    Manufacturer,
    StabilityChamberProfile,
)
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.organization.organization import Organization
from app.models.user.user import User
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.instrument_service import InstrumentService


class InstrumentContractTests(unittest.TestCase):
    def test_controlled_values_and_scoped_code_are_database_constraints(self):
        checks = {
            constraint.name
            for constraint in Instrument.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        self.assertIn("ck_instruments_status", checks)
        self.assertIn("ck_instruments_criticality", checks)
        uniques = {
            tuple(column.name for column in constraint.columns)
            for constraint in Instrument.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        self.assertIn(("organization_id", "instrument_code"), uniques)
        self.assertNotIn(("serial_number",), uniques)

    def test_normalization_and_application_vocabulary_validation(self):
        values = InstrumentService.normalize({
            "instrument_code": "  inst-01 ",
            "instrument_name": "  Main Chamber  ",
            "model_number": " ",
            "serial_number": " SN-1 ",
            "description": "  ",
            "status": "AVAILABLE",
            "criticality": "HIGH",
        })
        self.assertEqual(values["instrument_code"], "INST-01")
        self.assertEqual(values["instrument_name"], "Main Chamber")
        self.assertIsNone(values["model_number"])
        self.assertEqual(values["serial_number"], "SN-1")
        self.assertIsNone(values["description"])
        with self.assertRaises(ValidationException):
            InstrumentService.normalize({"status": "UNKNOWN"})
        with self.assertRaises(ValidationException):
            InstrumentService.normalize({"criticality": "URGENT"})

    def test_exact_instrument_permissions_only(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        expected = {
            f"instrument.{action}"
            for action in ("view", "create", "update", "delete")
        }
        self.assertEqual({code for code in codes if code.startswith("instrument.")}, expected)
        self.assertEqual(len(codes), len(set(codes)))
        self.assertFalse(any(code.startswith((
            "calibration.", "maintenance.", "qualification."
        )) for code in codes))


class Sprint17ADatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:10].upper()
        self.organization = Organization(
            organization_code=f"I17A{suffix}", organization_name="Instrument Test Org"
        )
        self.other_organization = Organization(
            organization_code=f"J17A{suffix}", organization_name="Other Instrument Org"
        )
        self.db.add_all([self.organization, self.other_organization])
        self.db.flush()
        self.instrument_type = InstrumentType(
            organization_id=self.organization.id, code=f"TYPE{suffix}", name="Chamber"
        )
        self.other_instrument_type = InstrumentType(
            organization_id=self.other_organization.id,
            code=f"OTYPE{suffix}", name="Other Chamber",
        )
        self.manufacturer = Manufacturer(
            organization_id=self.organization.id, code=f"MFR{suffix}", name="Maker"
        )
        self.location = Location(
            organization_id=self.organization.id, code=f"LOC{suffix}",
            name="Room", location_type="ROOM",
        )
        self.db.add_all([
            self.instrument_type, self.other_instrument_type,
            self.manufacturer, self.location,
        ])
        self.db.flush()
        self.service = InstrumentService()

    def tearDown(self):
        self.db.close()
        self.transaction.rollback()
        self.connection.close()

    def _values(self, code="INST-01", **overrides):
        values = {
            "instrument_type_id": self.instrument_type.id,
            "instrument_code": code,
            "instrument_name": "Main instrument",
        }
        values.update(overrides)
        return values

    def _expect_integrity_error(self, record):
        savepoint = self.db.begin_nested()
        self.db.add(record)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        savepoint.rollback()

    def test_creation_defaults_references_and_organization_scoped_code(self):
        record = self.service.create(
            self.db, self.organization.id,
            self._values(
                code=" inst-01 ", manufacturer_id=self.manufacturer.id,
                location_id=self.location.id,
            ),
        )
        self.assertEqual(record.instrument_code, "INST-01")
        self.assertEqual(record.status, "AVAILABLE")
        self.assertFalse(record.calibration_required)
        self.assertFalse(record.maintenance_required)
        self.assertFalse(record.qualification_required)
        with self.assertRaises(DuplicateResourceException):
            self.service.create(self.db, self.organization.id, self._values("INST-01"))
        other = self.service.create(
            self.db, self.other_organization.id,
            self._values("INST-01", instrument_type_id=self.other_instrument_type.id),
        )
        self.assertNotEqual(record.organization_id, other.organization_id)

    def test_database_checks_and_restrictive_reference(self):
        self._expect_integrity_error(Instrument(
            organization_id=self.organization.id,
            **self._values("BAD-STATUS", status="INVALID"),
        ))
        self._expect_integrity_error(Instrument(
            organization_id=self.organization.id,
            **self._values("BAD-CRIT", criticality="URGENT"),
        ))
        self.service.create(self.db, self.organization.id, self._values("REFERENCES-TYPE"))
        savepoint = self.db.begin_nested()
        self.db.delete(self.instrument_type)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        savepoint.rollback()
        self.db.expire_all()

    def test_cross_organization_shared_references_are_rejected(self):
        with self.assertRaises(ValidationException):
            self.service.create(
                self.db, self.organization.id,
                self._values("CROSS-TYPE", instrument_type_id=self.other_instrument_type.id),
            )
        with self.assertRaises(ResourceNotFoundException):
            self.service.validate_references(
                self.db, self.organization.id,
                {"instrument_type_id": uuid4()},
            )

    def test_hierarchy_and_responsible_user_consistency(self):
        unit = BusinessUnit(
            organization_id=self.organization.id,
            business_unit_code=f"BU{uuid4().hex[:8]}", business_unit_name="Unit",
        )
        other_unit = BusinessUnit(
            organization_id=self.other_organization.id,
            business_unit_code=f"OU{uuid4().hex[:8]}", business_unit_name="Other Unit",
        )
        self.db.add_all([unit, other_unit])
        self.db.flush()
        division = Division(
            business_unit_id=unit.id, division_code=f"DV{uuid4().hex[:8]}",
            division_name="Division",
        )
        other_division = Division(
            business_unit_id=other_unit.id, division_code=f"OD{uuid4().hex[:8]}",
            division_name="Other Division",
        )
        self.db.add_all([division, other_division])
        self.db.flush()
        department = Department(
            division_id=division.id, department_code=f"DP{uuid4().hex[:8]}",
            department_name="Department",
        )
        self.db.add(department)
        self.db.flush()
        designation = Designation(
            department_id=department.id, designation_code=f"DS{uuid4().hex[:8]}",
            designation_name="Owner",
        )
        self.db.add(designation)
        self.db.flush()
        user_suffix = uuid4().hex[:10]
        user = User(
            organization_id=self.organization.id, business_unit_id=unit.id,
            division_id=division.id, department_id=department.id,
            designation_id=designation.id, employee_code=f"EMP{user_suffix}",
            first_name="Asset", last_name="Owner", display_name="Asset Owner",
            email=f"asset-{user_suffix}@example.test", username=f"asset-{user_suffix}",
            password_hash="not-a-real-secret-hash",
        )
        self.db.add(user)
        self.db.flush()
        record = self.service.create(
            self.db, self.organization.id,
            self._values(
                "HIERARCHY", business_unit_id=unit.id, division_id=division.id,
                department_id=department.id, responsible_user_id=user.id,
            ),
        )
        self.assertEqual(record.responsible_user_id, user.id)
        with self.assertRaises(ValidationException):
            self.service.create(
                self.db, self.organization.id,
                self._values("BAD-HIERARCHY", business_unit_id=unit.id,
                             division_id=other_division.id),
            )
        with self.assertRaises(ValidationException):
            self.service.create(
                self.db, self.other_organization.id,
                self._values("BAD-OWNER", instrument_type_id=self.other_instrument_type.id,
                             responsible_user_id=user.id),
            )

    def test_expected_version_and_chamber_profile_one_to_one(self):
        record = self.service.create(
            self.db, self.organization.id, self._values("VERSIONED")
        )
        updated = self.service.update_expected(
            self.db, self.organization.id, record.id, 1,
            {"instrument_name": " Updated "},
        )
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.instrument_name, "Updated")
        with self.assertRaises(VersionConflictException):
            self.service.update_expected(
                self.db, self.organization.id, record.id, 1,
                {"instrument_name": "Stale"},
            )
        profile = self.service.create_chamber_profile(
            self.db, self.organization.id, record.id,
            {"temperature_setpoint": 25, "temperature_unit": " C "},
        )
        self.assertEqual(profile.temperature_unit, "C")
        with self.assertRaises(DuplicateResourceException):
            self.service.create_chamber_profile(
                self.db, self.organization.id, record.id,
                {"humidity_setpoint": 60},
            )
        self.assertIsInstance(profile, StabilityChamberProfile)


if __name__ == "__main__":
    unittest.main()
