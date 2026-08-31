from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.auth.hashing import hash_password
from app.auth.password_policy import PasswordPolicy

from app.services.base_service import BaseService

from app.models.user.user import User

from app.repositories.user.user_repository import UserRepository

from app.schemas.user.user import (
    UserCreate,
    UserUpdate,
)

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
)
from app.services.user.admin_safety_service import AdminSafetyService
from app.services.organization_scope_service import OrganizationScopeService
from app.services.audit_service import AuditService


class UserService(BaseService[User]):

    def __init__(self):
        super().__init__(UserRepository())

        self.admin_safety_service = AdminSafetyService()
        self.scope_service = OrganizationScopeService()
        self.audit_service = AuditService()

    def get_all_scoped(self, db: Session, actor: User):
        return self.scope_service.filter_users(db, actor, "user.view").all()

    def get_scoped(self, db: Session, user_id, actor: User, permission_code: str):
        user = self.repository.get(db, user_id)
        if user is None:
            raise ResourceNotFoundException("User not found.")
        self.scope_service.ensure_can_access_user(actor, user, permission_code)
        return user

    def hierarchy_lookups(self, db: Session, actor: User, permission_code: str):
        return self.scope_service.user_hierarchy_lookups(db, actor, permission_code)

    def create(
        self,
        db: Session,
        user: UserCreate,
        actor: User,
    ):

        PasswordPolicy.validate(user.password)

        self.scope_service.validate_hierarchy(
            db,
            organization_id=user.organization_id,
            business_unit_id=user.business_unit_id,
            division_id=user.division_id,
            department_id=user.department_id,
            designation_id=user.designation_id,
        )
        self.scope_service.ensure_can_access_user(actor, user, "user.create")

        # -----------------------------
        # Duplicate checks
        # -----------------------------

        if self.repository.get_by_username(
            db,
            user.username,
        ):
            raise DuplicateResourceException(
                "Username already exists."
            )

        if self.repository.get_by_email(
            db,
            user.email,
        ):
            raise DuplicateResourceException(
                "Email already exists."
            )

        if self.repository.get_by_employee_code(
            db,
            user.employee_code,
        ):
            raise DuplicateResourceException(
                "Employee code already exists."
            )

        db_object = User(
            organization_id=user.organization_id,
            business_unit_id=user.business_unit_id,
            division_id=user.division_id,
            department_id=user.department_id,
            designation_id=user.designation_id,
            employee_code=user.employee_code,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            email=user.email,
            mobile=user.mobile,
            username=user.username,
            password_hash=hash_password(
                user.password
            ),
            password_changed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            force_password_change=True,
            timezone=user.timezone,
            language=user.language,
        )

        db.add(db_object)
        db.flush()
        self.audit_service.record_create(db, entity=db_object, actor=actor)
        db.commit()
        db.refresh(db_object)
        return db_object

    def update(
        self,
        db: Session,
        db_object: User,
        update: UserUpdate,
        actor: User,
    ):

        self.scope_service.ensure_can_access_user(actor, db_object, "user.update")

        before = self.audit_service.snapshot(db_object)
        data = update.model_dump(
            exclude_unset=True,
        )

        hierarchy = {
            key: data.get(key, getattr(db_object, key))
            for key in (
                "organization_id", "business_unit_id", "division_id",
                "department_id", "designation_id",
            )
        }
        self.scope_service.validate_hierarchy(
            db,
            **hierarchy,
        )
        self.scope_service.ensure_can_access_user(
            actor, SimpleNamespace(id=db_object.id, **hierarchy), "user.update"
        )
        for key, value in data.items():
            setattr(db_object, key, value)
        self.audit_service.record_update(
            db, entity=db_object, actor=actor, before=before
        )
        db.commit()
        db.refresh(db_object)
        return db_object

    def delete(
        self,
        db: Session,
        db_object: User,
        actor: User,
    ):
        self.scope_service.ensure_can_access_user(actor, db_object, "user.delete")
        self.admin_safety_service.ensure_user_can_lose_admin_access(
            db,
            db_object.id,
            actor_user_id=actor.id,
            operation="DELETE_USER",
        )
        before = self.audit_service.snapshot(db_object)
        self.audit_service.record_delete(
            db, entity=db_object, actor=actor, before=before
        )
        db.delete(db_object)
        db.commit()
