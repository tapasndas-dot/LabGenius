from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base_entities import MasterEntity


class InstrumentType(MasterEntity):
    __tablename__ = "instrument_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_instrument_types_organization_code"),
        CheckConstraint("version > 0", name="ck_instrument_types_version_positive"),
        Index("ix_instrument_types_organization_active", "organization_id", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
