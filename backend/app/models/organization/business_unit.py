from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class BusinessUnit(MasterEntity):
    """
    Business Unit within an Organization.
    """

    __tablename__ = "business_units"
    
    from uuid import UUID

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
    )

    business_unit_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    business_unit_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    organization = relationship(
        "Organization",
        back_populates="business_units",
    )
    divisions = relationship(
    "Division",
    back_populates="business_unit",
    cascade="all, delete-orphan",
)