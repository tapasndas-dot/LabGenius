from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, SecurityConflictException
from app.models.business.qc_method import Method, MethodParameter, MethodVersion, Test
from app.models.business.specification import Specification, SpecificationLimit, SpecificationTest, SpecificationVersion
from app.repositories.business import (
    MethodParameterRepository, MethodRepository, MethodVersionRepository, SpecificationLimitRepository,
    SpecificationRepository, SpecificationTestRepository, SpecificationVersionRepository, TestRepository,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.organization_scope_service import OrganizationScopeService
from .qc_method_service import MethodParameterService, MethodService, MethodVersionService, TestService
from .specification_service import SpecificationLimitService, SpecificationService, SpecificationTestService, SpecificationVersionService


class _Transactions:
    audit_service = AuditService()

    @staticmethod
    def _owner(header):
        return header

    def _commit_create(self, db, record, actor, owner):
        try:
            self.audit_service.record_create(db, entity=record, actor=actor, owner=owner)
            db.commit(); db.refresh(record)
            return record
        except Exception:
            db.rollback(); raise

    def _create(self, db, actor, owner, mutation):
        try:
            return self._commit_create(db, mutation(), actor, owner)
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException("A conflicting child record already exists.") from exc

    def _commit_update(self, db, record, actor, owner, before, action=AuditAction.UPDATE):
        try:
            self.audit_service.record_update(db, entity=record, actor=actor, owner=owner, before=before, action=action)
            db.commit(); db.refresh(record)
            return record
        except Exception:
            db.rollback(); raise

    def _commit_delete(self, db, record, actor, owner, before, mutation):
        try:
            mutation()
            self.audit_service.record_delete(db, entity=record, actor=actor, owner=owner, before=before)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateResourceException("This record is referenced and cannot be deleted.") from exc
        except Exception:
            db.rollback(); raise


class SharedHeaderAPIService(_Transactions):
    def __init__(self, domain, repository, code_field):
        self.domain, self.repository, self.code_field = domain, repository, code_field
        self.scope_service = OrganizationScopeService()

    def list(self, db, actor, permission, *, limit=100, offset=0, **filters):
        query = self.scope_service.filter_shared_masters(self.repository.query(db), actor, permission, self.repository.model)
        query = self.repository.apply_list_filters(query, **filters)
        return query.order_by(getattr(self.repository.model, self.code_field), self.repository.model.id).offset(offset).limit(limit).all()

    def get(self, db, actor, record_id, permission):
        record = self.repository.get(db, actor.organization_id, record_id)
        if record is None:
            raise ResourceNotFoundException(f"{self.repository.model.__name__} not found.")
        self.scope_service.ensure_can_access_shared_master(actor, record, permission, resource_name=self.repository.model.__name__)
        return record

    def create(self, db, actor, permission, values):
        self.scope_service.ensure_can_create_shared_master(actor, permission)
        try:
            return self._commit_create(db, self.domain.create(db, actor.organization_id, values), actor, actor)
        except IntegrityError as exc:
            db.rollback(); raise DuplicateResourceException("A record with this code already exists.") from exc

    def update(self, db, actor, record_id, expected, permission, values):
        current = self.get(db, actor, record_id, permission)
        before = self.audit_service.snapshot(current)
        try:
            updated = self.domain.update_expected(db, actor.organization_id, record_id, expected, values)
            return self._commit_update(db, updated, actor, updated, before)
        except IntegrityError as exc:
            db.rollback(); raise DuplicateResourceException("A record with this code already exists.") from exc
        except Exception:
            db.rollback(); raise

    def set_active(self, db, actor, record_id, expected, permission, active):
        current = self.get(db, actor, record_id, permission)
        before = self.audit_service.snapshot(current)
        try:
            updated = self.repository.update_expected(db, actor.organization_id, record_id, expected, {"is_active": active})
            if updated is None:
                from app.core.exceptions import VersionConflictException
                from .organization_master_service import VERSION_CONFLICT_MESSAGE
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
            action = AuditAction.ACTIVATE if active else AuditAction.DEACTIVATE
            return self._commit_update(db, updated, actor, updated, before, action)
        except Exception:
            db.rollback(); raise

class HeaderService(SharedHeaderAPIService):
    def delete(self, db, actor, record_id, expected, permission):
        record = self.get(db, actor, record_id, permission)
        before = self.audit_service.snapshot(record)
        def mutation():
            from app.core.exceptions import VersionConflictException
            from .organization_master_service import VERSION_CONFLICT_MESSAGE
            if not self.repository.delete_expected(db, actor.organization_id, record_id, expected):
                raise VersionConflictException(VERSION_CONFLICT_MESSAGE)
        self._commit_delete(db, record, actor, record, before, mutation)


class NestedAPIService(_Transactions):
    def __init__(self):
        self.scope_service = OrganizationScopeService()

    def _header(self, db, actor, header_repo, header_id, permission):
        header = header_repo.get(db, actor.organization_id, header_id)
        if header is None:
            raise ResourceNotFoundException("Parent record not found.")
        self.scope_service.ensure_can_access_shared_master(actor, header, permission, resource_name=type(header).__name__)
        return header

    @staticmethod
    def _match(record, field, expected):
        if record is None or getattr(record, field) != expected:
            raise ResourceNotFoundException("Nested record not found.")
        return record


class MethodTreeAPIService(NestedAPIService):
    def __init__(self):
        super().__init__()
        self.headers = MethodRepository(); self.versions = MethodVersionRepository(); self.parameters = MethodParameterRepository()
        self.version_domain = MethodVersionService(); self.parameter_domain = MethodParameterService()

    def list_versions(self, db, actor, method_id, permission, status=None):
        self._header(db, actor, self.headers, method_id, permission)
        query = db.query(MethodVersion).filter(MethodVersion.method_id == method_id)
        if status is not None: query = query.filter(MethodVersion.status == status)
        return query.order_by(MethodVersion.version_number).all()

    def version(self, db, actor, method_id, version_id, permission):
        self._header(db, actor, self.headers, method_id, permission)
        return self._match(self.versions.get(db, actor.organization_id, version_id), "method_id", method_id)

    def create_version(self, db, actor, method_id, permission, values):
        owner = self._header(db, actor, self.headers, method_id, permission)
        self.scope_service.ensure_can_create_shared_master(actor, permission)
        return self._create(db, actor, owner, lambda: self.version_domain.create(db, actor.organization_id, method_id, values))

    def update_version(self, db, actor, method_id, version_id, expected, permission, values):
        owner = self._header(db, actor, self.headers, method_id, permission)
        current = self.version(db, actor, method_id, version_id, permission); before = self.audit_service.snapshot(current)
        try:
            return self._commit_update(db, self.version_domain.update_draft(db, actor.organization_id, version_id, expected, values), actor, owner, before)
        except Exception: db.rollback(); raise

    def lifecycle(self, db, actor, method_id, version_id, expected, permission, target):
        owner = self._header(db, actor, self.headers, method_id, permission)
        current = self.version(db, actor, method_id, version_id, permission); before = self.audit_service.snapshot(current)
        try:
            updated = self.version_domain.transition_status(db, actor.organization_id, version_id, expected, target)
            action = {"APPROVED": AuditAction.APPROVE, "RETIRED": AuditAction.RETIRE, "SUPERSEDED": AuditAction.SUPERSEDE}[target]
            return self._commit_update(db, updated, actor, owner, before, action)
        except Exception as exc:
            db.rollback()
            from app.core.exceptions import ValidationException
            if isinstance(exc, ValidationException): raise SecurityConflictException(str(exc)) from exc
            raise

    def list_parameters(self, db, actor, method_id, version_id, permission):
        self.version(db, actor, method_id, version_id, permission)
        return db.query(MethodParameter).filter(MethodParameter.method_version_id == version_id).order_by(MethodParameter.sequence_number.nullslast(), MethodParameter.parameter_code).all()

    def create_parameter(self, db, actor, method_id, version_id, permission, values):
        owner = self._header(db, actor, self.headers, method_id, permission); self.version(db, actor, method_id, version_id, permission)
        self.scope_service.ensure_can_create_shared_master(actor, permission)
        return self._create(db, actor, owner, lambda: self.parameter_domain.create(db, actor.organization_id, version_id, values))

    def update_parameter(self, db, actor, method_id, version_id, parameter_id, expected, permission, values):
        owner = self._header(db, actor, self.headers, method_id, permission); self.version(db, actor, method_id, version_id, permission)
        current = self._match(self.parameters.get(db, actor.organization_id, parameter_id), "method_version_id", version_id); before = self.audit_service.snapshot(current)
        try: return self._commit_update(db, self.parameter_domain.update_draft(db, actor.organization_id, parameter_id, expected, values), actor, owner, before)
        except Exception: db.rollback(); raise

    def delete_parameter(self, db, actor, method_id, version_id, parameter_id, expected, permission):
        owner = self._header(db, actor, self.headers, method_id, permission); self.version(db, actor, method_id, version_id, permission)
        current = self._match(self.parameters.get(db, actor.organization_id, parameter_id), "method_version_id", version_id); before = self.audit_service.snapshot(current)
        self._commit_delete(db, current, actor, owner, before, lambda: self.parameter_domain.delete_draft(db, actor.organization_id, parameter_id, expected))


class SpecificationTreeAPIService(NestedAPIService):
    def __init__(self):
        super().__init__()
        self.headers = SpecificationRepository(); self.versions = SpecificationVersionRepository(); self.tests = SpecificationTestRepository(); self.limits = SpecificationLimitRepository()
        self.version_domain = SpecificationVersionService(); self.test_domain = SpecificationTestService(); self.limit_domain = SpecificationLimitService()

    def version(self, db, actor, header_id, version_id, permission):
        self._header(db, actor, self.headers, header_id, permission)
        return self._match(self.versions.get(db, actor.organization_id, version_id), "specification_id", header_id)

    def list_versions(self, db, actor, header_id, permission, status=None):
        self._header(db, actor, self.headers, header_id, permission)
        query = db.query(SpecificationVersion).filter(SpecificationVersion.specification_id == header_id)
        if status is not None: query = query.filter(SpecificationVersion.status == status)
        return query.order_by(SpecificationVersion.version_number).all()

    def create_version(self, db, actor, header_id, permission, values):
        owner = self._header(db, actor, self.headers, header_id, permission); self.scope_service.ensure_can_create_shared_master(actor, permission)
        return self._create(db, actor, owner, lambda: self.version_domain.create(db, actor.organization_id, header_id, values))

    def update_version(self, db, actor, header_id, version_id, expected, permission, values):
        owner = self._header(db, actor, self.headers, header_id, permission); current = self.version(db, actor, header_id, version_id, permission); before = self.audit_service.snapshot(current)
        try: return self._commit_update(db, self.version_domain.update_draft(db, actor.organization_id, version_id, expected, values), actor, owner, before)
        except Exception: db.rollback(); raise

    def lifecycle(self, db, actor, header_id, version_id, expected, permission, target):
        owner = self._header(db, actor, self.headers, header_id, permission); current = self.version(db, actor, header_id, version_id, permission); before = self.audit_service.snapshot(current)
        try:
            updated = self.version_domain.transition_status(db, actor.organization_id, version_id, expected, target)
            action = {"APPROVED": AuditAction.APPROVE, "RETIRED": AuditAction.RETIRE, "SUPERSEDED": AuditAction.SUPERSEDE}[target]
            return self._commit_update(db, updated, actor, owner, before, action)
        except Exception as exc:
            db.rollback()
            from app.core.exceptions import ValidationException
            if isinstance(exc, ValidationException) and "cannot transition" in str(exc): raise SecurityConflictException(str(exc)) from exc
            raise

    def list_tests(self, db, actor, header_id, version_id, permission):
        self.version(db, actor, header_id, version_id, permission)
        return db.query(SpecificationTest).filter(SpecificationTest.specification_version_id == version_id).order_by(SpecificationTest.sequence_number).all()

    def test(self, db, actor, header_id, version_id, test_id, permission):
        self.version(db, actor, header_id, version_id, permission)
        return self._match(self.tests.get(db, actor.organization_id, test_id), "specification_version_id", version_id)

    def create_test(self, db, actor, header_id, version_id, permission, values):
        owner = self._header(db, actor, self.headers, header_id, permission); self.version(db, actor, header_id, version_id, permission); self.scope_service.ensure_can_create_shared_master(actor, permission)
        return self._create(db, actor, owner, lambda: self.test_domain.create(db, actor.organization_id, version_id, values))

    def update_test(self, db, actor, header_id, version_id, test_id, expected, permission, values):
        owner = self._header(db, actor, self.headers, header_id, permission); current = self.test(db, actor, header_id, version_id, test_id, permission); before = self.audit_service.snapshot(current)
        try: return self._commit_update(db, self.test_domain.update_draft(db, actor.organization_id, test_id, expected, values), actor, owner, before)
        except Exception: db.rollback(); raise

    def delete_test(self, db, actor, header_id, version_id, test_id, expected, permission):
        owner = self._header(db, actor, self.headers, header_id, permission); current = self.test(db, actor, header_id, version_id, test_id, permission); before = self.audit_service.snapshot(current)
        self._commit_delete(db, current, actor, owner, before, lambda: self.test_domain.delete_draft(db, actor.organization_id, test_id, expected))

    def list_limits(self, db, actor, header_id, version_id, test_id, permission):
        self.test(db, actor, header_id, version_id, test_id, permission)
        return db.query(SpecificationLimit).filter(SpecificationLimit.specification_test_id == test_id).order_by(SpecificationLimit.sequence_number.nullslast(), SpecificationLimit.id).all()

    def limit(self, db, actor, header_id, version_id, test_id, limit_id, permission):
        self.test(db, actor, header_id, version_id, test_id, permission)
        return self._match(self.limits.get(db, actor.organization_id, limit_id), "specification_test_id", test_id)

    def create_limit(self, db, actor, header_id, version_id, test_id, permission, values):
        owner = self._header(db, actor, self.headers, header_id, permission); self.test(db, actor, header_id, version_id, test_id, permission); self.scope_service.ensure_can_create_shared_master(actor, permission)
        return self._create(db, actor, owner, lambda: self.limit_domain.create(db, actor.organization_id, test_id, values))

    def update_limit(self, db, actor, header_id, version_id, test_id, limit_id, expected, permission, values):
        owner = self._header(db, actor, self.headers, header_id, permission); current = self.limit(db, actor, header_id, version_id, test_id, limit_id, permission); before = self.audit_service.snapshot(current)
        try: return self._commit_update(db, self.limit_domain.update_draft(db, actor.organization_id, limit_id, expected, values), actor, owner, before)
        except Exception: db.rollback(); raise

    def delete_limit(self, db, actor, header_id, version_id, test_id, limit_id, expected, permission):
        owner = self._header(db, actor, self.headers, header_id, permission); current = self.limit(db, actor, header_id, version_id, test_id, limit_id, permission); before = self.audit_service.snapshot(current)
        self._commit_delete(db, current, actor, owner, before, lambda: self.limit_domain.delete_draft(db, actor.organization_id, limit_id, expected))


test_api_service = HeaderService(TestService(), TestRepository(), "test_code")
method_api_service = HeaderService(MethodService(), MethodRepository(), "method_code")
specification_api_service = HeaderService(SpecificationService(), SpecificationRepository(), "specification_code")
