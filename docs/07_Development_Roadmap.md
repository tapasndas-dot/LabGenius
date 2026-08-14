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

### Planned Work

#### 11.1 — Permission APIs

- Permission repository
- Permission service
- Permission response schemas
- Permission list API
- Permission detail API
- Permission filtering
- Permission active-state management

#### 11.2 — Role APIs

- Role repository
- Role service
- Role schemas
- Role CRUD APIs
- Role validation
- Role active-state management

#### 11.3 — Role-Permission Management

- Assign permission to role
- Remove permission from role
- List role permissions
- Validate duplicate mappings
- Validate inactive permissions
- Role permission administration

#### 11.4 — User-Role Management

- Assign role to user
- Remove role from user
- List user roles
- Validate duplicate assignments
- Active/inactive assignment management

---

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

Current release:

    v0.8.0

Next release:

    v0.9.0

Planned release focus:

    Permission-Based RBAC & Foundation API Security

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