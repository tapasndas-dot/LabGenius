from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.dependencies.database import get_db
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization_service import OrganizationService
from app.services.hierarchy_read_service import HierarchyReadService


router = APIRouter()

service = OrganizationService()
read_service = HierarchyReadService(service.repository.model, "organizations", "organization.view")


@router.get(
    "/",
    response_model=list[OrganizationResponse],
)
def get_organizations(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "organization.view",
        ),
    ),
):
    return read_service.list(db, current_user)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "organization.view",
        ),
    ),
):
    return read_service.get(
        db,
        current_user,
        organization_id,
    )


@router.post(
    "/",
    response_model=OrganizationResponse,
)
def create_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "organization.create",
        ),
    ),
):
    return service.create(
        db,
        organization,
    )


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def update_organization(
    organization_id: UUID,
    update: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "organization.update",
        ),
    ),
):
    organization = service.get(
        db,
        organization_id,
    )

    return service.update(
        db,
        organization,
        update,
    )


@router.delete(
    "/{organization_id}",
)
def delete_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission(
            "organization.delete",
        ),
    ),
):
    organization = service.get(
        db,
        organization_id,
    )

    service.delete(
        db,
        organization,
    )

    return {
        "message": "Organization deleted successfully"
    }
