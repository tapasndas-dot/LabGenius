from uuid import UUID

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models.business.sample import Sample, SampleTest


class SampleRepository:
    def query(self, db: Session):
        return db.query(Sample)

    def get(self, db: Session, organization_id: UUID, sample_id: UUID):
        return self.query(db).filter(Sample.organization_id == organization_id, Sample.id == sample_id).first()

    def get_by_number(self, db: Session, organization_id: UUID, sample_number: str):
        return self.query(db).filter(Sample.organization_id == organization_id, Sample.sample_number == sample_number).first()

    def update_expected(self, db: Session, organization_id: UUID, sample_id: UUID, expected_version: int, values: dict):
        updated_id = db.execute(update(Sample).where(
            Sample.organization_id == organization_id, Sample.id == sample_id, Sample.version == expected_version,
        ).values(**values, version=Sample.version + 1, updated_at=func.now()).returning(Sample.id)).scalar_one_or_none()
        if updated_id is None:
            return None
        db.flush()
        return db.get(Sample, updated_id)


class SampleTestRepository:
    def for_sample(self, db: Session, sample_id: UUID):
        return db.query(SampleTest).filter(SampleTest.sample_id == sample_id).order_by(SampleTest.sequence_number, SampleTest.id).all()

    def existing_source_ids(self, db: Session, sample_id: UUID):
        return {row[0] for row in db.query(SampleTest.specification_test_id).filter(SampleTest.sample_id == sample_id).all()}
