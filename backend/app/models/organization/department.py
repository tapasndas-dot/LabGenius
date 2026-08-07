from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class Department(MasterEntity):
    """
    Department within a Division.
    """

    __tablename__ = "departments"

    division_id: Mapped[str] = mapped_column(
        ForeignKey("divisions.id"),
        nullable=False,
    )

    department_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    department_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    division = relationship(
        "Division",
        back_populates="departments",
    )