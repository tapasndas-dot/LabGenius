from sqlalchemy.orm import Session

from app.models.organization.department import Department
from app.repositories.base_repository import BaseRepository


class DepartmentRepository(BaseRepository[Department]):

    def __init__(self):
        super().__init__(Department)

    def get_by_code(
        self,
        db: Session,
        department_code: str,
    ):
        return (
            db.query(Department)
            .filter(
                Department.department_code == department_code
            )
            .first()
        )

    def get_by_division(
        self,
        db: Session,
        division_id,
    ):
        return (
            db.query(Department)
            .filter(
                Department.division_id == division_id
            )
            .all()
        )