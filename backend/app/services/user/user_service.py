from sqlalchemy.orm import Session

from app.auth.hashing import hash_password

from app.services.base_service import BaseService

from app.models.user.user import User

from app.repositories.user.user_repository import UserRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.business_unit_repository import BusinessUnitRepository
from app.repositories.division_repository import DivisionRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.designation_repository import DesignationRepository

from app.schemas.user.user import (
    UserCreate,
    UserUpdate,
)

from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
)


class UserService(BaseService[User]):

    def __init__(self):
        super().__init__(UserRepository())

        self.organization_repository = OrganizationRepository()
        self.business_unit_repository = BusinessUnitRepository()
        self.division_repository = DivisionRepository()
        self.department_repository = DepartmentRepository()
        self.designation_repository = DesignationRepository()

    def create(
        self,
        db: Session,
        user: UserCreate,
    ):

        # -----------------------------
        # Validate hierarchy
        # -----------------------------

        if self.organization_repository.get(
            db,
            user.organization_id,
        ) is None:
            raise ResourceNotFoundException(
                "Organization not found."
            )

        if self.business_unit_repository.get(
            db,
            user.business_unit_id,
        ) is None:
            raise ResourceNotFoundException(
                "Business Unit not found."
            )

        if self.division_repository.get(
            db,
            user.division_id,
        ) is None:
            raise ResourceNotFoundException(
                "Division not found."
            )

        if self.department_repository.get(
            db,
            user.department_id,
        ) is None:
            raise ResourceNotFoundException(
                "Department not found."
            )

        if self.designation_repository.get(
            db,
            user.designation_id,
        ) is None:
            raise ResourceNotFoundException(
                "Designation not found."
            )

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
            timezone=user.timezone,
            language=user.language,
        )

        return self.repository.create(
            db,
            db_object,
        )

    def update(
        self,
        db: Session,
        db_object: User,
        update: UserUpdate,
    ):

        data = update.model_dump(
            exclude_unset=True,
        )

        for key, value in data.items():
            setattr(
                db_object,
                key,
                value,
            )

        return self.repository.update(
            db,
            db_object,
        )