from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
)
from app.models.organization.division import Division
from app.repositories.business_unit_repository import BusinessUnitRepository
from app.repositories.division_repository import DivisionRepository
from app.schemas.division import (
    DivisionCreate,
    DivisionUpdate,
)
from app.services.base_service import BaseService


class DivisionService(BaseService[Division]):

    def __init__(self):
        super().__init__(DivisionRepository())
        self.business_unit_repository = BusinessUnitRepository()

    def get_by_business_unit(
        self,
        db: Session,
        business_unit_id,
    ):
        return self.repository.get_by_business_unit(
            db,
            business_unit_id,
        )

    def create(
        self,
        db: Session,
        division: DivisionCreate,
    ):
        business_unit = self.business_unit_repository.get(
            db,
            division.business_unit_id,
        )

        if business_unit is None:
            raise ResourceNotFoundException(
                "Business Unit not found."
            )

        existing = self.repository.get_by_code(
            db,
            division.division_code,
        )

        if existing:
            raise DuplicateResourceException(
                "Division code already exists."
            )

        db_object = Division(
            **division.model_dump()
        )

        return self.repository.create(
            db,
            db_object,
        )