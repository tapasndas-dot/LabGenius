from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services.department_service import DepartmentService


router = APIRouter()

service = DepartmentService()


@router.get(
    "/",
    response_model=list[DepartmentResponse],
)
def get_departments(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "department.view",
        ),
    ),
):
    return service.get_all(db)


@router.get(
    "/division/{division_id}",
    response_model=list[DepartmentResponse],
)
def get_departments_by_division(
    division_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "department.view",
        ),
    ),
):
    return service.get_by_division(
        db,
        division_id,
    )


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
)
def get_department(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "department.view",
        ),
    ),
):
    return service.get(
        db,
        department_id,
    )


@router.post(
    "/",
    response_model=DepartmentResponse,
)
def create_department(
    department: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "department.create",
        ),
    ),
):
    return service.create(
        db,
        department,
    )


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse,
)
def update_department(
    department_id: UUID,
    update: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "department.update",
        ),
    ),
):
    department = service.get(
        db,
        department_id,
    )

    return service.update(
        db,
        department,
        update,
    )


@router.delete(
    "/{department_id}",
)
def delete_department(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "department.delete",
        ),
    ),
):
    department = service.get(
        db,
        department_id,
    )

    service.delete(
        db,
        department,
    )

    return {
        "message": "Department deleted successfully"
    }