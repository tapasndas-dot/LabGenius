from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_entities import MasterEntity


class Designation(MasterEntity):
    """
    Designation within a Department.
    """

    __tablename__ = "designations"

    department_id: Mapped[str] = mapped_column(
        ForeignKey("departments.id"),
        nullable=False,
    )

    designation_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    designation_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ---------- Business Capabilities ----------

    can_approve_workflows: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_manage_assets: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_schedule_calibration: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_execute_calibration: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_close_service: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_manage_documents: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_review_results: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_release_results: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_manage_users: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    can_view_reports: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    department = relationship(
        "Department",
        back_populates="designations",
    )