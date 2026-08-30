from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.business.material import Material
from app.models.business.sample import Sample, SamplePriority, SampleTest, SampleTestStatus
from app.models.business.specification import Specification, SpecificationTest, SpecificationVersion, SpecificationVersionStatus
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.repositories.business.sample_repository import SampleRepository, SampleTestRepository
from app.services.organization_scope_service import OrganizationScopeService
from .normalization import normalize_code, normalize_optional
from .organization_master_service import VERSION_CONFLICT_MESSAGE


class SampleService:
    MUTABLE_FIELDS = {
        "business_unit_id", "division_id", "department_id", "external_reference",
        "sample_description", "quantity", "quantity_unit", "received_at", "sampled_at",
        "due_at", "priority", "notes",
    }

    def __init__(self, repository=None):
        self.repository = repository or SampleRepository()
        self.scope_service = OrganizationScopeService()

    def scoped_query(self, db: Session, actor, permission_code: str):
        return self.scope_service.filter_samples(self.repository.query(db), actor, permission_code)

    @staticmethod
    def normalize(values: dict) -> dict:
        result = dict(values)
        if "sample_number" in result:
            result["sample_number"] = normalize_code(result["sample_number"])
        for field in ("external_reference", "sample_description", "quantity_unit", "notes"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if "priority" in result:
            try:
                result["priority"] = SamplePriority(result["priority"]).value
            except ValueError as exc:
                raise ValidationException("Invalid Sample priority.") from exc
        if result.get("quantity") is not None and result["quantity"] <= 0:
            raise ValidationException("Sample quantity must be positive.")
        return result

    @staticmethod
    def validate_hierarchy(db: Session, organization_id: UUID, values: dict) -> None:
        business_unit = db.get(BusinessUnit, values.get("business_unit_id")) if values.get("business_unit_id") else None
        division = db.get(Division, values.get("division_id")) if values.get("division_id") else None
        department = db.get(Department, values.get("department_id")) if values.get("department_id") else None
        if values.get("business_unit_id") and business_unit is None or values.get("division_id") and division is None or values.get("department_id") and department is None:
            raise ValidationException("Invalid Sample organizational hierarchy.")
        if business_unit and business_unit.organization_id != organization_id:
            raise ValidationException("Sample hierarchy must belong to its organization.")
        if division:
            division_bu = db.get(BusinessUnit, division.business_unit_id)
            if division_bu is None or division_bu.organization_id != organization_id or business_unit and division.business_unit_id != business_unit.id:
                raise ValidationException("Sample organizational hierarchy is inconsistent.")
        if department:
            department_division = db.get(Division, department.division_id)
            department_bu = db.get(BusinessUnit, department_division.business_unit_id) if department_division else None
            if department_division is None or department_bu is None or department_bu.organization_id != organization_id or division and department.division_id != division.id or business_unit and department_division.business_unit_id != business_unit.id:
                raise ValidationException("Sample organizational hierarchy is inconsistent.")

    @staticmethod
    def validate_testing_basis(db: Session, organization_id: UUID, material_id: UUID, specification_version_id: UUID) -> None:
        material = db.get(Material, material_id)
        version = db.query(SpecificationVersion).join(Specification).filter(SpecificationVersion.id == specification_version_id).first()
        if material is None or material.organization_id != organization_id:
            raise ValidationException("Material must belong to the Sample organization.")
        if version is None or version.specification.organization_id != organization_id:
            raise ValidationException("Specification Version must belong to the Sample organization.")
        if version.specification.material_id != material_id:
            raise ValidationException("Specification Version does not belong to the selected Material.")
        if version.status != SpecificationVersionStatus.APPROVED:
            raise ValidationException("Sample registration requires an APPROVED Specification Version.")

    def create(self, db: Session, organization_id: UUID, values: dict) -> Sample:
        values = self.normalize(values)
        if values.get("status", "REGISTERED") != "REGISTERED":
            raise ValidationException("New Samples must start in REGISTERED status.")
        values.pop("status", None)
        if not values.get("sample_number"):
            raise ValidationException("Sample number is required.")
        if not values.get("material_id") or not values.get("specification_version_id"):
            raise ValidationException("Material and Specification Version are required.")
        self.validate_hierarchy(db, organization_id, values)
        self.validate_testing_basis(db, organization_id, values["material_id"], values["specification_version_id"])
        if self.repository.get_by_number(db, organization_id, values["sample_number"]):
            raise DuplicateResourceException("A Sample with this number already exists.")
        record = Sample(organization_id=organization_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_expected(self, db: Session, organization_id: UUID, sample_id: UUID, expected_version: int, values: dict) -> Sample:
        current = self.repository.get(db, organization_id, sample_id)
        if current is None:
            raise ResourceNotFoundException("Sample not found.")
        values = self.normalize({key: value for key, value in values.items() if key in self.MUTABLE_FIELDS})
        hierarchy = {field: values.get(field, getattr(current, field)) for field in ("business_unit_id", "division_id", "department_id")}
        self.validate_hierarchy(db, organization_id, hierarchy)
        updated = self.repository.update_expected(db, organization_id, sample_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated


class SampleTestService:
    def __init__(self, sample_repository=None, repository=None):
        self.sample_repository = sample_repository or SampleRepository()
        self.repository = repository or SampleTestRepository()

    def generate(self, db: Session, organization_id: UUID, sample_id: UUID) -> list[SampleTest]:
        sample = self.sample_repository.get(db, organization_id, sample_id)
        if sample is None:
            raise ResourceNotFoundException("Sample not found.")
        sources = db.query(SpecificationTest).filter(
            SpecificationTest.specification_version_id == sample.specification_version_id
        ).order_by(SpecificationTest.sequence_number, SpecificationTest.id).all()
        existing = self.repository.existing_source_ids(db, sample.id)
        for source in sources:
            if source.id not in existing:
                db.add(SampleTest(
                    sample_id=sample.id, specification_test_id=source.id, test_id=source.test_id,
                    method_version_id=source.method_version_id, sequence_number=source.sequence_number,
                    status=SampleTestStatus.PENDING, is_required=source.is_required,
                    display_name=source.display_name,
                ))
        db.flush()
        return self.repository.for_sample(db, sample.id)
