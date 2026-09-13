"""Focused PostgreSQL/domain tests for Sprint 23A."""
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.audit_event import AuditEvent
from app.models.business.instrument import Instrument, StabilityChamberProfile
from app.models.business.instrument_type import InstrumentType
from app.models.business.material import Material
from app.models.business.stability import StabilityProtocol, StabilityProtocolTimepoint, StabilityStudy
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.stability_service import StabilityProtocolConditionService, StabilityProtocolService, StabilityProtocolTimepointService, StabilityProtocolVersionService, StabilityStudyConditionService, StabilityStudyService
from app.services.organization_scope_service import OrganizationScopeService
from tests.test_sprint19a_samples import Sprint19ADatabaseTests


def scoped_actor(organization_id, scope="ORGANIZATION", permission="stability_study.view"):
    mapping = SimpleNamespace(is_active=True, permission=SimpleNamespace(is_active=True, permission_code=permission))
    role = SimpleNamespace(is_active=True, role_permissions=[mapping])
    assignment = SimpleNamespace(is_active=True, role=role, access_scope=scope)
    return SimpleNamespace(id=None, organization_id=organization_id, business_unit_id=None, division_id=None, department_id=None, user_roles=[assignment])


class Sprint23AStabilityTests(Sprint19ADatabaseTests):
    def setUp(self):
        super().setUp()
        self.actor = scoped_actor(self.org.id)
        self.other_actor = scoped_actor(self.other_org.id)
        self.protocols = StabilityProtocolService()
        self.versions = StabilityProtocolVersionService()
        self.conditions = StabilityProtocolConditionService()
        self.timepoints = StabilityProtocolTimepointService()
        self.studies = StabilityStudyService()
        self.study_conditions = StabilityStudyConditionService()

    def protocol_tree(self, *, approve=False, specification=None):
        protocol = self.protocols.create(self.db, self.actor, {"protocol_code": f"P-{uuid4().hex[:6]}", "protocol_name": "Stability"})
        version = self.versions.create(self.db, self.actor, protocol.id, {"version_number": 1})
        condition = self.conditions.create(self.db, self.actor, version.id, {"sequence_number": 1, "condition_code": "CUSTOM", "condition_name": "Custom", "temperature_unit": "custom-unit"})
        if specification:
            self.timepoints.create(self.db, self.actor, condition.id, {"sequence_number": 1, "label": "Initial", "is_initial": True, "specification_version_id": specification.id})
        if approve:
            version = self.versions.transition(self.db, self.actor, version.id, version.version, "APPROVED")
        return protocol, version, condition

    def test_stability_permissions_and_no_parallel_result_model(self):
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual({code for code in codes if code.startswith("stability_protocol.")}, {f"stability_protocol.{action}" for action in ("view", "create", "update", "delete")})
        self.assertEqual({code for code in codes if code.startswith("stability_study.")}, {f"stability_study.{action}" for action in ("view", "create", "update", "cancel")})
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(
            {code for code in codes if code.startswith("stability_pull.")},
            {"stability_pull.view", "stability_pull.execute"},
        )
        self.assertIn("stability_pulls", StabilityProtocol.metadata.tables)
        self.assertNotIn("stability_results", StabilityProtocol.metadata.tables)
        self.assertIn("stability_chamber_profiles", StabilityProtocol.metadata.tables)

    def test_protocol_normalization_uniqueness_isolation_concurrency_and_audit(self):
        protocol = self.protocols.create(self.db, self.actor, {"protocol_code": " p-001 ", "protocol_name": " Protocol "})
        self.assertEqual(protocol.protocol_code, "P-001")
        with self.assertRaises(DuplicateResourceException): self.protocols.create(self.db, self.actor, {"protocol_code": "p-001", "protocol_name": "Duplicate"})
        other = self.protocols.create(self.db, self.other_actor, {"protocol_code": "P-001", "protocol_name": "Other"})
        self.assertNotEqual(protocol.organization_id, other.organization_id)
        with self.assertRaises(ResourceNotFoundException): self.protocols.update(self.db, self.other_actor, protocol.id, protocol.version, {"description": "hidden"})
        updated = self.protocols.update(self.db, self.actor, protocol.id, protocol.version, {"description": "changed"})
        with self.assertRaises(VersionConflictException): self.protocols.update(self.db, self.actor, protocol.id, 1, {"description": "stale"})
        self.assertEqual(updated.version, 2)
        events = self.db.query(AuditEvent).filter(AuditEvent.entity_id == protocol.id).all()
        self.assertEqual({event.action for event in events}, {"CREATE", "UPDATE"})

    def test_protocol_lifecycle_and_approved_structure_is_immutable(self):
        specification = self._basis()[0]
        _, version, condition = self.protocol_tree(specification=specification)
        approved = self.versions.transition(self.db, self.actor, version.id, version.version, "APPROVED")
        with self.assertRaises(ValidationException): self.versions.update(self.db, self.actor, approved.id, approved.version, {"description": "late"})
        with self.assertRaises(ValidationException): self.conditions.update(self.db, self.actor, condition.id, condition.version, {"condition_name": "late"})
        timepoint = self.db.query(StabilityProtocolTimepoint).filter_by(stability_protocol_condition_id=condition.id).one()
        with self.assertRaises(ValidationException): self.timepoints.update(self.db, self.actor, timepoint.id, timepoint.version, {"label": "late"})
        with self.assertRaises(ValidationException): self.conditions.delete(self.db, self.actor, condition.id, condition.version)
        with self.assertRaises(ValidationException): self.timepoints.delete(self.db, self.actor, timepoint.id, timepoint.version)
        self.assertIsNotNone(self.db.get(type(condition), condition.id))
        self.assertIsNotNone(self.db.get(type(timepoint), timepoint.id))
        retired = self.versions.transition(self.db, self.actor, approved.id, approved.version, "RETIRED")
        with self.assertRaises(ValidationException): self.versions.transition(self.db, self.actor, retired.id, retired.version, "APPROVED")
        _, second, _ = self.protocol_tree()
        second = self.versions.transition(self.db, self.actor, second.id, second.version, "APPROVED")
        self.assertEqual(self.versions.transition(self.db, self.actor, second.id, second.version, "SUPERSEDED").status, "SUPERSEDED")

    def test_timepoint_specification_interval_and_single_initial_validation(self):
        approved = self._basis()[0]; draft = self._basis(approved=False)[0]
        _, _, condition = self.protocol_tree()
        for values in ({"sequence_number": 1, "label": "Bad", "interval_value": 0, "interval_unit": "MONTH", "specification_version_id": approved.id}, {"sequence_number": 1, "label": "Bad", "interval_value": 1, "interval_unit": "HOUR", "specification_version_id": approved.id}, {"sequence_number": 1, "label": "Bad", "is_initial": True, "interval_value": 1, "interval_unit": "DAY", "specification_version_id": approved.id}):
            with self.assertRaises(ValidationException): self.timepoints.create(self.db, self.actor, condition.id, values)
        with self.assertRaises(ValidationException): self.timepoints.create(self.db, self.actor, condition.id, {"sequence_number": 1, "label": "Draft", "is_initial": True, "specification_version_id": draft.id})
        other_spec = self._basis(self.other_org, self.other_material)[0]
        with self.assertRaises(ValidationException): self.timepoints.create(self.db, self.actor, condition.id, {"sequence_number": 1, "label": "Cross", "is_initial": True, "specification_version_id": other_spec.id})
        self.timepoints.create(self.db, self.actor, condition.id, {"sequence_number": 1, "label": "Initial", "is_initial": True, "specification_version_id": approved.id})
        with self.assertRaises(DuplicateResourceException): self.timepoints.create(self.db, self.actor, condition.id, {"sequence_number": 2, "label": "Initial 2", "is_initial": True, "specification_version_id": approved.id})

    def test_study_references_hierarchy_activation_and_frozen_basis(self):
        protocol, draft, _ = self.protocol_tree(); values = {"study_number": "ST-1", "study_name": "Study", "material_id": self.material.id, "stability_protocol_version_id": draft.id, "start_date": date(2026, 1, 1)}
        study = self.studies.create(self.db, self.actor, values)
        with self.assertRaises(ValidationException): self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        approved = self.versions.transition(self.db, self.actor, draft.id, draft.version, "APPROVED")
        active = self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        self.assertEqual(active.stability_protocol_version_id, approved.id)
        with self.assertRaises(ValidationException): self.studies.update(self.db, self.actor, active.id, active.version, {"stability_protocol_version_id": uuid4()})
        other_protocol = self.protocols.create(self.db, self.other_actor, {"protocol_code": "OTHER", "protocol_name": "Other"})
        other_version = self.versions.create(self.db, self.other_actor, other_protocol.id, {"version_number": 1})
        with self.assertRaises(ValidationException): self.studies.create(self.db, self.actor, {**values, "study_number": "CROSS", "stability_protocol_version_id": other_version.id})
        with self.assertRaises(ValidationException): self.studies.create(self.db, self.actor, {**values, "study_number": "MAT", "material_id": self.other_material.id})
        other_bu = BusinessUnit(organization_id=self.other_org.id, business_unit_code=f"B{uuid4().hex[:6]}", business_unit_name="Other"); self.db.add(other_bu); self.db.flush()
        with self.assertRaises(ValidationException): self.studies.create(self.db, self.actor, {**values, "study_number": "HIER", "business_unit_id": other_bu.id})

    def test_study_activation_accepts_matching_timepoint_specification_material(self):
        specification_version = self._basis()[0]
        _, protocol_version, _ = self.protocol_tree(approve=True, specification=specification_version)
        study = self.studies.create(self.db, self.actor, {"study_number": "MATCH", "study_name": "Matching Material", "material_id": self.material.id, "stability_protocol_version_id": protocol_version.id, "start_date": date(2026, 1, 1)})

        active = self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")

        self.assertEqual(active.status, "ACTIVE")

    def test_study_activation_rejects_same_organization_timepoint_material_mismatch(self):
        other_material = Material(organization_id=self.org.id, code=f"OTHER-{uuid4().hex[:6]}", name="Other Material", material_type="OTHER")
        self.db.add(other_material); self.db.flush()
        other_specification_version = self._basis(material=other_material)[0]
        _, protocol_version, _ = self.protocol_tree(approve=True, specification=other_specification_version)
        study = self.studies.create(self.db, self.actor, {"study_number": "MISMATCH", "study_name": "Mismatched Material", "material_id": self.material.id, "stability_protocol_version_id": protocol_version.id, "start_date": date(2026, 1, 1)})

        with self.assertRaises(ValidationException):
            self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")

        self.db.refresh(study)
        self.assertEqual(study.status, "DRAFT")

    def test_study_condition_chamber_rules_and_concurrency(self):
        _, version, condition = self.protocol_tree(approve=True)
        study = self.studies.create(self.db, self.actor, {"study_number": "ST-C", "study_name": "Study", "material_id": self.material.id, "stability_protocol_version_id": version.id})
        instrument_type = InstrumentType(organization_id=self.org.id, code=f"I{uuid4().hex[:6]}", name="Chamber"); self.db.add(instrument_type); self.db.flush()
        instrument = Instrument(organization_id=self.org.id, instrument_type_id=instrument_type.id, instrument_code=f"C{uuid4().hex[:6]}", instrument_name="Chamber")
        self.db.add(instrument); self.db.flush()
        with self.assertRaises(ValidationException): self.study_conditions.create(self.db, self.actor, study.id, {"stability_protocol_condition_id": condition.id, "instrument_id": instrument.id})
        self.db.add(StabilityChamberProfile(instrument_id=instrument.id)); self.db.flush()
        assigned = self.study_conditions.create(self.db, self.actor, study.id, {"stability_protocol_condition_id": condition.id, "instrument_id": instrument.id, "assigned_at": datetime.now(timezone.utc)})
        with self.assertRaises(VersionConflictException): self.study_conditions.update(self.db, self.actor, assigned.id, assigned.version + 1, {"notes": "stale"})
        instrument.status = "RETIRED"; self.db.flush()
        with self.assertRaises(ValidationException): self.study_conditions.update(self.db, self.actor, assigned.id, assigned.version, {"notes": "unavailable"})
        instrument.status = "OUT_OF_SERVICE"; self.db.flush()
        _, _, other_condition = self.protocol_tree(approve=True)
        with self.assertRaises(ValidationException): self.study_conditions.create(self.db, self.actor, study.id, {"stability_protocol_condition_id": other_condition.id, "instrument_id": instrument.id})

    def test_study_condition_mutations_follow_parent_study_lifecycle(self):
        protocol = self.protocols.create(self.db, self.actor, {"protocol_code": f"L-{uuid4().hex[:6]}", "protocol_name": "Lifecycle"})
        version = self.versions.create(self.db, self.actor, protocol.id, {"version_number": 1})
        condition_one = self.conditions.create(self.db, self.actor, version.id, {"sequence_number": 1, "condition_code": "ONE", "condition_name": "One"})
        condition_two = self.conditions.create(self.db, self.actor, version.id, {"sequence_number": 2, "condition_code": "TWO", "condition_name": "Two"})
        version = self.versions.transition(self.db, self.actor, version.id, version.version, "APPROVED")
        instrument_type = InstrumentType(organization_id=self.org.id, code=f"L{uuid4().hex[:6]}", name="Lifecycle Chamber")
        self.db.add(instrument_type); self.db.flush()
        instrument = Instrument(organization_id=self.org.id, instrument_type_id=instrument_type.id, instrument_code=f"L{uuid4().hex[:6]}", instrument_name="Lifecycle Chamber")
        self.db.add(instrument); self.db.flush()
        self.db.add(StabilityChamberProfile(instrument_id=instrument.id)); self.db.flush()

        def study(number):
            return self.studies.create(self.db, self.actor, {"study_number": number, "study_name": number, "material_id": self.material.id, "stability_protocol_version_id": version.id, "start_date": date(2026, 1, 1)})

        draft = study("LIFE-DRAFT")
        draft_condition = self.study_conditions.create(self.db, self.actor, draft.id, {"stability_protocol_condition_id": condition_one.id, "instrument_id": instrument.id})
        draft_condition = self.study_conditions.update(self.db, self.actor, draft_condition.id, draft_condition.version, {"notes": "updated in draft"})
        self.study_conditions.delete(self.db, self.actor, draft_condition.id, draft_condition.version)
        self.assertIsNone(self.db.get(type(draft_condition), draft_condition.id))

        active = study("LIFE-ACTIVE")
        active = self.studies.transition(self.db, self.actor, active.id, active.version, "ACTIVE")
        active_condition = self.study_conditions.create(self.db, self.actor, active.id, {"stability_protocol_condition_id": condition_one.id, "instrument_id": instrument.id})
        active_condition = self.study_conditions.update(self.db, self.actor, active_condition.id, active_condition.version, {"notes": "updated while active"})
        with self.assertRaises(ValidationException): self.study_conditions.delete(self.db, self.actor, active_condition.id, active_condition.version)
        self.assertIsNotNone(self.db.get(type(active_condition), active_condition.id))

        completed = self.studies.transition(self.db, self.actor, active.id, active.version, "COMPLETED")
        with self.assertRaises(ValidationException): self.study_conditions.create(self.db, self.actor, completed.id, {"stability_protocol_condition_id": condition_two.id, "instrument_id": instrument.id})
        with self.assertRaises(ValidationException): self.study_conditions.update(self.db, self.actor, active_condition.id, active_condition.version, {"notes": "late"})
        with self.assertRaises(ValidationException): self.study_conditions.delete(self.db, self.actor, active_condition.id, active_condition.version)

        cancelled = study("LIFE-CANCELLED")
        cancelled_condition = self.study_conditions.create(self.db, self.actor, cancelled.id, {"stability_protocol_condition_id": condition_one.id, "instrument_id": instrument.id})
        cancelled = self.studies.transition(self.db, self.actor, cancelled.id, cancelled.version, "CANCELLED")
        with self.assertRaises(ValidationException): self.study_conditions.create(self.db, self.actor, cancelled.id, {"stability_protocol_condition_id": condition_two.id, "instrument_id": instrument.id})
        with self.assertRaises(ValidationException): self.study_conditions.update(self.db, self.actor, cancelled_condition.id, cancelled_condition.version, {"notes": "late"})
        with self.assertRaises(ValidationException): self.study_conditions.delete(self.db, self.actor, cancelled_condition.id, cancelled_condition.version)

    def test_study_self_scope_is_unsupported(self):
        actor = scoped_actor(self.org.id, "SELF")
        query = OrganizationScopeService().filter_stability_studies(self.db.query(StabilityStudy), actor, "stability_study.view")
        self.assertEqual(query.count(), 0)
        with self.assertRaises(HTTPException):
            OrganizationScopeService().resolve_scope(SimpleNamespace(user_roles=[]), "stability_study.view")
