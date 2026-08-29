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
---

## Decision: Role-Permission Administration

### Decision

LabGenius will manage the relationship between roles and permissions through controlled application-level APIs.

### Rationale

The application must be able to determine and administer effective authorization without requiring direct database manipulation.

Application-level management provides:

- validation;
- authorization;
- duplicate protection;
- active-state enforcement;
- consistent API behavior.

### Active-State Policy

Only active roles and active permissions may participate in new Role-Permission assignments.

Historical assignments remain represented by the relationship model but inactive security entities must not grant authorization.

### Authorization Policy

Role-Permission administration is itself protected through permissions:

    role.view
    role.update

This maintains a consistent permission-based security model.

### User-Role Separation

Role-Permission management is intentionally separated from User-Role management.

Role-Permission answers:

    What can a role do?

User-Role management answers:

    Which roles does a user have?

These capabilities will be implemented independently.

### Consequence

The LabGenius security foundation now supports effective permission-based authorization from the authenticated user through role membership and permission assignment to protected API operations.

---

## Decision: User-Role Administration

### Decision

LabGenius will manage User-Role assignments through controlled application-level APIs.

### Rationale

User-role relationships directly determine a user's effective authorization and therefore must not depend on direct database administration.

Application-level management provides:

- validation;
- authorization;
- duplicate protection;
- active-state enforcement;
- consistent API behavior.

### Authorization Policy

User-Role administration uses the existing user permissions:

    user.view
    user.update

No separate UserRole permission family is introduced.

### Active-State Policy

Only active users and active roles may participate in new UserRole assignments.

Inactive UserRole records do not contribute to effective authorization.

### Security Model

The effective authorization chain is:

    User
        ↓
    UserRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission

This completes the application-level identity and authorization foundation.

### Consequence

LabGenius can now administer the complete security relationship through application APIs without relying on direct database manipulation.

---

## ADR-016 — Dedicated Account Security Operations

### Decision

Account activation, deactivation, lockout, and unlock are security operations and
must not be exposed through generic user-profile updates. `UserUpdate` excludes
`account_status` and `is_active`; dedicated APIs require `user.view` or
`user.update` as appropriate.

Unlock and activation are separate actions. Unlock clears the failure counter
and lock timestamp but preserves an inactive account's inactive state.

### Consequences

- Account lifecycle changes have explicit authorization and audit points.
- Generic user editing cannot bypass security-state controls.
- Administrators must explicitly activate an inactive account.

## ADR-017 — Append-Only Authentication and Security Audit Records

### Decision

LabGenius persists authentication attempts in `LoginHistory` and account security
activity in `SecurityEvent`. Security-state mutation and audit creation share one
transaction boundary. Read access reuses `user.view`; no new permission code is
introduced.

Audit data excludes credentials. Event details are restricted to useful
non-secret metadata and sanitized for credential-like keys.

### Consequences

- Failed and successful authentication can be investigated without storing secrets.
- Administrative events identify actor and target accounts.
- Anonymous failures retain attempted username and request metadata without falsely identifying an actor.

## ADR-018 — Last Active ADMIN Protection Deferred to Sprint 12.4

### Context

The current environment has one ADMIN account (`tapas`). Deactivation or lockout
of the final active administrator could remove application-level recovery paths.

### Decision

Sprint 12.1/12.2 closure documents, but does not partially implement,
last-ADMIN protection. Sprint 12.4 will define an atomic last-active-ADMIN
safeguard and a controlled recovery/bootstrap policy.

Production should maintain at least two active ADMIN users or an explicit,
tested, controlled recovery mechanism until that safeguard exists.

### Consequences

- No ad hoc ADMIN bypass is added to authentication or RBAC.
- Live security tests must not lock or deactivate the only ADMIN.
- This deferred safeguard was completed in Sprint 12.4; see ADR-020 and ADR-021.

---

## ADR-019 — Central Password Policy and Forced-Change Access

### Decision

Password rules are centralized in a configurable `PasswordPolicy` and applied to
user creation, self-service change, and administrative reset. Plaintext passwords
are accepted only as transient request/service inputs and are never persisted,
logged, or placed in security-event metadata.

Administrative resets require `user.update`, set `force_password_change=true`,
and preserve account activation state. Self-service change verifies the current
password and clears forced-change state.

Forced-change users may authenticate and receive a JWT so they can access
`/auth/me` and `/auth/change-password`. Existing role and permission dependencies
block ordinary protected access until the password changes.

### Token Decision

Existing JWTs remain valid after password change or reset. Reliable invalidation
requires token/session versioning or a revocation store, neither of which exists
in the current architecture. Sprint 12.3 documents this limitation instead of
adding an incomplete revocation mechanism.

### Consequences

- Swagger OAuth2 authentication remains compatible with forced password changes.
- Password policy logic is not duplicated across routers or services.
- Password lifecycle actions are atomic with `PASSWORD_CHANGED` or
  `PASSWORD_RESET` events.
- Sprint 12.4 supplies the administrative safeguards required for Sprint 12 closure.

---

## ADR-020 — Serialized Last-Usable-ADMIN Protection

### Decision

All existing application operations that can remove usable ADMIN access use one
`AdminSafetyService`. The service locks the stable ADMIN role row with
`SELECT ... FOR UPDATE`, calculates usable administrators, and rejects a change
with HTTP 409 when it would leave zero.

Protected operations are user deactivation, hard deletion, ADMIN assignment
removal, and ADMIN-role deactivation. `force_password_change` is not a reason to
exclude an ADMIN because authentication and password remediation remain possible.

Blocked attempts record `ADMIN_SAFETY_BLOCKED` with safe operation metadata.

### Consequences

- Concurrent guarded operations serialize against a shared database row.
- Ordinary non-ADMIN lifecycle and role operations remain unchanged.
- Failed-login lockout remains part of normal authentication security and is not bypassed.

## ADR-021 — Controlled ADMIN Recovery Without an Application Backdoor

### Decision

LabGenius will not expose an unauthenticated ADMIN bootstrap/recovery API and will
not ship hard-coded accounts, IDs, passwords, or default secrets. Production
should maintain at least two usable ADMIN users.

If all ADMIN access is lost through an exceptional condition such as normal
failed-login lockout, recovery uses separately authorized database-operator
access under the deployment's operational controls. The incident must be
documented, and normal password/security state must subsequently be restored
through authenticated application workflows.

### Consequences

- Recovery authority remains outside the public application attack surface.
- Deployment runbooks and database access governance are operational prerequisites.

## ADR-022 — JWT Expiry Is the Sprint 12 Session-Security Boundary

### Decision

Sprint 12 retains stateless JWT behavior. Password changes and resets do not
invalidate already-issued tokens; tokens remain valid until the centrally
configured expiry, currently 60 minutes.

A token-security-stamp would require a schema migration and validation on every
authenticated request, while robust revocation would introduce session state.
Neither is necessary to safely close Sprint 12, so both remain future work.

### Consequences

- No refresh-token or partial revocation architecture is introduced.
- Operators understand the maximum current exposure window.
- Sprint 12 is complete; Sprint 13 Organization-Level Authorization is next.

---

## ADR-023 — Permission-Specific Scope on UserRole

### Decision

Organizational access scope is persisted on `UserRole`, not User or Role. This
supports one user with multiple roles and the same reusable role with different
scope assignments. Scope values are ORGANIZATION, BUSINESS_UNIT, DIVISION,
DEPARTMENT, and SELF.

Effective scope is resolved independently for each permission. Only active
assignments whose active roles and active role-permission mappings grant the
requested permission participate; the broadest qualifying scope wins. Assignment
scope cannot exceed the administrator's effective `user.update` scope.

### Isolation and Filtering

All scope remains anchored inside the user's organization. User collection
queries apply SQL filters, and direct objects are separately checked with 404 on
denial to limit UUID-based information disclosure. Hierarchy relationships are
validated centrally.

### Catalog and Designation Decision

Role and permission catalogs remain global security configuration and are not
organization-scoped in Sprint 13. Designation is validated as belonging to the
user's department but remains a job/workflow attribute rather than a scope level.

### Consequences

- Future entities with organization, BU, division, department, or owner IDs can
  reuse the same scope service without a generic policy-engine redesign.
- Existing ADMIN assignments are backfilled to ORGANIZATION; other assignments
  default safely to SELF.
- Sprint 13 is complete; Sprint 14 Audit & Compliance Foundation is next.
