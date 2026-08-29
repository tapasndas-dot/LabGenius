# LabGenius Repository Instructions

## Repository and source of truth

- The Git repository root is `C:\LabGenius`. Run Git commands from this root.
- The current repository is always the source of truth. Inspect relevant files before changing a feature; adapt old prompts when the implementation has evolved.
- Never invent APIs, models, paths, relationships, IDs, credentials, or configuration. Do not encode real user IDs, passwords, or other secrets.
- Keep changes within the requested scope. Preserve compatible behavior and avoid broad unrelated refactors.

## Project context

- Backend: Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, JWT/OAuth2 authentication.
- Backend code is organized under `backend/app` into models, repositories, services, schemas, routers, authentication/core helpers, dependencies, seeds, and supporting utilities. Tests are in `backend/tests`; migrations are in `backend/alembic/versions`.
- Frontend: React/Vite scaffold under `frontend`; frontend foundation work begins with Sprint 15. Inspect its actual configuration before implementation.
- Preserve the existing model/repository/service/schema/router separation. Put business rules primarily in services and database query behavior in repositories/services following nearby conventions. Keep routers thin.
- Reuse centralized helpers for authorization, hierarchy validation, security, sanitization, auditing, and exceptions. Avoid duplicated policy logic, circular imports, premature frameworks, and unnecessary abstraction.

## Database, migrations, and transactions

- PostgreSQL is authoritative. Use Alembic for schema changes; do not create a migration when no schema change is needed.
- Before migration work inspect `alembic current`, `alembic heads`, the current revision chain, and nearby migrations. Never guess `down_revision`; exactly one head must remain.
- Inspect both `upgrade()` and `downgrade()`. After schema changes run `alembic upgrade head`, `alembic current`, `alembic heads`, and `alembic check` where database access is available.
- Never hard-code production record IDs.
- Keep a business mutation and its `AuditEvent` in the same transaction. Avoid scattered or redundant `db.commit()` calls. A failed mutation must not leave a committed, misleading audit record. Preserve existing transaction semantics unless deliberately and narrowly improving them.

## Authentication, authorization, and security

- JWT authentication exists. Keep the OAuth2 token URL `/auth/login` unless a task explicitly redesigns authentication.
- RBAC determines **what** an actor may do; organization scope determines **which data** the permission reaches. Enforce both on lists and direct-object operations.
- Preserve `force_password_change`, inactive-user, locked-account, and final-usable-ADMIN safeguards.
- Never log, persist in audit details, return, or print passwords, password hashes, tokens, JWTs, Authorization headers, credentials, API keys, database passwords, or secrets. Use centralized recursive sanitization.
- Unlocking or resetting the password of an inactive user must not activate that user. Password reset follows the current design and sets `force_password_change`; successful self-service password change clears it.
- Generic user updates must not bypass dedicated account-security operations. Normal administrative operations must never remove the final usable ADMIN.

## Organization scope

- Access scope is stored per `UserRole`: `ORGANIZATION`, `BUSINESS_UNIT`, `DIVISION`, `DEPARTMENT`, or `SELF`.
- Effective scope is permission-specific. The broadest scope wins only among active assignments whose active roles and active mappings grant that exact active permission.
- Scope may not cross the authenticated user's organization unless a future explicit cross-organization mechanism is introduced.
- Reuse `OrganizationScopeService`; filter collections in SQL and preserve the current 404 concealment behavior for direct out-of-scope UUID access.
- Designation must remain hierarchy-valid but is not currently an authorization boundary.
- New organization-owned business entities must explicitly integrate the centralized scope service; ownership alone does not enforce access.

## Audit and compliance

- Keep these concepts distinct: `LoginHistory` records authentication attempts, `SecurityEvent` records security activity, and `AuditEvent` records application/administrative changes.
- `AuditEvent` is append-only through ordinary application APIs. Do not expose audit update or delete endpoints.
- Use `AuditService` and centralized sanitization. Retain actor, entity identity, organization hierarchy ownership, safe changes, and request/source context where applicable.
- Audit functionality supports traceability but does not by itself establish regulatory, GxP, 21 CFR Part 11, EU Annex 11, data-integrity, or electronic-signature compliance. Do not make certification claims or treat a reason/comment as an electronic signature.

## Frontend

- Inspect the current React scaffold and build configuration before changing it; do not assume exact versions or libraries.
- The backend remains the authorization source of truth. Frontend permission/scope controls improve UX but never replace backend enforcement.
- Do not duplicate backend business or hierarchy rules in React.

## Testing and completion

- During implementation, run focused tests for changed behavior. Use isolated test data, never destructively test against the sole real ADMIN, and never guess credentials.
- At sprint closure, where practical: run the full backend regression suite, compile Python sources, validate FastAPI import/startup and OpenAPI generation, check `/docs` and `/openapi.json`, and verify the OAuth2 token URL remains `/auth/login`.
- When database code changes, run the Alembic checks above. Do not repeatedly run the full suite after every small edit without need.
- Before handoff, remove debug code, run `git diff --check`, and report exact `git status --short`.

## Git and documentation

- Unless explicitly requested, do not commit, push, or create tags. Leave changes available for review. Never use destructive Git commands merely to remove unexpected user changes.
- Standard project documents are `docs/05_Security_Model.md`, `docs/06_Business_Rules.md`, `docs/07_Development_Roadmap.md`, `docs/CHANGELOG.md`, and `docs/DECISIONS.md`. Update them when the task requires it; do not modify all five automatically for a small change.
- Prefer simple, production-readable code and existing naming/style conventions. Remove stale debug output, avoid customer/country-specific hard-coding, preserve multi-customer deployability, and build reusable foundations without over-engineering.
