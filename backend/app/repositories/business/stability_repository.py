from uuid import UUID

from sqlalchemy import delete, func, update
from sqlalchemy.orm import Session

from app.models.business.stability import StabilityProtocol, StabilityProtocolCondition, StabilityProtocolTimepoint, StabilityProtocolVersion, StabilityStudy, StabilityStudyCondition


class _VersionedRepository:
    model = None

    def query(self, db: Session):
        return db.query(self.model)

    def update_expected(self, db: Session, record_id: UUID, expected_version: int, values: dict):
        updated_id = db.execute(update(self.model).where(
            self.model.id == record_id, self.model.version == expected_version,
        ).values(**values, version=self.model.version + 1, updated_at=func.now()).returning(self.model.id)).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(self.model, updated_id)

    def delete_expected(self, db: Session, record_id: UUID, expected_version: int) -> bool:
        return db.execute(delete(self.model).where(
            self.model.id == record_id, self.model.version == expected_version,
        )).rowcount == 1


class StabilityProtocolRepository(_VersionedRepository):
    model = StabilityProtocol

    def get(self, db: Session, organization_id: UUID, protocol_id: UUID):
        return self.query(db).filter(StabilityProtocol.organization_id == organization_id, StabilityProtocol.id == protocol_id).first()

    def get_by_code(self, db: Session, organization_id: UUID, protocol_code: str):
        return self.query(db).filter(StabilityProtocol.organization_id == organization_id, StabilityProtocol.protocol_code == protocol_code).first()


class StabilityProtocolVersionRepository(_VersionedRepository):
    model = StabilityProtocolVersion

    def get(self, db: Session, organization_id: UUID, version_id: UUID):
        return self.query(db).join(StabilityProtocol).filter(StabilityProtocol.organization_id == organization_id, StabilityProtocolVersion.id == version_id).first()


class StabilityProtocolConditionRepository(_VersionedRepository):
    model = StabilityProtocolCondition

    def get(self, db: Session, organization_id: UUID, condition_id: UUID):
        return self.query(db).join(StabilityProtocolVersion).join(StabilityProtocol).filter(StabilityProtocol.organization_id == organization_id, StabilityProtocolCondition.id == condition_id).first()


class StabilityProtocolTimepointRepository(_VersionedRepository):
    model = StabilityProtocolTimepoint

    def get(self, db: Session, organization_id: UUID, timepoint_id: UUID):
        return self.query(db).join(StabilityProtocolCondition).join(StabilityProtocolVersion).join(StabilityProtocol).filter(StabilityProtocol.organization_id == organization_id, StabilityProtocolTimepoint.id == timepoint_id).first()


class StabilityStudyRepository(_VersionedRepository):
    model = StabilityStudy

    def get(self, db: Session, organization_id: UUID, study_id: UUID):
        return self.query(db).filter(StabilityStudy.organization_id == organization_id, StabilityStudy.id == study_id).first()

    def get_by_number(self, db: Session, organization_id: UUID, study_number: str):
        return self.query(db).filter(StabilityStudy.organization_id == organization_id, StabilityStudy.study_number == study_number).first()


class StabilityStudyConditionRepository(_VersionedRepository):
    model = StabilityStudyCondition

    def get(self, db: Session, organization_id: UUID, study_condition_id: UUID):
        return self.query(db).join(StabilityStudy).filter(StabilityStudy.organization_id == organization_id, StabilityStudyCondition.id == study_condition_id).first()
