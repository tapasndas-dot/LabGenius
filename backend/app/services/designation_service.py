from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
)
from app.models.organization.designation import Designation
from app.repositories.department_repository import DepartmentRepository
from app.repositories.designation_repository import DesignationRepository
from app.schemas.designation import (
    DesignationCreate,
    DesignationUpdate,
)
from app.services.base_service import BaseService


class DesignationService(BaseService[Designation]):

    def __init__(self):
        super().__init__(DesignationRepository())
        self.department_repository = DepartmentRepository()

    def get_by_department(
        self,
        db: Session,
        department_id,
    ):
        return self.repository.get_by_department(
            db,
            department_id,
        )

    def create(
        self,
        db: Session,
        designation: DesignationCreate,
    ):
        department = self.department_repository.get(
            db,
            designation.department_id,
        )

        if department is None:
            raise ResourceNotFoundException(
                "Department not found."
            )

        existing = self.repository.get_by_code(
            db,
            designation.designation_code,
        )

        if existing:
            raise DuplicateResourceException(
                "Designation code already exists."
            )

        db_object = Designation(
            **designation.model_dump()
        )

        return self.repository.create(
            db,
            db_object,
        )