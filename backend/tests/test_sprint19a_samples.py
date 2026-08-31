"""Focused PostgreSQL/domain tests for Sprint 19A."""
import unittest
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceException, ValidationException, VersionConflictException
from app.database.session import engine
from app.models.business.material import Material
from app.models.business.sample import Sample, SamplePriority, SampleStatus, SampleTest, SampleTestStatus
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.models.organization.organization import Organization
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.qc_method_service import MethodService, MethodVersionService, TestService
from app.services.business.sample_service import SampleService, SampleTestService
from app.services.business.specification_service import SpecificationLimitService, SpecificationService, SpecificationTestService, SpecificationVersionService


class Sprint19AContractTests(unittest.TestCase):
    def test_vocabularies_and_permissions(self):
        self.assertEqual(set(SampleStatus), {"REGISTERED", "IN_TESTING", "REVIEW", "FINALIZED", "CANCELLED"})
        self.assertEqual(set(SamplePriority), {"LOW", "NORMAL", "HIGH", "URGENT"})
        self.assertEqual(set(SampleTestStatus), {"PENDING", "ASSIGNED", "IN_PROGRESS", "RESULT_ENTERED", "REVIEWED", "FINALIZED", "CANCELLED"})
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual(
            {code for code in codes if code.startswith("sample.")},
            {"sample.view", "sample.create", "sample.update", "sample.cancel", "sample.assign"},
        )
        self.assertEqual(len(codes), len(set(codes)))


class Sprint19ADatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect(); self.transaction = self.connection.begin(); self.db = Session(bind=self.connection)
        suffix = uuid4().hex[:10].upper()
        self.org = Organization(organization_code=f"S19{suffix}", organization_name="Sprint 19A")
        self.other_org = Organization(organization_code=f"T19{suffix}", organization_name="Other")
        self.db.add_all([self.org, self.other_org]); self.db.flush()
        self.material = Material(organization_id=self.org.id, code="MAT", name="Material", material_type="OTHER")
        self.other_material = Material(organization_id=self.other_org.id, code="MAT", name="Other", material_type="OTHER")
        self.db.add_all([self.material, self.other_material]); self.db.flush()
        self.samples = SampleService(); self.sample_tests = SampleTestService()
        self.specs = SpecificationService(); self.spec_versions = SpecificationVersionService()
        self.spec_tests = SpecificationTestService(); self.limits = SpecificationLimitService()
        self.tests = TestService(); self.methods = MethodService(); self.method_versions = MethodVersionService()

    def tearDown(self):
        self.db.close()
        if self.transaction.is_active: self.transaction.rollback()
        self.connection.close()

    def _basis(self, org=None, material=None, code="SPEC", approved=True):
        org = org or self.org; material = material or self.material
        spec = self.specs.create(self.db, org.id, {"material_id": material.id, "specification_code": f"{code}-{uuid4().hex[:6]}", "specification_name": "Release"})
        version = self.spec_versions.create(self.db, org.id, spec.id, {"version_number": 1})
        test = self.tests.create(self.db, org.id, {"test_code": f"T-{uuid4().hex[:6]}", "test_name": "Assay"})
        method = self.methods.create(self.db, org.id, {"method_code": f"M-{uuid4().hex[:6]}", "method_name": "Method"})
        method_version = self.method_versions.create(self.db, org.id, method.id, {"version_number": 1})
        method_version = self.method_versions.transition_status(self.db, org.id, method_version.id, method_version.version, "APPROVED")
        source = self.spec_tests.create(self.db, org.id, version.id, {"test_id": test.id, "method_version_id": method_version.id, "sequence_number": 1, "is_required": True, "display_name": "Assay result"})
        limit = self.limits.create(self.db, org.id, source.id, {"criterion_type": "INFORMATIONAL", "parameter_name": "Result"})
        if approved: version = self.spec_versions.transition_status(self.db, org.id, version.id, version.version, "APPROVED")
        return version, source, method_version, limit

    def _create(self, number="S-001", **extra):
        version = extra.pop("version", None) or self._basis()[0]
        values = {"sample_number": number, "material_id": self.material.id, "specification_version_id": version.id, **extra}
        return self.samples.create(self.db, self.org.id, values)

    def test_registration_normalization_uniqueness_references_and_concurrency(self):
        version, _, _, _ = self._basis()
        sample = self.samples.create(self.db, self.org.id, {"sample_number": " s-001 ", "material_id": self.material.id, "specification_version_id": version.id, "priority": "HIGH", "notes": " "})
        self.assertEqual((sample.sample_number, sample.status, sample.priority, sample.notes), ("S-001", "REGISTERED", "HIGH", None))
        with self.assertRaises(DuplicateResourceException): self.samples.create(self.db, self.org.id, {"sample_number": "s-001", "material_id": self.material.id, "specification_version_id": version.id})
        other_version = self._basis(self.other_org, self.other_material)[0]
        other = self.samples.create(self.db, self.other_org.id, {"sample_number": "S-001", "material_id": self.other_material.id, "specification_version_id": other_version.id})
        self.assertEqual(other.sample_number, sample.sample_number)
        updated = self.samples.update_expected(self.db, self.org.id, sample.id, 1, {"notes": " Updated ", "specification_version_id": other_version.id})
        self.assertEqual((updated.notes, updated.version, updated.specification_version_id), ("Updated", 2, version.id))
        with self.assertRaises(VersionConflictException): self.samples.update_expected(self.db, self.org.id, sample.id, 1, {"notes": "stale"})

    def test_rejects_invalid_testing_basis_and_hierarchy(self):
        draft = self._basis(approved=False)[0]
        with self.assertRaises(ValidationException): self.samples.create(self.db, self.org.id, {"sample_number": "DRAFT", "material_id": self.material.id, "specification_version_id": draft.id})
        other_version = self._basis(self.other_org, self.other_material)[0]
        with self.assertRaises(ValidationException): self.samples.create(self.db, self.org.id, {"sample_number": "CROSS", "material_id": self.material.id, "specification_version_id": other_version.id})
        wrong_material = Material(organization_id=self.org.id, code="WRONG", name="Wrong", material_type="OTHER"); self.db.add(wrong_material); self.db.flush()
        version = self._basis()[0]
        with self.assertRaises(ValidationException): self.samples.create(self.db, self.org.id, {"sample_number": "WRONG", "material_id": wrong_material.id, "specification_version_id": version.id})
        bu = BusinessUnit(organization_id=self.org.id, business_unit_code=f"BU{uuid4().hex[:6]}", business_unit_name="BU")
        other_bu = BusinessUnit(organization_id=self.other_org.id, business_unit_code=f"BU{uuid4().hex[:6]}", business_unit_name="Other BU")
        self.db.add_all([bu, other_bu]); self.db.flush()
        division = Division(business_unit_id=bu.id, division_code=f"DV{uuid4().hex[:6]}", division_name="Division")
        self.db.add(division); self.db.flush()
        department = Department(division_id=division.id, department_code=f"DP{uuid4().hex[:6]}", department_name="Department")
        self.db.add(department); self.db.flush()
        accepted = self.samples.create(self.db, self.org.id, {"sample_number": "HIER", "material_id": self.material.id, "specification_version_id": version.id, "business_unit_id": bu.id, "division_id": division.id, "department_id": department.id})
        self.assertEqual(accepted.department_id, department.id)
        with self.assertRaises(ValidationException): self.samples.create(self.db, self.org.id, {"sample_number": "BAD-HIER", "material_id": self.material.id, "specification_version_id": version.id, "business_unit_id": other_bu.id})

    def test_generation_is_idempotent_and_freezes_exact_traceability(self):
        version, source, method_version, limit = self._basis()
        sample = self.samples.create(self.db, self.org.id, {"sample_number": "TRACE", "material_id": self.material.id, "specification_version_id": version.id})
        generated = self.sample_tests.generate(self.db, self.org.id, sample.id)
        again = self.sample_tests.generate(self.db, self.org.id, sample.id)
        self.assertEqual(len(generated), 1); self.assertEqual(len(again), 1)
        item = again[0]
        self.assertEqual((item.specification_test_id, item.test_id, item.method_version_id, item.sequence_number, item.is_required, item.display_name), (source.id, source.test_id, method_version.id, 1, True, "Assay result"))
        self.assertEqual(item.specification_test.limits[0].id, limit.id)
        later_spec = self._basis(code="LATER")[0]
        later_method = self.methods.create(self.db, self.org.id, {"method_code": f"L-{uuid4().hex[:6]}", "method_name": "Later"})
        later_method_version = self.method_versions.create(self.db, self.org.id, later_method.id, {"version_number": 2})
        self.assertNotEqual(later_spec.id, sample.specification_version_id)
        self.assertNotEqual(later_method_version.id, item.method_version_id)
        self.assertEqual((sample.specification_version_id, item.specification_test_id, item.method_version_id), (version.id, source.id, method_version.id))

    def test_database_status_priority_sequence_and_duplicate_constraints(self):
        version, source, _, _ = self._basis(); sample = self.samples.create(self.db, self.org.id, {"sample_number": "CHECK", "material_id": self.material.id, "specification_version_id": version.id})
        for record in (
            Sample(organization_id=self.org.id, sample_number="BAD-STATUS", material_id=self.material.id, specification_version_id=version.id, status="BAD"),
            Sample(organization_id=self.org.id, sample_number="BAD-PRIORITY", material_id=self.material.id, specification_version_id=version.id, priority="BAD"),
            SampleTest(sample_id=sample.id, specification_test_id=source.id, test_id=source.test_id, sequence_number=0),
        ):
            nested = self.db.begin_nested(); self.db.add(record)
            with self.assertRaises(IntegrityError): self.db.flush()
            nested.rollback()
