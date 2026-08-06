from sqlalchemy.orm import Session

from app.models.organization.organization import Organization
from app.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self):
        super().__init__(Organization)

    def get_by_code(
        self,
        db: Session,
        organization_code: str,
    ):
        return (
            db.query(Organization)
            .filter(
                Organization.organization_code == organization_code
            )
            .first()
        )