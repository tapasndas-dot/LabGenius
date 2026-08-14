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