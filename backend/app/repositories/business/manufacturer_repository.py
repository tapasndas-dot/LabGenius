from app.models.business.manufacturer import Manufacturer
from .organization_master_repository import OrganizationMasterRepository


class ManufacturerRepository(OrganizationMasterRepository[Manufacturer]):
    def __init__(self):
        super().__init__(Manufacturer)
