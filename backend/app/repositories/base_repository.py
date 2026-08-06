from typing import Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: UUID):
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session):
        return db.query(self.model).all()

    def create(self, db: Session, obj):
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, obj):
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, obj):
        db.delete(obj)
        db.commit()