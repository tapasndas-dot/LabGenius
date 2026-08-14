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
- login history;
- account lockout workflow;
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
