from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, VersionConflictException
from app.database.base_entities import MasterEntity
from app.repositories.business.organization_master_repository import OrganizationMasterRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.organization_scope_service import OrganizationScopeService
from .normalization import normalize_code, normalize_name, normalize_optional

MasterType = TypeVar("MasterType", bound=MasterEntity)
VERSION_CONFLICT_MESSAGE = "Record has been modified by another user. Refresh and try again."


class OrganizationMasterService(Generic[MasterType]):
    """Shared mechanics only; each business master retains its own public service."""

    def __init__(
        self, repository: OrganizationMasterRepository[MasterType],
        resource_name: str | None = None,
    ):
        self.repository = repository
        self.audit_service = AuditService()
        self.scope_service = OrganizationScopeService()
        self.resource_name = resource_name or repository.model.__name__.replace("Type", " type").lower()

    def _normalize_common(self, values: dict) -> dict:
        normalized = dict(values)
        if "code" in normalized:
            normalized["code"] = normalize_code(normalized["code"])
        if "name" in normalized:
            normalized["name"] = normalize_name(normalized["name"])
        for field in ("description", "website", "default_unit_of_measure"):
            if field in normalized:
                normalized[field] = normalize_optional(normalized[field])
        return normalized

    def _mutate(
        self, db: Session, organization_id: UUID, record_id: UUID,
        expected_version: int, values: dict,
    ) -> MasterType:
        updated = self.repository.update_expected(
            db, organization_id, record_id, expected_version, values
        )
        if updated is not None:
            return updated
        if self.repository.get(db, organization_id, record_id) is None:
            raise ResourceNotFoundException("Record not found.")
        raise VersionConflictException(VERSION_CONFLICT_MESSAGE)

    def set_active(
        self, db: Session, organization_id: UUID, record_id: UUID,
        expected_version: int, is_active: bool,
    ) -> MasterType:
        return self._mutate(db, organization_id, record_id, expected_version, {"is_active": is_active})

    def delete(
        self, db: Session, organization_id: UUID, record_id: UUID, expected_version: int
    ) -> None:
        if self.repository.delete_expected(db, organization_id, record_id, expected_version):
            return
        if self.repository.get(db, organization_id, record_id) is None:
            raise ResourceNotFoundException("Record not found.")
        raise VersionConflictException(VERSION_CONFLICT_MESSAGE)

    def list_scoped(
        self, db: Session, actor, permission_code: str, *, limit: int = 100,
        offset: int = 0, search: str | None = None, is_active: bool | None = None,
        **filters,
    ):
        query = self.scope_service.filter_shared_masters(
            self.repository.query(db), actor, permission_code, self.repository.model
        )
        query = self.repository.apply_list_filters(
            query, search=search, is_active=is_active, **filters
        )
        return query.order_by(self.repository.model.code.asc(), self.repository.model.id.asc()).offset(offset).limit(limit).all()

    def get_scoped(self, db: Session, record_id: UUID, actor, permission_code: str):
        record = self.repository.get(db, actor.organization_id, record_id)
        if record is None:
            raise ResourceNotFoundException(f"{self.repository.model.__name__} not found.")
        self.scope_service.ensure_can_access_shared_master(
            actor, record, permission_code, resource_name=self.repository.model.__name__
        )
        return record

    def _duplicate_message(self) -> str:
        return f"A {self.resource_name} with this code already exists."

    def _commit_create(self, db: Session, record: MasterType, actor) -> MasterType:
        try:
            self.audit_service.record_create(db, entity=record, actor=actor, owner=record)
            db.commit()
            db.refresh(record)
            return record
        except Exception:
            db.rollback()
            raise

    def _add_and_commit_create(self, db: Session, record: MasterType, actor) -> MasterType:
        try:
            self.repository.add(db, record)
            return self._commit_create(db, record, actor)
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(self._duplicate_message()) from exc

    def update_scoped(
        self, db: Session, actor, record_id: UUID, expected_version: int, values: dict,
        permission_code: str,
    ) -> MasterType:
        before_record = self.get_scoped(db, record_id, actor, permission_code)
        before = self.audit_service.snapshot(before_record)
        try:
            updated = self._mutate(
                db, actor.organization_id, record_id, expected_version, values
            )
            self.audit_service.record_update(
                db, entity=updated, actor=actor, owner=updated, before=before
            )
            db.commit()
            db.refresh(updated)
            return updated
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(self._duplicate_message()) from exc
        except Exception:
            db.rollback()
            raise

    def set_active_scoped(
        self, db: Session, actor, record_id: UUID, expected_version: int,
        is_active: bool, permission_code: str,
    ) -> MasterType:
        before_record = self.get_scoped(db, record_id, actor, permission_code)
        before = self.audit_service.snapshot(before_record)
        try:
            updated = self._mutate(
                db, actor.organization_id, record_id, expected_version,
                {"is_active": is_active},
            )
            self.audit_service.record_update(
                db, entity=updated, actor=actor, owner=updated, before=before,
                action=AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE,
            )
            db.commit()
            db.refresh(updated)
            return updated
        except Exception:
            db.rollback()
            raise

    def delete_scoped(
        self, db: Session, actor, record_id: UUID, expected_version: int,
        permission_code: str,
    ) -> None:
        record = self.get_scoped(db, record_id, actor, permission_code)
        before = self.audit_service.snapshot(record)
        try:
            if not self.repository.delete_expected(
                db, actor.organization_id, record_id, expected_version
            ):
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            self.audit_service.record_delete(
                db, entity=record, actor=actor, owner=record, before=before
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException(
                f"This {self.resource_name} is referenced and cannot be deleted."
            ) from exc
        except Exception:
            db.rollback()
            raise
