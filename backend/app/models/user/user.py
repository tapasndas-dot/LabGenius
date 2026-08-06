from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class User(MasterEntity):
    """
    LabGenius application user.
    """

    __tablename__ = "users"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
    )

    business_unit_id: Mapped[str] = mapped_column(
        ForeignKey("business_units.id"),
        nullable=False,
    )

    division_id: Mapped[str] = mapped_column(
        ForeignKey("divisions.id"),
        nullable=False,
    )

    employee_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    organization = relationship("Organization")
    business_unit = relationship("BusinessUnit")
    division = relationship("Division")