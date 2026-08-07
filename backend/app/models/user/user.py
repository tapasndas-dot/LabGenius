from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class User(MasterEntity):
    """
    LabGenius application user.

    A User represents an employee of an organization and contains:

    - Organization assignment
    - Employee profile
    - Authentication information
    - Security information
    - User preferences
    """

    __tablename__ = "users"

    # ==========================================================
    # Organization Assignment
    # ==========================================================

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

    department_id: Mapped[str] = mapped_column(
        ForeignKey("departments.id"),
        nullable=False,
    )

    designation_id: Mapped[str] = mapped_column(
        ForeignKey("designations.id"),
        nullable=False,
    )

    # ==========================================================
    # Employee Information
    # ==========================================================

    employee_code: Mapped[str] = mapped_column(
        String(30),
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

    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
        index=True,
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # ==========================================================
    # Login Information
    # ==========================================================

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ==========================================================
    # Security
    # ==========================================================

    account_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    force_password_change: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    # ==========================================================
    # Preferences
    # ==========================================================

    timezone: Mapped[str] = mapped_column(
        String(100),
        default="Asia/Kolkata",
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(20),
        default="en",
        nullable=False,
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    organization = relationship(
    "Organization",
    )

    business_unit = relationship(
        "BusinessUnit",
    )

    division = relationship(
        "Division",
    )

    department = relationship(
        "Department",
    )

    designation = relationship(
        "Designation",
    )

    user_roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )