# LabGenius Security Model

## 1. Purpose

This document defines the authentication, authorization, role, permission, and access-control model used by the LabGenius platform.

The security model is designed around:

- JWT-based authentication
- Role-Based Access Control (RBAC)
- Permission-based API authorization
- Active/inactive security controls
- Explicit separation of authentication and authorization
- Centralized authorization dependencies
- Secure password hashing
- Least-privilege access

The security model is intended to provide a consistent foundation for all current and future LabGenius modules.

---

## 2. Security Architecture

LabGenius uses the following security flow:

    User
      |
      v
    Login
      |
      v
    Password Verification
      |
      v
    JWT Access Token
      |
      v
    Current User
      |
      v
    User Role Assignment
      |
      v
    Role
      |
      v
    Role Permission Assignment
      |
      v
    Permission
      |
      v
    Authorized API Operation

Authentication and authorization are deliberately separated.

Authentication establishes:

> Who is the user?

Authorization establishes:

> What is the user allowed to do?

---

## 3. Authentication

### 3.1 Login

The authentication endpoint is:

    POST /auth/login

The login process:

1. Receives username and password.
2. Locates the user.
3. Verifies the password hash.
4. Validates that the user can authenticate.
5. Generates a JWT access token.
6. Returns the access token to the client.

---

## 4. Password Security

LabGenius uses `pwdlib` for password hashing and verification.

Password handling is centralized in:

    app/auth/hashing.py

The application uses the recommended `pwdlib` password hashing configuration.

Passwords are never stored as plain text.

The database stores:

    password_hash

rather than the original password.

---

## 5. JWT Authentication

LabGenius uses JSON Web Tokens for API authentication.

The JWT configuration includes:

    Algorithm: HS256
    Access token expiration: 60 minutes

The JWT contains the authenticated user's identifier in the:

    sub

claim.

The token is validated before protected API operations are executed.

---

## 6. Current User Resolution

The authenticated user is resolved centrally through:

    app/auth/dependencies.py

The primary dependency is:

    get_current_user()

The process is:

1. Extract bearer token from the request.
2. Decode and validate the JWT.
3. Read the `sub` claim.
4. Convert the subject to the user's UUID.
5. Load the user together with the required role relationships.
6. Confirm that the user exists.
7. Confirm that the user is active.
8. Return the authenticated user.

Invalid or malformed authentication results in:

    HTTP 401 Unauthorized

---

## 7. Active User Security

An inactive user cannot access protected APIs using an existing JWT.

The authorization system explicitly checks:

    User.is_active

If the user is inactive, authentication is rejected.

This prevents a previously issued token from continuing to provide access after a user has been disabled.

---

## 8. Role-Based Access Control

LabGenius uses RBAC as the organizational structure for authorization.

The main entities are:

    users
    roles
    permissions
    user_roles
    role_permissions

The relationships are:

    User
      |
      +-- UserRole
              |
              +-- Role
                    |
                    +-- RolePermission
                              |
                              +-- Permission

A user does not receive permissions directly.

Permissions are granted through roles.

---

## 9. User-Role Assignment

The `user_roles` table associates users with roles.

A user can have multiple roles.

Each user-role assignment has its own active state.

The authorization engine requires:

    user_roles.is_active = true

An inactive user-role assignment does not grant any role-based access.

---

## 10. Role Security

Roles are stored in:

    roles

Each role has:

    role_code
    role_name
    description
    is_active

Only active roles can grant authorization.

The authorization engine therefore requires:

    role.is_active = true

---

## 11. Permission Security

Permissions are stored in:

    permissions

Each permission has:

    permission_code
    permission_name
    description
    is_active

Permissions represent specific application capabilities.

Examples:

    organization.view
    organization.create
    organization.update
    organization.delete

A permission must be active before it can authorize an operation.

---

## 12. Role-Permission Assignment

The `role_permissions` table connects roles to permissions.

Each assignment has its own active state.

The authorization engine requires:

    role_permissions.is_active = true

Therefore a permission can be disabled for a role without deleting either the role or the permission.

---

## 13. Authorization Decision Chain

A permission-based authorization request follows this sequence:

    User active?
        |
        +-- No --> 401 Unauthorized
        |
        +-- Yes
              |
              v
        UserRole active?
              |
              +-- No --> Continue searching other roles
              |
              +-- Yes
                    |
                    v
                Role active?
                    |
                    +-- No --> Continue searching
                    |
                    +-- Yes
                          |
                          v
                  RolePermission active?
                          |
                          +-- No --> Continue searching
                          |
                          +-- Yes
                                |
                                v
                       Permission active?
                                |
                                +-- No --> Continue searching
                                |
                                +-- Yes
                                      |
                                      v
                                  ALLOWED

If no valid permission path is found:

    HTTP 403 Forbidden

---

## 14. Central Authorization Functions

Authorization is centralized in:

    app/auth/dependencies.py

### 14.1 Role authorization

    require_role(role_code)

This dependency verifies that the authenticated user has the requested active role.

### 14.2 Permission authorization

    require_permission(permission_code)

This dependency verifies that the authenticated user has the requested active permission through:

    active user
        ->
    active user-role assignment
        ->
    active role
        ->
    active role-permission assignment
        ->
    active permission

Permission-based authorization is preferred for application APIs.

---

## 15. Permission Naming Strategy

LabGenius uses the following naming convention:

    <module>.<action>

Examples:

    organization.view
    organization.create
    organization.update
    organization.delete

This provides:

- consistent naming;
- easy identification of the affected module;
- clear separation of read and write operations;
- predictable permission checks;
- future scalability.

---

## 16. Initial Permission Catalog

The initial LabGenius permission catalog contains 24 permissions.

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

## 17. Initial ADMIN Role

The initial `ADMIN` role is the system administration role.

The seeded ADMIN role currently has all 24 initial permissions.

This provides full administrative access to the current identity and organizational foundation APIs.

The ADMIN role is not implemented as a hard-coded bypass.

Instead:

    ADMIN
       |
       +-- 24 explicit permissions
               |
               +-- API authorization

This is important because it allows future roles to receive selected permissions without requiring application-code changes.

---

## 18. Protected APIs

The following foundation APIs are protected by permissions.

### Organizations

    GET    /organizations/
        organization.view

    GET    /organizations/{organization_id}
        organization.view

    POST   /organizations/
        organization.create

    PUT    /organizations/{organization_id}
        organization.update

    DELETE /organizations/{organization_id}
        organization.delete

### Business Units

    GET    /business-units/
        business_unit.view

    GET    /business-units/organization/{organization_id}
        business_unit.view

    GET    /business-units/{business_unit_id}
        business_unit.view

    POST   /business-units/
        business_unit.create

    PUT    /business-units/{business_unit_id}
        business_unit.update

    DELETE /business-units/{business_unit_id}
        business_unit.delete

### Divisions

    GET    /divisions/
        division.view

    GET    /divisions/business-unit/{business_unit_id}
        division.view

    GET    /divisions/{division_id}
        division.view

    POST   /divisions/
        division.create

    PUT    /divisions/{division_id}
        division.update

    DELETE /divisions/{division_id}
        division.delete

### Departments

    GET    /departments/
        department.view

    GET    /departments/division/{division_id}
        department.view

    GET    /departments/{department_id}
        department.view

    POST   /departments/
        department.create

    PUT    /departments/{department_id}
        department.update

    DELETE /departments/{department_id}
        department.delete

### Designations

    GET    /designations/
        designation.view

    GET    /designations/department/{department_id}
        designation.view

    GET    /designations/{designation_id}
        designation.view

    POST   /designations/
        designation.create

    PUT    /designations/{designation_id}
        designation.update

    DELETE /designations/{designation_id}
        designation.delete

### Users

    GET    /users/
        user.view

    GET    /users/{user_id}
        user.view

    POST   /users/
        user.create

    PUT    /users/{user_id}
        user.update

    DELETE /users/{user_id}
        user.delete

---

## 19. Authentication Endpoints

Authentication endpoints remain separate from CRUD authorization.

    POST /auth/login
    GET  /auth/me

Additional controlled test endpoints were used during RBAC validation.

The authentication layer is implemented separately from the user administration router.

---

## 20. HTTP Security Responses

### 401 Unauthorized

Used when authentication cannot be established.

Examples:

- missing token;
- invalid token;
- malformed token;
- invalid JWT subject;
- nonexistent user;
- inactive user.

### 403 Forbidden

Used when the user is authenticated but lacks the required authorization.

Examples:

- missing role;
- inactive role;
- inactive user-role assignment;
- missing permission;
- inactive role-permission assignment;
- inactive permission.

---

## 21. Least Privilege

LabGenius follows the principle of least privilege.

Users should receive only the roles and permissions required for their responsibilities.

The ADMIN role is intended for administrative operations.

Future operational roles should receive selected permissions rather than inheriting administrative access.

---

## 22. Security Validation Performed

The RBAC implementation has been validated through:

### Authentication tests

- successful login;
- JWT generation;
- authenticated `/auth/me`;
- invalid authentication handling.

### ADMIN authorization tests

- protected API access;
- role authorization;
- permission authorization.

### Restricted-role tests

A temporary `LAB_USER` role was created with only five view permissions.

The following results were verified:

    LAB_USER -> organization.view
        200 OK

    LAB_USER -> organization.create
        403 Forbidden

    LAB_USER -> user.view
        403 Forbidden

This confirms that authorization is permission-driven.

### Active-state test

The temporary user's active role assignment was disabled.

Result:

    Protected API
        ->
    403 Forbidden

The assignment was then reactivated and access returned to:

    200 OK

This confirms that inactive role assignments do not grant access.

---

## 23. Security Design Principles

The LabGenius security model follows these principles:

1. Never store plain-text passwords.
2. Authenticate through JWT.
3. Centralize current-user resolution.
4. Centralize authorization dependencies.
5. Prefer permission-based authorization for APIs.
6. Do not hard-code ADMIN as a universal bypass.
7. Respect active/inactive state at every authorization layer.
8. Follow least privilege.
9. Keep authentication separate from business APIs.
10. Keep authorization logic outside business services.
11. Use explicit permission names.
12. Maintain auditable role and permission relationships.

---

## 24. Future Security Enhancements

The following capabilities are planned for later stages and are not part of the current RBAC foundation:

- refresh tokens;
- password change and reset;
- password policy enforcement;
- password reset;
- password expiration policies;
- session/device management;
- detailed security audit logging;
- organization-level authorization;
- row-level/tenant-level access control;
- field-level permissions where required;
- security event monitoring;
- rate limiting;
- MFA.

These should be implemented as separate controlled enhancements rather than complicating the current foundation.

---

## 24A. Permission Administration

LabGenius provides a controlled permission administration API.

The current permission administration endpoints are:

    GET /permissions/
    GET /permissions/active
    GET /permissions/{permission_id}
    PUT /permissions/{permission_id}/status

Permission administration is itself protected by explicit permissions:

    permission.view
    permission.update

The application does not currently allow arbitrary creation or deletion of permission definitions through the API.

The permission catalog is therefore treated as controlled application security configuration.

### Permission Catalog

The initial permission catalog contains 24 business permissions covering:

    organization
    business_unit
    division
    department
    designation
    user

Each module follows the standard:

    <module>.<action>

naming convention.

Two security-administration permissions were subsequently added:

    permission.view
    permission.update

The current catalog therefore contains:

    26 permissions

The ADMIN role receives all 26 permissions explicitly.

### Permission Active-State Enforcement

An inactive permission cannot grant authorization.

Authorization evaluates active state at every relevant level:

    User
        ->
    UserRole
        ->
    Role
        ->
    RolePermission
        ->
    Permission

An inactive element in this chain prevents authorization.

This allows permissions to be disabled without deleting their definitions or historical relationships.

### Permission Administration Security

Permission administration is protected through the same permission-based authorization mechanism used by the rest of the application.

A user with:

    permission.view

may view the permission catalog.

A user with:

    permission.update

may change the active state of a permission.

A restricted user without:

    permission.view

receives:

    403 Forbidden

when attempting to access the permission catalog.

This behavior was validated using a dedicated restricted test role.

## 25. Current Security Status

Authentication, foundational RBAC, permission-based authorization, and permission administration are implemented and validated.

Current status:

    JWT Authentication              COMPLETE
    Password Hashing                COMPLETE
    Current User Resolution         COMPLETE
    Role Authorization              COMPLETE
    Permission Authorization        COMPLETE
    Active-State Authorization      COMPLETE
    26 Application Permissions      COMPLETE
    ADMIN Role                      COMPLETE
    Foundation API Protection       COMPLETE
    Permission Administration       COMPLETE
    Restricted Role Validation      COMPLETE
    Negative Authorization Testing  COMPLETE

The LabGenius identity and authorization foundation is ready for the next development phase.

---

## 24B. Role Administration

LabGenius provides controlled administration of security roles.

The current role administration endpoints are:

    GET /roles/
    GET /roles/active
    GET /roles/{role_id}
    POST /roles/
    PUT /roles/{role_id}
    PUT /roles/{role_id}/status

Role administration is protected through explicit permissions.

The required permissions are:

    role.view
    role.create
    role.update
    role.delete

The current API implements role viewing, creation, update, and active-state management.

Role deletion is intentionally not exposed through the current API and remains a controlled/deferred operation.

### Active Role Enforcement

Only active roles may participate in authorization.

An authenticated user with an inactive role may successfully authenticate if the user account itself is active, but the inactive role must not grant role-based permissions.

Role administration therefore follows:

    Active User
        +
    Active UserRole
        +
    Active Role
        +
    Required Permission
        =
    Authorized Request

If any required authorization condition is not satisfied, the API returns HTTP 403 Forbidden.

### Role Code Stability

Role codes are security identifiers and are not editable through the normal role update API.

The role code is established when the role is created and remains stable during ordinary role administration.

### Role Administration Validation

Role creation prevents duplicate role codes and returns HTTP 409 Conflict when a duplicate role code is submitted.

Role active-state changes are performed through the dedicated status endpoint.

### Current Test Roles

The development/test environment contains controlled roles used for authorization validation:

    ADMIN
    TEST_ROLE
    TEST_VIEWER

TEST_VIEWER is retained as an inactive role for restricted-access testing.

---

## 24C. Role-Permission Administration

LabGenius provides controlled administration of the relationship between security roles and application permissions.

The current role-permission endpoints are:

    GET /roles/{role_id}/permissions
    POST /roles/{role_id}/permissions
    DELETE /roles/{role_id}/permissions/{permission_id}

### Role-Permission Authorization

Role-permission administration requires:

    role.view
    role.update

Viewing the permissions assigned to a role requires `role.view`.

Assigning or removing a permission from a role requires `role.update`.

### Assignment Rules

A permission may be assigned to a role only when:

    the role exists;
    the role is active;
    the permission exists;
    the permission is active.

Duplicate role-permission assignments are rejected with HTTP 409 Conflict.

### Active-State Enforcement

Inactive roles cannot receive new permission assignments.

Inactive permissions cannot be assigned to roles.

An inactive permission must not grant authorization even if a historical RolePermission record exists.

### Permission-Driven Authorization

Authorization is evaluated through the following relationship:

    User
        ↓
    UserRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission

A protected operation is authorized only when the authenticated user's active role provides the required active permission.

### Validation

The Role-Permission implementation has been validated for:

- permission listing by role;
- permission assignment;
- duplicate assignment prevention;
- permission removal;
- permission-based authorization;
- unauthorized operation rejection with HTTP 403 Forbidden.

The authorization model therefore separates authentication, role membership, permission assignment, and endpoint authorization.

---

## 24D. User-Role Administration

LabGenius provides controlled application-level administration of User-Role assignments.

The current User-Role endpoints are:

    GET /users/{user_id}/roles
    POST /users/{user_id}/roles
    DELETE /users/{user_id}/roles/{role_id}

### User-Role Authorization

Viewing roles assigned to a user requires:

    user.view

Assigning or removing roles requires:

    user.update

### Assignment Rules

A role may be assigned to a user only when:

    the user exists;
    the user is active;
    the role exists;
    the role is active.

Duplicate User-Role assignments are rejected with HTTP 409 Conflict.

### Authorization Impact

A user's effective permissions are determined through active UserRole assignments.

The complete authorization chain is:

    User
        ↓
    UserRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission

Inactive UserRole, Role, RolePermission, or Permission records must not contribute to authorization.

### Validation

User-Role administration has been validated for:

- role listing by user;
- role assignment;
- duplicate assignment prevention;
- inactive-user protection;
- inactive-role protection;
- role removal;
- nonexistent assignment handling;
- permission-based authorization;
- unauthorized operation rejection with HTTP 403 Forbidden.

Authentication and authorization were separately validated using a restricted TEST_VIEWER account.

---

## 24E. Account Lifecycle and Authentication Security (Sprint 12.1)

Sprint 12.1 is complete. User account security state is managed through dedicated
security operations rather than the generic user update API.

Authentication enforces a configurable failed-login threshold and lockout
duration. A wrong password increments `failed_login_attempts`; reaching the
threshold sets `account_status` to `LOCKED` and records `locked_until`. A locked
account is rejected before password verification, including when the supplied
password is correct. Inactive accounts are also rejected before verification.

A successful login clears the failure counter and lock timestamp and updates
`last_login`. Existing user security fields use naive UTC because the current
PostgreSQL columns are `timestamp without time zone`.

Dedicated operations are available at:

    GET /users/{user_id}/security       user.view
    PUT /users/{user_id}/activate       user.update
    PUT /users/{user_id}/deactivate     user.update
    PUT /users/{user_id}/unlock         user.update

Unlock clears lock state but does not implicitly reactivate an inactive account.
Activation and deactivation remain distinct administrative actions.
`account_status` and `is_active` are excluded from `UserUpdate` so generic
profile updates cannot change account security state.

## 24F. Login History and Security Events (Sprint 12.2)

Sprint 12.2 is complete. Authentication attempts are persisted in the
append-only `login_history` table with the known user ID, attempted username,
result, failure category, timezone-aware timestamp, request IP address, and user
agent when available.

The append-only `security_events` table supports these implemented event types:

    LOGIN_SUCCESS
    LOGIN_FAILURE
    ACCOUNT_LOCKED
    ACCOUNT_UNLOCKED
    ACCOUNT_ACTIVATED
    ACCOUNT_DEACTIVATED

Security events support actor and target user IDs. Login failures have no actor
because possession of a username does not establish identity. Administrative
operations record the authenticated administrator as actor and the affected
account as target.

Account-state changes and associated audit records share one commit boundary.
Low-level Sprint 12 repositories flush changes but do not independently commit.

Audit models contain no password, password hash, JWT, authorization-header,
client-secret, or token fields. Authentication never passes credentials to the
audit layer, and credential-like keys are removed recursively from event details.

Security history APIs are:

    GET /security/login-history
    GET /security/login-history/{user_id}
    GET /security/events
    GET /security/events/{user_id}

All require `user.view` and support bounded `limit`/`offset` pagination.
Migration `b7219de4a612` creates both audit tables, foreign keys, and indexes.

## 24G. Password Security (Sprint 12.3)

Sprint 12.3 is complete. Password validation is centralized in `PasswordPolicy`
and configured through application settings. The default policy requires at
least 12 characters, one uppercase letter, one lowercase letter, one digit, and
one special character. Validation errors state unmet rules without repeating the
submitted password.

Authenticated users change their own password through:

    POST /auth/change-password

The operation verifies the current password, requires matching new-password
confirmation, rejects reuse of the current password, hashes the new password,
updates `password_changed_at`, clears `force_password_change`, and resets
temporary failure/lock state. It records `PASSWORD_CHANGED` with the same actor
and target user ID.

Administrative password reset is available through:

    POST /users/{user_id}/reset-password    user.update

Reset validates and hashes the supplied password, updates
`password_changed_at`, sets `force_password_change=true`, and clears failure and
lock state without activating an inactive account. It records `PASSWORD_RESET`
with administrator actor and affected-user target IDs. Passwords are never
emailed, generated as defaults, or included in event details.

A user marked `force_password_change=true` may authenticate and receive a JWT,
access `/auth/me`, and call `/auth/change-password`. Role- and permission-guarded
application endpoints return HTTP 403 until the password is changed. This keeps
Swagger OAuth2 login functional while enforcing the required change.

New user creation applies the same centralized policy, initializes
`password_changed_at`, stores only a hash, and intentionally begins with
`force_password_change=true`.

Existing JWTs remain valid after password change/reset because token revocation
and session-version infrastructure do not yet exist. This limitation is explicit;
Sprint 12.3 does not invent a partial revocation mechanism.

At the v0.14.0 database review, both active users, including the sole ADMIN, were
already marked for forced password change. On rollout they can still authenticate,
but must use `/auth/change-password` before resuming permission-protected work.

## 24H. Administrative Security Operations (Sprint 12.4)

Sprint 12.4 is complete. LabGenius protects the final usable ADMIN from
administrative removal. A usable ADMIN is an active user whose account status
permits authentication, with an active UserRole assignment to the active `ADMIN`
role. `force_password_change` does not make an administrator unusable because the
user can authenticate and complete the required change.

The centralized `AdminSafetyService` guards:

- user deactivation;
- hard user deletion;
- removal of an ADMIN UserRole assignment; and
- deactivation of the ADMIN role.

The guard locks the shared ADMIN role row in PostgreSQL before calculating usable
administrators. Concurrent guarded changes therefore serialize through the same
row. An operation that would leave zero usable administrators returns HTTP 409,
does not mutate the target, and records one `ADMIN_SAFETY_BLOCKED` event with
actor/target IDs where applicable and only the safe operation category.

Normal failed-password lockout remains possible for an ADMIN. Production should
maintain at least two usable administrators. Emergency recovery is an operator-
controlled database procedure using separately governed database access; there
is no public bootstrap API, hard-coded account, credential, ADMIN ID, or backdoor.
After recovery, operators must document the incident and restore normal password
and audit controls through authenticated application workflows.

JWT behavior remains intentionally unchanged. Already-issued access tokens remain
valid until their configured expiry (currently 60 minutes) after password change
or reset. A token-version or revocation subsystem is deferred because it would be
a larger session-management capability, not a low-risk Sprint 12 closure change.

Security-history APIs remain `user.view` protected, newest-first, and bounded to
1–500 records per request. No advanced Sprint 14 reporting/filtering was added.

With Sprint 12.1–12.4 complete, User Administration & Security Operations is
ready for closure. Sprint 13 Organization-Level Authorization is next.

## 24I. Organization-Level Authorization (Sprint 13)

### Instrument Registry scope

Instrument API authorization requires both the operation-specific `instrument.*`
permission and the organization's enabled `INSTRUMENTS` capability. Instrument
lists are filtered in SQL, and inaccessible direct UUIDs are concealed with 404.
`SELF` has one explicit meaning for Instruments: `responsible_user_id` equals the
authenticated user ID. It does not mean created-by or department membership, and
an unassigned Instrument is not visible through SELF alone. SELF cannot authorize
creation or hierarchy reassignment by itself.

Sprint 13 is complete. Data scope is stored per `UserRole`, allowing the same
role to have different reach for different users without making role definitions
organization-specific. Supported levels are `ORGANIZATION`, `BUSINESS_UNIT`,
`DIVISION`, `DEPARTMENT`, and `SELF`.

RBAC determines what operation is allowed; scope determines which records the
permission applies to. Scope is resolved per permission using only active role
assignments whose active role and active permission mapping grant that permission.
When multiple qualifying assignments exist, the broadest scope wins. An unrelated
role cannot broaden another permission.

All scopes remain anchored to the authenticated user's own organization and
hierarchy IDs. User lists are filtered in SQL, while direct lookup/mutation uses
the same centralized `OrganizationScopeService` and returns 404 outside scope.
User create/update hierarchy chains are centrally validated.

Designation remains a job/workflow attribute and must belong to the selected
department, but it is not a data-access boundary. Role and permission catalogs
remain global security configuration; user administration, user security, and
user-role assignment are scope protected.

Migration `d40a6c87e913` adds constrained `user_roles.access_scope`, defaults
existing non-ADMIN assignments to `SELF`, and backfills ADMIN assignments to
`ORGANIZATION`.

## 24J. Application Audit Foundation (Sprint 14)

`LoginHistory`, `SecurityEvent`, and `AuditEvent` remain separate. Login history
records authentication attempts; security events record account/security activity;
audit events record successful application and administrative changes. A lifecycle
operation may create both a security event and an audit event.

`AuditEvent` is append-only and does not inherit mutable `MasterEntity` fields such
as `is_active`, `version`, or `updated_at`. No mutation/delete API is exposed. Target
`entity_id` has no polymorphic FK, so history survives target deletion. Nullable actor
and hierarchy FKs use `ON DELETE SET NULL`.

Every HTTP request receives a server-generated UUID returned as `X-Request-ID`;
untrusted inbound values are ignored. Direct `Request.client.host` is captured as the
baseline source IP. Proxy-aware attribution is a deployment concern and forwarded-for
headers are not trusted.

The `audit.view` permission and its assignment scope are both required. Organization,
BU, division, and department scopes filter ownership in SQL. SELF is conservative:
only events performed by that actor are visible. Global/unowned events are hidden by
normal scopes. Direct UUID lookup uses the same scope and returns 404 on denial.

Sanitization is shared by application and security auditing and recursively removes
password, token, JWT, authorization, API-key, secret, database-password, and credential
keys. Current JWTs still remain valid until expiry because revocation is not implemented.

## 24K. Frontend Authentication and Authorization (Sprint 15)

React authenticates through `/auth/login`, centrally stores the stateless bearer JWT in
`localStorage`, and restores `/auth/me`. This is not equivalent to an HttpOnly cookie;
XSS hardening and a future session/refresh architecture remain relevant.

Protected routes wait for restoration. Forced-password users remain in the password
workflow until refreshed backend state confirms clearance. Effective permissions control
UI visibility only; FastAPI RBAC and organization scope remain the security boundary.
401 clears invalid auth, 403 preserves the session. Administration uses dedicated user
security endpoints, selectively refreshes authorization, and keeps audit history read-only.

## 24L. Future Business-Domain Authorization

Business domains reuse the existing JWT authentication, permission-based RBAC,
`OrganizationScopeService`, direct-ID concealment, and `AuditService`. Organization-owned
roots carry the ownership needed for scope filtering; child access normally resolves
through a scoped parent rather than duplicating hierarchy columns.

Business permissions will follow the existing `<domain>.<action>` direction and will be
introduced incrementally during their implementation sprints. This blueprint documentation
does not create or claim any Sprint 16+ permission codes. Domain-specific SELF behavior
must be explicit; QC analyst SELF means actively assigned work.

## 24M. Future Optional-Module Authorization

Organization module enablement does not replace RBAC, and RBAC does not represent module
licensing or enablement. Module configuration is a third, separate concern.

Future optional-module APIs require both the organization's enabled capability and the
authenticated user's applicable active permission and organization scope. Backend APIs
must enforce these conditions independently. Frontend navigation may combine capability
enablement with effective permissions for usability, but frontend visibility is not a
security control.

Sprint 16D implements a server-authoritative capability guard. Future optional-domain
routes compose `require_capability(<code>)` with their existing permission dependency;
both checks must pass. A disabled or inactive capability returns 403 without granting or
altering RBAC. Existing authentication, Administration, and shared-master routes remain
backward-compatible and are not retrofitted with optional capability guards.

`module.view` permits inspection of the global system registry and the authenticated
organization's state. `module.manage` permits enable/disable mutations only for that
same server-derived organization. PLATFORM and CORE_LAB are mandatory and implicitly
enabled. Optional capabilities default disabled until assigned.
