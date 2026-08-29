from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class LocationType(StrEnum):
    SITE = "SITE"
    BUILDING = "BUILDING"
    AREA = "AREA"
    LABORATORY = "LABORATORY"
    ROOM = "ROOM"
    STORAGE = "STORAGE"
    OTHER = "OTHER"


class Location(MasterEntity):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_locations_organization_code"),
        UniqueConstraint("organization_id", "id", name="uq_locations_organization_id"),
        ForeignKeyConstraint(
            ["organization_id", "parent_location_id"],
            ["locations.organization_id", "locations.id"],
            name="fk_locations_parent_same_organization",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "location_type IN ('SITE', 'BUILDING', 'AREA', 'LABORATORY', 'ROOM', 'STORAGE', 'OTHER')",
            name="ck_locations_location_type",
        ),
        CheckConstraint("version > 0", name="ck_locations_version_positive"),
        CheckConstraint("parent_location_id IS NULL OR parent_location_id <> id", name="ck_locations_not_self_parent"),
        Index("ix_locations_organization_active", "organization_id", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parent_location_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    parent = relationship(
        "Location", remote_side="Location.id", back_populates="children",
        foreign_keys=[parent_location_id],
    )
    children = relationship(
        "Location", back_populates="parent", passive_deletes=True,
        foreign_keys=[parent_location_id],
    )
