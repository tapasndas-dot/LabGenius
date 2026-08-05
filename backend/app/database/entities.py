"""
Base entity hierarchy for the Ozolytic Platform.
"""

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .base import BaseModel
from .mixins import (
    ActiveMixin,
    CreatedByMixin,
    DeletedByMixin,
    OrganizationMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    UpdatedByMixin,
    VersionMixin,
)


class ReferenceEntity(
    UUIDMixin,
    TimestampMixin,
    ActiveMixin,
    BaseModel,
):
    """
    Base class for lookup/reference tables.
    """

    __abstract__ = True

    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]


class MasterEntity(
    UUIDMixin,
    TimestampMixin,
    ActiveMixin,
    VersionMixin,
    BaseModel,
):
    """
    Base class for master data.
    """

    __abstract__ = True


class TransactionEntity(
    UUIDMixin,
    TimestampMixin,
    OrganizationMixin,
    CreatedByMixin,
    UpdatedByMixin,
    DeletedByMixin,
    SoftDeleteMixin,
    ActiveMixin,
    VersionMixin,
    BaseModel,
):
    """
    Base class for transactional data.
    """

    __abstract__ = True