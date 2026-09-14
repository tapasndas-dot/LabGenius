"""Focused PostgreSQL/service tests for Sprint 24B."""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException, ValidationException, VersionConflictException
from app.models.audit_event import AuditEvent
from app.models.business.sample import Sample, SampleTest
from app.models.business.stability import StabilityPull
from app.models.organization.business_unit import BusinessUnit
from app.models.organization.department import Department
from app.models.organization.division import Division
from app.schemas.business.stability import StabilityPullMarkPulledRequest
from app.services.business.stability_api_service import StabilityPullAPIService
from tests.test_sprint24a_stability_pull_scheduling import Sprint24AStabilityPullTests


def actor_with_permissions(organization_id, *permissions, scope="ORGANIZATION"):
    mappings = [SimpleNamespace(
        is_active=True,
        permission=SimpleNamespace(is_active=True, permission_code=permission),
    ) for permission in permissions]
    role = SimpleNamespace(is_active=True, role_permissions=mappings)
    assignment = SimpleNamespace(is_active=True, role=role, access_scope=scope)
    return SimpleNamespace(
        id=None, organization_id=organization_id, business_unit_id=None,
        division_id=None, department_id=None, user_roles=[assignment],
    )


def actor_with_permission_scopes(organization_id, **permission_scopes):
    assignments = []
    for permission, scope in permission_scopes.items():
        mapping = SimpleNamespace(
            is_active=True,
            permission=SimpleNamespace(is_active=True, permission_code=permission),
        )
        assignments.append(SimpleNamespace(
            is_active=True,
            role=SimpleNamespace(is_active=True, role_permissions=[mapping]),
            access_scope=scope,
        ))
    return SimpleNamespace(
        id=None, organization_id=organization_id, business_unit_id=None,
        division_id=None, department_id=None, user_roles=assignments,
    )


class Sprint24BStabilityPullAPITests(Sprint24AStabilityPullTests):
    def setUp(self):
        super().setUp()
        self.pulls_api = StabilityPullAPIService()

    def _active_pull(self):
        study, study_condition, timepoints, specification = self._schedule_basis(
            intervals=((True, None, None), (False, 1, "MONTH"))
        )
        study = self.studies.transition(self.db, self.actor, study.id, study.version, "ACTIVE")
        pull = self.db.query(StabilityPull).filter_by(
            stability_study_id=study.id,
            stability_protocol_timepoint_id=timepoints[0].id,
        ).one()
        return study, study_condition, pull, specification

    def _hierarchy(self):
        suffix = uuid4().hex[:6]
        business_unit = BusinessUnit(
            organization_id=self.org.id, business_unit_code=f"BU-{suffix}",
            business_unit_name="Stability BU",
        )
        self.db.add(business_unit); self.db.flush()
        division = Division(
            business_unit_id=business_unit.id, division_code=f"DV-{suffix}",
            division_name="Stability Division",
        )
        self.db.add(division); self.db.flush()
        department = Department(
            division_id=division.id, department_code=f"DP-{suffix}",
            department_name="Stability Department",
        )
        self.db.add(department); self.db.flush()
        return business_unit, division, department

    def test_request_rejects_naive_pulled_at(self):
        with self.assertRaises(ValueError):
            StabilityPullMarkPulledRequest(version=1, pulled_at=datetime(2026, 1, 1))

    def test_list_get_filters_context_scope_and_parent_chain(self):
        study, study_condition, pull, _ = self._active_pull()
        actor = actor_with_permissions(self.org.id, "stability_pull.view")
        records = self.pulls_api.list(
            self.db, actor, study.id, "stability_pull.view", status="SCHEDULED",
            study_condition_id=study_condition.id, scheduled_from=date(2024, 1, 1),
            scheduled_to=date(2024, 1, 31),
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["protocol_condition"]["code"], "C1")
        self.assertEqual(records[0]["timepoint"]["label"], "T1")
        self.assertEqual(records[0]["assigned_instrument"]["name"], "Chamber")
        self.assertEqual(self.pulls_api.get(
            self.db, actor, study.id, pull.id, "stability_pull.view"
        )["id"], pull.id)
        other_study, _, _, _ = self._active_pull()
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.get(self.db, actor, other_study.id, pull.id, "stability_pull.view")
        self_actor = actor_with_permissions(self.org.id, "stability_pull.view", scope="SELF")
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.get(self.db, self_actor, study.id, pull.id, "stability_pull.view")

        cross_actor = actor_with_permissions(self.other_org.id, "stability_pull.view")
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.get(self.db, cross_actor, study.id, pull.id, "stability_pull.view")

    def test_pull_read_department_scope_isolation(self):
        business_unit, division, department = self._hierarchy()
        study, _, pull, _ = self._active_pull()
        study.business_unit_id = business_unit.id
        study.division_id = division.id
        study.department_id = department.id
        self.db.flush()
        actor = actor_with_permissions(self.org.id, "stability_pull.view", scope="DEPARTMENT")
        actor.department_id = department.id
        self.assertEqual(self.pulls_api.get(
            self.db, actor, study.id, pull.id, "stability_pull.view"
        )["id"], pull.id)
        actor.department_id = uuid4()
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.get(self.db, actor, study.id, pull.id, "stability_pull.view")

    def test_mark_pulled_and_cancel_lifecycle_audit_and_concurrency(self):
        study, _, pull, _ = self._active_pull()
        actor = actor_with_permissions(self.org.id, "stability_pull.execute")
        pulled_at = datetime(2026, 2, 3, 4, 5, tzinfo=timezone.utc)
        result = self.pulls_api.mark_pulled(
            self.db, actor, study.id, pull.id, pull.version, pulled_at, " pulled ",
            notes_supplied=True,
        )
        self.assertEqual((result["status"], result["pulled_at"], result["notes"], result["version"]),
                         ("PULLED", pulled_at, "pulled", 2))
        event = self.db.query(AuditEvent).filter_by(
            entity_type="StabilityPull", entity_id=pull.id, action="UPDATE"
        ).order_by(AuditEvent.occurred_at.desc()).first()
        self.assertEqual(event.organization_id, study.organization_id)
        self.assertEqual((event.business_unit_id, event.division_id, event.department_id),
                         (study.business_unit_id, study.division_id, study.department_id))
        with self.assertRaises(VersionConflictException):
            self.pulls_api.mark_pulled(
                self.db, actor, study.id, pull.id, 1, pulled_at, None,
                notes_supplied=False,
            )
        with self.assertRaises(ValidationException):
            self.pulls_api.mark_pulled(
                self.db, actor, study.id, pull.id, 2, pulled_at, None,
                notes_supplied=False,
            )
        inaccessible = actor_with_permissions(self.other_org.id, "stability_pull.execute")
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.mark_pulled(
                self.db, inaccessible, study.id, pull.id, 2, pulled_at, None,
                notes_supplied=False,
            )
        with self.assertRaises(VersionConflictException):
            self.pulls_api.cancel(self.db, actor, study.id, pull.id, 1)
        with self.assertRaises(ValidationException):
            self.pulls_api.cancel(self.db, actor, study.id, pull.id, 2)

        other_study, _, scheduled, _ = self._active_pull()
        cancelled = self.pulls_api.cancel(
            self.db, actor, other_study.id, scheduled.id, scheduled.version
        )
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertIsNotNone(self.db.query(AuditEvent).filter_by(
            entity_type="StabilityPull", entity_id=scheduled.id, action="CANCEL"
        ).first())
        with self.assertRaises(ValidationException):
            self.pulls_api.cancel(self.db, actor, other_study.id, scheduled.id, 2)
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.cancel(self.db, inaccessible, other_study.id, scheduled.id, 2)

    def test_mark_pulled_rejects_non_active_study(self):
        study, _, pull, _ = self._active_pull()
        study.status = "DRAFT"
        self.db.flush()
        actor = actor_with_permissions(self.org.id, "stability_pull.execute")
        with self.assertRaises(ValidationException):
            self.pulls_api.mark_pulled(
                self.db, actor, study.id, pull.id, pull.version,
                datetime(2026, 2, 3, tzinfo=timezone.utc), None,
                notes_supplied=False,
            )

    def test_create_sample_is_atomic_and_uses_frozen_mapping(self):
        business_unit, division, department = self._hierarchy()
        study, _, pull, specification = self._active_pull()
        study.business_unit_id, study.division_id, study.department_id = (
            business_unit.id, division.id, department.id
        )
        self.db.flush()
        actor = actor_with_permissions(
            self.org.id, "stability_pull.execute", "sample.create"
        )
        pulled_at = datetime(2026, 3, 4, 5, 6, tzinfo=timezone.utc)
        pulled = self.pulls_api.mark_pulled(
            self.db, actor, study.id, pull.id, pull.version, pulled_at, None,
            notes_supplied=False,
        )
        created = self.pulls_api.create_sample(
            self.db, actor, study.id, pull.id, pulled["version"], " qc-24b "
        )
        sample = self.db.get(Sample, created["qc_sample_id"])
        self.assertEqual(created["status"], "SAMPLE_CREATED")
        self.assertEqual(created["version"], 3)
        self.assertEqual((sample.organization_id, sample.business_unit_id, sample.division_id,
                          sample.department_id, sample.sample_number, sample.material_id,
                          sample.specification_version_id, sample.sampled_at, sample.status,
                          sample.priority, sample.due_at),
                         (self.org.id, business_unit.id, division.id, department.id, "QC-24B",
                          study.material_id, pull.specification_version_id, pulled_at,
                          "REGISTERED", "NORMAL", None))
        self.assertEqual(sample.specification_version_id, specification.id)
        self.assertEqual(created["qc_sample_id"], sample.id)
        generated = self.db.query(SampleTest).filter_by(sample_id=sample.id).all()
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0].specification_test.specification_version_id, specification.id)
        self.assertEqual(self.db.query(AuditEvent).filter_by(
            entity_type="SampleTest", entity_id=generated[0].id, action="CREATE"
        ).count(), 1)
        sample_audit = self.db.query(AuditEvent).filter_by(
            entity_type="Sample", entity_id=sample.id, action="CREATE"
        ).one()
        test_audit = self.db.query(AuditEvent).filter_by(
            entity_type="SampleTest", entity_id=generated[0].id, action="CREATE"
        ).one()
        pull_audit = self.db.query(AuditEvent).filter_by(
            entity_type="StabilityPull", entity_id=pull.id, action="UPDATE"
        ).order_by(AuditEvent.occurred_at.desc()).first()
        expected_owner = (business_unit.id, division.id, department.id)
        self.assertEqual((sample_audit.business_unit_id, sample_audit.division_id,
                          sample_audit.department_id), expected_owner)
        self.assertEqual((test_audit.business_unit_id, test_audit.division_id,
                          test_audit.department_id), expected_owner)
        self.assertEqual((pull_audit.business_unit_id, pull_audit.division_id,
                          pull_audit.department_id), expected_owner)
        with self.assertRaises(VersionConflictException):
            self.pulls_api.create_sample(self.db, actor, study.id, pull.id, 2, "SECOND")
        with self.assertRaises(ValidationException):
            self.pulls_api.create_sample(self.db, actor, study.id, pull.id, 3, "SECOND")
        self.assertEqual(self.db.query(Sample).filter_by(organization_id=self.org.id).count(), 1)
        self.assertEqual(self.db.query(StabilityPull).filter_by(
            id=pull.id, qc_sample_id=sample.id, status="SAMPLE_CREATED"
        ).count(), 1)

    def test_create_sample_permission_placement_and_failure_rollback(self):
        study, _, pull, _ = self._active_pull()
        execute_only = actor_with_permissions(self.org.id, "stability_pull.execute")
        pulled_at = datetime(2026, 4, 5, tzinfo=timezone.utc)
        pulled = self.pulls_api.mark_pulled(
            self.db, execute_only, study.id, pull.id, pull.version, pulled_at, None,
            notes_supplied=False,
        )
        with self.assertRaises(HTTPException):
            self.pulls_api.create_sample(
                self.db, execute_only, study.id, pull.id, pulled["version"], "NO-PERM"
            )
        inaccessible = actor_with_permissions(self.other_org.id, "stability_pull.execute")
        with self.assertRaises(ResourceNotFoundException):
            self.pulls_api.create_sample(
                self.db, inaccessible, study.id, pull.id, pulled["version"], "HIDDEN"
            )

        sample_only = actor_with_permissions(self.org.id, "sample.create")
        with self.assertRaises(HTTPException):
            self.pulls_api.create_sample(
                self.db, sample_only, study.id, pull.id, pulled["version"], "NO-EXECUTE"
            )

        actor = actor_with_permissions(
            self.org.id, "stability_pull.execute", "sample.create"
        )
        sample_count = self.db.query(Sample).count()
        sample_test_count = self.db.query(SampleTest).count()
        audit_count = self.db.query(AuditEvent).count()
        pull_status, pull_sample_id, pull_version = pull.status, pull.qc_sample_id, pull.version
        rollback_number = f"ROLL-{uuid4().hex[:6]}"
        savepoint = self.db.begin_nested()
        with patch.object(self.pulls_api.repository, "update_expected", return_value=None), \
             patch.object(self.db, "rollback", side_effect=savepoint.rollback):
                with self.assertRaises(VersionConflictException):
                    self.pulls_api.create_sample(
                        self.db, actor, study.id, pull.id, pulled["version"], rollback_number
                    )
        self.assertEqual(self.db.query(Sample).count(), sample_count)
        self.assertEqual(self.db.query(SampleTest).count(), sample_test_count)
        self.assertEqual(self.db.query(AuditEvent).count(), audit_count)
        self.assertIsNone(self.db.query(Sample).filter_by(
            sample_number=rollback_number
        ).first())
        self.db.refresh(pull)
        self.assertEqual((pull.status, pull.qc_sample_id, pull.version),
                         (pull_status, pull_sample_id, pull_version))

    def test_create_sample_rejects_scheduled_duplicate_and_outside_placement(self):
        study, _, pull, specification = self._active_pull()
        actor = actor_with_permissions(
            self.org.id, "stability_pull.execute", "sample.create"
        )
        with self.assertRaises(ValidationException):
            self.pulls_api.create_sample(
                self.db, actor, study.id, pull.id, pull.version, "TOO-EARLY"
            )

        pulled = self.pulls_api.mark_pulled(
            self.db, actor, study.id, pull.id, pull.version,
            datetime(2026, 5, 6, tzinfo=timezone.utc), None, notes_supplied=False,
        )
        self.samples.create(self.db, self.org.id, {
            "sample_number": "DUPLICATE", "material_id": study.material_id,
            "specification_version_id": specification.id,
        })
        savepoint = self.db.begin_nested()
        with patch.object(self.db, "rollback", side_effect=savepoint.rollback):
            with self.assertRaises(DuplicateResourceException):
                self.pulls_api.create_sample(
                    self.db, actor, study.id, pull.id, pulled["version"], " duplicate "
                )

        business_unit, division, department = self._hierarchy()
        study.business_unit_id, study.division_id, study.department_id = (
            business_unit.id, division.id, department.id
        )
        self.db.flush()
        department_actor = actor_with_permission_scopes(
            self.org.id,
            **{"stability_pull.execute": "ORGANIZATION", "sample.create": "DEPARTMENT"},
        )
        department_actor.department_id = uuid4()
        with self.assertRaises(HTTPException):
            self.pulls_api.create_sample(
                self.db, department_actor, study.id, pull.id, pulled["version"], "OUTSIDE"
            )
