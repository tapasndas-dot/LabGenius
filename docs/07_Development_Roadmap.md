# LabGenius Development Roadmap

## Project Status

LabGenius has completed the foundational architecture, organizational hierarchy, identity management, authentication, and permission-based RBAC foundation.

---

# Completed Sprints

## Sprint 1 — Project Foundation

### Status
Completed

### Completed
- Initial project structure
- Backend application foundation
- Database connectivity
- SQLAlchemy foundation
- Alembic migration framework
- Environment/configuration foundation
- Git repository foundation

---

## Sprint 2 — Entity Foundation

### Status
Completed

### Completed
- Base model architecture
- UUID primary-key strategy
- Timestamp management
- Active/inactive state
- Versioning foundation
- Reusable SQLAlchemy mixins
- Entity inheritance hierarchy

---

## Sprint 3 — Organization Foundation

### Status
Completed

### Completed
- Organization model
- Organization migration
- Organization repository/service/API foundation
- Organization CRUD operations

---

## Sprint 4 — Business Unit

### Status
Completed

### Completed
- Business Unit model
- Organization → Business Unit relationship
- Business Unit migration
- Business Unit CRUD APIs
- Organization-based Business Unit retrieval

---

## Sprint 5 — Division

### Status
Completed

### Completed
- Division model
- Business Unit → Division relationship
- Division migration
- Division CRUD APIs
- Business Unit-based Division retrieval

---

## Sprint 6 — Department & Designation

### Status
Completed

### Completed
- Department model
- Division → Department relationship
- Designation model
- Department → Designation relationship
- Department CRUD APIs
- Designation CRUD APIs
- Hierarchical retrieval APIs

---

## Sprint 7 — Identity Schema

### Status
Completed

### Completed
- User model
- User organizational relationships
- Employee code
- Username
- Email
- Password hash
- User status
- Login security fields
- User-role relationship foundation
- Role model
- Permission model
- Role-permission relationship
- Alembic migrations

---

## Sprint 8 — Identity Management

### Status
Completed

### Completed
- User repository
- User service
- User CRUD APIs
- Duplicate validation
- Organizational hierarchy validation
- Secure password hashing
- User validation
- Identity management foundation
- Database migration refinement
- Repository architecture

---

## Sprint 9 — Authentication & RBAC Foundation

### Status
Completed

### Completed
- JWT authentication
- JWT access-token generation
- JWT validation
- Current-user dependency
- `/auth/login`
- `/auth/me`
- Role authorization
- `require_role()`
- ADMIN role
- Authentication security handling
- OAuth2 bearer authentication in Swagger
- Active-user authentication enforcement

---

## Sprint 10 — Permission-Based Authorization

### Status
Completed

### Sprint 10.1 — Permission Engine

### Completed
- `require_permission()`
- Permission lookup through active roles
- Role-permission validation
- Active user validation
- Active user-role validation
- Active role validation
- Active role-permission validation
- Active permission validation

---

### Sprint 10.2 — Permission Catalog

### Completed
- Standard permission naming strategy
- `<module>.<action>` convention
- Initial permission catalog
- 24 standard permissions
- ADMIN → permission mappings
- Permission seed script
- Idempotent permission seeding

---

### Sprint 10.3 — Secure Existing Modules

### Completed

#### Organization
- `organization.view`
- `organization.create`
- `organization.update`
- `organization.delete`

#### Business Unit
- `business_unit.view`
- `business_unit.create`
- `business_unit.update`
- `business_unit.delete`

#### Division
- `division.view`
- `division.create`
- `division.update`
- `division.delete`

#### Department
- `department.view`
- `department.create`
- `department.update`
- `department.delete`

#### Designation
- `designation.view`
- `designation.create`
- `designation.update`
- `designation.delete`

#### User
- `user.view`
- `user.create`
- `user.update`
- `user.delete`

---

### Sprint 10.4 — RBAC Validation

### Completed
- ADMIN authorization testing
- Restricted-role testing
- LAB_USER temporary role
- Permission-granted API testing
- Missing-permission testing
- 403 authorization testing
- Active/inactive user-role testing
- Final foundation API regression testing
- Cleanup of temporary RBAC test data

---

# Current Architecture Status

The current security flow is:

    User
      |
      v
    JWT Authentication
      |
      v
    Active User
      |
      v
    User Role Assignment
      |
      v
    Active Role
      |
      v
    Role Permission Assignment
      |
      v
    Active Permission
      |
      v
    Protected API

The current permission model is:

    <module>.<action>

Example:

    organization.view
    organization.create
    organization.update
    organization.delete

---

# Next Development Phase

## Sprint 11 — Permission & Role Administration

### Objective

Build application-level management of roles and permissions rather than relying on direct database administration.

# Sprint 11.1 — Permission Administration

## Status

    COMPLETE

## Completed Work

### Permission Catalog

- Expanded permission catalog from 24 to 26 permissions.
- Added `permission.view`.
- Added `permission.update`.
- Updated ADMIN mappings to include all 26 permissions.

### Permission Administration API

Implemented:

    GET /permissions/
    GET /permissions/active
    GET /permissions/{permission_id}
    PUT /permissions/{permission_id}/status

### Authorization

- Permission administration APIs are protected by explicit permissions.
- Active-state enforcement was extended to permissions.
- Inactive permissions cannot grant authorization.
- Active-state enforcement applies across User, UserRole, Role, RolePermission, and Permission.

### Validation

- ADMIN permission access validated.
- Permission status update validated.
- Inactive permission authorization rejection validated.
- Restricted user authentication validated.
- Restricted user permission denial validated with HTTP 403.

### Architecture

Implemented layers:

    PermissionRepository
        ↓
    PermissionService
        ↓
    PermissionRouter
        ↓
    Permission Administration API

## Sprint 11.1 Exit Criteria

    Permission catalog available             COMPLETE
    Permission administration API            COMPLETE
    Permission active-state control          COMPLETE
    Authorization enforcement                COMPLETE
    Restricted-user test                     COMPLETE
    Regression testing                       COMPLETE
    Documentation                            COMPLETE
    Git commit                                PENDING
    Git tag v0.10.0                           PENDING

---

## Sprint 11.2 — Role Administration

# Sprint 11.2 — Role Administration

## Status

    COMPLETE

## Completed Work

### Role Repository

Implemented:

- Role lookup by ID.
- Role lookup by role code.
- Active role retrieval.
- Ordered role catalog retrieval.
- Role retrieval for administration.

### Role Schemas

Implemented:

- Role response schema.
- Role creation schema.
- Role update schema.
- Role active-status update schema.

### Role Administration API

Implemented:

    GET /roles/
    GET /roles/active
    GET /roles/{role_id}
    POST /roles/
    PUT /roles/{role_id}
    PUT /roles/{role_id}/status

### Authorization

Role administration is protected through:

    role.view
    role.create
    role.update

The role.delete permission is present in the permission catalog but role deletion remains deferred.

### Validation

Validated:

- ADMIN can view roles.
- ADMIN can create roles.
- Duplicate role codes are rejected with HTTP 409.
- ADMIN can update roles.
- ADMIN can activate/deactivate roles.
- Inactive roles are excluded from the active-role catalog.
- Authenticated users without role administration permission receive HTTP 403.
- Users associated with inactive roles cannot obtain role administration authorization.

### Test Roles

Retained:

    ADMIN
    TEST_ROLE
    TEST_VIEWER

TEST_VIEWER remains inactive for future authorization testing.

---

# Sprint 11.3 — Role ↔ Permission Administration

## Status

    COMPLETE

## Completed Work

### Role-Permission Repository

Implemented:

- Role-permission lookup.
- Permission assignments by role.
- Permission assignments by permission.
- Role-permission removal.
- Duplicate assignment detection.

### Role-Permission Schemas

Implemented:

- Role-permission assignment request.
- Role-permission response.

### Role-Permission Service

Implemented:

- Role existence validation.
- Permission existence validation.
- Active role validation.
- Active permission validation.
- Duplicate assignment protection.
- Assignment creation.
- Assignment removal.

### Role-Permission API

Implemented:

    GET /roles/{role_id}/permissions
    POST /roles/{role_id}/permissions
    DELETE /roles/{role_id}/permissions/{permission_id}

### Authorization

Implemented:

    role.view
    role.update

Role-permission administration is protected through the existing permission-based authorization engine.

### Validation

Validated:

- ADMIN can view role permissions.
- ADMIN can assign permissions.
- Duplicate assignments return HTTP 409.
- Assigned permissions are persisted.
- Assigned permissions affect endpoint authorization.
- Unauthorized operations return HTTP 403.
- Permissions can be removed.
- Removed permissions no longer provide authorization.
- Inactive roles and permissions are prevented from participating in new assignments.

### End-to-End Authorization Validation

Validated the complete chain:

    User
        ↓
    UserRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission
        ↓
    Protected API

A controlled TEST_ROLE assignment of `organization.view` successfully allowed organization viewing while an operation requiring `organization.create` remained unauthorized.

---

# Sprint 11.4 — User ↔ Role Administration

## Status

    COMPLETE

## Completed Work

### User-Role Repository

Implemented:

- User-role lookup.
- User-role assignment lookup.
- Active UserRole lookup.
- User-role removal.

### User-Role Schemas

Implemented:

- User-role assignment request.
- User-role response.

### User-Role Service

Implemented:

- User existence validation.
- Active-user validation.
- Role existence validation.
- Active-role validation.
- Duplicate assignment protection.
- Assignment creation.
- Assignment removal.

### User-Role API

Implemented:

    GET /users/{user_id}/roles
    POST /users/{user_id}/roles
    DELETE /users/{user_id}/roles/{role_id}

### Authorization

Implemented:

    user.view
    user.update

User-Role administration is protected by the existing permission-based authorization engine.

### Validation

Validated:

- Role listing for a user.
- Role assignment.
- Duplicate assignment returns HTTP 409.
- Inactive-user assignment is rejected.
- Inactive-role assignment is rejected.
- Role removal.
- Nonexistent assignment returns HTTP 404.
- Unauthorized role viewing returns HTTP 403.
- Unauthorized role modification returns HTTP 403.

### End-to-End Security Validation

Validated the complete chain:

    User
        ↓
    UserRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission
        ↓
    Protected API

A restricted TEST_VIEWER user successfully authenticated but was denied User-Role administration because the required permissions were absent.

---

# Next Phase — Business Application Foundation

The core identity and authorization foundation is now complete.

Completed security foundation:

    Authentication                  COMPLETE
    User foundation                 COMPLETE
    Role administration             COMPLETE
    Permission administration       COMPLETE
    Role-Permission administration  COMPLETE
    User-Role administration        COMPLETE

The next development phase should transition from generic security infrastructure toward LabGenius application business capabilities.

Candidate next areas will be evaluated against the Project Vision, domain architecture, and business requirements before implementation.

# Sprint 12 — User Administration & Security Operations

### Planned Work

- User administration improvements
- Account activation/deactivation
- Account lockout workflow
- Failed-login handling
- Login history
- Password change
- Password reset
- Password policy
- Security event logging
- Administrative security operations

---

# Sprint 13 — Organization-Level Authorization

### Planned Work

- Organization-scoped access
- Business Unit-scoped access
- Division-scoped access
- Department-scoped access
- Designation-scoped access
- Organizational data isolation
- Multi-organization authorization rules

---

# Sprint 14 — Audit & Compliance Foundation

### Planned Work

- Audit logging
- Security event logging
- User activity tracking
- Role/permission change history
- Data change history
- Administrative action history
- Compliance reporting foundation

---

# Sprint 15 — Frontend Foundation

### Planned Work

- React application foundation
- Authentication integration
- JWT handling
- Protected routes
- Permission-aware navigation
- Dynamic menu visibility
- Permission-aware action buttons
- User/role administration UI
- Organization hierarchy UI

---

# Sprint 16 — Business Modules

### Planned Work

- Asset Management
- Calibration Management
- Service Management
- Stability Management
- Laboratory workflows
- Customer management
- Field-service workflows

---

# Future Security Enhancements

The following capabilities remain future enhancements:

- Refresh tokens
- MFA
- Device/session management
- Rate limiting
- Password expiration
- Advanced password policies
- Security monitoring
- Advanced audit trails
- Segregation of duties
- Field-level authorization
- Row-level security
- Tenant isolation

---

# Release Milestones

Completed releases:

    v0.7.0
    OAuth2 JWT Authentication

    v0.8.0
    Role-Based Access Control

    v0.9.0
    Permission-Based RBAC Foundation

Current completed milestone:

    Sprint 11.1
    Permission Administration

Next release:

    v0.10.0

Release focus:

    Permission Administration API

Next development milestone:

    Sprint 11.2
    Role Administration

Completed Sprint 11.1 capabilities:

    Permission catalog
    Permission view API
    Active permission API
    Individual permission retrieval
    Permission active-state management
    permission.view
    permission.update
    Active-state authorization enforcement
    Restricted-user authorization validation

Future releases will be tagged according to completed development milestones.

---

# Development Principle

Each sprint should follow:

    Design
      ↓
    Implement
      ↓
    Validate
      ↓
    Regression Test
      ↓
    Document
      ↓
    Git Commit
      ↓
    Git Tag
      ↓
    Push

No sprint should be considered complete until the implemented functionality has been tested and documented.