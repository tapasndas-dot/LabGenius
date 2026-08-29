from uuid import UUID

from sqlalchemy.orm import Session
from app.core.exceptions import (
    DuplicateResourceException, ResourceNotFoundException, ValidationException,
    VersionConflictException,
)
from app.models.business.instrument import (
    Instrument, InstrumentCriticality, InstrumentStatus, StabilityChamberProfile,
)
from app.models.business.instrument_type import InstrumentType
from app.models.business.location import Location
from app.models.business.manufacturer import Manufacturer
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.division import Division
from app.models.organization.department import Department
from app.models.user.user import User
from app.repositories.business.instrument_repository import InstrumentRepository
from .normalization import normalize_code, normalize_name, normalize_optional
from .organization_master_service import VERSION_CONFLICT_MESSAGE


class InstrumentService:
    def __init__(self, repository: InstrumentRepository | None = None):
        self.repository = repository or InstrumentRepository()

    @staticmethod
    def _active(db: Session, model, record_id, message: str):
        if record_id is None:
            return None
        record = db.query(model).filter(
            model.id == record_id, model.is_active.is_(True)
        ).first()
        if record is None:
            raise ResourceNotFoundException(message)
        return record

    def validate_references(self, db: Session, organization_id: UUID, values: dict) -> None:
        if values.get("instrument_type_id") is None:
            raise ValidationException("Instrument type is required.")
        business_unit = self._active(db, BusinessUnit, values.get("business_unit_id"), "Business unit not found.")
        division = self._active(db, Division, values.get("division_id"), "Division not found.")
        department = self._active(db, Department, values.get("department_id"), "Department not found.")
        if business_unit and business_unit.organization_id != organization_id:
            raise ValidationException("Instrument hierarchy must belong to its organization.")
        if division:
            division_bu = self._active(db, BusinessUnit, division.business_unit_id, "Division business unit not found.")
            if division_bu.organization_id != organization_id or (business_unit and division.business_unit_id != business_unit.id):
                raise ValidationException("Instrument hierarchy is inconsistent.")
        if department:
            department_division = self._active(db, Division, department.division_id, "Department division not found.")
            department_bu = self._active(db, BusinessUnit, department_division.business_unit_id, "Department business unit not found.")
            if department_bu.organization_id != organization_id or (division and department.division_id != division.id) or (business_unit and department_division.business_unit_id != business_unit.id):
                raise ValidationException("Instrument hierarchy is inconsistent.")
        for model, field, message in (
            (InstrumentType, "instrument_type_id", "Instrument type not found."),
            (Manufacturer, "manufacturer_id", "Manufacturer not found."),
            (Location, "location_id", "Location not found."),
            (User, "responsible_user_id", "Responsible user not found."),
        ):
            record = self._active(db, model, values.get(field), message)
            if record is not None and record.organization_id != organization_id:
                raise ValidationException("Instrument references must belong to its organization.")

    @staticmethod
    def normalize(values: dict) -> dict:
        result = dict(values)
        if "instrument_code" in result:
            result["instrument_code"] = normalize_code(result["instrument_code"])
        if "instrument_name" in result:
            result["instrument_name"] = normalize_name(result["instrument_name"])
        for field in ("model_number", "serial_number", "description"):
            if field in result:
                result[field] = normalize_optional(result[field])
        if "status" in result:
            try:
                result["status"] = InstrumentStatus(result["status"]).value
            except ValueError as exc:
                raise ValidationException("Invalid instrument status.") from exc
        if result.get("criticality") is not None:
            try:
                result["criticality"] = InstrumentCriticality(result["criticality"]).value
            except ValueError as exc:
                raise ValidationException("Invalid instrument criticality.") from exc
        return result

    def create(self, db: Session, organization_id: UUID, values: dict) -> Instrument:
        values = self.normalize(values)
        if "instrument_code" not in values or "instrument_name" not in values:
            raise ValidationException("Instrument code and name are required.")
        self.validate_references(db, organization_id, values)
        if self.repository.get_by_code(db, organization_id, values["instrument_code"]):
            raise DuplicateResourceException("An instrument with this code already exists.")
        record = Instrument(organization_id=organization_id, **values)
        db.add(record)
        db.flush()
        return record

    def update_expected(self, db: Session, organization_id: UUID, instrument_id: UUID, expected_version: int, values: dict):
        values = self.normalize(values)
        current = self.repository.get(db, organization_id, instrument_id)
        if current is None:
            raise ResourceNotFoundException("Instrument not found.")
        if "instrument_code" in values:
            duplicate = self.repository.get_by_code(
                db, organization_id, values["instrument_code"]
            )
            if duplicate is not None and duplicate.id != instrument_id:
                raise DuplicateResourceException(
                    "An instrument with this code already exists."
                )
        merged = {field: values.get(field, getattr(current, field, None)) for field in ("business_unit_id", "division_id", "department_id", "instrument_type_id", "manufacturer_id", "location_id", "responsible_user_id")}
        self.validate_references(db, organization_id, merged)
        updated = self.repository.update_expected(db, organization_id, instrument_id, expected_version, values)
        if updated is None:
            raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        return updated

    def create_chamber_profile(self, db: Session, organization_id: UUID, instrument_id: UUID, values: dict):
        instrument = self.repository.get(db, organization_id, instrument_id)
        if instrument is None:
            raise ResourceNotFoundException("Instrument not found.")
        if self.repository.chamber_profile(db, instrument_id):
            raise DuplicateResourceException(
                "Instrument already has a chamber profile."
            )
        normalized = {key: normalize_optional(value) if key in ("temperature_unit", "humidity_unit", "description") else value for key, value in values.items()}
        profile = StabilityChamberProfile(instrument_id=instrument_id, **normalized)
        db.add(profile)
        db.flush()
        return profile
