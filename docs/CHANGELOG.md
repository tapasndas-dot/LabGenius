# Changelog

## [Unreleased]

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

- Sprint 12.3: password change/reset/policy, `force_password_change`, and `password_changed_at`.
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
