from app.models.business.location import Location
from .organization_master_repository import OrganizationMasterRepository


class LocationRepository(OrganizationMasterRepository[Location]):
    def __init__(self):
        super().__init__(Location)
