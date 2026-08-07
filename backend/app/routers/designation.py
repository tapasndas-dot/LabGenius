from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.designation import (
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
)
from app.services.designation_service import DesignationService

router = APIRouter()

service = DesignationService()


@router.get(
    "/",
    response_model=list[DesignationResponse],
)
def get_designations(
    db: Session = Depends(get_db),
):
    return service.get_all(db)


@router.get(
    "/department/{department_id}",
    response_model=list[DesignationResponse],
)
def get_by_department(
    department_id: UUID,
    db: Session = Depends(get_db),
):
    return service.get_by_department(
        db,
        department_id,
    )


@router.get(
    "/{designation_id}",
    response_model=DesignationResponse,
)
def get_designation(
    designation_id: UUID,
    db: Session = Depends(get_db),
):
    return service.get(
        db,
        designation_id,
    )


@router.post(
    "/",
    response_model=DesignationResponse,
)
def create_designation(
    designation: DesignationCreate,
    db: Session = Depends(get_db),
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