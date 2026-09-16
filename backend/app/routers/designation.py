from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.designation import (
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
)
from app.services.designation_service import DesignationService
from app.services.hierarchy_read_service import HierarchyReadService


router = APIRouter()

service = DesignationService()
read_service = HierarchyReadService(service.repository.model, "designations", "designation.view")


@router.get(
    "/",
    response_model=list[DesignationResponse],
)
def get_designations(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "designation.view",
        ),
    ),
):
    return read_service.list(db, current_user)


@router.get(
    "/department/{department_id}",
    response_model=list[DesignationResponse],
)
def get_by_department(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "designation.view",
        ),
    ),
):
    return read_service.list(
        db,
        current_user,
        department_id=department_id,
    )


@router.get(
    "/{designation_id}",
    response_model=DesignationResponse,
)
def get_designation(
    designation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "designation.view",
        ),
    ),
):
    return read_service.get(
        db,
        current_user,
        designation_id,
    )


@router.post(
    "/",
    response_model=DesignationResponse,
)
def create_designation(
    designation: DesignationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "designation.create",
        ),
    ),
):
    return service.create(
        db,
        designation,
    )


@router.put(
    "/{designation_id}",
    response_model=DesignationResponse,
)
def update_designation(
    designation_id: UUID,
    update: DesignationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "designation.update",
        ),
    ),
):
    designation = service.get(
        db,
        designation_id,
    )

    return service.update(
        db,
        designation,
        update,
    )


@router.delete(
    "/{designation_id}",
)
def delete_designation(
    designation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "designation.delete",
        ),
    ),
):
    designation = service.get(
        db,
        designation_id,
    )

    service.delete(
        db,
        designation,
    )

    return {
        "message": "Designation deleted successfully"
    }
