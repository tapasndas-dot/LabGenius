from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException

ModelType = TypeVar("ModelType")


class BaseService(Generic[ModelType]):

    def __init__(self, repository):
        self.repository = repository

    def get_all(
        self,
        db: Session,
    ):
        return self.repository.get_all(db)

    def get(
        self,
        db: Session,
        object_id,
    ):
        db_object = self.repository.get(
            db,
            object_id,
        )

        if db_object is None:
            raise ResourceNotFoundException(
                f"{self.repository.model.__name__} not found."
            )

        return db_object

    def update(
        self,
        db: Session,
        db_object,
        update,
    ):
        data = update.model_dump(
            exclude_unset=True,
        )

        for key, value in data.items():
            setattr(
                db_object,
                key,
                value,
            )

        return self.repository.update(
            db,
            db_object,
        )

    def delete(
        self,
        db: Session,
        db_object,
    ):
        return self.repository.delete(
            db,
            db_object,
        )