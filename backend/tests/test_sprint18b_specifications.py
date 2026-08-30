"""Focused PostgreSQL and domain tests for Sprint 18B."""

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceException, ValidationException, VersionConflictException
from app.database.session import engine
from app.models.business.material import Material
from app.models.business.specification import SpecificationLimit, SpecificationVersion
from app.models.organization.organization import Organization
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.qc_method_service import MethodService, MethodVersionService, TestService
from app.services.business.specification_service import (
    SpecificationLimitService,
    SpecificationService,
    SpecificationTestService,
    SpecificationVersionService,
)


class Sprint18BContractTests(unittest.TestCase):
    def test_permissions_are_exact_and_unique(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual(
            {code for code in codes if code.startswith("specification.")},
            {f"specification.{action}" for action in ("view", "create", "update", "delete")},
        )
        self.assertEqual(len(codes), len(set(codes)))


class Sprint18BDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:10].upper()
        self.org = Organization(organization_code=f"S18{suffix}", organization_name="Sprint 18B")
        self.other_org = Organization(organization_code=f"T18{suffix}", organization_name="Other")
        self.db.add_all([self.org, self.other_org])
        self.db.flush()
        self.material = Material(organization_id=self.org.id, code="MAT", name="Material", material_type="OTHER")
        self.other_material = Material(organization_id=self.other_org.id, code="MAT", name="Material", material_type="OTHER")
        self.db.add_all([self.material, self.other_material])
        self.db.flush()
        self.specifications = SpecificationService()
        self.versions = SpecificationVersionService()
        self.tests = SpecificationTestService()
        self.limits = SpecificationLimitService()
        self.test_service = TestService()
        self.method_service = MethodService()
        self.method_versions = MethodVersionService()

    def tearDown(self):
        self.db.close()
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()

    def _specification(self, org=None, material=None, code="SPEC-1"):
        org = org or self.org
        material = material or self.material
        return self.specifications.create(self.db, org.id, {
            "material_id": material.id,
            "specification_code": f" {code.lower()} ",
            "specification_name": "  Release requirements  ",
            "description": " ",
        })

    def _version(self, specification=None, number=1):
        specification = specification or self._specification()
        return self.versions.create(self.db, specification.organization_id, specification.id, {
            "version_number": number, "version_label": " Initial ",
        })

    def _test(self, org=None, code="ASSAY"):
        org = org or self.org
        return self.test_service.create(self.db, org.id, {"test_code": code, "test_name": code.title()})

    def _method_version(self, org=None, code="METHOD", approved=False):
        org = org or self.org
        method = self.method_service.create(self.db, org.id, {"method_code": code, "method_name": code.title()})
        version = self.method_versions.create(self.db, org.id, method.id, {"version_number": 1})
        if approved:
            version = self.method_versions.transition_status(self.db, org.id, version.id, version.version, "APPROVED")
        return version

    def _tree(self, required=True, method_version=None):
        version = self._version(self._specification(code=f"SPEC-{uuid4().hex[:8]}"))
        test = self._test()
        item = self.tests.create(self.db, self.org.id, version.id, {
            "test_id": test.id, "method_version_id": method_version.id if method_version else None,
            "sequence_number": 1, "is_required": required,
        })
        return version, item

    def _expect_integrity(self, record):
        savepoint = self.db.begin_nested()
        self.db.add(record)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        savepoint.rollback()

    def test_specification_normalization_organization_integrity_and_concurrency(self):
        record = self._specification()
        self.assertEqual((record.specification_code, record.specification_name, record.description), ("SPEC-1", "Release requirements", None))
        with self.assertRaises(DuplicateResourceException):
            self._specification(code="SPEC-1")
        other = self._specification(self.other_org, self.other_material, "SPEC-1")
        self.assertEqual(other.specification_code, "SPEC-1")
        with self.assertRaises(ValidationException):
            self.specifications.create(self.db, self.org.id, {"material_id": self.other_material.id, "specification_code": "X", "specification_name": "X"})
        updated = self.specifications.update_expected(self.db, self.org.id, record.id, 1, {"specification_name": " Updated "})
        self.assertEqual((updated.specification_name, updated.version), ("Updated", 2))
        with self.assertRaises(VersionConflictException):
            self.specifications.update_expected(self.db, self.org.id, record.id, 1, {"specification_name": "Stale"})

    def test_version_constraints_effectivity_and_immutability(self):
        specification = self._specification()
        version = self._version(specification)
        self.assertEqual(version.status, "DRAFT")
        with self.assertRaises(DuplicateResourceException):
            self._version(specification)
        with self.assertRaises(ValidationException):
            self.versions.create(self.db, self.org.id, specification.id, {"version_number": 0})
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValidationException):
            self.versions.update_draft(self.db, self.org.id, version.id, version.version, {"effective_from": now, "effective_to": now - timedelta(days=1)})
        version = self.versions.update_draft(self.db, self.org.id, version.id, version.version, {"description": " Draft "})
        version = self.versions.transition_status(self.db, self.org.id, version.id, version.version, "RETIRED")
        with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
            self.versions.update_draft(self.db, self.org.id, version.id, version.version, {"description": "Overwrite"})
        self._expect_integrity(SpecificationVersion(specification_id=specification.id, version_number=2, status="INVALID"))

    def test_test_relationship_integrity_duplicates_sequence_and_exact_method(self):
        version = self._version()
        test = self._test()
        method_version = self._method_version()
        item = self.tests.create(self.db, self.org.id, version.id, {
            "test_id": test.id, "method_version_id": method_version.id, "sequence_number": 1,
        })
        self.assertEqual(item.method_version_id, method_version.id)
        with self.assertRaises(DuplicateResourceException):
            self.tests.create(self.db, self.org.id, version.id, {"test_id": test.id, "sequence_number": 2})
        with self.assertRaises(ValidationException):
            self.tests.create(self.db, self.org.id, version.id, {"test_id": self._test(self.other_org, "OTHER").id, "sequence_number": 2})
        with self.assertRaises(ValidationException):
            self.tests.update_draft(self.db, self.org.id, item.id, item.version, {"method_version_id": self._method_version(self.other_org, "OTHER-M").id})
        with self.assertRaises(ValidationException):
            self.tests.update_draft(self.db, self.org.id, item.id, item.version, {"sequence_number": 0})

    def test_all_limit_criteria_and_contradictions(self):
        _, item = self._tree(required=False)
        cases = [
            {"criterion_type": "BETWEEN", "lower_limit": Decimal("1"), "upper_limit": Decimal("2")},
            {"criterion_type": "MINIMUM", "lower_limit": Decimal("1")},
            {"criterion_type": "MAXIMUM", "upper_limit": Decimal("2")},
            {"criterion_type": "EQUAL", "target_value": Decimal("1.25")},
            {"criterion_type": "TEXT_MATCH", "text_value": " Pass "},
            {"criterion_type": "BOOLEAN", "boolean_value": False},
            {"criterion_type": "INFORMATIONAL"},
        ]
        for sequence, values in enumerate(cases, 1):
            record = self.limits.create(self.db, self.org.id, item.id, {**values, "sequence_number": sequence})
            self.assertEqual(record.sequence_number, sequence)
        invalid = [
            {"criterion_type": "BETWEEN", "lower_limit": 2, "upper_limit": 1},
            {"criterion_type": "MINIMUM", "lower_limit": 1, "upper_limit": 2},
            {"criterion_type": "MAXIMUM"},
            {"criterion_type": "EQUAL", "text_value": "one"},
            {"criterion_type": "TEXT_MATCH", "text_value": " "},
            {"criterion_type": "BOOLEAN"},
            {"criterion_type": "INFORMATIONAL", "target_value": 1},
        ]
        for values in invalid:
            with self.assertRaises(ValidationException):
                self.limits.create(self.db, self.org.id, item.id, values)
        self._expect_integrity(SpecificationLimit(specification_test_id=item.id, criterion_type="INVALID"))

    def test_approval_readiness_and_protected_tree(self):
        empty = self._version()
        with self.assertRaises(ValidationException):
            self.versions.validate_approval_ready(self.db, self.org.id, empty.id)
        method_version = self._method_version(code="READY")
        version, item = self._tree(method_version=method_version)
        self.limits.create(self.db, self.org.id, item.id, {"criterion_type": "INFORMATIONAL"})
        with self.assertRaises(ValidationException):
            self.versions.validate_approval_ready(self.db, self.org.id, version.id)
        method_version = self.method_versions.transition_status(self.db, self.org.id, method_version.id, method_version.version, "APPROVED")
        self.assertTrue(self.versions.validate_approval_ready(self.db, self.org.id, version.id))
        version = self.versions.transition_status(self.db, self.org.id, version.id, version.version, "APPROVED")
        with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
            self.tests.delete_draft(self.db, self.org.id, item.id, item.version)
        limit = item.limits[0]
        with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
            self.limits.update_draft(self.db, self.org.id, limit.id, limit.version, {"description": "No"})
