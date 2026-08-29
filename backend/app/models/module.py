from uuid import UUID
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base_entities import MasterEntity


class Module(MasterEntity):
    __tablename__ = "modules"
    __table_args__ = (
        CheckConstraint(
            "capability_class IN ('PLATFORM', 'CORE_LAB', 'OPTIONAL_SHARED', 'OPTIONAL_DOMAIN')",
            name="ck_modules_capability_class",
        ),
        CheckConstraint("version > 0", name="ck_modules_version_positive"),
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capability_class: Mapped[str] = mapped_column(String(30), nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrganizationModule(MasterEntity):
    __tablename__ = "organization_modules"
    __table_args__ = (
        UniqueConstraint("organization_id", "module_id", name="uq_organization_modules_organization_module"),
        CheckConstraint("version > 0", name="ck_organization_modules_version_positive"),
    )
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    module_id: Mapped[UUID] = mapped_column(ForeignKey("modules.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
