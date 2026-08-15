# Changelog

## [Unreleased]

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