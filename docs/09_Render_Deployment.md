# Render Deployment Foundation

**Milestones:** D1.1 deployment foundation; D1.2B demo viewer hardening

**Baseline:** v0.28.0

**Environment classification:** Demonstration

## Architecture

The initial hosted topology is:

`Render Static Site -> Render Web Service -> separate demo PostgreSQL/Supabase database`

This remains the long-term topology. The temporary early pre-sales database exception
below permits the existing development database only under the stated safeguards.

The browser loads the React/Vite application from the Static Site and calls the FastAPI
Web Service over HTTPS. The backend alone connects to the demo database and Supabase.
The frontend and backend have separate origins, so the exact frontend URL must be in the
backend CORS allowlist.

This is initially a demo environment. Its presence and audit features do not constitute
a 21 CFR Part 11, electronic-signature, GxP, EU Annex 11, or other compliance claim.

## Render services

The repository-level `render.yaml` defines:

| Service | Root directory | Build command | Start/publish setting |
|---|---|---|---|
| Backend Web Service | `backend` | `pip install -r requirements.txt` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Frontend Static Site | `frontend` | `npm ci && npm run build` | Publish `dist` |

The backend health check is `/health/`. The Static Site rewrites `/*` to `/index.html`,
which is required for direct navigation and refreshes with `BrowserRouter`.

Alembic is deliberately absent from the backend start command. Application startup must
not mutate the database schema.

## Environment variables

Configure these backend variables in Render:

- `APP_NAME` and `APP_VERSION` (safe blueprint defaults are supplied).
- `SUPABASE_URL` and `SUPABASE_KEY` for the approved target project.
- `DATABASE_URL` for the approved target PostgreSQL database (normally isolated demo).
- `JWT_SECRET_KEY`, unique to this environment.
- `JWT_ALGORITHM` and `ACCESS_TOKEN_EXPIRE_MINUTES` (safe defaults are supplied).
- `CORS_ALLOWED_ORIGINS`, a comma-separated list of exact frontend origins, such as
  `https://your-frontend-service.onrender.com`. Do not include paths and do not use `*`.
- The account/password policy variables shown in `backend/.env.example` may be set when
  the defaults are not appropriate.

Configure `VITE_API_BASE_URL` on the frontend to the backend HTTPS origin, without a
trailing slash (for example, `https://your-backend-service.onrender.com`). Vite embeds
this value during the build, so rebuild the Static Site after changing it.
`VITE_API_PROXY_TARGET` remains available for local development only; it is not needed by
the deployed static bundle.

The blueprint marks secrets and environment-specific URLs with `sync: false`. Enter them
manually in Render; never add their values to `render.yaml` or commit a real `.env` file.

Generate a JWT secret locally with a cryptographically secure tool, for example:

```text
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Paste the result directly into Render's secret environment-variable field. Do not save
the output in source control, logs, tickets, or deployment documentation.

## Database isolation and migrations

An isolated PostgreSQL/Supabase project, credentials, and data lifecycle remain the
long-term requirement for the demo environment.

**TEMPORARY PRE-SALES EXCEPTION:** For the early pre-sales preview phase only, the hosted
application may use the existing LabGenius development database for cost control if:

- It contains no confidential customer or prospect data.
- Prospect access uses a strictly read-only `DEMO_VIEWER` assignment.
- Credentials are shared only for intended demo access; the ADMIN account stays private.
- The database is backed up appropriately.
- Prospect access is monitored and can be revoked promptly.

An isolated Demo/UAT database becomes mandatory before serious prospect evaluation/PoC,
customer-specific data loading, production-like testing, external integrations, or
production deployment. The exception is not permission to expose confidential data or
to share administrative credentials.

After setting the demo `DATABASE_URL`, run migrations as a controlled deployment step
from the `backend` directory/context:

```text
alembic upgrade head
```

Confirm the command targets the approved database before running it; do not rerun schema
changes blindly against a shared development database. D1.1 and D1.2B add no migration.
Do not add `alembic upgrade head` to the Web Service start command.

## Deployment order

1. Select the approved database: provision an isolated demo database, or verify every
   safeguard of the temporary pre-sales exception.
2. Create the backend Web Service from the blueprint and set all unsynchronized backend
   environment variables.
3. Run `alembic upgrade head` once, under operator control, against the demo database.
4. Deploy the backend and verify `/health/` over HTTPS.
5. Create/deploy the frontend Static Site with `VITE_API_BASE_URL` set to the backend URL.
6. Set backend `CORS_ALLOWED_ORIGINS` to the exact frontend URL and redeploy the backend.
7. Verify the application end to end.

## Verification checklist

- Backend `/health/` returns a healthy response over HTTPS.
- `/openapi.json` reports application version `0.28.0` and OAuth2 uses `/auth/login`.
- The frontend loads and a nested route survives a direct request/refresh.
- Browser API calls go to `VITE_API_BASE_URL`, not the Vite development proxy.
- Preflight and authenticated API requests from the frontend origin succeed.
- Requests from an unlisted origin do not receive an allow-origin header.
- The database is isolated, or all temporary pre-sales safeguards have been verified;
  no confidential customer/prospect data is exposed.
- No secret appears in source, build logs, browser code, or committed files.

## Rollback and redeployment

Render retains deploy history, so application rollback should select a previously known
good backend or frontend deploy. Keep frontend and backend versions compatible when
rolling either service back. Database rollback is a separate, operator-controlled
decision: review the relevant Alembic migration's downgrade behavior and protect data
before executing it. Never assume application rollback reverses a migration.

Changes to `VITE_API_BASE_URL` require a frontend rebuild. Changes to backend runtime
environment variables require a backend redeploy. Re-run the verification checklist
after either action.

Do not hard-code demo credentials or add demo users to deployment configuration. Seeded
representative demo data is not provided by D1.2B. Before treating any environment as
production, maintain at least two active ADMIN accounts or establish and test an explicit
administrative recovery mechanism.

## DEMO_VIEWER provisioning and revocation

`DEMO_VIEWER` is normal RBAC, not a guest mode, authentication bypass, or role-name
special case. Its canonical permissions are intentionally curated, not inferred from
every code ending in `.view`:

```text
organization.view
business_unit.view
division.view
department.view
designation.view
location.view
manufacturer.view
instrument_type.view
material.view
instrument.view
test.view
method.view
specification.view
sample.view
sample_test_result.view
stability_protocol.view
stability_study.view
stability_pull.view
```

After confirming the target database and taking an appropriate backup, an operator runs
from the `backend` context:

```text
python -m app.seeds.demo_viewer --apply
```

The utility creates/reconciles only the `DEMO_VIEWER` role and its exact 18 active
role-permission mappings, removing extra mappings. It requires all approved catalog
permissions to exist and be active; otherwise it fails before role writes. Changes and
operator-source audit events share one transaction. A second run without drift is a
no-op. It does not invoke the general ADMIN permission seed or change any user/account.
Newly created roles are active. Reconciliation restores canonical permission mappings
but preserves an existing role's active/inactive status. Role deactivation is a supported
global demo-access revocation mechanism; reconciliation does not reactivate the role.

Create the eventual prospect as a new normal user through existing private admin APIs/UI,
using operator-supplied identity and credentials at execution time. Do not reuse
`TEST_VIEWER` or the existing ADMIN. Preserve hierarchy validity and the normal
`force_password_change`/self-service password-change flow. Assign only `DEMO_VIEWER`,
with `UserRole.access_scope=ORGANIZATION`, in the intended organization. Scope belongs to
the user-role assignment, not the Role record. Do not add other roles: effective RBAC
permissions are additive, and another assignment could grant mutation/admin access.
Verify the effective `/auth/me` permissions are exactly the approved list before sharing
access. Instruments and Stability still require their ordinary organization capabilities
to be enabled; do not grant `module.view` or `module.manage` to work around capability setup.

The viewer may see operational QC information through its view permissions, but the
Review/Finalize workflow queue remains unavailable. No workflow permissions are granted
to fill that queue. Authentication/account-security behavior remains unchanged.

Revoke access using the existing administrative account/assignment/role deactivation APIs/UI.
Account deactivation denies existing tokens on subsequent authenticated requests;
assignment deactivation removes its permission grants. Deactivating `DEMO_VIEWER` removes
its grants globally and remains effective after reconciliation. Keep administrative monitoring
private, review access/role drift regularly, and never share ADMIN credentials.
