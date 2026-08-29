from app.models.business.material import Material
from .organization_master_repository import OrganizationMasterRepository


class MaterialRepository(OrganizationMasterRepository[Material]):
    def __init__(self):
        super().__init__(Material)
