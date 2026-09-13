from uuid import UUID

from sqlalchemy import func, or_, update
from sqlalchemy.orm import Session
from app.models.business.instrument import Instrument, StabilityChamberProfile
from .organization_master_repository import OrganizationMasterRepository


class InstrumentRepository(OrganizationMasterRepository[Instrument]):
    def __init__(self):
        super().__init__(Instrument)

    def get_by_code(self, db: Session, organization_id: UUID, code: str):
        return db.query(Instrument).filter(
            Instrument.organization_id == organization_id,
            Instrument.instrument_code == code,
        ).first()

    def list_query(self, db: Session, organization_id: UUID):
        return db.query(Instrument).filter(Instrument.organization_id == organization_id)

    def apply_list_filters(
        self, query, *, search: str | None = None, is_active: bool | None = None,
        **filters,
    ):
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(
                Instrument.instrument_code.ilike(pattern),
                Instrument.instrument_name.ilike(pattern),
                Instrument.model_number.ilike(pattern),
                Instrument.serial_number.ilike(pattern),
            ))
        if is_active is not None:
            query = query.filter(Instrument.is_active == is_active)
        for field, value in filters.items():
            if value is not None:
                query = query.filter(getattr(Instrument, field) == value)
        return query

    def chamber_profile(self, db: Session, instrument_id: UUID):
        return db.query(StabilityChamberProfile).filter(
            StabilityChamberProfile.instrument_id == instrument_id
        ).first()

    def update_chamber_profile_expected(
        self, db: Session, profile_id: UUID, instrument_id: UUID,
        expected_version: int, values: dict,
    ):
        updated_id = db.execute(update(StabilityChamberProfile).where(
            StabilityChamberProfile.id == profile_id,
            StabilityChamberProfile.instrument_id == instrument_id,
            StabilityChamberProfile.version == expected_version,
        ).values(
            **values, version=StabilityChamberProfile.version + 1,
            updated_at=func.now(),
        ).returning(StabilityChamberProfile.id)).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(StabilityChamberProfile, updated_id)
