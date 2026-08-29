from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base_entities import MasterEntity


class MaterialType(StrEnum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PACKAGING_MATERIAL = "PACKAGING_MATERIAL"
    INTERMEDIATE = "INTERMEDIATE"
    BULK_PRODUCT = "BULK_PRODUCT"
    FINISHED_PRODUCT = "FINISHED_PRODUCT"
    REFERENCE_STANDARD = "REFERENCE_STANDARD"
    REAGENT = "REAGENT"
    OTHER = "OTHER"


class Material(MasterEntity):
    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_materials_organization_code"),
        CheckConstraint(
            "material_type IN ('RAW_MATERIAL', 'PACKAGING_MATERIAL', 'INTERMEDIATE', 'BULK_PRODUCT', 'FINISHED_PRODUCT', 'REFERENCE_STANDARD', 'REAGENT', 'OTHER')",
            name="ck_materials_material_type",
        ),
        CheckConstraint("version > 0", name="ck_materials_version_positive"),
        Index("ix_materials_organization_active", "organization_id", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_unit_of_measure: Mapped[str | None] = mapped_column(String(50), nullable=True)
