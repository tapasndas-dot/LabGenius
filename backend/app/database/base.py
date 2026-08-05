"""
Base SQLAlchemy classes for the Ozolytic Platform.

Every ORM model in LabGenius inherits from BaseModel.
"""

from sqlalchemy.orm import DeclarativeBase


class BaseModel(DeclarativeBase):
    """
    Root class for all SQLAlchemy ORM models.
    """

    pass