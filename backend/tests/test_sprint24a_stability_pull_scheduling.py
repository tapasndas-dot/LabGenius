"""Focused PostgreSQL/domain tests for Sprint 24A."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ValidationException, VersionConflictException
from app.models.audit_event import AuditEvent
from app.models.business.instrument import Instrument, StabilityChamberProfile
from app.models.business.instrument_type import InstrumentType
from app.models.business.stability import (
    StabilityProtocolTimepoint,
    StabilityPull,
    StabilityPullStatus,
    StabilityStudy,
)
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.repositories.business.stability_repository import StabilityPullRepository
from app.seeds.permissions import PERMISSION_CATALOG
from app.services.business.stability_scheduling import calculate_pull_date
from app.services.organization_scope_service import OrganizationScopeService
from tests.test_sprint23a_stability_foundation import Sprint23AStabilityTests, scoped_actor


class Sprint24AStabilityPullTests(Sprint23AStabilityTests):
    def _schedule_basis(self, intervals=((True, None, None), (False, 1, "MONTH"))):
        specification = self._basis()[0]
        protocol = self.protocols.create(self.db, self.actor, {
            "protocol_code": f"PULL-{uuid4().hex[:6]}", "protocol_name": "Pull Schedule",
        })
        version = self.versions.create(self.db, self.actor, protocol.id, {"version_number": 1})
        condition = self.conditions.create(self.db, self.actor, version.id, {
            "sequence_number": 1, "condition_code": "C1", "condition_name": "Condition 1",
        })
        timepoints = []
        for sequence, (is_initial, interval_value, interval_unit) in enumerate(intervals, 1):
            timepoints.append(self.timepoints.create(self.db, self.actor, condition.id, {
                "sequence_number": sequence,
                "label": f"T{sequence}",
                "is_initial": is_initial,
                "interval_value": interval_value,
                "interval_unit": interval_unit,
                "specification_version_id": specification.id,
            }))
        version = self.versions.transition(self.db, self.actor, version.id, version.version, "APPROVED")
        instrument_type = InstrumentType(
            organization_id=self.org.id, code=f"CH-{uuid4().hex[:6]}", name="Chamber Type",
        )
        self.db.add(instrument_type); self.db.flush()
        instrument = Instrument(
            organization_id=self.org.id, instrument_type_id=instrument_type.id,
            instrument_code=f"CH-{uuid4().hex[:6]}", instrument_name="Chamber",
        )
        self.db.add(instrument); self.db.flush()
        self.db.add(StabilityChamberProfile(instrument_id=instrument.id)); self.db.flush()
        study = self.studies.create(self.db, self.actor, {
            "study_number": f"ST-{uuid4().hex[:6]}", "study_name": "Pull Study",
            "material_id": self.material.id, "stability_protocol_version_id": version.id,
            "start_date": date(2024, 1, 31),
        })
        study_condition = self.study_conditions.create(self.db, self.actor, study.id, {
            "stability_protocol_condition_id": condition.id, "instrument_id": instrument.id,
        })
        return study, study_condition, timepoints, specification

    def _active_study_with_unassigned_condition(self):
        specification = self._basis()[0]
        protocol = self.protocols.create(self.db, self.actor, {"protocol_code": f"LATE-{uuid4().hex[:6]}", "protocol_name": "Late Condition"})
        version = self.versions.create(self.db, self.actor, protocol.id, {"version_number": 1})
        condition_one = self.conditions.create(self.db, self.actor, version.id, {"sequence_number": 1, "condition_code": "ONE", "condition_name": "One"})
        condition_two = self.conditions.create(self.db, self.actor, version.id, {"sequence_number": 2, "condition_code": "TWO", "condition_name": "Two"})
        self.timepoints.create(self.db, self.actor, condition_one.id, {"sequence_number": 1, "label": "Initial", "is_initial": True, "specification_version_id": specification.id})
        late_timepoints = [
            self.timepoints.create(self.db, self.actor, condition_two.id, {"sequence_number": 1, "label": "Day 1", "interval_value": 1, "interval_unit": "DAY", "specification_version_id": specification.id}),
            self.timepoints.create(self.db, self.actor, condition_two.id, {"sequence_number": 2, "label": "Month 1", "interval_value": 1, "interval_unit": "MONTH", "specification_version_id": specification.id}),
        ]
        version = self.versions.transition(self.db, self.actor, version.id, version.version, "APPROVED")
        instrument_type = InstrumentType(organization_id=self.org.id, code=f"LATE-{uuid4().hex[:6]}", name="Late Chamber")
        self.db.add(instrument_type); self.db.flush()
        instrument = Instrument(organization_id=self.org.id, instrument_type_id=instrument_type.id, instrument_code=f"LATE-{uuid4().hex[:6]}", instrument_name="Late Chamber")
        self.db.add(instrument); self.db.flush(); self.db.add(StabilityChamberProfile(instrument_id=instrument.id)); self.db.flush()
        study = self.studies.create(self.db, self.actor, {"study_number": f"LATE-{uuid4().hex[:6]}", "study_name": "Late", "material_id": self.material.id, "stability_protocol_version_id": version.id, "start_date": date(2024, 1, 31)})
        self.study_conditions.create(self.db, self.actor, study.id, {"stability_protocol_condition_id": condition_one.id, "instrument_id": instrument.id})
        study = self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        return study, condition_one, condition_two, late_timepoints, specification, instrument

    def test_model_contract_permissions_and_constraints(self):
        table = StabilityPull.__table__
        self.assertEqual(set(StabilityPullStatus), {"SCHEDULED", "PULLED", "SAMPLE_CREATED", "CANCELLED"})
        self.assertEqual(
            {column.name for column in table.columns},
            {"id", "stability_study_id", "stability_study_condition_id",
             "stability_protocol_timepoint_id", "specification_version_id", "scheduled_date",
             "status", "qc_sample_id", "pulled_at", "notes", "version", "created_at", "updated_at"},
        )
        constraint_names = {constraint.name for constraint in table.constraints}
        self.assertIn("uq_stability_pulls_condition_timepoint", constraint_names)
        self.assertIn("ck_stability_pulls_status", constraint_names)
        self.assertIn("ck_stability_pulls_version_positive", constraint_names)
        codes = [item["permission_code"] for item in PERMISSION_CATALOG]
        self.assertEqual({code for code in codes if code.startswith("stability_pull.")}, {"stability_pull.view", "stability_pull.execute"})
        self.assertEqual(len(codes), len(set(codes)))

    def test_calendar_date_calculation(self):
        tp = lambda initial=False, value=None, unit=None: SimpleNamespace(
            is_initial=initial, interval_value=value, interval_unit=unit,
        )
        self.assertEqual(calculate_pull_date(date(2024, 1, 31), tp(True)), date(2024, 1, 31))
        self.assertEqual(calculate_pull_date(date(2024, 1, 31), tp(value=2, unit="DAY")), date(2024, 2, 2))
        self.assertEqual(calculate_pull_date(date(2024, 1, 31), tp(value=2, unit="WEEK")), date(2024, 2, 14))
        self.assertEqual(calculate_pull_date(date(2024, 1, 31), tp(value=1, unit="MONTH")), date(2024, 2, 29))
        self.assertEqual(calculate_pull_date(date(2024, 1, 31), tp(value=2, unit="MONTH")), date(2024, 3, 31))
        self.assertEqual(calculate_pull_date(date(2024, 2, 29), tp(value=1, unit="YEAR")), date(2025, 2, 28))

    def test_activation_generates_exact_idempotent_schedule_and_audits(self):
        study, study_condition, timepoints, specification = self._schedule_basis()
        active = self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        pulls = StabilityPullRepository().for_study(self.db, self.org.id, study.id)
        self.assertEqual(active.status, "ACTIVE")
        self.assertEqual(len(pulls), 2)
        self.assertEqual({pull.stability_study_condition_id for pull in pulls}, {study_condition.id})
        self.assertEqual({pull.stability_protocol_timepoint_id for pull in pulls}, {tp.id for tp in timepoints})
        self.assertEqual({pull.specification_version_id for pull in pulls}, {specification.id})
        self.assertEqual({pull.scheduled_date for pull in pulls}, {date(2024, 1, 31), date(2024, 2, 29)})
        self.assertEqual(self.studies.generate_pull_schedule(self.db, self.actor, active), [])
        events = self.db.query(AuditEvent).filter(
            AuditEvent.entity_type == "StabilityPull",
            AuditEvent.entity_id.in_([pull.id for pull in pulls]),
        ).all()
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event.action == "CREATE" and event.organization_id == self.org.id for event in events))

    def test_active_condition_create_generates_exact_idempotent_pulls_and_audits(self):
        study, _, condition_two, timepoints, specification, instrument = self._active_study_with_unassigned_condition()
        before_ids = {pull.id for pull in StabilityPullRepository().for_study(self.db, self.org.id, study.id)}

        assigned = self.study_conditions.create(self.db, self.actor, study.id, {"stability_protocol_condition_id": condition_two.id, "instrument_id": instrument.id})

        pulls = [pull for pull in StabilityPullRepository().for_study(self.db, self.org.id, study.id) if pull.stability_study_condition_id == assigned.id]
        self.assertEqual({pull.stability_protocol_timepoint_id for pull in pulls}, {timepoint.id for timepoint in timepoints})
        self.assertEqual({pull.specification_version_id for pull in pulls}, {specification.id})
        self.assertEqual({pull.scheduled_date for pull in pulls}, {date(2024, 2, 1), date(2024, 2, 29)})
        self.assertTrue(before_ids.isdisjoint({pull.id for pull in pulls}))
        self.assertEqual(self.studies.generate_pull_schedule(self.db, self.actor, study, study_condition_ids={assigned.id}), [])
        events = self.db.query(AuditEvent).filter(AuditEvent.entity_type == "StabilityPull", AuditEvent.entity_id.in_([pull.id for pull in pulls])).all()
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event.action == "CREATE" and event.organization_id == study.organization_id for event in events))

    def test_active_condition_metadata_update_preserves_schedule_and_protocol_change_is_rejected(self):
        study, condition_one, condition_two, _, _, instrument = self._active_study_with_unassigned_condition()
        assigned = self.study_conditions.create(self.db, self.actor, study.id, {"stability_protocol_condition_id": condition_two.id, "instrument_id": instrument.id})
        before = [(pull.id, pull.scheduled_date, pull.specification_version_id) for pull in StabilityPullRepository().for_study_condition(self.db, self.org.id, assigned.id)]

        updated = self.study_conditions.update(self.db, self.actor, assigned.id, assigned.version, {"notes": "Updated while active", "instrument_id": instrument.id})

        self.assertEqual(updated.notes, "Updated while active")
        self.assertEqual([(pull.id, pull.scheduled_date, pull.specification_version_id) for pull in StabilityPullRepository().for_study_condition(self.db, self.org.id, assigned.id)], before)
        with self.assertRaisesRegex(ValidationException, "cannot be changed after Stability Study activation"):
            self.study_conditions.update(self.db, self.actor, assigned.id, updated.version, {"stability_protocol_condition_id": condition_one.id})
        self.assertEqual([(pull.id, pull.scheduled_date, pull.specification_version_id) for pull in StabilityPullRepository().for_study_condition(self.db, self.org.id, assigned.id)], before)

    def test_draft_condition_behavior_and_active_generation_failure_are_transactional(self):
        study, study_condition, _, _ = self._schedule_basis(intervals=((True, None, None),))
        updated = self.study_conditions.update(self.db, self.actor, study_condition.id, study_condition.version, {"notes": "Draft update"})
        self.assertEqual(updated.notes, "Draft update")
        self.assertEqual(StabilityPullRepository().for_study(self.db, self.org.id, study.id), [])

        active, _, condition_two, _, _, instrument = self._active_study_with_unassigned_condition()
        condition_count = self.db.query(type(study_condition)).filter_by(stability_study_id=active.id).count()
        audit_count = self.db.query(AuditEvent).count()
        nested = self.db.begin_nested()
        with patch.object(self.study_conditions.study_service, "generate_pull_schedule", side_effect=ValidationException("schedule failure")):
            with self.assertRaisesRegex(ValidationException, "schedule failure"):
                self.study_conditions.create(self.db, self.actor, active.id, {"stability_protocol_condition_id": condition_two.id, "instrument_id": instrument.id})
        nested.rollback()
        self.assertEqual(self.db.query(type(study_condition)).filter_by(stability_study_id=active.id).count(), condition_count)
        self.assertEqual(self.db.query(AuditEvent).count(), audit_count)

    def test_missing_start_date_and_stale_activation_are_rejected(self):
        specification = self._basis()[0]
        _, version, _ = self.protocol_tree(approve=True, specification=specification)
        study = self.studies.create(self.db, self.actor, {
            "study_number": "NO-DATE", "study_name": "No Date", "material_id": self.material.id,
            "stability_protocol_version_id": version.id,
        })
        with self.assertRaisesRegex(ValidationException, "requires a start date"):
            self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        study.start_date = date(2026, 1, 1); self.db.flush()
        with self.assertRaises(VersionConflictException):
            self.studies.transition(self.db, self.actor, study.id, study.version + 1, "ACTIVE")
        self.assertEqual(study.status, "DRAFT")
        self.assertEqual(self.db.query(StabilityPull).filter_by(stability_study_id=study.id).count(), 0)

    def test_invalid_frozen_condition_chain_fails_before_transition(self):
        study, study_condition, _, _ = self._schedule_basis()
        _, _, unrelated = self.protocol_tree(approve=True)
        study_condition.stability_protocol_condition_id = unrelated.id
        self.db.flush()
        with self.assertRaisesRegex(ValidationException, "frozen Protocol Version"):
            self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        self.db.refresh(study)
        self.assertEqual(study.status, "DRAFT")
        self.assertEqual(self.db.query(StabilityPull).filter_by(stability_study_id=study.id).count(), 0)
        self.assertEqual(self.db.query(AuditEvent).filter(AuditEvent.entity_type == "StabilityPull").count(), 0)

    def test_completion_guard_and_pull_own_concurrency(self):
        study, _, _, _ = self._schedule_basis(intervals=((True, None, None),))
        active = self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        pull = StabilityPullRepository().for_study(self.db, self.org.id, study.id)[0]
        with self.assertRaisesRegex(ValidationException, "scheduled Stability Pulls"):
            self.studies.transition(self.db, self.actor, active.id, active.version, "COMPLETED")
        updated = StabilityPullRepository().update_expected(self.db, pull.id, pull.version, {"status": "PULLED"})
        self.assertEqual(updated.version, 2)
        with self.assertRaises(VersionConflictException):
            if StabilityPullRepository().update_expected(self.db, pull.id, 1, {"status": "CANCELLED"}) is None:
                raise VersionConflictException("stale")
        completed = self.studies.transition(self.db, self.actor, active.id, active.version, "COMPLETED")
        self.assertEqual(completed.status, "COMPLETED")

    def test_database_uniqueness_and_status_constraints(self):
        study, study_condition, timepoints, specification = self._schedule_basis(intervals=((True, None, None),))
        self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        for duplicate in (
            StabilityPull(
                stability_study_id=study.id, stability_study_condition_id=study_condition.id,
                stability_protocol_timepoint_id=timepoints[0].id,
                specification_version_id=specification.id, scheduled_date=study.start_date,
            ),
            StabilityPull(
                stability_study_id=study.id, stability_study_condition_id=study_condition.id,
                stability_protocol_timepoint_id=uuid4(), specification_version_id=specification.id,
                scheduled_date=study.start_date, status="INVALID",
            ),
        ):
            nested = self.db.begin_nested(); self.db.add(duplicate)
            with self.assertRaises(IntegrityError): self.db.flush()
            nested.rollback()

    def test_pull_scope_inherits_parent_study_and_self_is_unsupported(self):
        bu = BusinessUnit(organization_id=self.org.id, business_unit_code="PBU", business_unit_name="Pull BU")
        self.db.add(bu); self.db.flush()
        division = Division(business_unit_id=bu.id, division_code="PDV", division_name="Pull Division")
        self.db.add(division); self.db.flush()
        department = Department(division_id=division.id, department_code="PDP", department_name="Pull Department")
        self.db.add(department); self.db.flush()
        study, _, _, _ = self._schedule_basis(intervals=((True, None, None),))
        study.business_unit_id, study.division_id, study.department_id = bu.id, division.id, department.id
        self.db.flush()
        self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        query = self.db.query(StabilityPull)
        scope = OrganizationScopeService()
        for level, attrs in (
            ("ORGANIZATION", {}), ("BUSINESS_UNIT", {"business_unit_id": bu.id}),
            ("DIVISION", {"division_id": division.id}), ("DEPARTMENT", {"department_id": department.id}),
        ):
            actor = scoped_actor(self.org.id, level, "stability_pull.view")
            for key, value in attrs.items(): setattr(actor, key, value)
            self.assertEqual(scope.filter_stability_pulls(query, actor, "stability_pull.view").count(), 1)
        self_actor = scoped_actor(self.org.id, "SELF", "stability_pull.view")
        self.assertEqual(scope.filter_stability_pulls(query, self_actor, "stability_pull.view").count(), 0)
        cross_actor = scoped_actor(self.other_org.id, "ORGANIZATION", "stability_pull.view")
        self.assertEqual(scope.filter_stability_pulls(query, cross_actor, "stability_pull.view").count(), 0)
