from sqlalchemy import String
from sqlalchemy.orm import (Mapped, mapped_column, relationship)


from app.database.base_entities import MasterEntity


class Permission(MasterEntity):
    """
    Application permission.
    """

    __tablename__ = "permissions"

    permission_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    permission_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    role_permissions = relationship(
    "RolePermission",
    back_populates="permission",
    cascade="all, delete-orphan",
    )