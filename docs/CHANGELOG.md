# Changelog

## [Unreleased]

### Added — Sprint 20C SampleTest Assignment frontend

- Extended Sample detail with human-readable current assignment and immutable history,
  plus permission-driven Assign, Reassign, and confirmed Unassign controls.
- Added active same-organization user selection through a minimal `sample.view`-guarded
  assignment-user lookup; mutation eligibility remains authoritative on the backend.
- Reconciled Sample, SampleTest, assignment, history, and server-issued versions after
  every mutation, with explicit readable HTTP 409 refresh recovery and no automatic retry.
- Added focused frontend coverage for permissions, mutation lifecycles, retained history,
  cancelled/finalized behavior, and authoritative version chaining.

### Added — Sprint 20B SampleTest Assignment API

- Added nested assign, reassign, unassign, current-assignment, and chronological-history
  endpoints under each Sample/SampleTest, with explicit SampleTest and assignment versions.
- Enforced `sample.assign` hierarchy scope for mutations and `sample.view` for reads,
  including 404 concealment, SELF mutation denial, and SQL union of hierarchy and active-
  assignment access for viewing.
- Added clean concurrency conflicts and transactionally coupled `ASSIGN`/`UNASSIGN`
  audit events. Audit failure rolls back the assignment mutation.
- Excluded CANCELLED/FINALIZED Samples and SampleTests from assignment-derived SELF access
  while preserving complete assignment history.

### Added — Sprint 20A SampleTest assignment foundation

- Added retained per-SampleTest assignment history with restrictive foreign keys,
  optimistic versions, and a PostgreSQL partial unique index enforcing one active
  assignment per SampleTest.
- Added flush-only assign, reassign, and unassign operations with active same-organization
  user validation, safe SampleTest status transitions, row locking, and expected-version
  conflict protection.
- Activated SQL-level SampleTest and Sample SELF semantics based exclusively on active
  assignments, including reassignment transfer and duplicate-free Sample queries.
- Added the single `sample.assign` permission for idempotent ADMIN mapping. Sprint 20B
  now supplies the HTTP and transactional audit integration.

### Validated — Sprint 19D automation and release validation

- Completed the full backend regression: 190 tests passed, 0 failed, 0 skipped, with 8
  warnings from existing pytest collection deprecations and no functional regressions.
- Completed the full frontend validation: lint passed, production build passed, and the
  dependency audit reported 0 vulnerabilities.
- Confirmed the single `f19a0c6e8b05` Alembic head with no schema drift, FastAPI startup and
  OpenAPI health, the `/auth/login` token URL, and the expected Sprint 19 Sample permissions.
- Manual browser acceptance remains pending and is not claimed by this validation.

### Added — Sprint 19C Sample Registration frontend

- Added the permission-protected `/app/samples` workspace with backend-paginated
  Sample browsing, filters, readable master-data labels, registration, detail,
  permitted editing, and expected-version cancellation.
- Added Material-dependent approved Specification Version selection and reusable
  Business Unit, Division, and Department lookups with safe unavailable states and
  dependent-selection clearing.
- Added idempotent SampleTest generation and read-only display of the exact frozen
  Test and Method Version references, plus explicit stale-record recovery for HTTP 409.

### Added — Sprint 19B Sample APIs

- Added permission-protected Sample list/create/detail/update/cancel endpoints and
  SampleTest read/idempotent-generation endpoints under `/samples`.
- Added SQL-level operational hierarchy scope, permission-specific target hierarchy
  enforcement, SELF deferral, UUID concealment, pagination, filters, and optimistic
  concurrency.
- Added transactional Sample CREATE/UPDATE/CANCEL auditing and CREATE audit events for
  newly generated SampleTests. Cancellation preserves Samples and generated history;
  no Sample DELETE API exists.

### Added — Sprint 19A Sample foundation

- Added organization/hierarchy-owned `qc_samples` with organization-unique normalized
  Sample numbers, exact approved Specification Version binding, optimistic versioning,
  Blueprint-aligned status checks, and industry-neutral priority checks.
- Added restrictive `sample_tests` children that freeze exact Specification Test, Test,
  and Method Version references and generate idempotently in source order.
- Preserved Specification Limit traceability through immutable approved Specification
  Test trees; result, assignment, workflow API, and operational `SELF` semantics remain
  deferred.
- Added `sample.view`, `sample.create`, `sample.update`, and `sample.cancel` permissions.

### Validated — Sprint 18E QC Release Readiness

- Completed the full automated regression: 173 backend tests and 48 frontend tests
  passed with zero failures or skips; frontend lint, production build, and dependency
  audit also passed with zero known vulnerabilities.
- Confirmed the single `e18b0d5f7a04` Alembic head with no model/schema drift, complete
  startup/OpenAPI health, unique idempotent permissions, and no duplicate routes.
- Revalidated permission-specific shared-master scope, nested UUID concealment,
  expected-version concurrency, historical immutability, lifecycle/readiness rules,
  transactional audit rollback, all seven limit criteria, CORE_LAB isolation, and exact
  MethodVersion traceability after a later version exists.
- Sprint 18 automated implementation is complete. Manual browser acceptance and final
  Sprint closure remain pending and are not claimed by this validation.

### Added — Sprint 18D QC Shared-Master Frontend

- Added permission-gated Laboratory Masters navigation and management pages for Tests,
  Methods/Versions/Parameters, and Specifications/Versions/Tests/Limits.
- Added readable Material, Test, Method, and exact MethodVersion selectors with safe
  lookup-unavailable behavior and no manual UUID input.
- Added lifecycle confirmations, DRAFT-only structural editing, historical read-only
  presentation, criterion-adaptive limit fields, expected-version mutations, and stale-
  conflict refresh behavior.
- Added focused frontend coverage while leaving Sprint 18 open for 18E manual acceptance,
  full regression, and closure.

### Added — Sprint 18C QC Shared-Master APIs

- Added secured Test, Method/Version/Parameter, and Specification/Version/Test/Limit
  REST APIs with strict schemas, practical filtering, and nested-parent concealment.
- Applied permission-specific organization-wide shared-master scope: hierarchy scopes
  reach same-organization records while SELF has no QC-master access or create authority.
- Added explicit expected-version approve, retire, and supersede operations with
  transactional APPROVE, RETIRE, and SUPERSEDE audit actions.
- Preserved DRAFT-only structural mutation, Specification approval readiness, exact
  MethodVersion bindings, CORE_LAB's implicit capability boundary, and no e-signature
  claim. Sprint 18 remains open.

### Added — Sprint 18B Specification Foundation

- Added organization-owned, Material-linked Specification headers and historical
  Specification Version/Test/Limit trees with restrictive relationships.
- Added exact Test-to-Method-Version bindings within Specification Versions; approved
  Specifications never dynamically follow later Method Versions.
- Added seven precision-safe limit criteria with domain semantic validation, DRAFT-only
  tree mutation, approval-readiness validation, and expected-version concurrency.
- Added four future Specification API permissions, a single-head PostgreSQL migration,
  flush-only repositories/services, and focused coverage. Sprint 18 remains open.

### Added — Sprint 18A QC Test and Method Foundation

- Added independent organization-owned Test and Method masters; Test remains what is
  measured and Method remains how it is performed, with no premature direct link.
- Added historical Method Versions with controlled lifecycle status, effectivity,
  expected-version concurrency, and DRAFT-only structural mutation protection.
- Added industry-neutral structured Method Parameters with controlled value types and
  DRAFT-version immutability inheritance.
- Added eight future API permissions, restrictive PostgreSQL tables and constraints,
  flush-only repositories/services, and focused PostgreSQL coverage. Sprint 18 remains open.

### Validated — Sprint 17 Instrument / Asset Registry Closure

- Completed integrated backend, frontend, database, migration, startup, OpenAPI,
  permission-seed, capability, authorization, concurrency, audit, and hygiene validation.
- Final scope includes the shared Instrument Registry, hierarchy and shared-master
  ownership, optional Stability Chamber Profile foundation, `INSTRUMENTS` capability,
  permission-specific organization scope (`SELF` is responsible user), transactional
  audit, expected-version concurrency, and frontend management UI.
- Calibration, Maintenance, Qualification, QC Instrument usage, and Stability workflows
  remain intentionally deferred future modules.

### Added — Sprint 17C Instrument Registry Frontend

- Added the capability- and permission-aware `/app/instruments` route and navigation.
- Added responsive Instrument list, filters, pagination, create/edit forms, controlled
  status/criticality choices, and permission-specific lifecycle actions.
- Added human-readable shared-master, hierarchy, and responsible-user lookups with
  dependent hierarchy selection and safe lookup-unavailable behavior.
- Added expected-version mutations, stale-conflict refresh, confirmation prompts, and
  focused frontend coverage. Chamber-profile editing remains deferred.

### Added — Sprint 17B Instrument Registry API and Security

- Added list/detail/create/update/activate/deactivate/delete Instrument APIs with
  strict schemas, safe conflicts, optimistic concurrency, and transactional audit.
- Enforced operation permissions together with the organization `INSTRUMENTS`
  capability and SQL-level organization hierarchy scope predicates.
- Froze Instrument SELF scope as `responsible_user_id == authenticated user.id`;
  SELF alone cannot create Instruments or reassign their ownership hierarchy.
- Preserved 404 concealment, active/status separation, and the Sprint 17A schema.

### Added — Sprint 17A Instrument Registry Foundation

- Added the organization-owned Instrument model, controlled operational status and
  criticality, hierarchy/shared-master references, responsible user, and governance flags.
- Added the optional one-to-one Stability Chamber Profile foundation without workflows,
  monitoring, alarms, schedules, or a separate chamber registry.
- Added flush-only repository/service foundations with normalization, active same-organization
  reference validation, SQL filtering, and atomic expected-version updates.
- Added `instrument.view/create/update/delete` permissions and the single-head Sprint 17A
  migration; Sprint 17 remains open for APIs and frontend.

### Added — Sprint 16D Module Capability Foundation

- Added the system-managed capability registry and versioned organization capability
  assignments with restrictive ownership and no historical-data deletion behavior.
- Added dependency-aware enable/disable services, atomic audit events, expected-version
  conflicts, `module.view`/`module.manage`, and the reusable backend capability guard.
- PLATFORM and CORE_LAB are mandatory, implicitly available capabilities; optional
  assignments default disabled, preserving existing Administration and shared Masters.
- Added organization capability APIs, centralized frontend capability context, and the
  permission-aware Administration capability page.
- Sprint 16 is complete; no future-domain workflows or commercial package logic were added.

### Added — Sprint 16C Frontend Shared Masters

- Added permission-aware Masters navigation and guarded pages for Locations,
  Manufacturers, Instrument Types, and Materials.
- Added shared typed CRUD, filtering, pagination, detail, status, delete-confirmation,
  safe error, and optimistic-concurrency UI patterns.
- Added a reusable human-readable lookup/select foundation for parent Locations.
- Completed Sprint 16 frontend/backend/database closure validation while leaving Sprint
  16D Module Capability Foundation as the next task; Sprint 16 overall remains open.
- Updated the transitive `nanoid` dependency to the patched release; npm audit reports
  zero known vulnerabilities.

### Documentation — Business Domain Blueprint v1.1

- Established LabGenius as an industry-neutral laboratory platform with pharmaceutical
  QC/R&D as the first reference implementation.
- Approved the separation of organization module enablement, user RBAC authorization,
  and structured module configuration.
- Added provisional capability classes, technical dependency rules, historical-data
  preservation on disablement, and the proposed Sprint 16D module foundation.
- Planning documentation only; no module registry, capability guard, pricing/package
  logic, schema, backend, or frontend implementation was added.

### Documentation — Business Domain Blueprint v1.0

- Approved the permanent business-domain architecture baseline for Sprints 16–24.
- Established the implementation sequence from shared masters and instruments through
  QC operations and Stability-to-QC integration.
- Added entity, relationship, ownership, versioning, audit, historical-integrity, and
  concurrency direction for future business domains.
- Architecture and documentation only; no business-domain production code was added.

### Added — Sprint 15 Frontend Foundation

- React/TypeScript/Vite foundation with configurable API client and JWT restoration.
- Protected and forced-password routes, application shell, safe 403/404 handling.
- Effective-permission navigation with backend authorization remaining authoritative.
- Scoped users, roles, role/user assignments, access scopes, and read-only audit UI.
- Selective `/auth/me` refresh after authorization-changing operations.

### Security — Sprint 15

- Centralized `localStorage` JWT handling documents its XSS trade-off.
- Organization scope remains server-enforced and is not reimplemented in React.

### Added — Sprint 14 Audit & Compliance Foundation

- Append-only `AuditEvent` records with actor, entity identity, hierarchy ownership,
  safe JSONB changes, optional reason, request UUID, source IP, and source type.
- Atomic auditing for user CRUD and activation/deactivation, role create/update/status,
  user-role assignment/removal, and role-permission assignment/removal.
- Read-only audit APIs with bounded SQL pagination, filters, newest-first ordering,
  `audit.view`, and organization scope.
- Server-generated `X-Request-ID` values and shared recursive sanitization.
- Migration `e7a4c1d9b302`; idempotent ADMIN seeding updated for `audit.view`.

### Fixed — Sprint 14

- Restored reachable organizational hierarchy validation during user updates.

### Compliance Position

- This traceability foundation is not certification of 21 CFR Part 11, EU Annex 11,
  GxP, data-integrity compliance, or electronic-signature compliance.

### Added — Sprint 13 Organization-Level Authorization

- Per-UserRole ORGANIZATION, BUSINESS_UNIT, DIVISION, DEPARTMENT, and SELF scopes.
- Permission-specific multi-role scope resolution.
- Central hierarchy validation and reusable scope filtering/access helpers.
- SQL-filtered and direct-ID-protected user administration.
- Scope enforcement for user security and user-role administration.
- Migration `d40a6c87e913`, including ADMIN organization-scope backfill.

### Security — Sprint 13

- Strict cross-organization isolation with 404 responses for out-of-scope users.
- Role assignment scope escalation protection.
- Designation retained as a workflow/job attribute, not an access boundary.
- Role and permission catalogs remain global configuration.

### Added — Sprint 12.4 Administrative Security Closure

- Centralized last-usable-ADMIN protection for user deactivation/deletion,
  ADMIN assignment removal, and ADMIN-role deactivation.
- PostgreSQL row-lock serialization through the shared ADMIN role.
- HTTP 409 security-conflict handling for blocked final-ADMIN operations.
- Safe `ADMIN_SAFETY_BLOCKED` security events.
- Full Sprint 12.1–12.4 regression coverage.

### Security — Sprint 12.4

- `force_password_change` ADMIN users continue to count as usable because they can remediate.
- Inactive, actively locked, inactive-assignment, and inactive-role accounts do not count as usable ADMIN backups.
- No unauthenticated recovery endpoint, hard-coded account, credential, or backdoor was added.
- JWT expiry remains the current post-password-change risk boundary; token revocation is deferred.
- Security-history responses remain permission protected, newest-first, and limited to 500 records.

### Sprint 12 Status

- Sprint 12 — User Administration & Security Operations: COMPLETE.
- Next: Sprint 13 — Organization-Level Authorization.

### Added — Sprint 12.3 Password Security

- Centralized configurable password policy with 12-character default minimum and
  uppercase, lowercase, digit, and special-character requirements.
- Authenticated `POST /auth/change-password` self-service flow.
- `user.update`-protected `POST /users/{user_id}/reset-password` administrative flow.
- `PASSWORD_CHANGED` and `PASSWORD_RESET` security events.
- `force_password_change` restriction across role- and permission-protected APIs.
- Password-policy enforcement and lifecycle initialization during user creation.

### Changed — Sprint 12.3

- Password changes update `password_changed_at`, clear forced-change state, and
  reset temporary login failure state.
- Administrative resets set forced-change state and clear lock/failure state
  without activating inactive users.

### Security — Sprint 12.3

- Passwords and hashes are excluded from security-event details and validation messages.
- Forced-change users retain OAuth2/JWT access only for identity inspection and password change.
- Existing JWT revocation after password mutation remains deferred because session
  versioning/revocation infrastructure is not present.
- Rollout note: existing active accounts currently marked `force_password_change`
  must complete `/auth/change-password`; OAuth2 login remains available for this.

### Added — Sprint 12.1 Account Lifecycle Security

- Configurable failed-login threshold and account lockout duration.
- Failed-login counting, `locked_until`, successful-login reset, and `last_login`.
- Dedicated user security, activation, deactivation, and unlock APIs.
- RBAC protection through `user.view` and `user.update`.

### Added — Sprint 12.2 Security History

- Persistent `LoginHistory` and `SecurityEvent` models.
- Login success/failure and account lock/unlock/activation/deactivation events.
- Request IP and user-agent capture for login attempts.
- Actor/target attribution for administrative security events.
- `user.view`-protected, paginated security-history APIs.
- Alembic migration `b7219de4a612` for both audit tables and indexes.

### Changed

- Removed account security-state fields from generic `UserUpdate`.
- Consolidated each security action and audit records into one commit boundary.
- Unlock preserves inactive state instead of implicitly reactivating an account.
- Removed configuration startup debug output.

### Security

- Locked and inactive accounts are rejected before password verification.
- Audit schemas exclude credentials and event metadata removes credential-like keys.
- Added authentication, lifecycle-event, authorization, pagination, and credential-exclusion tests.

### Deferred

- Sprint 12.4: last-active-ADMIN protection, controlled recovery, and final Sprint 12 closure.

## [v0.13.0] - Sprint 11.4

### Added

- User-Role repository.
- User-Role service.
- User-Role schemas.
- User-Role administration API.
- User role listing.
- Role assignment to users.
- Role removal from users.
- Duplicate assignment protection.

### Security

- User-Role administration protected by `user.view` and `user.update`.
- Active-user validation implemented.
- Active-role validation implemented.
- Effective authorization through UserRole → Role → RolePermission → Permission validated.
- Unauthorized User-Role operations return HTTP 403 Forbidden.

### Testing

- User-role assignment validated.
- Duplicate assignment validation validated.
- Inactive-user protection validated.
- Inactive-role protection validated.
- Role removal validated.
- Restricted-user authorization validated.

## [v0.12.0] - Sprint 11.3

### Added

- Role-Permission repository.
- Role-Permission service.
- Role-Permission schemas.
- Role-Permission administration API.
- Role permission listing.
- Permission assignment to roles.
- Permission removal from roles.
- Duplicate assignment protection.

### Security

- Role-Permission administration protected by `role.view` and `role.update`.
- Active-role validation implemented.
- Active-permission validation implemented.
- Permission-driven endpoint authorization validated.
- Unauthorized operations return HTTP 403 Forbidden.

### Testing

- ADMIN role-permission access validated.
- Permission assignment validated.
- Duplicate assignment validation validated.
- Permission removal validated.
- End-to-end permission authorization validated using TEST_ROLE.

## [v0.11.0] - Sprint 11.2

### Added

- Role administration repository.
- Role administration service.
- Role administration schemas.
- Role administration API.
- Role listing and active-role filtering.
- Role creation and update.
- Role active/inactive management.
- Role administration permissions.
- Duplicate role-code validation.

### Security

- Role administration protected by explicit permissions.
- Inactive roles cannot grant authorization.
- Restricted-user authorization validated with HTTP 403.

### Testing

- ADMIN role administration validated.
- Duplicate role creation validated.
- Role activation/deactivation validated.
- Restricted-user authorization validated.

### Security / RBAC

- Completed foundational JWT authentication.
- Implemented secure password hashing using `pwdlib`.
- Implemented centralized current-user resolution.
- Implemented role-based authorization.
- Implemented permission-based authorization.
- Implemented active-state checks for:
  - Users
  - User-role assignments
  - Roles
  - Role-permission assignments
  - Permissions
- Established the `<module>.<action>` permission naming convention.
- Seeded the initial 24 business permissions.
- Added `permission.view` and `permission.update` for security administration.
- Expanded the application permission catalog to 26 permissions.
- Seeded the ADMIN role with the complete 26-permission set.
- Implemented Permission Administration API:
  - `GET /permissions/`
  - `GET /permissions/active`
  - `GET /permissions/{permission_id}`
  - `PUT /permissions/{permission_id}/status`
- Protected Permission Administration APIs using explicit `permission.view` and `permission.update` permissions.
- Enforced active-state authorization for permissions.
- Validated that inactive permissions cannot grant authorization.
- Validated restricted-user authentication and permission denial.
- Confirmed `403 Forbidden` for users without `permission.view`.
- Protected Organization APIs with permission-based authorization.
- Protected Business Unit APIs with permission-based authorization.
- Protected Division APIs with permission-based authorization.
- Protected Department APIs with permission-based authorization.
- Protected Designation APIs with permission-based authorization.
- Protected User APIs with permission-based authorization.
- Validated restricted-role behavior using a temporary LAB_USER role.
- Validated successful authorization for granted permissions.
- Validated `403 Forbidden` responses for missing permissions.
- Validated active/inactive role-assignment enforcement.
- Completed authentication and RBAC regression testing.

### API Authorization Matrix

- Organization:
  - `organization.view`
  - `organization.create`
  - `organization.update`
  - `organization.delete`
- Business Unit:
  - `business_unit.view`
  - `business_unit.create`
  - `business_unit.update`
  - `business_unit.delete`
- Division:
  - `division.view`
  - `division.create`
  - `division.update`
  - `division.delete`
- Department:
  - `department.view`
  - `department.create`
  - `department.update`
  - `department.delete`
- Designation:
  - `designation.view`
  - `designation.create`
  - `designation.update`
  - `designation.delete`
- User:
  - `user.view`
  - `user.create`
  - `user.update`
  - `user.delete`

### Validation

- Confirmed successful JWT login.
- Confirmed `/auth/me`.
- Confirmed ADMIN role authorization.
- Confirmed permission authorization.
- Confirmed restricted-role authorization.
- Confirmed inactive user-role assignment blocks access.
- Confirmed final foundation API regression tests.

---

### Sprint 11.1 — Permission Administration

- Permission catalog expanded to 26 permissions.
- Permission administration repository implemented.
- Permission administration service implemented.
- Permission administration router implemented.
- Permission status management implemented.
- Active permission filtering implemented.
- Permission administration authorization validated.
- Restricted-user negative authorization test completed.
- Permission active-state enforcement validated.
