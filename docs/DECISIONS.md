# Decision Records

## ADR-010 — Permission-Based RBAC for API Authorization

**Status:** Accepted

**Date:** 2026-08-14

### Context

LabGenius requires controlled access to application APIs based on the responsibilities of individual users.

A simple role-name check such as:

    ADMIN

is insufficient for long-term scalability because it couples application behavior directly to specific role names.

The platform requires the ability to create future roles with different combinations of capabilities.

### Decision

LabGenius will use permission-based authorization for protected APIs.

The authorization relationship is:

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

API endpoints will declare the required permission using a centralized dependency:

    require_permission("<module>.<action>")

### Permission Naming

Permissions use:

    <module>.<action>

Examples:

    organization.view
    organization.create
    organization.update
    organization.delete

### Consequences

Positive:

- Fine-grained authorization.
- Clear API security requirements.
- Future roles can be configured without code changes.
- Reduced coupling between business logic and role names.
- Easier auditing of access rights.
- Supports least-privilege design.

Trade-off:

- Additional role and permission configuration is required.
- Authorization depends on multiple related database entities.

---

## ADR-011 — Centralized Authorization Dependencies

**Status:** Accepted

**Date:** 2026-08-14

### Context

Authentication and authorization logic must remain consistent across all LabGenius APIs.

Duplicating authorization checks inside individual routers or services would create maintenance and security risks.

### Decision

Authentication and authorization will be centralized in:

    app/auth/dependencies.py

The primary dependencies are:

    get_current_user()
    require_role()
    require_permission()

Routers declare their required permission through FastAPI dependencies.

Business services remain responsible for business operations rather than authentication or authorization.

### Consequences

- Consistent authorization behavior.
- Reduced duplication.
- Easier security testing.
- Clear separation of concerns.
- New protected APIs can adopt the same authorization pattern.

---

## ADR-012 — Active-State Enforcement in Authorization

**Status:** Accepted

**Date:** 2026-08-14

### Context

The identity and authorization model includes active/inactive states.

Simply checking whether a relationship exists is insufficient because an administrator may need to disable a user, role, or permission without deleting the associated records.

### Decision

Authorization must verify active state at every relevant level:

    User
    UserRole
    Role
    RolePermission
    Permission

An inactive element cannot grant authorization.

### Consequences

Access can be revoked by changing active state without deleting historical or configuration records.

This also supports future audit and lifecycle-management requirements.

---

## ADR-013 — ADMIN Role Uses Explicit Permissions

**Status:** Accepted

**Date:** 2026-08-14

### Context

The initial LabGenius system requires an administrative role with broad access.

A hard-coded rule such as:

    if role == "ADMIN":
        allow

would make future permission management difficult.

### Decision

The ADMIN role is granted the initial 24 permissions explicitly.

ADMIN therefore receives broad access through the same permission mechanism used by all other roles.

### Consequences

- Consistent authorization model.
- No special application-code bypass for ADMIN.
- Future roles can receive selected permissions.
- Permission assignments remain visible and manageable as data.

---

## ADR-014 — Permission Naming Convention

**Status:** Accepted

**Date:** 2026-08-14

### Decision

LabGenius permissions will use:

    <module>.<action>

The initial action set is:

    view
    create
    update
    delete

The initial module set includes:

    organization
    business_unit
    division
    department
    designation
    user

### Consequences

Permission names remain predictable and scalable as new modules are introduced.

---

## ADR-015 — Controlled Permission Administration

**Status:** Accepted

**Date:** 2026-08-15

### Context

The LabGenius platform requires a controlled mechanism for viewing and managing the application permission catalog.

Permissions are security configuration and should not be treated as ordinary business data.

The initial permission catalog contained 24 business permissions.

Permission administration also requires authorization of its own APIs.

### Decision

LabGenius will expose a controlled Permission Administration API.

The current endpoints are:

    GET /permissions/
    GET /permissions/active
    GET /permissions/{permission_id}
    PUT /permissions/{permission_id}/status

Permission administration is protected by two explicit permissions:

    permission.view
    permission.update

The permission catalog therefore contains 26 permissions.

The API does not currently support arbitrary creation or deletion of permission definitions.

Permissions may instead be activated or deactivated.

### Authorization Rule

An inactive permission cannot grant authorization.

Authorization must verify active state across:

    User
    UserRole
    Role
    RolePermission
    Permission

An inactive element in this chain prevents access.

### Consequences

- Permission configuration remains controlled.
- Security administration follows the same permission-based authorization model as business APIs.
- Permissions can be disabled without deleting configuration records.
- ADMIN access remains permission-driven rather than hard-coded.
- The permission catalog can evolve without introducing arbitrary runtime permission creation.
- Future security administration capabilities can be added under explicit permissions.

---

## Decision: Controlled Role Administration

### Decision

LabGenius will provide application-level administration of security roles rather than relying on direct database administration.

### Rationale

Application-level administration provides:

- controlled validation;
- consistent authorization;
- auditability;
- stable role identifiers;
- separation between security configuration and database administration.

### Role Code Policy

Role codes are treated as stable security identifiers and cannot be modified through normal role updates.

### Role Deletion Policy

Role deletion is intentionally deferred.

Roles may instead be deactivated so that historical relationships and security configuration are preserved.

### Active-State Policy

Only active roles may participate in authorization.

An inactive role must not grant permissions even when the associated user account and UserRole relationship remain active.

### Consequence

Role administration is implemented as a controlled security-management capability and remains separate from business-domain authorization.