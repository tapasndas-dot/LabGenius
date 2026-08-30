from enum import StrEnum
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy import false, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.organization.organization import Organization
from app.models.user.user import User
from app.models.business.instrument import Instrument
from app.models.business.sample import Sample


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

    def filter_instruments(self, query, actor: User, permission_code: str):
        """Apply the permission-specific Instrument scope as SQL predicates."""
        scope = self.resolve_scope(actor, permission_code)
        query = query.filter(Instrument.organization_id == actor.organization_id)
        if scope == AccessScope.ORGANIZATION:
            return query
        if scope == AccessScope.BUSINESS_UNIT:
            divisions = select(Division.id).where(
                Division.business_unit_id == actor.business_unit_id
            )
            departments = select(Department.id).where(
                Department.division_id.in_(divisions)
            )
            return query.filter(or_(
                Instrument.business_unit_id == actor.business_unit_id,
                Instrument.division_id.in_(divisions),
                Instrument.department_id.in_(departments),
            ))
        if scope == AccessScope.DIVISION:
            departments = select(Department.id).where(
                Department.division_id == actor.division_id
            )
            return query.filter(or_(
                Instrument.division_id == actor.division_id,
                Instrument.department_id.in_(departments),
            ))
        if scope == AccessScope.DEPARTMENT:
            return query.filter(Instrument.department_id == actor.department_id)
        return query.filter(Instrument.responsible_user_id == actor.id)

    def filter_samples(self, query, actor: User, permission_code: str):
        """Apply operational Sample hierarchy scope; SELF awaits assignments."""
        scope = self.resolve_scope(actor, permission_code)
        query = query.filter(Sample.organization_id == actor.organization_id)
        if scope == AccessScope.ORGANIZATION:
            return query
        if scope == AccessScope.BUSINESS_UNIT:
            divisions = select(Division.id).where(Division.business_unit_id == actor.business_unit_id)
            departments = select(Department.id).where(Department.division_id.in_(divisions))
            return query.filter(or_(
                Sample.business_unit_id == actor.business_unit_id,
                Sample.division_id.in_(divisions),
                Sample.department_id.in_(departments),
            ))
        if scope == AccessScope.DIVISION:
            departments = select(Department.id).where(Department.division_id == actor.division_id)
            return query.filter(or_(
                Sample.division_id == actor.division_id,
                Sample.department_id.in_(departments),
            ))
        if scope == AccessScope.DEPARTMENT:
            return query.filter(Sample.department_id == actor.department_id)
        return query.filter(false())

    def can_place_sample(self, db: Session, actor: User, permission_code: str, values: dict) -> bool:
        scope = self.resolve_scope(actor, permission_code)
        if scope == AccessScope.ORGANIZATION:
            return True
        if scope == AccessScope.SELF:
            return False
        business_unit_id = values.get("business_unit_id")
        division_id = values.get("division_id")
        department_id = values.get("department_id")
        division = db.get(Division, division_id) if division_id else None
        department = db.get(Department, department_id) if department_id else None
        effective_division_id = division_id or (department.division_id if department else None)
        effective_division = division or (db.get(Division, effective_division_id) if effective_division_id else None)
        effective_business_unit_id = business_unit_id or (effective_division.business_unit_id if effective_division else None)
        if scope == AccessScope.BUSINESS_UNIT:
            return effective_business_unit_id == actor.business_unit_id
        if scope == AccessScope.DIVISION:
            return effective_division_id == actor.division_id
        return department_id == actor.department_id

    def can_place_instrument(
        self, db: Session, actor: User, permission_code: str, values: dict
    ) -> bool:
        """Authorize a validated target hierarchy for create or reassignment."""
        scope = self.resolve_scope(actor, permission_code)
        if scope == AccessScope.ORGANIZATION:
            return True
        if scope == AccessScope.SELF:
            return False

        business_unit_id = values.get("business_unit_id")
        division_id = values.get("division_id")
        department_id = values.get("department_id")
        division = db.query(Division).filter(Division.id == division_id).first() if division_id else None
        department = (
            db.query(Department).filter(Department.id == department_id).first()
            if department_id else None
        )
        effective_division_id = division_id or (
            department.division_id if department is not None else None
        )
        effective_division = division or (
            db.query(Division).filter(Division.id == effective_division_id).first()
            if effective_division_id else None
        )
        effective_business_unit_id = business_unit_id or (
            effective_division.business_unit_id
            if effective_division is not None else None
        )
        if scope == AccessScope.BUSINESS_UNIT:
            return effective_business_unit_id == actor.business_unit_id
        if scope == AccessScope.DIVISION:
            return effective_division_id == actor.division_id
        return department_id == actor.department_id

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
