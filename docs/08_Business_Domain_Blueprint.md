# LabGenius Business Domain Blueprint

**Version:** 1.0  
**Status:** Approved Design Baseline  
**Implementation horizon:** Sprints 16–24

This document is the permanent design baseline for the first LabGenius business
domains. Implementation discoveries that require an architectural change must be
recorded explicitly in a future blueprint revision; implementations must not silently
change this baseline.

## 1. Architectural principles

- Reuse the platform services already established for JWT authentication, RBAC,
  organization scope, audit, request correlation, sanitization, and ADMIN safety.
- Keep bounded domains explicit. A Test, Method, Specification, Sample, Result,
  Instrument, and Stability record each has a distinct identity and responsibility.
- Organization-owned roots carry scope ownership. Children normally inherit access
  through their parent instead of repeating every hierarchy column.
- Preserve historical truth. Approved definitions and finalized operations are not
  overwritten as ordinary CRUD records.
- Use PostgreSQL foreign keys for real relationships, UUID primary keys, UTC-aware
  timestamps, bounded SQL queries, and explicit domain statuses.
- Keep workflow rules in services, persistence queries in repositories/services, and
  HTTP translation in routers/schemas.
- The backend remains the authorization and workflow authority. Frontend controls are
  usability aids, not security boundaries.

## 2. Locked cross-domain decisions

1. One shared Instrument Registry serves QC, Stability Chambers, Calibration,
   Maintenance, and Qualification.
2. Stability has no separate result engine. Stability Pulls create or link QC Samples
   and reuse the QC testing workflow.
3. Test means what is measured; Method means how it is measured; Specification means
   the acceptance criteria.
4. Approved Methods, Specifications, and Stability Protocols use version-controlled
   historical records rather than overwrite.
5. Finalized operational records are not ordinary editable CRUD records.
6. Existing authentication, RBAC, permission, scope, and audit services are reused.
7. Organization-owned roots carry ownership; child scope normally follows parents.
8. QC `SELF` means work actively assigned to the authenticated analyst, not every
   record created by that user.
9. Central optimistic concurrency must be strengthened before workflow-heavy QC work.
10. There is no universal workflow-status enum; each bounded domain owns its vocabulary.
11. Business forms use permission-aware lookup/select controls, not manual UUID entry.

## 3. Modelling conventions

### 3.1 Versioning classes

| Class | Meaning | Update rule |
|---|---|---|
| M | Mutable master/reference data | Controlled edits while active; referenced rows are normally deactivated, not deleted. |
| V | Version-controlled definition | Stable root identity with immutable numbered versions; approval selects the effective version. |
| W | Workflow/operational record | Changes only through explicit service transitions and authorization. |
| I | Immutable/finalized history | Append-only or correction-by-new-record; no ordinary update/delete. |

### 3.2 Common columns

All proposed tables use UUID `id` primary keys and appropriate `created_at` /
`updated_at` timestamps. M/V/W roots use active/version metadata where appropriate.
Organization-owned roots carry `organization_id` and only the hierarchy ownership
needed for their scope boundary. Workflow records carry actor/assignment/finalization
metadata as their sprint defines it. AuditEvent remains separate from domain tables.

Foreign keys are explicit; varying entity references are not implemented as generic
polymorphic foreign keys. Codes are unique within their approved ownership boundary.
Deletion behavior must protect referenced history.

## 4. Sprint 16–24 entity catalog

Table names below are the approved proposed names. Exact column sizing and indexes are
confirmed during the owning sprint without changing entity meaning.

### Sprint 16 — Shared Business Domain Foundation

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| Business Location / `business_locations` | M | `id`; `organization_id` → organizations; nullable `parent_location_id` → business_locations | ACTIVE/INACTIVE; organization-owned hierarchy |
| Material / `materials` | M | `id`; `organization_id` → organizations | ACTIVE/INACTIVE; organization-owned |

A location has zero or one parent and zero to many child locations. Materials are shared
business masters used by QC samples/specifications and Stability protocols. Location
types and material classifications are bounded reference values owned by this domain,
not a platform-wide workflow enum.

### Sprint 17 — Instrument / Asset Registry

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| Instrument / `instruments` | M | `id`; `organization_id` → organizations; `location_id` → business_locations | ACTIVE/INACTIVE/OUT_OF_SERVICE/RETIRED; organization-owned |

One location has many instruments. A chamber is an instrument with the appropriate
instrument classification/capability, not a second chamber registry. Later Calibration,
Maintenance, and Qualification domains reference `instruments.id`.

### Sprint 18 — QC Master Data

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| QC Test / `qc_tests` | M | `id`; `organization_id` → organizations | ACTIVE/INACTIVE; organization-owned |
| Method / `methods` | V root | `id`; `organization_id` → organizations; optional `test_id` → qc_tests | ACTIVE/INACTIVE; organization-owned |
| Method Version / `method_versions` | V | `id`; `method_id` → methods; unique `(method_id, version_number)` | DRAFT/APPROVED/RETIRED; scope inherited from Method |
| Specification / `specifications` | V root | `id`; `organization_id` → organizations; `material_id` → materials | ACTIVE/INACTIVE; organization-owned |
| Specification Version / `specification_versions` | V | `id`; `specification_id` → specifications; unique version | DRAFT/APPROVED/RETIRED; inherited |
| Specification Test / `specification_tests` | V child | `id`; `specification_version_id` → specification_versions; `test_id` → qc_tests; `method_version_id` → method_versions | Acceptance criteria belong to the specification version |

A Test can be supported by many Method Versions. A Specification Version contains one
or more Specification Tests. Each Specification Test identifies what is measured, the
approved method used, and its acceptance criteria. Approval never overwrites an older
approved version.

### Sprint 19 — Sample Registration & Test Generation

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| QC Sample / `qc_samples` | W | `id`; organization ownership; `material_id` → materials; `specification_version_id` → specification_versions | REGISTERED/IN_TESTING/REVIEW/FINALIZED/CANCELLED |
| Sample Test / `sample_tests` | W | `id`; `sample_id` → qc_samples; `test_id` → qc_tests; `method_version_id` and specification-test reference | PENDING/ASSIGNED/IN_PROGRESS/RESULT_ENTERED/REVIEWED/FINALIZED/CANCELLED |

One Sample has one or more generated Sample Tests. Generation snapshots or references
the approved definition versions required to reproduce the decision later. Sample scope
is owned at the Sample root; Sample Tests inherit it.

### Sprint 20 — Analyst Assignment & Workbench

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| Analyst Assignment / `analyst_assignments` | W | `id`; `sample_test_id` → sample_tests; `analyst_user_id` → users | ACTIVE/COMPLETED/CANCELLED; inherited from Sample Test |

A Sample Test may have assignment history but at most one active primary assignment as
defined by the sprint constraint. QC `SELF` visibility is based on an active assignment
to the authenticated analyst.

### Sprint 21 — Result Entry, Review & Finalization

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| Sample Test Result / `sample_test_results` | W → I | `id`; `sample_test_id` → sample_tests; entry/reviewer/finalizer user FKs | DRAFT/ENTERED/REVIEWED/FINALIZED/REJECTED/CANCELLED |

A Sample Test can retain result history/corrections, while only the effective result is
used for the current decision. FINALIZED results are immutable; correction/reopen is an
explicit authorized workflow creating preserved history and audit evidence. Result scope
inherits through Sample Test → Sample.

### Sprint 22 — QC Operational Dashboard

This sprint adds bounded operational queries/reporting projections over Samples, Sample
Tests, Assignments, and Results. It does not create a second source of truth or a new
result model. Queries remain permission- and organization-scoped, paginated, and indexed.

### Sprint 23 — Stability Protocol & Study Management

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| Stability Protocol / `stability_protocols` | V root | `id`; `organization_id` → organizations; `material_id` → materials | ACTIVE/INACTIVE; organization-owned |
| Protocol Version / `stability_protocol_versions` | V | `id`; `protocol_id` → stability_protocols; unique version | DRAFT/APPROVED/RETIRED |
| Protocol Condition / `stability_protocol_conditions` | V child | `id`; `protocol_version_id` → stability_protocol_versions | Inherited version state |
| Protocol Timepoint / `stability_protocol_timepoints` | V child | `id`; condition/protocol-version FK as finalized in sprint design | Inherited version state |
| Stability Study / `stability_studies` | W | `id`; organization ownership; `protocol_version_id` → stability_protocol_versions | PLANNED/ACTIVE/ON_HOLD/COMPLETED/CANCELLED |
| Chamber Placement / `stability_chamber_placements` | W | `id`; `study_id` → stability_studies; `instrument_id` → instruments; condition reference | PLANNED/PLACED/REMOVED/CANCELLED |

One approved Protocol Version defines conditions and timepoints. One Study binds to one
approved Protocol Version and can have placement history. Chamber references always use
the shared Instrument Registry. Children inherit study/protocol scope.

### Sprint 24 — Stability Pull Scheduling & QC Integration

| Entity / table | Class | Key structure and relationship | Status / scope |
|---|---|---|---|
| Stability Pull / `stability_pulls` | W | `id`; `study_id` → stability_studies; timepoint/condition reference; nullable `qc_sample_id` → qc_samples | SCHEDULED/DUE/PULLED/QC_CREATED/COMPLETED/MISSED/CANCELLED |

A Study has many scheduled Pulls. A Pull creates or links one QC Sample under an
idempotent service operation, then the existing Sample Test, assignment, result, review,
and finalization engine owns testing. Stability stores the link and scheduling context,
not duplicate results.

## 5. Ownership, authorization, audit, and SELF

- Business permission namespaces follow `<domain>.<action>` and are added incrementally
  in the implementing sprint; this blueprint does not claim that codes already exist.
- Every operation requires RBAC permission and applicable organization scope.
- Root query filters execute in SQL. Direct out-of-scope identifiers preserve current
  404 concealment. Child access joins through the scoped parent.
- SELF is explicitly defined by each domain. For QC analyst work it means currently
  active assignment to that analyst. Creator identity alone does not grant SELF access.
- CREATE, UPDATE, status transitions, assignment, review, finalization, cancellation,
  override, and correction actions use AuditService in the business transaction.
- Audit details use centralized sanitization and retain organization/request context.

## 6. Historical integrity and concurrency

Referenced masters are normally deactivated rather than hard deleted. Approved V-class
versions remain addressable by historical operations. W-class transitions validate the
current state, authorization, and required relationships. Finalized I-class information
has no ordinary edit/delete endpoint.

Version columns exist today, but SQLAlchemy mapper-level optimistic locking is not
configured. The approved direction is a central concurrency contract (version checks,
consistent conflict response, and regression tests) before workflow-heavy QC result
implementation. This document does not claim that protection currently exists.

## 7. Dependency sequence

```text
Shared Masters
  → Instruments
  → QC Masters
  → Samples
  → Assignments
  → Results
  → QC Dashboard
  → Stability Protocols / Studies
  → Stability Pulls
  → existing QC testing engine
```

Calibration, Maintenance, and Qualification are later domains. They reuse the shared
Instrument Registry and are not part of Sprints 16–24.

## 8. Definition of done for each business domain

- Models, one clean migration with one Alembic head, repositories, services, schemas,
  routers, and permission seeds follow current conventions.
- Permission and organization-scope behavior covers SQL lists and direct identifiers.
- Parent/child ownership and domain SELF semantics are explicit and tested.
- Business mutation and AuditEvent commit or roll back together.
- Status transitions, historical/version rules, finalization, and concurrency behavior
  are explicit; no ordinary CRUD bypass exists.
- API lists are bounded, indexed for expected access patterns, and avoid Python-side
  cross-scope filtering and obvious N+1 behavior.
- Frontend uses permission-aware lookups rather than manual UUID entry and never replaces
  backend authorization.
- Focused and full regression, compilation, startup/OpenAPI, migration drift, security,
  documentation, and Git hygiene checks pass.

## 9. Deferred capabilities

- Calibration, Maintenance, and Qualification workflows beyond the shared registry
- Electronic signatures and formal regulatory-validation claims
- LIMS/ERP/instrument integrations and automated data acquisition
- Advanced result calculations, worksheets, limits trending, and statistical controls
- Stability forecasting, notifications, excursions, and advanced chamber monitoring
- General workflow engine, universal status enum, or event sourcing
- Central optimistic locking implementation (required before workflow-heavy QC)
- Archival/retention automation and reporting/export beyond domain sprint scope
