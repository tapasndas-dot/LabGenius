from sqlalchemy.orm import Session

from app.services.base_service import BaseService

from app.models.organization.organization import Organization
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
)
from app.core.exceptions import DuplicateResourceException


class OrganizationService(BaseService[Organization]):

    def __init__(self):
        super().__init__(OrganizationRepository())

  
    def create(
        self,
        db: Session,
        organization: OrganizationCreate,
    ):

        existing = self.repository.get_by_code(
            db,
            organization.organization_code,
        )

        if existing:
            raise DuplicateResourceException(
                "Organization code already exists."
            )

        db_object = Organization(**organization.model_dump())

        return self.repository.create(
            db,
            db_object,
        )

  