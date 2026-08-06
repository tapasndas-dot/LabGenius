from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class Division(MasterEntity):
    """
    Division within a Business Unit.
    """

    __tablename__ = "divisions"

    business_unit_id: Mapped[str] = mapped_column(
        ForeignKey("business_units.id"),
        nullable=False,
    )

    division_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    division_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    business_unit = relationship(
        "BusinessUnit",
        back_populates="divisions",
    )