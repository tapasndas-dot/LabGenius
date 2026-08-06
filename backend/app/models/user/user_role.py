from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class UserRole(MasterEntity):
    """
    Links Users and Roles.
    """

    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role_id",
            name="uq_user_role",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id"),
        nullable=False,
    )

    user = relationship("User")

    role = relationship("Role")