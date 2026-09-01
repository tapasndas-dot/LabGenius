from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (ResourceNotFoundException, ValidationException,
                                 VersionConflictException)
from app.models.business.qc_method import Method, MethodParameter, MethodVersion, Test
from app.models.business.sample import Sample, SampleTest
from app.models.business.sample_test_result import (ParameterResult,
                                                    ResultInstrumentUsage,
                                                    SampleTestResult)
from app.services.audit_service import AuditAction, AuditService
from app.services.organization_scope_service import OrganizationScopeService

from .sample_service import SampleService, SampleTestService
from .sample_test_result_service import SampleTestResultService


class SampleTestResultAPIService:
    """Secured HTTP transaction boundary for Sprint 21B result entry."""

    def __init__(self):
        self.samples = SampleService()
        self.sample_tests = SampleTestService(self.samples.repository)
        self.results = SampleTestResultService(sample_repository=self.samples.repository)
        self.scope = OrganizationScopeService()
        self.audit = AuditService()

    def _context(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
                 permission: str) -> tuple[Sample, SampleTest]:
        test = self.scope.filter_sample_tests(
            self.sample_tests.repository.query(db), actor, permission
        ).filter(
            SampleTest.id == sample_test_id,
            SampleTest.sample_id == sample_id,
        ).first()
        if test is None:
            raise ResourceNotFoundException("Sample Test not found.")
        sample = db.query(Sample).filter(
            Sample.id == sample_id,
            Sample.organization_id == actor.organization_id,
        ).first()
        if sample is None:
            raise ResourceNotFoundException("Sample not found.")
        return sample, test

    def _result(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
                result_id: UUID, permission: str) -> tuple[Sample, SampleTest, SampleTestResult]:
        sample, test = self._context(db, actor, sample_id, sample_test_id, permission)
        result = self.results.result_repository.get_for_sample_test(db, test.id, result_id)
        if result is None:
            raise ResourceNotFoundException("Result not found.")
        return sample, test, result

    @staticmethod
    def _audit_context(sample: Sample, test: SampleTest,
                       result: SampleTestResult, **extra) -> dict:
        return {
            "sample_id": sample.id, "sample_number": sample.sample_number,
            "sample_test_id": test.id, "result_id": result.id,
            "result_sequence_number": result.sequence_number, **extra,
        }

    @staticmethod
    def _response(db: Session, sample: Sample, test: SampleTest,
                  result: SampleTestResult) -> dict:
        test_master = db.get(Test, test.test_id)
        method_version = db.get(MethodVersion, test.method_version_id)
        method = db.get(Method, method_version.method_id)
        method_parameters = db.query(MethodParameter).filter(
            MethodParameter.method_version_id == method_version.id
        ).order_by(MethodParameter.sequence_number, MethodParameter.id).all()
        parameter_results = db.query(ParameterResult).filter(
            ParameterResult.sample_test_result_id == result.id
        ).all()
        usages = db.query(ResultInstrumentUsage).filter(
            ResultInstrumentUsage.sample_test_result_id == result.id
        ).all()

        def parameter_context(parameter):
            return {
                "id": parameter.id, "code": parameter.parameter_code,
                "name": parameter.parameter_name, "value_type": parameter.value_type,
                "unit": parameter.unit, "is_required": parameter.is_required,
                "sequence_number": parameter.sequence_number,
            }

        return {
            "id": result.id, "sample_test_id": result.sample_test_id,
            "sequence_number": result.sequence_number, "status": result.status,
            "started_at": result.started_at, "completed_at": result.completed_at,
            "entered_at": result.entered_at,
            "entered_by": ({"id": result.entered_by_user.id,
                            "display_name": result.entered_by_user.display_name}
                           if result.entered_by_user else None),
            "notes": result.notes,
            "sample": {"id": sample.id, "code": sample.sample_number,
                       "name": sample.sample_description or sample.sample_number},
            "sample_test": {"id": test.id, "code": str(test.sequence_number),
                            "name": test.display_name or test_master.test_name},
            "test": {"id": test_master.id, "code": test_master.test_code,
                     "name": test_master.test_name},
            "method_version": {
                "id": method_version.id, "method_id": method.id,
                "code": method.method_code, "name": method.method_name,
                "version_number": method_version.version_number,
            },
            "method_parameters": [parameter_context(item) for item in method_parameters],
            "parameters": [{
                "id": item.id, "method_parameter_id": item.method_parameter_id,
                "parameter": parameter_context(item.method_parameter),
                "value_type": item.value_type, "text_value": item.text_value,
                "numeric_value": item.numeric_value, "integer_value": item.integer_value,
                "boolean_value": item.boolean_value, "date_value": item.date_value,
                "datetime_value": item.datetime_value, "version": item.version,
                "created_at": item.created_at, "updated_at": item.updated_at,
            } for item in parameter_results],
            "instrument_usages": [{
                "id": item.id, "instrument_id": item.instrument_id,
                "instrument": {"id": item.instrument.id,
                               "code": item.instrument.instrument_code,
                               "name": item.instrument.instrument_name,
                               "model_number": item.instrument.model_number,
                               "serial_number": item.instrument.serial_number},
                "usage_notes": item.usage_notes, "version": item.version,
                "created_at": item.created_at, "updated_at": item.updated_at,
            } for item in usages],
            "version": result.version, "created_at": result.created_at,
            "updated_at": result.updated_at,
        }

    def list(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID):
        sample, test = self._context(db, actor, sample_id, sample_test_id,
                                     "sample_test_result.view")
        return [self._response(db, sample, test, result) for result in
                self.results.result_repository.list_for_sample_test(db, test.id)]

    def get(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
            result_id: UUID):
        sample, test, result = self._result(
            db, actor, sample_id, sample_test_id, result_id,
            "sample_test_result.view",
        )
        return self._response(db, sample, test, result)

    def create(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
               values: dict):
        sample, test = self._context(db, actor, sample_id, sample_test_id,
                                     "sample_test_result.create")
        # Correction/reopen authority is deliberately deferred: the API manages one
        # retained result revision until Sprint 21D defines how another is authorized.
        if self.results.result_repository.list_for_sample_test(db, test.id):
            raise ValidationException(
                "A result revision already exists; correction/revision workflow is not available."
            )
        try:
            result = self.results.create_draft_result(
                db, actor.organization_id, test.id, values.get("notes")
            )
            self.audit.record_action(
                db, action=AuditAction.CREATE, entity_type=type(result).__name__,
                entity_id=result.id, actor=actor, owner=sample,
                changes={"created": self._audit_context(sample, test, result)},
            )
            db.commit(); db.refresh(result)
            return self._response(db, sample, test, result)
        except IntegrityError as exc:
            db.rollback()
            raise VersionConflictException("Result revision changed concurrently.") from exc
        except Exception:
            db.rollback(); raise

    def update(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
               result_id: UUID, expected_version: int, values: dict):
        sample, test, result = self._result(
            db, actor, sample_id, sample_test_id, result_id,
            "sample_test_result.update",
        )
        before = self.audit.snapshot(result)
        try:
            result = self.results.update_draft_result(db, result, expected_version, values)
            self.audit.record_update(db, entity=result, actor=actor, before=before, owner=sample)
            db.commit(); db.refresh(result)
            return self._response(db, sample, test, result)
        except Exception:
            db.rollback(); raise

    def add_parameter(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
                      result_id: UUID, values: dict):
        sample, test, result = self._result(db, actor, sample_id, sample_test_id,
                                            result_id, "sample_test_result.update")
        try:
            item = self.results.add_parameter_result(
                db, result.id, values["method_parameter_id"], values["value_type"],
                **values["typed_values"],
            )
            self.audit.record_action(
                db, action=AuditAction.CREATE, entity_type=type(item).__name__,
                entity_id=item.id, actor=actor, owner=sample,
                changes={"created": self._audit_context(
                    sample, test, result, method_parameter_id=item.method_parameter_id
                )},
            )
            db.commit(); db.refresh(item)
            return self._response(db, sample, test, result)
        except IntegrityError as exc:
            db.rollback()
            raise VersionConflictException("Parameter result changed concurrently.") from exc
        except Exception:
            db.rollback(); raise

    def update_parameter(self, db: Session, actor, sample_id: UUID,
                         sample_test_id: UUID, result_id: UUID,
                         parameter_result_id: UUID, values: dict):
        sample, test, result = self._result(db, actor, sample_id, sample_test_id,
                                            result_id, "sample_test_result.update")
        item = self.results.parameter_repository.get(db, parameter_result_id)
        if item is None or item.sample_test_result_id != result.id:
            raise ResourceNotFoundException("ParameterResult not found.")
        before = self.audit.snapshot(item)
        try:
            item = self.results.update_parameter_result(
                db, result, item, values["version"], values["value_type"],
                **values["typed_values"],
            )
            self.audit.record_update(db, entity=item, actor=actor, before=before, owner=sample)
            db.commit()
            return self._response(db, sample, test, result)
        except Exception:
            db.rollback(); raise

    def remove_parameter(self, db: Session, actor, sample_id: UUID,
                         sample_test_id: UUID, result_id: UUID,
                         parameter_result_id: UUID, expected_version: int):
        sample, test, result = self._result(db, actor, sample_id, sample_test_id,
                                            result_id, "sample_test_result.update")
        item = self.results.parameter_repository.get(db, parameter_result_id)
        if item is None or item.sample_test_result_id != result.id:
            raise ResourceNotFoundException("ParameterResult not found.")
        before = self.audit.snapshot(item)
        try:
            self.results.remove_parameter_result(db, result, item, expected_version)
            self.audit.record_delete(db, entity=item, actor=actor, before=before, owner=sample)
            db.commit()
            return self._response(db, sample, test, result)
        except Exception:
            db.rollback(); raise

    def add_instrument(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
                       result_id: UUID, values: dict):
        sample, test, result = self._result(db, actor, sample_id, sample_test_id,
                                            result_id, "sample_test_result.update")
        try:
            usage = self.results.add_instrument_usage(
                db, actor.organization_id, result.id, values["instrument_id"],
                values.get("usage_notes"),
            )
            self.audit.record_action(
                db, action=AuditAction.CREATE, entity_type=type(usage).__name__,
                entity_id=usage.id, actor=actor, owner=sample,
                changes={"created": self._audit_context(
                    sample, test, result, instrument_id=usage.instrument_id
                )},
            )
            db.commit()
            return self._response(db, sample, test, result)
        except IntegrityError as exc:
            db.rollback()
            raise VersionConflictException("Instrument usage changed concurrently.") from exc
        except Exception:
            db.rollback(); raise

    def remove_instrument(self, db: Session, actor, sample_id: UUID,
                          sample_test_id: UUID, result_id: UUID, usage_id: UUID,
                          expected_version: int):
        sample, test, result = self._result(db, actor, sample_id, sample_test_id,
                                            result_id, "sample_test_result.update")
        usage = self.results.instrument_usage_repository.get(db, usage_id)
        if usage is None or usage.sample_test_result_id != result.id:
            raise ResourceNotFoundException("Instrument usage not found.")
        before = self.audit.snapshot(usage)
        try:
            self.results.remove_instrument_usage(db, result, usage, expected_version)
            self.audit.record_delete(db, entity=usage, actor=actor, before=before, owner=sample)
            db.commit()
            return self._response(db, sample, test, result)
        except Exception:
            db.rollback(); raise

    def submit(self, db: Session, actor, sample_id: UUID, sample_test_id: UUID,
               result_id: UUID, expected_version: int):
        sample, test, result = self._result(db, actor, sample_id, sample_test_id,
                                            result_id, "sample_test_result.submit")
        before = self.audit.snapshot(result)
        try:
            result = self.results.submit(
                db, actor.organization_id, result, actor.id, expected_version
            )
            self.audit.record_update(db, entity=result, actor=actor, before=before,
                                     owner=sample, action=AuditAction.SUBMIT)
            db.commit(); db.refresh(result)
            return self._response(db, sample, test, result)
        except Exception:
            db.rollback(); raise


sample_test_result_api_service = SampleTestResultAPIService()
