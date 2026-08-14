# Changelog

## [Unreleased]

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
- Seeded the initial 24 application permissions.
- Seeded the ADMIN role with the complete initial permission set.
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