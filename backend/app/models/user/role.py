from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base_entities import MasterEntity


class Role(MasterEntity):
    """
    Security role.
    """

    __tablename__ = "roles"

    role_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )