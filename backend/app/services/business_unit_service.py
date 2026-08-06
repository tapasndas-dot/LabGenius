from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateResourceException,    
)
from app.models.organization.business_unit import BusinessUnit
from app.repositories.business_unit_repository import BusinessUnitRepository
from app.schemas.business_unit import (
    BusinessUnitCreate,
    BusinessUnitUpdate,
)
from app.services.base_service import BaseService


class BusinessUnitService(BaseService[BusinessUnit]):

    def __init__(self):
        super().__init__(BusinessUnitRepository())
        self.business_unit_repository = BusinessUnitRepository()

    def get_by_organization(
        self,
        db: Session,
        organization_id: UUID,
    ):
        return self.repository.get_by_organization(
            db,
            organization_id,
        )

    def create(
        self,
        db: Session,
        business_unit: BusinessUnitCreate,
    ):
        existing = self.repository.get_by_code(
            db,
            business_unit.business_unit_code,
        )

        if existing:
            raise DuplicateResourceException(
                "Business Unit code already exists."
            )

        db_object = BusinessUnit(
            **business_unit.model_dump()
        )

        return self.repository.create(
            db,
            db_object,
        )