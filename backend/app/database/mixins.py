"""
Reusable SQLAlchemy mixins used throughout the Ozolytic Platform.
"""

import uuid

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import func

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class UUIDMixin:
    """Primary Key"""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Created / Updated timestamps"""

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ActiveMixin:
    """Soft active flag"""

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class VersionMixin:
    """Optimistic concurrency"""

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )
    import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class OrganizationMixin:
    """Provides organization ownership."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


class SoftDeleteMixin:
    """Supports soft deletion."""

    deleted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CreatedByMixin:
    """Stores creator."""

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )


class UpdatedByMixin:
    """Stores last modifier."""

    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )


class DeletedByMixin:
    """Stores deleting user."""

    deleted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )