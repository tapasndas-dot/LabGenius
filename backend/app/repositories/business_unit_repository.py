from sqlalchemy.orm import Session

from app.models.organization.business_unit import BusinessUnit
from app.repositories.base_repository import BaseRepository


class BusinessUnitRepository(BaseRepository[BusinessUnit]):
    def __init__(self):
        super().__init__(BusinessUnit)

    def get_by_code(
        self,
        db: Session,
        business_unit_code: str,
    ):
        return (
            db.query(BusinessUnit)
            .filter(
                BusinessUnit.business_unit_code == business_unit_code
            )
            .first()
        )

    def get_by_organization(
        self,
        db: Session,
        organization_id,
    ):
        return (
            db.query(BusinessUnit)
            .filter(
                BusinessUnit.organization_id == organization_id
            )
            .all()
        )