from sqlalchemy.orm import Session

from app.models.organization.division import Division
from app.repositories.base_repository import BaseRepository


class DivisionRepository(BaseRepository[Division]):

    def __init__(self):
        super().__init__(Division)

    def get_by_code(
        self,
        db: Session,
        division_code: str,
    ):
        return (
            db.query(Division)
            .filter(
                Division.division_code == division_code
            )
            .first()
        )

    def get_by_business_unit(
        self,
        db: Session,
        business_unit_id,
    ):
        return (
            db.query(Division)
            .filter(
                Division.business_unit_id == business_unit_id
            )
            .all()
        )