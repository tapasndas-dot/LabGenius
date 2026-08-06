from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.business_unit import (
    BusinessUnitCreate,
    BusinessUnitResponse,
    BusinessUnitUpdate,
)
from app.services.business_unit_service import BusinessUnitService

router = APIRouter()

service = BusinessUnitService()


@router.get(
    "/",
    response_model=list[BusinessUnitResponse],
)
def get_business_units(
    db: Session = Depends(get_db),
):
    return service.get_all(db)


@router.get(
    "/organization/{organization_id}",
    response_model=list[BusinessUnitResponse],
)
def get_business_units_by_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
):
    return service.get_by_organization(
        db,
        organization_id,
    )


@router.get(
    "/{business_unit_id}",
    response_model=BusinessUnitResponse,
)
def get_business_unit(
    business_unit_id: UUID,
    db: Session = Depends(get_db),
):
    return service.get(
        db,
        business_unit_id,
    )


@router.post(
    "/",
    response_model=BusinessUnitResponse,
)
def create_business_unit(
    business_unit: BusinessUnitCreate,
    db: Session = Depends(get_db),
):
    return service.create(
        db,
        business_unit,
    )


@router.put(
    "/{business_unit_id}",
    response_model=BusinessUnitResponse,
)
def update_business_unit(
    business_unit_id: UUID,
    update: BusinessUnitUpdate,
    db: Session = Depends(get_db),
):
    business_unit = service.get(
        db,
        business_unit_id,
    )

    return service.update(
        db,
        business_unit,
        update,
    )


@router.delete(
    "/{business_unit_id}",
)
def delete_business_unit(
    business_unit_id: UUID,
    db: Session = Depends(get_db),
):
    business_unit = service.get(
        db,
        business_unit_id,
    )

    service.delete(
        db,
        business_unit,
    )

    return {
        "message": "Business Unit deleted successfully"
    }