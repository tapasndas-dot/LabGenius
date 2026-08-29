from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
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
from app.services.audit_service import AuditAction, AuditService
from app.services.organization_scope_service import AccessScope, OrganizationScopeService
from .normalization import normalize_code, normalize_name, normalize_optional
from .organization_master_service import VERSION_CONFLICT_MESSAGE


class InstrumentService:
    def __init__(self, repository: InstrumentRepository | None = None):
        self.repository = repository or InstrumentRepository()
        self.audit_service = AuditService()
        self.scope_service = OrganizationScopeService()

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

    def scoped_query(self, db: Session, actor, permission_code: str):
        return self.scope_service.filter_instruments(
            self.repository.query(db), actor, permission_code
        )

    def list_scoped(
        self, db: Session, actor, permission_code: str, *, limit: int = 100,
        offset: int = 0, search: str | None = None,
        is_active: bool | None = None, **filters,
    ):
        query = self.repository.apply_list_filters(
            self.scoped_query(db, actor, permission_code), search=search,
            is_active=is_active, **filters,
        )
        return query.order_by(
            Instrument.instrument_code.asc(), Instrument.id.asc()
        ).offset(offset).limit(limit).all()

    def get_scoped(
        self, db: Session, actor, instrument_id: UUID, permission_code: str
    ) -> Instrument:
        record = self.scoped_query(db, actor, permission_code).filter(
            Instrument.id == instrument_id
        ).first()
        if record is None:
            raise ResourceNotFoundException("Instrument not found.")
        return record

    def _ensure_target_scope(
        self, db: Session, actor, permission_code: str, values: dict
    ) -> None:
        if not self.scope_service.can_place_instrument(
            db, actor, permission_code, values
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Target Instrument hierarchy is outside the authorized scope.",
            )

    def create_scoped(self, db: Session, actor, values: dict) -> Instrument:
        normalized = self.normalize(values)
        if self.scope_service.resolve_scope(
            actor, "instrument.create"
        ) == AccessScope.SELF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SELF scope cannot create Instruments.",
            )
        self.validate_references(db, actor.organization_id, normalized)
        self._ensure_target_scope(db, actor, "instrument.create", normalized)
        try:
            record = self.create(db, actor.organization_id, normalized)
            self.audit_service.record_create(
                db, entity=record, actor=actor, owner=record
            )
            db.commit()
            db.refresh(record)
            return record
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(
                "An instrument with this code already exists."
            ) from exc
        except Exception:
            db.rollback()
            raise

    def update_scoped(
        self, db: Session, actor, instrument_id: UUID, expected_version: int,
        values: dict,
    ) -> Instrument:
        record = self.get_scoped(db, actor, instrument_id, "instrument.update")
        before = self.audit_service.snapshot(record)
        hierarchy_fields = ("business_unit_id", "division_id", "department_id")
        hierarchy_changed = any(
            field in values and values[field] != getattr(record, field)
            for field in hierarchy_fields
        )
        merged = {
            field: values.get(field, getattr(record, field))
            for field in hierarchy_fields
        }
        if hierarchy_changed:
            if self.scope_service.resolve_scope(
                actor, "instrument.update"
            ) == AccessScope.SELF:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="SELF scope cannot reassign Instrument hierarchy.",
                )
            self._ensure_target_scope(db, actor, "instrument.update", merged)
        try:
            updated = self.update_expected(
                db, actor.organization_id, instrument_id, expected_version, values
            )
            self.audit_service.record_update(
                db, entity=updated, actor=actor, owner=updated, before=before
            )
            db.commit()
            db.refresh(updated)
            return updated
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(
                "Instrument update conflicts with an existing or referenced record."
            ) from exc
        except Exception:
            db.rollback()
            raise

    def set_active_scoped(
        self, db: Session, actor, instrument_id: UUID, expected_version: int,
        is_active: bool,
    ) -> Instrument:
        record = self.get_scoped(db, actor, instrument_id, "instrument.update")
        before = self.audit_service.snapshot(record)
        try:
            updated = self.update_expected(
                db, actor.organization_id, instrument_id, expected_version,
                {"is_active": is_active},
            )
            self.audit_service.record_update(
                db, entity=updated, actor=actor, owner=updated, before=before,
                action=(AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE),
            )
            db.commit()
            db.refresh(updated)
            return updated
        except Exception:
            db.rollback()
            raise

    def delete_scoped(
        self, db: Session, actor, instrument_id: UUID, expected_version: int
    ) -> None:
        record = self.get_scoped(db, actor, instrument_id, "instrument.delete")
        before = self.audit_service.snapshot(record)
        try:
            if not self.repository.delete_expected(
                db, actor.organization_id, instrument_id, expected_version
            ):
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit_service.record_delete(
                db, entity=record, actor=actor, owner=record, before=before
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(
                "This instrument is referenced and cannot be deleted."
            ) from exc
        except Exception:
            db.rollback()
            raise
