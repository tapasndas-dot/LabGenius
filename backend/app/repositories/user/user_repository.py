from sqlalchemy.orm import Session, joinedload

from app.models.user.user import User
from app.models.user.user_role import UserRole
from app.models.user.role import Role
from app.models.user.role_permission import RolePermission

from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self):
        super().__init__(User)

    def get_by_username(
        self,
        db: Session,
        username: str,
    ):
        return (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

    def get_by_email(
        self,
        db: Session,
        email: str,
    ):
        return (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_by_employee_code(
        self,
        db: Session,
        employee_code: str,
    ):
        return (
            db.query(User)
            .filter(User.employee_code == employee_code)
            .first()
        )

    def get_by_department(
        self,
        db: Session,
        department_id,
    ):
        return (
            db.query(User)
            .filter(User.department_id == department_id)
            .all()
        )

    def get_by_designation(
        self,
        db: Session,
        designation_id,
    ):
        return (
            db.query(User)
            .filter(User.designation_id == designation_id)
            .all()
        )

    def get_with_roles(
        self,
        db: Session,
        user_id,
    ):
        """
        Load a user together with all roles and permissions.
        """

        return (
            db.query(User)
            .options(
                joinedload(User.user_roles)
                .joinedload(UserRole.role)
                .joinedload(Role.role_permissions)
                .joinedload(RolePermission.permission)
            )
            .filter(User.id == user_id)
            .first()
        )