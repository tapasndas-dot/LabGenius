from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseModel
from app.database.mixins import TimestampMixin, UUIDMixin, VersionMixin


class SampleTestAssignment(UUIDMixin, TimestampMixin, VersionMixin, BaseModel):
    """
    Assignment history for a SampleTest.
    
    A SampleTest may have at most one ACTIVE assignment at a time.
    Historical assignments are preserved and queryable.
    """

    __tablename__ = "qc_sample_test_assignments"
    __table_args__ = (
        Index(
            "uq_qc_sample_test_assignments_active",
            "sample_test_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index("ix_qc_sample_test_assignments_sample_test_active", "sample_test_id", "is_active"),
        Index("ix_qc_sample_test_assignments_assigned_user", "assigned_user_id"),
        Index("ix_qc_sample_test_assignments_active", "is_active"),
    )

    sample_test_id: Mapped[UUID] = mapped_column(ForeignKey("sample_tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unassigned_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sample_test = relationship("SampleTest", back_populates="assignments")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    assigned_by_user = relationship("User", foreign_keys=[assigned_by_user_id])
    unassigned_by_user = relationship("User", foreign_keys=[unassigned_by_user_id])
