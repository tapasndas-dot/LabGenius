from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
)
from app.models.organization.department import Department
from app.repositories.department_repository import DepartmentRepository
from app.repositories.division_repository import DivisionRepository
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
)
from app.services.base_service import BaseService


class DepartmentService(BaseService[Department]):

    def __init__(self):
        super().__init__(DepartmentRepository())
        self.division_repository = DivisionRepository()

    def get_by_division(
        self,
        db: Session,
        division_id,
    ):
        return self.repository.get_by_division(
            db,
            division_id,
        )

    def create(
        self,
        db: Session,
        department: DepartmentCreate,
    ):
        division = self.division_repository.get(
            db,
            department.division_id,
        )

        if division is None:
            raise ResourceNotFoundException(
                "Division not found."
            )

        existing = self.repository.get_by_code(
            db,
            department.department_code,
        )

        if existing:
            raise DuplicateResourceException(
                "Department code already exists."
            )

        db_object = Department(
            **department.model_dump()
        )

        return self.repository.create(
            db,
            db_object,
        )