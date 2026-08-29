from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, text
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
        CheckConstraint(
            "access_scope IN ('ORGANIZATION', 'BUSINESS_UNIT', 'DIVISION', 'DEPARTMENT', 'SELF')",
            name="ck_user_roles_access_scope",
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

    user = relationship(
        "User",
        back_populates="user_roles",
    )

    role = relationship(
        "Role",
        back_populates="user_roles",
    )

    access_scope: Mapped[str] = mapped_column(
        String(30),
        default="SELF",
        server_default=text("'SELF'"),
        nullable=False,
    )
