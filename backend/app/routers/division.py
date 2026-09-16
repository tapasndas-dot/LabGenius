from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.division import (
    DivisionCreate,
    DivisionResponse,
    DivisionUpdate,
)
from app.services.division_service import DivisionService
from app.services.hierarchy_read_service import HierarchyReadService


router = APIRouter()

service = DivisionService()
read_service = HierarchyReadService(service.repository.model, "divisions", "division.view")


@router.get(
    "/",
    response_model=list[DivisionResponse],
)
def get_divisions(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "division.view",
        ),
    ),
):
    return read_service.list(db, current_user)


@router.get(
    "/business-unit/{business_unit_id}",
    response_model=list[DivisionResponse],
)
def get_by_business_unit(
    business_unit_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "division.view",
        ),
    ),
):
    return read_service.list(
        db,
        current_user,
        business_unit_id=business_unit_id,
    )


@router.get(
    "/{division_id}",
    response_model=DivisionResponse,
)
def get_division(
    division_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "division.view",
        ),
    ),
):
    return read_service.get(
        db,
        current_user,
        division_id,
    )


@router.post(
    "/",
    response_model=DivisionResponse,
)
def create_division(
    division: DivisionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "division.create",
        ),
    ),
):
    return service.create(
        db,
        division,
    )


@router.put(
    "/{division_id}",
    response_model=DivisionResponse,
)
def update_division(
    division_id: UUID,
    update: DivisionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "division.update",
        ),
    ),
):
    division = service.get(
        db,
        division_id,
    )

    return service.update(
        db,
        division,
        update,
    )


@router.delete(
    "/{division_id}",
)
def delete_division(
    division_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "division.delete",
        ),
    ),
):
    division = service.get(
        db,
        division_id,
    )

    service.delete(
        db,
        division,
    )

    return {
        "message": "Division deleted successfully"
    }
