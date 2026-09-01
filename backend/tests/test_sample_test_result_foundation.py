"""Focused PostgreSQL tests for the Sprint 21A result foundation."""

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.business.instrument import Instrument
from app.models.business.instrument_type import InstrumentType
from app.models.business.qc_method import MethodParameter, MethodVersion
from app.models.business.sample_test_result import SampleTestResult
from app.models.business.specification import SpecificationVersion
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.sample_test_result_service import SampleTestResultService
from tests.test_sprint19a_samples import Sprint19ADatabaseTests


class Sprint21AResultFoundationTests(Sprint19ADatabaseTests):
    def setUp(self):
        super().setUp()
        self.service = SampleTestResultService()
        specification_version, _, _, _ = self._basis()
        self.sample = self.samples.create(self.db, self.org.id, {
            "sample_number": f"RESULT-{uuid4().hex[:6]}",
            "material_id": self.material.id,
            "specification_version_id": specification_version.id,
        })
        self.sample_test = self.sample_tests.generate(self.db, self.org.id, self.sample.id)[0]
        self.sample_test.status = "ASSIGNED"
        self.method_version = self.db.get(MethodVersion, self.sample_test.method_version_id)
        self.parameters = {}
        for value_type in ("TEXT", "NUMBER", "INTEGER", "BOOLEAN", "DATE", "DATETIME"):
            parameter = MethodParameter(
                method_version_id=self.method_version.id,
                parameter_code=f"{value_type}-{uuid4().hex[:6]}",
                parameter_name=value_type,
                value_type=value_type,
            )
            self.db.add(parameter)
            self.parameters[value_type] = parameter
        self.instrument_type = InstrumentType(
            organization_id=self.org.id, code=f"TYPE-{uuid4().hex[:6]}", name="Analyzer"
        )
        self.other_instrument_type = InstrumentType(
            organization_id=self.other_org.id, code=f"OTYPE-{uuid4().hex[:6]}", name="Other"
        )
        self.db.add_all([self.instrument_type, self.other_instrument_type]); self.db.flush()
        self.instrument = Instrument(
            organization_id=self.org.id, instrument_type_id=self.instrument_type.id,
            instrument_code=f"I-{uuid4().hex[:6]}", instrument_name="Analyzer",
        )
        self.instrument_two = Instrument(
            organization_id=self.org.id, instrument_type_id=self.instrument_type.id,
            instrument_code=f"J-{uuid4().hex[:6]}", instrument_name="Backup",
        )
        self.other_instrument = Instrument(
            organization_id=self.other_org.id, instrument_type_id=self.other_instrument_type.id,
            instrument_code=f"X-{uuid4().hex[:6]}", instrument_name="Other",
        )
        self.db.add_all([self.instrument, self.instrument_two, self.other_instrument]); self.db.flush()

    def draft(self):
        return self.service.create_draft_result(self.db, self.org.id, self.sample_test.id)

    def test_permissions_are_exact_and_unique(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual(
            {code for code in codes if code.startswith("sample_test_result.")},
            {f"sample_test_result.{action}" for action in ("view", "create", "update", "submit", "review")},
        )
        self.assertEqual(len(codes), len(set(codes)))

    def test_result_scope_inherits_parent_and_sequence_retains_history(self):
        first = self.draft(); second = self.draft()
        self.assertEqual((first.sequence_number, second.sequence_number), (1, 2))
        self.assertEqual(
            [row.id for row in self.service.result_repository.list_for_sample_test(self.db, self.sample_test.id)],
            [second.id, first.id],
        )
        with self.assertRaises(ResourceNotFoundException):
            self.service.create_draft_result(self.db, self.other_org.id, self.sample_test.id)
        nested = self.db.begin_nested()
        self.db.add(SampleTestResult(sample_test_id=self.sample_test.id, sequence_number=1))
        with self.assertRaises(IntegrityError): self.db.flush()
        nested.rollback()

    def test_historical_method_parameter_and_specification_basis_is_frozen(self):
        original_specification_version_id = self.sample.specification_version_id
        result = self.draft()
        recorded = self.service.add_parameter_result(
            self.db, result.id, self.parameters["TEXT"].id, "TEXT", text_value="v1"
        )
        method_two = MethodVersion(method_id=self.method_version.method_id, version_number=2, status="DRAFT")
        self.db.add(method_two); self.db.flush()
        v2_only = MethodParameter(
            method_version_id=method_two.id, parameter_code=f"NEW-{uuid4().hex[:6]}",
            parameter_name="New", value_type="TEXT",
        )
        self.db.add(v2_only); self.db.flush()
        with self.assertRaises(ValidationException):
            self.service.add_parameter_result(
                self.db, result.id, v2_only.id, "TEXT", text_value="wrong basis"
            )
        original_version = self.db.get(SpecificationVersion, original_specification_version_id)
        newer_specification_version = self.spec_versions.create(
            self.db, self.org.id, original_version.specification_id, {"version_number": 2}
        )
        self.assertEqual(recorded.method_parameter.method_version_id, self.method_version.id)
        self.assertEqual(self.sample_test.method_version_id, self.method_version.id)
        self.assertEqual(self.sample.specification_version_id, original_specification_version_id)
        self.assertNotEqual(newer_specification_version.id, original_specification_version_id)

    def test_all_typed_values_and_invalid_combinations(self):
        values = {
            "TEXT": ("text_value", "abc"),
            "NUMBER": ("numeric_value", Decimal("12.50")),
            "INTEGER": ("integer_value", 7),
            "BOOLEAN": ("boolean_value", True),
            "DATE": ("date_value", date(2026, 9, 1)),
            "DATETIME": ("datetime_value", datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)),
        }
        for value_type, (column, value) in values.items():
            result = self.draft()
            record = self.service.add_parameter_result(
                self.db, result.id, self.parameters[value_type].id, value_type, **{column: value}
            )
            self.assertEqual(getattr(record, column), value)
        invalid = self.draft()
        cases = [
            ("TEXT", {"numeric_value": Decimal("1")}),
            ("TEXT", {"text_value": "x", "integer_value": 1}),
            ("DATE", {"date_value": datetime(2026, 9, 1, tzinfo=timezone.utc)}),
            ("DATETIME", {"datetime_value": datetime(2026, 9, 1)}),
        ]
        for value_type, typed in cases:
            with self.assertRaises(ValidationException):
                self.service.add_parameter_result(
                    self.db, invalid.id, self.parameters[value_type].id, value_type, **typed
                )
        mismatch = self.draft()
        with self.assertRaises(ValidationException):
            self.service.add_parameter_result(
                self.db, mismatch.id, self.parameters["TEXT"].id, "INTEGER", integer_value=1
            )

    def test_content_is_draft_only_and_finalized_history_is_retained(self):
        result = self.draft()
        result.status = "FINALIZED"; self.db.flush()
        with self.assertRaises(ValidationException):
            self.service.add_parameter_result(
                self.db, result.id, self.parameters["TEXT"].id, "TEXT", text_value="late"
            )
        self.assertIsNotNone(self.service.result_repository.get(self.db, result.id))
        later = self.draft()
        self.assertEqual(later.sequence_number, 2)
        self.assertEqual(result.status, "FINALIZED")

    def test_zero_one_multiple_duplicate_cross_org_and_historical_instruments(self):
        zero = self.draft()
        self.assertEqual(self.service.instrument_usage_repository.list_for_result(self.db, zero.id), [])
        first = self.service.add_instrument_usage(
            self.db, self.org.id, zero.id, self.instrument.id, "primary"
        )
        second = self.service.add_instrument_usage(
            self.db, self.org.id, zero.id, self.instrument_two.id, "backup"
        )
        self.assertEqual({row.id for row in self.service.instrument_usage_repository.list_for_result(self.db, zero.id)}, {first.id, second.id})
        with self.assertRaises(ValidationException):
            self.service.add_instrument_usage(self.db, self.org.id, zero.id, self.instrument.id)
        with self.assertRaises(ValidationException):
            self.service.add_instrument_usage(self.db, self.org.id, zero.id, self.other_instrument.id)
        original_name = first.instrument.instrument_name
        self.instrument.instrument_name = "Renamed master"; self.db.flush()
        self.assertEqual(first.instrument_id, self.instrument.id)
        self.assertNotEqual(original_name, self.instrument.instrument_name)


if __name__ == "__main__":
    unittest.main()
