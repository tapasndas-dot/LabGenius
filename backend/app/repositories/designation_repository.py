from sqlalchemy.orm import Session

from app.models.organization.designation import Designation
from app.repositories.base_repository import BaseRepository


class DesignationRepository(BaseRepository[Designation]):

    def __init__(self):
        super().__init__(Designation)

    def get_by_code(
        self,
        db: Session,
        designation_code: str,
    ):
        return (
            db.query(Designation)
            .filter(
                Designation.designation_code == designation_code
            )
            .first()
        )

    def get_by_department(
        self,
        db: Session,
        department_id,
    ):
        return (
            db.query(Designation)
            .filter(
                Designation.department_id == department_id
            )
            .all()
        )