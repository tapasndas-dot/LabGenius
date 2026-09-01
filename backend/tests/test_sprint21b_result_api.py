"""Focused Sprint 21B secured result-entry API and submission tests."""
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.exceptions import (ResourceNotFoundException, ValidationException,
                                 VersionConflictException)
from app.dependencies.database import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.business.instrument import Instrument
from app.models.business.instrument_type import InstrumentType
from app.models.business.qc_method import MethodParameter, MethodVersion
from app.models.business.sample_test_assignment import SampleTestAssignment
from app.models.business.sample_test_result import SampleTestResult
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.designation import Designation
from app.models.organization.division import Division
from app.models.user.user import User
from app.services.business.sample_test_result_api_service import SampleTestResultAPIService
from tests import test_sprint19a_samples as sample_test_support
from tests.test_sprint19b_sample_api import assignment


class Sprint21BResultAPITests(unittest.TestCase):
    _basis = sample_test_support.Sprint19ADatabaseTests._basis

    def setUp(self):
        sample_test_support.Sprint19ADatabaseTests.setUp(self)
        self.api = SampleTestResultAPIService()
        self.user_a = self._user(self.org, "A")
        self.user_b = self._user(self.org, "B")
        specification_version, _, _, _ = self._basis()
        self.sample = self.samples.create(self.db, self.org.id, {
            "sample_number": f"RESULT-{uuid4().hex[:6]}",
            "material_id": self.material.id,
            "specification_version_id": specification_version.id,
        })
        self.sample_test = self.sample_tests.generate(
            self.db, self.org.id, self.sample.id
        )[0]
        self.sample.business_unit_id = self.user_a.business_unit_id
        self.sample.division_id = self.user_a.division_id
        self.sample.department_id = self.user_a.department_id
        self.sample_test.status = "ASSIGNED"
        self.method_version = self.db.get(MethodVersion, self.sample_test.method_version_id)
        self.parameters = {}
        for sequence, value_type in enumerate(
            ("TEXT", "NUMBER", "INTEGER", "BOOLEAN", "DATE", "DATETIME"), 1
        ):
            parameter = MethodParameter(
                method_version_id=self.method_version.id,
                parameter_code=f"{value_type}-{uuid4().hex[:6]}",
                parameter_name=value_type, value_type=value_type,
                sequence_number=sequence, is_required=True,
            )
            self.db.add(parameter); self.parameters[value_type] = parameter
        instrument_type = InstrumentType(
            organization_id=self.org.id, code=f"TYPE-{uuid4().hex[:6]}", name="Analyzer"
        )
        other_type = InstrumentType(
            organization_id=self.other_org.id, code=f"OTYPE-{uuid4().hex[:6]}", name="Other"
        )
        self.db.add_all([instrument_type, other_type]); self.db.flush()
        self.instruments = [Instrument(
            organization_id=self.org.id, instrument_type_id=instrument_type.id,
            instrument_code=f"I-{index}-{uuid4().hex[:5]}", instrument_name=f"Analyzer {index}",
            model_number=f"M{index}", serial_number=f"S{index}",
        ) for index in (1, 2)]
        self.other_instrument = Instrument(
            organization_id=self.other_org.id, instrument_type_id=other_type.id,
            instrument_code=f"X-{uuid4().hex[:5]}", instrument_name="Other",
        )
        self.db.add_all([*self.instruments, self.other_instrument]); self.db.flush()

    def _user(self, organization, marker):
        suffix = uuid4().hex[:8]
        business_unit = BusinessUnit(
            organization_id=organization.id, business_unit_code=f"B{marker}{suffix}",
            business_unit_name="Laboratory",
        )
        self.db.add(business_unit); self.db.flush()
        division = Division(
            business_unit_id=business_unit.id, division_code=f"D{marker}{suffix}",
            division_name="Quality",
        )
        self.db.add(division); self.db.flush()
        department = Department(
            division_id=division.id, department_code=f"P{marker}{suffix}",
            department_name="QC",
        )
        self.db.add(department); self.db.flush()
        designation = Designation(
            department_id=department.id, designation_code=f"G{marker}{suffix}",
            designation_name="Scientist",
        )
        self.db.add(designation); self.db.flush()
        user = User(
            organization_id=organization.id, business_unit_id=business_unit.id,
            division_id=division.id, department_id=department.id,
            designation_id=designation.id, employee_code=f"E{marker}{suffix}",
            first_name="Test", last_name=marker, display_name=f"Test {marker}",
            email=f"{marker.lower()}{suffix}@example.invalid",
            username=f"{marker.lower()}{suffix}", password_hash="not-a-real-password-hash",
            account_status="ACTIVE", is_active=True,
        )
        self.db.add(user); self.db.flush()
        return user

    def tearDown(self):
        app.dependency_overrides.clear()
        sample_test_support.Sprint19ADatabaseTests.tearDown(self)

    def actor(self, permission, scope="ORGANIZATION", user=None, extras=()):
        user = user or self.user_a
        roles = [assignment(permission, scope)]
        roles.extend(assignment(code, extra_scope) for code, extra_scope in extras)
        return SimpleNamespace(
            id=user.id, organization_id=user.organization_id,
            business_unit_id=user.business_unit_id, division_id=user.division_id,
            department_id=user.department_id, force_password_change=False,
            user_roles=roles,
        )

    def create(self, actor=None):
        return self.api.create(
            self.db, actor or self.actor("sample_test_result.create"),
            self.sample.id, self.sample_test.id, {"notes": "Draft"},
        )

    @staticmethod
    def typed_values():
        return {
            "TEXT": {"text_value": "observed"},
            "NUMBER": {"numeric_value": Decimal("12.50")},
            "INTEGER": {"integer_value": 7},
            "BOOLEAN": {"boolean_value": True},
            "DATE": {"date_value": date(2026, 9, 1)},
            "DATETIME": {"datetime_value": datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)},
        }

    def add_all_parameters(self, result_id, actor=None):
        actor = actor or self.actor("sample_test_result.update")
        for value_type, typed in self.typed_values().items():
            self.api.add_parameter(self.db, actor, self.sample.id, self.sample_test.id,
                                   result_id, {"method_parameter_id": self.parameters[value_type].id,
                                               "value_type": value_type, "typed_values": typed})

    def test_nested_routes_contract_permissions_and_wrong_chain(self):
        actor = self.actor("sample_test_result.create")
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: actor
        client = TestClient(app)
        base = f"/samples/{self.sample.id}/tests/{self.sample_test.id}/results"
        created = client.post(base, json={"notes": "HTTP"})
        self.assertEqual(created.status_code, 201, created.text)
        result_id = created.json()["id"]
        self.assertEqual(created.json()["sequence_number"], 1)
        actor.user_roles = [assignment("sample_test_result.view", "ORGANIZATION")]
        self.assertEqual(client.get(base).status_code, 200)
        self.assertEqual(client.get(f"{base}/{result_id}").status_code, 200)
        self.assertEqual(client.put(f"{base}/{result_id}", json={
            "version": 1, "notes": "denied"
        }).status_code, 403)
        actor.user_roles = [assignment("sample_test_result.update", "ORGANIZATION")]
        updated = client.put(f"{base}/{result_id}", json={"version": 1, "notes": "updated"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["version"], 2)
        parameter = client.post(f"{base}/{result_id}/parameters", json={
            "method_parameter_id": str(self.parameters["TEXT"].id),
            "value_type": "TEXT", "text_value": "HTTP value",
        })
        self.assertEqual(parameter.status_code, 201, parameter.text)
        parameter_item = parameter.json()["parameters"][0]
        parameter = client.put(
            f"{base}/{result_id}/parameters/{parameter_item['id']}", json={
                "version": parameter_item["version"], "value_type": "TEXT",
                "text_value": "HTTP updated",
            },
        )
        self.assertEqual(parameter.status_code, 200, parameter.text)
        parameter_item = parameter.json()["parameters"][0]
        self.assertEqual(client.request(
            "DELETE", f"{base}/{result_id}/parameters/{parameter_item['id']}",
            json={"version": parameter_item["version"]},
        ).status_code, 200)
        instrument = client.post(f"{base}/{result_id}/instruments", json={
            "instrument_id": str(self.instruments[0].id), "usage_notes": "HTTP",
        })
        self.assertEqual(instrument.status_code, 201, instrument.text)
        usage = instrument.json()["instrument_usages"][0]
        self.assertEqual(client.request(
            "DELETE", f"{base}/{result_id}/instruments/{usage['id']}",
            json={"version": usage["version"]},
        ).status_code, 200)
        self.assertEqual(client.get(
            f"/samples/{uuid4()}/tests/{self.sample_test.id}/results/{result_id}"
        ).status_code, 403)  # read permission is intentionally absent
        actor.user_roles = [assignment("sample_test_result.view", "ORGANIZATION")]
        self.assertEqual(client.get(
            f"/samples/{uuid4()}/tests/{self.sample_test.id}/results/{result_id}"
        ).status_code, 404)
        self.assertEqual(client.get(
            f"/samples/{self.sample.id}/tests/{uuid4()}/results/{result_id}"
        ).status_code, 404)
        self.assertEqual(client.get(f"{base}/{uuid4()}").status_code, 404)
        actor.user_roles = [assignment("sample_test_result.review", "ORGANIZATION")]
        self.assertEqual(client.get(base).status_code, 403)
        self.assertEqual(client.post(base, json={}).status_code, 403)
        actor.user_roles = [assignment("sample_test_result.submit", "ORGANIZATION")]
        self.assertEqual(client.post(
            f"{base}/{result_id}/submit", json={"version": 2}
        ).status_code, 400)

    def test_typed_parameter_crud_frozen_basis_duplicates_and_concurrency(self):
        result = self.create(); result_id = result["id"]
        editor = self.actor("sample_test_result.update")
        for value_type, typed in self.typed_values().items():
            response = self.api.add_parameter(
                self.db, editor, self.sample.id, self.sample_test.id, result_id,
                {"method_parameter_id": self.parameters[value_type].id,
                 "value_type": value_type, "typed_values": typed},
            )
            self.assertEqual(response["parameters"][-1]["value_type"], value_type)
        item = self.api.results.parameter_repository.get_for_result_and_parameter(
            self.db, result_id, self.parameters["TEXT"].id
        )
        updated = self.api.update_parameter(
            self.db, editor, self.sample.id, self.sample_test.id, result_id, item.id,
            {"version": item.version, "value_type": "TEXT",
             "typed_values": {"text_value": "changed"}},
        )
        current = next(row for row in updated["parameters"] if row["id"] == item.id)
        self.assertEqual((current["text_value"], current["version"]), ("changed", 2))
        removed = self.api.remove_parameter(
            self.db, editor, self.sample.id, self.sample_test.id, result_id,
            item.id, current["version"],
        )
        self.assertNotIn(item.id, {row["id"] for row in removed["parameters"]})
        with self.assertRaises(ValidationException):
            self.api.add_parameter(
                self.db, editor, self.sample.id, self.sample_test.id, result_id,
                {"method_parameter_id": self.parameters["NUMBER"].id,
                 "value_type": "NUMBER", "typed_values": {"numeric_value": Decimal("1")}},
            )

    def test_wrong_frozen_parameter_is_rejected(self):
        result = self.create(); editor = self.actor("sample_test_result.update")
        other_version = MethodVersion(
            method_id=self.method_version.method_id, version_number=99, status="DRAFT"
        )
        self.db.add(other_version); self.db.flush()
        foreign_parameter = MethodParameter(
            method_version_id=other_version.id, parameter_code="LATER",
            parameter_name="Later", value_type="TEXT",
        )
        self.db.add(foreign_parameter); self.db.flush()
        with self.assertRaises(ValidationException):
            self.api.add_parameter(
                self.db, editor, self.sample.id, self.sample_test.id, result["id"],
                {"method_parameter_id": foreign_parameter.id, "value_type": "TEXT",
                 "typed_values": {"text_value": "wrong version"}},
            )

    def test_stale_parameter_update_returns_conflict(self):
        result = self.create(); editor = self.actor("sample_test_result.update")
        self.api.add_parameter(
            self.db, editor, self.sample.id, self.sample_test.id, result["id"],
            {"method_parameter_id": self.parameters["TEXT"].id, "value_type": "TEXT",
             "typed_values": {"text_value": "value"}},
        )
        item = self.api.results.parameter_repository.get_for_result_and_parameter(
            self.db, result["id"], self.parameters["TEXT"].id
        )
        with self.assertRaises(VersionConflictException):
            self.api.update_parameter(
                self.db, editor, self.sample.id, self.sample_test.id, result["id"], item.id,
                {"version": item.version + 1, "value_type": "TEXT",
                 "typed_values": {"text_value": "stale"}},
            )

    def test_submission_readiness_entered_metadata_and_immutability(self):
        result = self.create(); result_id = result["id"]
        submitter = self.actor("sample_test_result.submit")
        self.add_all_parameters(result_id)
        current = self.api.results.result_repository.get(self.db, result_id)
        entered = self.api.submit(self.db, submitter, self.sample.id, self.sample_test.id,
                                  result_id, current.version)
        self.assertEqual(entered["status"], "ENTERED")
        self.assertEqual(entered["entered_by"]["id"], self.user_a.id)
        self.assertIsNotNone(entered["entered_at"])
        self.assertEqual(self.sample_test.status, "ASSIGNED")
        result_actions = {row.action for row in self.db.query(AuditEvent).filter(
            AuditEvent.entity_id == result_id
        )}
        self.assertIn("SUBMIT", result_actions)
        self.assertTrue(self.db.query(AuditEvent).filter(
            AuditEvent.entity_type == "ParameterResult", AuditEvent.action == "CREATE"
        ).count())
        editor = self.actor("sample_test_result.update")
        with self.assertRaises(ValidationException):
            self.api.update(self.db, editor, self.sample.id, self.sample_test.id,
                            result_id, entered["version"], {"notes": "late"})

    def test_incomplete_submission_is_rejected(self):
        result = self.create()
        with self.assertRaises(ValidationException):
            self.api.submit(
                self.db, self.actor("sample_test_result.submit"), self.sample.id,
                self.sample_test.id, result["id"], result["version"],
            )

    def test_entered_child_mutation_and_repeat_submit_are_rejected(self):
        result = self.create(); self.add_all_parameters(result["id"])
        current = self.api.results.result_repository.get(self.db, result["id"])
        entered = self.api.submit(
            self.db, self.actor("sample_test_result.submit"), self.sample.id,
            self.sample_test.id, result["id"], current.version,
        )
        with self.assertRaises(ValidationException):
            self.api.add_instrument(
                self.db, self.actor("sample_test_result.update"), self.sample.id,
                self.sample_test.id, result["id"], {"instrument_id": self.instruments[0].id},
            )

    def test_repeat_submit_is_rejected(self):
        result = self.create(); self.add_all_parameters(result["id"])
        current = self.api.results.result_repository.get(self.db, result["id"])
        entered = self.api.submit(
            self.db, self.actor("sample_test_result.submit"), self.sample.id,
            self.sample_test.id, result["id"], current.version,
        )
        with self.assertRaises(ValidationException):
            self.api.submit(
                self.db, self.actor("sample_test_result.submit"), self.sample.id,
                self.sample_test.id, result["id"], entered["version"],
            )

    def test_entered_parameter_mutation_is_rejected(self):
        result = self.create(); self.add_all_parameters(result["id"])
        item = self.api.results.parameter_repository.get_for_result_and_parameter(
            self.db, result["id"], self.parameters["TEXT"].id
        )
        current = self.api.results.result_repository.get(self.db, result["id"])
        self.api.submit(
            self.db, self.actor("sample_test_result.submit"), self.sample.id,
            self.sample_test.id, result["id"], current.version,
        )
        with self.assertRaises(ValidationException):
            self.api.update_parameter(
                self.db, self.actor("sample_test_result.update"), self.sample.id,
                self.sample_test.id, result["id"], item.id,
                {"version": item.version, "value_type": "TEXT",
                 "typed_values": {"text_value": "late"}},
            )

    def test_instruments_context_duplicates_cross_org_remove_and_stale(self):
        result = self.create(); editor = self.actor("sample_test_result.update")
        for instrument in self.instruments:
            response = self.api.add_instrument(
                self.db, editor, self.sample.id, self.sample_test.id, result["id"],
                {"instrument_id": instrument.id, "usage_notes": "used"},
            )
        self.assertEqual(len(response["instrument_usages"]), 2)
        self.assertEqual(set(response["instrument_usages"][0]["instrument"]),
                         {"id", "code", "name", "model_number", "serial_number"})
        usage = self.api.results.instrument_usage_repository.get_for_result_and_instrument(
            self.db, result["id"], self.instruments[0].id
        )
        response = self.api.remove_instrument(
            self.db, editor, self.sample.id, self.sample_test.id, result["id"],
            usage.id, usage.version,
        )
        self.assertEqual(len(response["instrument_usages"]), 1)
        instrument_actions = {row.action for row in self.db.query(AuditEvent).filter(
            AuditEvent.entity_type == "ResultInstrumentUsage"
        )}
        self.assertEqual(instrument_actions, {"CREATE", "DELETE"})

    def test_cross_org_instrument_is_rejected(self):
        result = self.create()
        with self.assertRaises(ValidationException):
            self.api.add_instrument(
                self.db, self.actor("sample_test_result.update"), self.sample.id,
                self.sample_test.id, result["id"],
                {"instrument_id": self.other_instrument.id},
            )

    def test_stale_instrument_mutation_is_rejected(self):
        result = self.create(); editor = self.actor("sample_test_result.update")
        self.api.add_instrument(
            self.db, editor, self.sample.id, self.sample_test.id, result["id"],
            {"instrument_id": self.instruments[0].id},
        )
        usage = self.api.results.instrument_usage_repository.get_for_result_and_instrument(
            self.db, result["id"], self.instruments[0].id
        )
        with self.assertRaises(VersionConflictException):
            self.api.remove_instrument(
                self.db, editor, self.sample.id, self.sample_test.id, result["id"],
                usage.id, usage.version + 1,
            )

    def test_duplicate_instrument_is_rejected(self):
        result = self.create(); editor = self.actor("sample_test_result.update")
        self.api.add_instrument(
            self.db, editor, self.sample.id, self.sample_test.id, result["id"],
            {"instrument_id": self.instruments[0].id},
        )
        with self.assertRaises(ValidationException):
            self.api.add_instrument(
                self.db, editor, self.sample.id, self.sample_test.id, result["id"],
                {"instrument_id": self.instruments[0].id},
            )

    def test_permission_specific_hierarchy_and_assignment_self_semantics(self):
        result = self.create()
        for scope in ("ORGANIZATION", "BUSINESS_UNIT", "DIVISION", "DEPARTMENT"):
            self.assertEqual(len(self.api.list(
                self.db, self.actor("sample_test_result.view", scope),
                self.sample.id, self.sample_test.id,
            )), 1)
        outside = self.actor(
            "sample_test_result.view", "DEPARTMENT", user=self.user_b,
            extras=(("sample.view", "ORGANIZATION"),),
        )
        with self.assertRaises(ResourceNotFoundException):
            self.api.get(self.db, outside, self.sample.id, self.sample_test.id, result["id"])
        self.db.add(SampleTestAssignment(
            sample_test_id=self.sample_test.id, assigned_user_id=self.user_a.id,
            assigned_at=datetime.now(timezone.utc), is_active=True,
        )); self.db.commit()
        self_actor = self.actor("sample_test_result.view", "SELF")
        self.assertEqual(self.api.get(
            self.db, self_actor, self.sample.id, self.sample_test.id, result["id"]
        )["id"], result["id"])
        active = self.db.query(SampleTestAssignment).filter_by(
            sample_test_id=self.sample_test.id, is_active=True
        ).one()
        active.is_active = False; self.db.commit()
        with self.assertRaises(ResourceNotFoundException):
            self.api.get(self.db, self_actor, self.sample.id, self.sample_test.id, result["id"])
        # Creator/entered-by identity and unrelated broad permissions do not define SELF.
        self.db.query(SampleTestResult).filter_by(id=result["id"]).update({
            "entered_by_user_id": self.user_a.id
        }); self.db.commit()
        self_actor.user_roles.append(assignment("sample.view", "ORGANIZATION"))
        with self.assertRaises(ResourceNotFoundException):
            self.api.get(self.db, self_actor, self.sample.id, self.sample_test.id, result["id"])

    def test_concurrency_audit_rollback_revision_rule_and_history_retention(self):
        actor = self.actor("sample_test_result.create")
        result = self.create(actor)
        with self.assertRaises(ValidationException):
            self.create(actor)
        self.assertEqual(self.db.query(SampleTestResult).filter_by(
            sample_test_id=self.sample_test.id
        ).count(), 1)
        actions = {row.action for row in self.db.query(AuditEvent).filter(
            AuditEvent.entity_id == result["id"]
        )}
        self.assertIn("CREATE", actions)
        failing = SampleTestResultAPIService(); failing.audit = Mock()
        failing.audit.record_action.side_effect = RuntimeError("forced audit failure")
        other_specification, _, _, _ = self._basis()
        other_sample = self.samples.create(self.db, self.org.id, {
            "sample_number": f"ROLLBACK-{uuid4().hex[:6]}",
            "material_id": self.material.id,
            "specification_version_id": other_specification.id,
        })
        other_test = self.sample_tests.generate(self.db, self.org.id, other_sample.id)[0]
        other_test_id = other_test.id
        with self.assertRaises(RuntimeError):
            failing.create(self.db, actor, other_sample.id, other_test.id, {})
        self.assertEqual(self.db.query(SampleTestResult).filter_by(
            sample_test_id=other_test_id
        ).count(), 0)

    def test_stale_result_update_returns_conflict(self):
        result = self.create()
        with self.assertRaises(VersionConflictException):
            self.api.update(
                self.db, self.actor("sample_test_result.update"),
                self.sample.id, self.sample_test.id, result["id"],
                result["version"] + 1, {"notes": "stale"},
            )


if __name__ == "__main__":
    unittest.main()
