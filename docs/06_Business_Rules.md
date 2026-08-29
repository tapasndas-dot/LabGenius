# LabGenius Business Rules

## 1. Purpose

This document defines the business rules governing the LabGenius platform foundation, identity management, organizational hierarchy, and access control.

The rules in this document represent implemented or formally established application behavior.

---

## 2. Organizational Hierarchy

The current organizational hierarchy is:

    Organization
        |
        +-- Business Unit
                |
                +-- Division
                        |
                        +-- Department
                                |
                                +-- Designation

Users are associated with the organizational hierarchy through:

    Organization
    Business Unit
    Division
    Department
    Designation

This hierarchy provides the foundation for future organizational reporting and access-control rules.

---

## 3. Organization Rules

### BR-ORG-001 — Unique Organization

Each organization must have a unique identifier/code according to the organization data model.

### BR-ORG-002 — Organization Lifecycle

Organizations support an active/inactive state.

### BR-ORG-003 — Organization Authorization

Viewing an organization requires:

    organization.view

Creating an organization requires:

    organization.create

Updating an organization requires:

    organization.update

Deleting an organization requires:

    organization.delete

---

## 4. Business Unit Rules

### BR-BU-001 — Organizational Ownership

A Business Unit belongs to an Organization.

### BR-BU-002 — Business Unit Lifecycle

Business Units support an active/inactive state.

### BR-BU-003 — Business Unit Authorization

Viewing Business Units requires:

    business_unit.view

Creating a Business Unit requires:

    business_unit.create

Updating a Business Unit requires:

    business_unit.update

Deleting a Business Unit requires:

    business_unit.delete

---

## 5. Division Rules

### BR-DIV-001 — Business Unit Ownership

A Division belongs to a Business Unit.

### BR-DIV-002 — Division Lifecycle

Divisions support an active/inactive state.

### BR-DIV-003 — Division Authorization

Viewing Divisions requires:

    division.view

Creating a Division requires:

    division.create

Updating a Division requires:

    division.update

Deleting a Division requires:

    division.delete

---

## 6. Department Rules

### BR-DEPT-001 — Division Ownership

A Department belongs to a Division.

### BR-DEPT-002 — Department Lifecycle

Departments support an active/inactive state.

### BR-DEPT-003 — Department Authorization

Viewing Departments requires:

    department.view

Creating a Department requires:

    department.create

Updating a Department requires:

    department.update

Deleting a Department requires:

    department.delete

---

## 7. Designation Rules

### BR-DES-001 — Department Ownership

A Designation belongs to a Department.

### BR-DES-002 — Designation Lifecycle

Designations support an active/inactive state.

### BR-DES-003 — Designation Authorization

Viewing Designations requires:

    designation.view

Creating a Designation requires:

    designation.create

Updating a Designation requires:

    designation.update

Deleting a Designation requires:

    designation.delete

---

## 8. User Rules

### BR-USR-001 — User Identity

A User represents an application account.

### BR-USR-002 — User Uniqueness

User identity fields subject to unique database constraints must remain unique.

The current identity model includes unique constraints for:

    employee_code
    username
    email

### BR-USR-003 — Password Storage

User passwords must never be stored as plain text.

The application stores a password hash.

### BR-USR-004 — User Active State

An inactive user cannot access protected APIs.

### BR-USR-005 — User Authorization

Viewing users requires:

    user.view

Creating users requires:

    user.create

Updating users requires:

    user.update

Deleting users requires:

    user.delete

---

## 9. Role Rules

### BR-ROLE-001 — Role Identification

Every role has a unique role code.

### BR-ROLE-002 — Role Lifecycle

Roles have an active/inactive state.

### BR-ROLE-003 — Inactive Roles

An inactive role cannot grant permissions.

---

## 10. Permission Rules

### BR-PERM-001 — Permission Identification

Every permission has a unique permission code.

### BR-PERM-002 — Permission Naming

Permissions follow:

    <module>.<action>

Examples:

    organization.view
    organization.create
    organization.update
    organization.delete

### BR-PERM-003 — Permission Lifecycle

Permissions have an active/inactive state.

### BR-PERM-004 — Inactive Permissions

An inactive permission cannot authorize an API operation.

---

## 11. User-Role Rules

### BR-UR-001 — Many-to-Many Role Assignment

A user can have multiple roles.

### BR-UR-002 — Duplicate Role Assignment

The same role must not be assigned to the same user more than once.

### BR-UR-003 — Assignment Lifecycle

User-role assignments have an active/inactive state.

### BR-UR-004 — Inactive Assignment

An inactive user-role assignment cannot grant access.

---

## 12. Role-Permission Rules

### BR-RP-001 — Role Permission Mapping

A role can have multiple permissions.

### BR-RP-002 — Duplicate Permission Mapping

The same permission must not be assigned to the same role more than once.

### BR-RP-003 — Assignment Lifecycle

Role-permission assignments have an active/inactive state.

### BR-RP-004 — Inactive Mapping

An inactive role-permission mapping cannot grant access.

---

## 13. Authorization Rules

### BR-AUTH-001 — Authentication Required

Protected APIs require an authenticated user.

### BR-AUTH-002 — JWT Validation

The access token must be valid before protected operations are executed.

### BR-AUTH-003 — Active User Required

The authenticated user must be active.

### BR-AUTH-004 — Permission Required

A protected API operation must define the permission required to execute it.

### BR-AUTH-005 — Permission Resolution

A user receives a permission through:

    User
      |
      v
    UserRole
      |
      v
    Role
      |
      v
    RolePermission
      |
      v
    Permission

### BR-AUTH-006 — Active Authorization Chain

Every element in the authorization chain must be active:

    User
    UserRole
    Role
    RolePermission
    Permission

### BR-AUTH-007 — Forbidden Access

An authenticated user without the required permission receives:

    HTTP 403 Forbidden

### BR-AUTH-008 — Unauthorized Access

A request without valid authentication receives:

    HTTP 401 Unauthorized

---

## 14. Initial Permission Catalog

The initial system contains 24 permissions.

### Organization

    organization.view
    organization.create
    organization.update
    organization.delete

### Business Unit

    business_unit.view
    business_unit.create
    business_unit.update
    business_unit.delete

### Division

    division.view
    division.create
    division.update
    division.delete

### Department

    department.view
    department.create
    department.update
    department.delete

### Designation

    designation.view
    designation.create
    designation.update
    designation.delete

### User

    user.view
    user.create
    user.update
    user.delete

---

## 15. ADMIN Role

### BR-ADMIN-001 — Administrative Role

The `ADMIN` role is the initial system administration role.

### BR-ADMIN-002 — Initial Permissions

The initial ADMIN role is mapped to all 24 initial permissions.

### BR-ADMIN-003 — No Hard-Coded Permission Bypass

ADMIN authorization is implemented through explicit permissions rather than a universal code-level bypass.

This ensures that future roles can be configured independently.

---

## 16. Authentication Rules

### BR-AUTHN-001 — Login

Users authenticate using username and password.

### BR-AUTHN-002 — Password Verification

The supplied password is verified against the stored password hash.

### BR-AUTHN-003 — Access Token

Successful authentication results in a JWT access token.

### BR-AUTHN-004 — Token Expiration

The current access token lifetime is:

    60 minutes

### BR-AUTHN-005 — Token Subject

The JWT subject identifies the authenticated user's UUID.

---

## 17. CRUD Authorization Matrix

| Module | View | Create | Update | Delete |
|---|---|---|---|---|
| Organization | organization.view | organization.create | organization.update | organization.delete |
| Business Unit | business_unit.view | business_unit.create | business_unit.update | business_unit.delete |
| Division | division.view | division.create | division.update | division.delete |
| Department | department.view | department.create | department.update | department.delete |
| Designation | designation.view | designation.create | designation.update | designation.delete |
| User | user.view | user.create | user.update | user.delete |

---

## 18. Validation Rules

The identity foundation validates:

- duplicate username;
- duplicate email;
- duplicate employee code;
- organizational hierarchy relationships;
- designation relationships;
- role relationships;
- permission relationships.

The application must reject invalid hierarchy relationships and duplicate identity data before persistence.

---

## 19. Security Validation Rules

The RBAC implementation has been tested using both administrative and restricted users.

### Administrative test

The ADMIN user successfully accessed protected foundation APIs.

### Restricted-role test

A temporary `LAB_USER` role was created with only:

    organization.view
    business_unit.view
    division.view
    department.view
    designation.view

The following behavior was validated:

    GET /organizations/
        -> 200 OK

    POST /organizations/
        -> 403 Forbidden

    GET /users/
        -> 403 Forbidden

### Active assignment test

Disabling the temporary user-role assignment resulted in:

    403 Forbidden

Re-enabling the assignment restored authorized access.

---

## 20. Future Business Rules

The following rules are intentionally deferred to later modules:

- organization-level data isolation;
- tenant-level access enforcement;
- department-specific access;
- role-specific workflow restrictions;
- approval authority;
- segregation of duties;
- audit trail requirements;
- login attempt limits;
- password expiration;
- password reset;
- MFA;
- business transaction authorization.

These rules should be introduced when the corresponding functional modules are implemented.

---

## 21. Permission Administration Rules

The permission catalog is controlled application security configuration.

### 21.1 Permission Catalog

The application maintains a controlled catalog of permissions.

The current catalog contains:

    26 permissions

The original 24 business permissions cover:

    organization
    business_unit
    division
    department
    designation
    user

The security administration permissions are:

    permission.view
    permission.update

### 21.2 Permission Naming

Permission codes follow:

    <module>.<action>

The standard actions currently include:

    view
    create
    update
    delete

Security administration permissions use the same naming convention.

### 21.3 Permission Administration

The permission administration API supports:

    View permissions
    View active permissions
    View an individual permission
    Activate or deactivate a permission

The application does not currently support arbitrary permission creation or deletion through the API.

### 21.4 Active Permission Rule

An inactive permission must not grant authorization.

Authorization must therefore verify:

    User is active
    User-role assignment is active
    Role is active
    Role-permission assignment is active
    Permission is active

If any required element is inactive, access must be denied.

### 21.5 Least-Privilege Rule

Users must receive permissions through role assignments.

A user without the required permission must receive:

    403 Forbidden

Authentication alone does not grant access to protected business or security-administration APIs.

### 21.6 ADMIN Rule

The ADMIN role does not receive a hard-coded application bypass.

ADMIN receives broad access through explicit permission assignments.

The current ADMIN role is mapped to all 26 application permissions.

### 21.7 Permission Administration Security

The following permissions control the permission administration API:

    permission.view
    permission.update

A user without `permission.view` must not be able to retrieve the permission catalog.

A user without `permission.update` must not be able to change permission active state.

---

## 22. Permission Administration Validation

Permission administration has been validated through API and authorization testing.

### Administrative validation

The ADMIN user successfully:

    authenticated through JWT
    retrieved the permission catalog
    retrieved active permissions
    retrieved an individual permission
    deactivated a permission
    reactivated the permission

### Inactive permission validation

An inactive permission was tested against a protected API.

The authorization dependency correctly returned:

    403 Forbidden

The permission was subsequently reactivated.

### Restricted-user validation

A dedicated restricted test user was assigned a role with no permissions.

The user successfully authenticated but received:

    403 Forbidden

when attempting to access:

    GET /permissions/

This confirms that authentication does not imply authorization.

---

## 23. Future Business Rules

The following rules are intentionally deferred to later modules:

- organization-level data isolation;
- tenant-level access enforcement;
- department-specific access;
- role-specific workflow restrictions;
- approval authority;
- segregation of duties;
- audit trail requirements;
- login attempt limits;
- password expiration;
- password reset;
- MFA;
- business transaction authorization;
- role and permission administration workflows;
- security configuration audit history.

These rules should be introduced when the corresponding functional modules are implemented.

---

## 22. Role Administration Rules

### 22.1 Role Catalog

The application maintains a controlled catalog of security roles.

Each role contains:

    role_code
    role_name
    description
    active status

### 22.2 Role Code Uniqueness

Role codes must be unique.

Attempting to create a role using an existing role code must return:

    HTTP 409 Conflict

### 22.3 Role Code Stability

Role codes cannot be changed through the normal role update operation.

The role name and description may be updated without changing the role code.

### 22.4 Role Active State

Roles may be activated or deactivated through the dedicated status operation.

An inactive role must not grant permissions.

### 22.5 Role Administration Authorization

Role administration operations require the appropriate permission:

    role.view
    role.create
    role.update

The `role.delete` permission is defined in the permission catalog but role deletion is not currently exposed through the API.

### 22.6 Role Hierarchy

Roles do not currently form a hierarchy.

A role receives authorization through its associated permissions.

Role-to-permission assignment is managed separately from role administration.

### 22.7 Test Role Policy

TEST_ROLE and TEST_VIEWER are controlled development/test roles.

TEST_VIEWER is intentionally retained as an inactive role for authorization testing.

These test roles must not be treated as production business roles.

---

## 23. Role-Permission Administration Rules

### 23.1 Role-Permission Relationship

A role may have multiple permissions.

A permission may be assigned to multiple roles.

The relationship is maintained through the `role_permissions` entity.

### 23.2 Assignment Uniqueness

A Role-Permission combination must be unique.

The application prevents duplicate assignments and returns:

    HTTP 409 Conflict

### 23.3 Active Role Requirement

Permissions cannot be newly assigned to an inactive role.

### 23.4 Active Permission Requirement

Inactive permissions cannot be assigned to a role.

Inactive permissions must not grant authorization.

### 23.5 Permission Removal

An existing Role-Permission assignment may be removed through the controlled administration API.

Attempting to remove an assignment that does not exist returns:

    HTTP 404 Not Found

### 23.6 Authorization Behavior

A user's effective authorization is determined by the permissions associated with the user's active roles.

For example:

    TEST_ROLE
        ↓
    organization.view
        ↓
    GET /organizations/
        ↓
    Authorized

If the same role does not contain:

    organization.create

then:

    POST /organizations/
        ↓
    HTTP 403 Forbidden

### 23.7 Separation of Responsibilities

Role administration and User-Role administration remain separate concerns.

Role-Permission administration controls which permissions a role provides.

User-Role administration controls which roles are assigned to users and will be implemented as a separate security capability.

---

## 24. User-Role Administration Rules

### 24.1 User-Role Relationship

A user may have multiple roles.

A role may be assigned to multiple users.

The relationship is maintained through the `user_roles` entity.

### 24.2 Assignment Uniqueness

A user-role combination must be unique.

Duplicate assignments return:

    HTTP 409 Conflict

### 24.3 Active User Requirement

A role cannot be newly assigned to an inactive user.

### 24.4 Active Role Requirement

An inactive role cannot be newly assigned to a user.

### 24.5 Role Removal

An existing UserRole assignment may be removed through the controlled API.

Attempting to remove a nonexistent assignment returns:

    HTTP 404 Not Found

### 24.6 Authorization

Viewing a user's roles requires:

    user.view

Changing a user's roles requires:

    user.update

The authorization engine evaluates only active security relationships.

### 24.7 Effective Authorization

A user's effective authorization is derived from the active roles assigned to the user and the active permissions assigned to those roles.

The application therefore separates:

    User identity
    User-Role assignment
    Role definition
    Role-Permission assignment
    Permission definition

---

## 25. Account Lifecycle Security Rules (Sprint 12.1)

### 25.1 Failed Login and Lockout

Each wrong password for a known active, unlocked account increments
`failed_login_attempts`. At the configured threshold the account becomes
`LOCKED` until `locked_until`. A currently locked account must reject
authentication before checking the supplied password.

### 25.2 Inactive Accounts

An inactive user cannot authenticate. Unlocking clears lock state but must not
implicitly activate an inactive account.

### 25.3 Successful Authentication

A successful login resets `failed_login_attempts`, clears `locked_until`, and
updates `last_login`.

### 25.4 Controlled Security State

Viewing user security state requires `user.view`. Activation, deactivation, and
unlock require `user.update`. Generic `UserUpdate` must not accept
`account_status` or `is_active`; security state uses dedicated operations.

## 26. Security History Rules (Sprint 12.2)

### 26.1 Login History

Every login attempt creates a `LoginHistory` record containing the attempted
username, result, timestamp, failure category where applicable, known user ID,
IP address, and user agent when available.

### 26.2 Security Events

The event catalog is `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `ACCOUNT_LOCKED`,
`ACCOUNT_UNLOCKED`, `ACCOUNT_ACTIVATED`, and `ACCOUNT_DEACTIVATED`.
Administrative events record actor and target IDs.

### 26.3 Credential Exclusion

Audit data must never contain plaintext passwords, password hashes, JWTs,
authorization headers, client secrets, refresh tokens, or other credentials.
Credential-like keys are removed from event details.

### 26.4 Transaction Integrity

An account-state change and its audit records must be committed as one
transaction. Audit failure must not leave the security-state change committed.

### 26.5 History Authorization

Login-history and security-event APIs require `user.view`. Collection and
user-filtered endpoints use bounded `limit` and `offset` pagination.

## 27. Password Security Rules (Sprint 12.3)

### 27.1 Central Password Policy

User creation, self-service password change, and administrative reset must use
one configurable policy. By default a password requires at least 12 characters,
uppercase and lowercase letters, a digit, and a special character. Errors must
describe rules without echoing submitted credentials.

### 27.2 Self-Service Password Change

An authenticated user must provide the correct current password and matching new
password confirmation. The new password must satisfy policy and differ from the
current password. Success updates the hash and `password_changed_at`, clears
`force_password_change`, resets temporary login failure state, and records
`PASSWORD_CHANGED` with the user as actor and target.

### 27.3 Administrative Password Reset

Reset requires `user.update`. It sets a policy-compliant hash,
`password_changed_at`, and `force_password_change=true`; clears failed-login and
lock state; preserves active/inactive state; and records `PASSWORD_RESET` with
administrator actor and affected-user target IDs.

### 27.4 Forced Password Change

A forced-change user may authenticate, inspect `/auth/me`, and change the
password. Role- and permission-protected application access must return HTTP 403
until the required change is completed.

### 27.5 Credential and Token Rules

Plaintext passwords and hashes must never be logged or stored in audit details.
Existing JWTs are not revoked by password changes because revocation/session
versioning is not currently implemented.

## 28. Administrative Security Closure Rules (Sprint 12.4)

### 28.1 Usable ADMIN

A usable ADMIN requires an active user, an authentication-permitted account
status, an active ADMIN assignment, and an active ADMIN role. A forced password
change does not make the account unusable.

### 28.2 Final ADMIN Protection

User deactivation/deletion, ADMIN assignment removal, and ADMIN-role deactivation
must return HTTP 409 when the operation would leave no usable administrator. The
rejected operation must leave target state unchanged.

### 28.3 Serialization

ADMIN-removal checks must lock the shared ADMIN role row and retain that lock
through the mutation transaction so concurrent administrative changes cannot
independently pass a stale count.

### 28.4 Safety Audit

Rejected final-ADMIN operations create `ADMIN_SAFETY_BLOCKED` with actor and
target where available and a safe operation name only. Credentials, tokens, and
authorization headers are prohibited.

### 28.5 Recovery Policy

No public recovery or bootstrap API is permitted. Production must maintain at
least two usable ADMIN users. Emergency recovery uses separately controlled
database-operator access and must be followed by incident documentation and
normal authenticated password/security administration.

### 28.6 JWT Boundary

Access-token expiry is the current risk-control boundary after password mutation.
Token revocation and session versioning remain deferred rather than introducing
an incomplete session subsystem during Sprint 12 closure.

## 29. Organization Scope Rules (Sprint 13)

- Every scoped operation requires both its RBAC permission and an applicable
  active `UserRole.access_scope`.
- Scope levels are ORGANIZATION, BUSINESS_UNIT, DIVISION, DEPARTMENT, and SELF.
- No scope crosses the authenticated user's organization.
- Multiple roles combine only when they grant the same requested permission;
  the broadest qualifying scope is effective.
- Lists must filter in SQL. Direct UUID operations outside scope return 404.
- User create/update must validate Organization → Business Unit → Division →
  Department and Designation → Department consistency.
- Assignment scope cannot exceed the assigning user's effective `user.update`
  scope.
- Designation is not an authorization boundary.
- Role and permission catalogs remain global configuration operations.
