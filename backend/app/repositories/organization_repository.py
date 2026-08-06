from app.database.session import SessionLocal
from app.models.organization.organization import Organization
from app.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self):
        super().__init__(Organization)