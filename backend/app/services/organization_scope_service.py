from enum import StrEnum
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy import false
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.organization.organization import Organization
from app.models.user.user import User


class AccessScope(StrEnum):
    SELF = "SELF"
    DEPARTMENT = "DEPARTMENT"
    DIVISION = "DIVISION"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    ORGANIZATION = "ORGANIZATION"


class OrganizationScopeService:
    _RANK = {
        AccessScope.SELF: 0,
        AccessScope.DEPARTMENT: 1,
        AccessScope.DIVISION: 2,
        AccessScope.BUSINESS_UNIT: 3,
        AccessScope.ORGANIZATION: 4,
    }

    def resolve_scope(self, user: User, permission_code: str) -> AccessScope:
        scopes: list[AccessScope] = []
        for assignment in user.user_roles:
            if not assignment.is_active or assignment.role is None or not assignment.role.is_active:
                continue
            grants_permission = any(
                mapping.is_active
                and mapping.permission is not None
                and mapping.permission.is_active
                and mapping.permission.permission_code == permission_code
                for mapping in assignment.role.role_permissions
            )
            if grants_permission:
                try:
                    scopes.append(AccessScope(assignment.access_scope))
                except ValueError:
                    continue
        if not scopes:
            raise HTTPException(status_code=403, detail="Permission scope is not available.")
        return max(scopes, key=self._RANK.get)

    def ensure_scope_not_escalated(
        self, actor: User, permission_code: str, requested_scope: str
    ) -> None:
        try:
            requested = AccessScope(requested_scope)
        except ValueError as exc:
            raise ValidationException("Invalid access scope.") from exc
        if self._RANK[requested] > self._RANK[self.resolve_scope(actor, permission_code)]:
            raise HTTPException(status_code=403, detail="Requested access scope is not allowed.")

    def filter_users(self, db: Session, actor: User, permission_code: str):
        query = db.query(User)
        scope = self.resolve_scope(actor, permission_code)
        if scope == AccessScope.ORGANIZATION:
            return query.filter(User.organization_id == actor.organization_id)
        if scope == AccessScope.BUSINESS_UNIT:
            return query.filter(User.business_unit_id == actor.business_unit_id)
        if scope == AccessScope.DIVISION:
            return query.filter(User.division_id == actor.division_id)
        if scope == AccessScope.DEPARTMENT:
            return query.filter(User.department_id == actor.department_id)
        return query.filter(User.id == actor.id)

    def can_access_user(self, actor: User, target: User, permission_code: str) -> bool:
        if actor.organization_id != target.organization_id:
            return False
        scope = self.resolve_scope(actor, permission_code)
        if scope == AccessScope.ORGANIZATION:
            return True
        if scope == AccessScope.BUSINESS_UNIT:
            return actor.business_unit_id == target.business_unit_id
        if scope == AccessScope.DIVISION:
            return actor.division_id == target.division_id
        if scope == AccessScope.DEPARTMENT:
            return actor.department_id == target.department_id
        return actor.id == getattr(target, "id", None)

    def ensure_can_access_user(self, actor: User, target: User, permission_code: str) -> None:
        if not self.can_access_user(actor, target, permission_code):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    def filter_shared_masters(self, query, actor: User, permission_code: str, model):
        """Scope organization-owned masters that have no lower-level ownership.

        Any qualifying hierarchy scope remains anchored to the actor's organization.
        SELF has no row meaning for shared reference masters and therefore returns none.
        """
        scope = self.resolve_scope(actor, permission_code)
        if scope == AccessScope.SELF:
            return query.filter(false())
        return query.filter(model.organization_id == actor.organization_id)

    def ensure_can_access_shared_master(
        self, actor: User, target, permission_code: str, *, resource_name: str = "Record"
    ) -> None:
        scope = self.resolve_scope(actor, permission_code)
        if scope == AccessScope.SELF or target.organization_id != actor.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_name} not found.",
            )

    def ensure_can_create_shared_master(self, actor: User, permission_code: str) -> None:
        if self.resolve_scope(actor, permission_code) == AccessScope.SELF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization scope is required for this shared master.",
            )

    def validate_hierarchy(
        self,
        db: Session,
        *,
        organization_id,
        business_unit_id,
        division_id,
        department_id,
        designation_id,
    ) -> SimpleNamespace:
        organization = db.query(Organization).filter(Organization.id == organization_id).first()
        business_unit = db.query(BusinessUnit).filter(BusinessUnit.id == business_unit_id).first()
        division = db.query(Division).filter(Division.id == division_id).first()
        department = db.query(Department).filter(Department.id == department_id).first()
        designation = db.query(Designation).filter(Designation.id == designation_id).first()
        if not all((organization, business_unit, division, department, designation)):
            raise ValidationException("Invalid organizational hierarchy.")
        if (
            business_unit.organization_id != organization.id
            or division.business_unit_id != business_unit.id
            or department.division_id != division.id
            or designation.department_id != department.id
        ):
            raise ValidationException("Organizational hierarchy is inconsistent.")
        return SimpleNamespace(
            organization_id=organization.id,
            business_unit_id=business_unit.id,
            division_id=division.id,
            department_id=department.id,
            designation_id=designation.id,
        )
