# Changelog

## [Unreleased]

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
