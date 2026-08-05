"""
Organization model.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.entities import MasterEntity


class Organization(MasterEntity):
    """
    Represents a tenant organization using the LabGenius platform.
    """

    __tablename__ = "organizations"

    organization_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    organization_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    legal_name: Mapped[str] = mapped_column(
        String(250),
        nullable=True,
    )

    registration_number: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    tax_number: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    website: Mapped[str] = mapped_column(
        String(200),
        nullable=True,
    )

    email: Mapped[str] = mapped_column(
        String(200),
        nullable=True,
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Asia/Kolkata",
    )

    currency_code: Mapped[str] = mapped_column(
        String(10),
        default="INR",
    )