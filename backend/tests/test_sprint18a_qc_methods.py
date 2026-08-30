"""Focused PostgreSQL and domain tests for Sprint 18A."""

import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException, VersionConflictException
from app.database.session import engine
from app.models.business.qc_method import Method, MethodParameter, MethodVersion, Test
from app.models.organization.organization import Organization
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.qc_method_service import MethodParameterService, MethodService, MethodVersionService, TestService


class Sprint18AContractTests(unittest.TestCase):
    def test_permissions_are_exact_and_unique(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        expected = {
            f"{resource}.{action}"
            for resource in ("test", "method")
            for action in ("view", "create", "update", "delete")
        }
        self.assertEqual({code for code in codes if code.split(".")[0] in {"test", "method"}}, expected)
        self.assertEqual(len(codes), len(set(codes)))
        self.assertFalse(any(code.startswith("specification.") for code in codes))

    def test_test_and_method_are_independent_masters(self):
        self.assertEqual(Test.__tablename__, "qc_tests")
        self.assertEqual(Method.__tablename__, "methods")
        self.assertNotIn("test_id", Method.__table__.columns)
        self.assertNotIn("method_id", Test.__table__.columns)


class Sprint18ADatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:10].upper()
        self.organization = Organization(organization_code=f"Q18{suffix}", organization_name="Sprint 18A")
        self.other_organization = Organization(organization_code=f"R18{suffix}", organization_name="Other")
        self.db.add_all([self.organization, self.other_organization])
        self.db.flush()
        self.test_service = TestService()
        self.method_service = MethodService()
        self.version_service = MethodVersionService()
        self.parameter_service = MethodParameterService()

    def tearDown(self):
        self.db.close()
        if self.transaction.is_active:
            self.transaction.rollback()
        self.connection.close()

    def _method(self, code="METHOD-1"):
        return self.method_service.create(self.db, self.organization.id, {
            "method_code": code, "method_name": "Method",
        })

    def _version(self, method=None, number=1):
        method = method or self._method()
        return self.version_service.create(self.db, self.organization.id, method.id, {
            "version_number": number, "version_label": f" Version {number} ",
        })

    def _expect_integrity(self, record):
        savepoint = self.db.begin_nested()
        self.db.add(record)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        savepoint.rollback()

    def test_test_persistence_normalization_uniqueness_and_concurrency(self):
        record = self.test_service.create(self.db, self.organization.id, {
            "test_code": " assay-1 ", "test_name": "  Assay One  ",
            "description": " ", "test_category": " Physical ", "default_unit": " % ",
        })
        self.assertEqual(record.test_code, "ASSAY-1")
        self.assertEqual(record.test_name, "Assay One")
        self.assertIsNone(record.description)
        self.assertEqual(record.test_category, "Physical")
        updated = self.test_service.update_expected(
            self.db, self.organization.id, record.id, 1, {"test_name": " Updated "}
        )
        self.assertEqual((updated.test_name, updated.version), ("Updated", 2))
        with self.assertRaises(VersionConflictException):
            self.test_service.update_expected(
                self.db, self.organization.id, record.id, 1, {"test_name": "Stale"}
            )

    def test_test_and_method_codes_are_unique_per_organization(self):
        self.db.add(Test(organization_id=self.organization.id, test_code="SHARED", test_name="One"))
        self.db.add(Method(organization_id=self.organization.id, method_code="SHARED", method_name="One"))
        self.db.flush()
        self._expect_integrity(Test(organization_id=self.organization.id, test_code="SHARED", test_name="Duplicate"))
        self._expect_integrity(Method(organization_id=self.organization.id, method_code="SHARED", method_name="Duplicate"))
        self.db.add_all([
            Test(organization_id=self.other_organization.id, test_code="SHARED", test_name="Other"),
            Method(organization_id=self.other_organization.id, method_code="SHARED", method_name="Other"),
        ])
        self.db.flush()

    def test_method_normalization_and_persistence(self):
        method = self.method_service.create(self.db, self.organization.id, {
            "method_code": " hplc-1 ", "method_name": "  General analysis  ",
            "description": " ",
        })
        self.assertEqual(method.method_code, "HPLC-1")
        self.assertEqual(method.method_name, "General analysis")
        self.assertIsNone(method.description)

    def test_method_version_constraints_effectivity_and_restrictive_fk(self):
        method = self._method()
        version = self._version(method)
        self.assertEqual((version.status, version.version_number), ("DRAFT", 1))
        self._expect_integrity(MethodVersion(method_id=method.id, version_number=1, status="DRAFT"))
        self._expect_integrity(MethodVersion(method_id=method.id, version_number=0, status="DRAFT"))
        self._expect_integrity(MethodVersion(method_id=method.id, version_number=2, status="INVALID"))
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValidationException):
            self.version_service.create(self.db, self.organization.id, method.id, {
                "version_number": 2, "effective_from": now,
                "effective_to": now - timedelta(days=1),
            })
        self._expect_integrity(MethodVersion(
            method_id=method.id, version_number=3, status="DRAFT",
            effective_from=now, effective_to=now - timedelta(days=1),
        ))
        savepoint = self.db.begin_nested()
        self.db.delete(method)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        savepoint.rollback()
        self.db.expire_all()

    def test_only_draft_method_versions_are_structurally_editable(self):
        method = self._method()
        draft = self._version(method, 1)
        updated = self.version_service.update_draft(
            self.db, self.organization.id, draft.id, draft.version,
            {"description": " Draft content "},
        )
        self.assertEqual((updated.description, updated.version), ("Draft content", 2))
        for number, target in ((2, "APPROVED"), (3, "RETIRED"), (4, "SUPERSEDED")):
            version = self._version(method, number)
            if target == "SUPERSEDED":
                version = self.version_service.transition_status(
                    self.db, self.organization.id, version.id, version.version, "APPROVED"
                )
            version = self.version_service.transition_status(
                self.db, self.organization.id, version.id, version.version, target
            )
            with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
                self.version_service.update_draft(
                    self.db, self.organization.id, version.id, version.version,
                    {"description": "Overwrite"},
                )
            with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
                self.version_service.delete_draft(
                    self.db, self.organization.id, version.id, version.version
                )

    def test_method_parameter_normalization_constraints_and_draft_edit(self):
        version = self._version()
        parameter = self.parameter_service.create(
            self.db, self.organization.id, version.id,
            {"parameter_code": " temp ", "parameter_name": " Temperature ",
             "value_type": "NUMBER", "unit": " C ", "sequence_number": 1},
        )
        self.assertEqual((parameter.parameter_code, parameter.parameter_name, parameter.unit), ("TEMP", "Temperature", "C"))
        updated = self.parameter_service.update_draft(
            self.db, self.organization.id, parameter.id, parameter.version,
            {"default_value": " 25 "},
        )
        self.assertEqual((updated.default_value, updated.version), ("25", 2))
        self._expect_integrity(MethodParameter(
            method_version_id=version.id, parameter_code="TEMP",
            parameter_name="Duplicate", value_type="NUMBER",
        ))
        self._expect_integrity(MethodParameter(
            method_version_id=version.id, parameter_code="TYPE",
            parameter_name="Bad", value_type="OBJECT",
        ))
        self._expect_integrity(MethodParameter(
            method_version_id=version.id, parameter_code="SEQ",
            parameter_name="Bad", value_type="TEXT", sequence_number=0,
        ))
        with self.assertRaises(ValidationException):
            self.parameter_service.create(
                self.db, self.organization.id, version.id,
                {"parameter_code": "BAD", "parameter_name": "Bad",
                 "value_type": "TEXT", "sequence_number": 0},
            )

    def test_approved_version_protects_parameters(self):
        version = self._version()
        parameter = self.parameter_service.create(
            self.db, self.organization.id, version.id,
            {"parameter_code": "FLAG", "parameter_name": "Flag", "value_type": "BOOLEAN"},
        )
        version = self.version_service.transition_status(
            self.db, self.organization.id, version.id, version.version, "APPROVED"
        )
        with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
            self.parameter_service.update_draft(
                self.db, self.organization.id, parameter.id, parameter.version,
                {"parameter_name": "Changed"},
            )
        with self.assertRaisesRegex(ValidationException, "Only DRAFT"):
            self.parameter_service.delete_draft(
                self.db, self.organization.id, parameter.id, parameter.version
            )


if __name__ == "__main__":
    unittest.main()
