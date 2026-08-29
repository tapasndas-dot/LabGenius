"""Idempotently seed the system-managed capability registry."""
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.module import Module
from app.services.module_service import MODULE_CATALOG


def seed_modules(db: Session) -> None:
    for item in MODULE_CATALOG:
        module = db.query(Module).filter(Module.code == item["code"]).first()
        if module is None:
            db.add(Module(**item))
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed_modules(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
