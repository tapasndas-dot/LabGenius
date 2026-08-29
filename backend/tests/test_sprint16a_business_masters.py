import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.core.exceptions import ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business import InstrumentType, Location, Manufacturer, Material
from app.models.business.location import LocationType
from app.models.business.material import MaterialType
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.location_service import LocationService
from app.services.business.manufacturer_service import ManufacturerService
from app.services.business.material_service import MaterialService
from app.services.business.normalization import normalize_code, normalize_name, normalize_optional


class ModelContractTests(unittest.TestCase):
    def test_exact_tables_and_common_columns_exist(self):
        models = (Location, Manufacturer, InstrumentType, Material)
        self.assertEqual({model.__tablename__ for model in models}, {
            "locations", "manufacturers", "instrument_types", "materials"
        })
        for model in models:
            self.assertTrue({
                "id", "organization_id", "code", "name", "description",
                "is_active", "version", "created_at", "updated_at",
            }.issubset(model.__table__.columns.keys()))

    def test_code_uniqueness_is_per_organization(self):
        for model in (Location, Manufacturer, InstrumentType, Material):
            unique_columns = {
                tuple(column.name for column in constraint.columns)
                for constraint in model.__table__.constraints
                if isinstance(constraint, UniqueConstraint)
            }
            self.assertIn(("organization_id", "code"), unique_columns)
            self.assertNotIn(("code",), unique_columns)

    def test_type_checks_are_database_constraints(self):
        location_checks = {c.name for c in Location.__table__.constraints if isinstance(c, CheckConstraint)}
        material_checks = {c.name for c in Material.__table__.constraints if isinstance(c, CheckConstraint)}
        self.assertIn("ck_locations_location_type", location_checks)
        self.assertIn("ck_materials_material_type", material_checks)

    def test_location_parent_is_restrictive_and_same_organization(self):
        constraints = [c for c in Location.__table__.constraints if isinstance(c, ForeignKeyConstraint)]
        parent = next(c for c in constraints if c.name == "fk_locations_parent_same_organization")
        self.assertEqual(tuple(parent.column_keys), ("organization_id", "parent_location_id"))
        self.assertEqual(parent.ondelete, "RESTRICT")


class NormalizationAndValidationTests(unittest.TestCase):
    def test_code_is_trimmed_and_uppercased(self):
        self.assertEqual(normalize_code("  raw-01  "), "RAW-01")

    def test_blank_code_and_name_are_rejected(self):
        with self.assertRaises(ValidationException):
            normalize_code(" \t")
        with self.assertRaises(ValidationException):
            normalize_name("  ")

    def test_name_case_is_preserved_and_empty_optional_becomes_none(self):
        self.assertEqual(normalize_name("  Main Lab  "), "Main Lab")
        self.assertIsNone(normalize_optional("  "))

    def test_invalid_types_are_rejected_by_application(self):
        with self.assertRaises(ValidationException):
            LocationService._validate_type("WAREHOUSE")
        with self.assertRaises(ValidationException):
            MaterialService._validate_type("CHEMICAL")
        self.assertEqual(LocationService._validate_type(LocationType.SITE), "SITE")
        self.assertEqual(MaterialService._validate_type(MaterialType.REAGENT), "REAGENT")


class LocationHierarchyTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.service = LocationService(self.repository)
        self.db = Mock()
        self.organization_id = uuid4()

    def test_same_organization_parent_is_accepted(self):
        parent_id = uuid4()
        self.repository.get.side_effect = [SimpleNamespace(parent_location_id=None)]
        self.service._validate_parent(self.db, self.organization_id, parent_id)
        self.repository.get.assert_called_once_with(self.db, self.organization_id, parent_id)

    def test_foreign_organization_parent_is_concealed_as_not_found(self):
        self.repository.get.return_value = None
        with self.assertRaises(ResourceNotFoundException):
            self.service._validate_parent(self.db, self.organization_id, uuid4())

    def test_self_parent_is_rejected(self):
        record_id = uuid4()
        with self.assertRaisesRegex(ValidationException, "own parent"):
            self.service._validate_parent(self.db, self.organization_id, record_id, record_id)

    def test_circular_hierarchy_is_rejected(self):
        record_id, parent_id = uuid4(), uuid4()
        self.repository.get.return_value = SimpleNamespace(parent_location_id=record_id)
        with self.assertRaisesRegex(ValidationException, "circular"):
            self.service._validate_parent(self.db, self.organization_id, parent_id, record_id)


class OptimisticConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.service = ManufacturerService(self.repository)
        self.db = Mock()
        self.organization_id = uuid4()
        self.record_id = uuid4()

    def test_successful_update_returns_incremented_record(self):
        updated = SimpleNamespace(version=5)
        self.repository.update_expected.return_value = updated
        result = self.service.update(
            self.db, self.organization_id, self.record_id, 4, name=" Updated "
        )
        self.assertEqual(result.version, 5)
        self.assertEqual(self.repository.update_expected.call_args.args[4], {"name": "Updated"})

    def test_stale_update_and_status_change_raise_safe_conflict(self):
        self.repository.update_expected.return_value = None
        self.repository.get.return_value = SimpleNamespace(version=5)
        for mutation in (
            lambda: self.service.update(self.db, self.organization_id, self.record_id, 4, name="Name"),
            lambda: self.service.set_active(self.db, self.organization_id, self.record_id, 4, False),
        ):
            with self.assertRaisesRegex(VersionConflictException, "Refresh and try again"):
                mutation()

    def test_missing_or_out_of_scope_update_is_404(self):
        self.repository.update_expected.return_value = None
        self.repository.get.return_value = None
        with self.assertRaises(ResourceNotFoundException):
            self.service.update(self.db, self.organization_id, self.record_id, 1, name="Name")

    def test_stale_delete_conflicts_and_successful_delete_does_not_cascade(self):
        self.repository.delete_expected.return_value = False
        self.repository.get.return_value = SimpleNamespace(version=2)
        with self.assertRaises(VersionConflictException):
            self.service.delete(self.db, self.organization_id, self.record_id, 1)
        self.repository.delete_expected.return_value = True
        self.service.delete(self.db, self.organization_id, self.record_id, 2)


class PermissionCatalogTests(unittest.TestCase):
    def test_exact_sprint16_permissions_are_unique(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        expected = {
            f"{resource}.{action}"
            for resource in ("location", "manufacturer", "instrument_type", "material")
            for action in ("view", "create", "update", "delete")
        }
        self.assertEqual({code for code in codes if code.split(".")[0] in {
            "location", "manufacturer", "instrument_type", "material"
        }}, expected)
        self.assertEqual(len(codes), len(set(codes)))

    def test_no_future_domain_permissions_were_added(self):
        codes = {item["permission_code"] for item in PERMISSION_CATALOG}
        forbidden_prefixes = ("instrument.", "qc_", "sample.", "stability.", "calibration.", "maintenance.")
        self.assertFalse(any(code.startswith(forbidden_prefixes) for code in codes))


if __name__ == "__main__":
    unittest.main()
