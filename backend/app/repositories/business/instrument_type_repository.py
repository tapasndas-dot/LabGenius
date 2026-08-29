from app.models.business.instrument_type import InstrumentType
from .organization_master_repository import OrganizationMasterRepository


class InstrumentTypeRepository(OrganizationMasterRepository[InstrumentType]):
    def __init__(self):
        super().__init__(InstrumentType)
