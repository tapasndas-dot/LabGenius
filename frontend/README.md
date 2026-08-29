# LabGenius Frontend

React, TypeScript, and Vite frontend for LabGenius.

## Local development

Start FastAPI on `http://127.0.0.1:8000`, then run `npm install` and
`npm run dev`. The default browser API base is `/api`; Vite proxies that prefix
to `VITE_API_PROXY_TARGET` and removes `/api`. This avoids adding a development-
only CORS exception to the backend. Copy `.env.example` to `.env.local` only for
local overrides. Production can set `VITE_API_BASE_URL` to its same-origin API
prefix or deployed backend URL without source changes.

## Authentication

Login posts OAuth2 form data to `/auth/login`; restoration calls `/auth/me`.
The stateless backend has no refresh-token or secure session-cookie flow, so Task
15A stores the bearer token through one `localStorage` adapter. This persistence
is not equivalent to an HttpOnly cookie: XSS could expose browser storage. Tokens
are never rendered or logged and are cleared on logout and conclusive 401 or
session-restoration failure.

`/auth/me` returns identity, `force_password_change`, and safe effective permission
codes. On startup the app restores this summary before routing. Unauthenticated
users are sent to `/login`; forced-change users are restricted to
`/change-password`; normal authenticated users enter the nested `/app` shell.

The password form posts the backend's exact `current_password`, `new_password`,
and `confirm_new_password` contract. After success it reloads `/auth/me` and enters
the application only after the backend confirms the forced-change flag is clear.

Navigation uses effective permission codes only to hide unavailable choices. This
is a UX feature, not an authorization boundary: FastAPI remains authoritative for
RBAC and organization scope on every request. The frontend does not reproduce
organization hierarchy scope calculations.

Current route foundation:

- `/login`
- `/change-password`
- `/app`
- `/app/masters/locations`
- `/app/masters/manufacturers`
- `/app/masters/instrument-types`
- `/app/masters/materials`
- `/app/administration/users`
- `/app/administration/roles`
- `/app/administration/role-permissions`
- `/app/administration/user-roles`
- `/app/administration/audit`
- `/not-authorized`
- routing-level not found handling

## Administration

Administration tabs are shown from effective permission codes. Users are always
the backend-scoped result set; dedicated lifecycle and password APIs are used.
Role and assignment changes that can alter the current session refresh `/auth/me`.
Audit history is read-only and paginated.

User creation hierarchy UUIDs remain backend-validated and are never invented or
hard-coded. API `version` values are displayed where returned, but mapper-level
optimistic locking is not yet a backend guarantee.

## Shared masters

The Masters area provides permission-aware CRUD for Locations, Manufacturers,
Instrument Types, and Materials. Lists use backend search, active-state filtering,
pagination, and organization isolation. Create/update/status/delete actions appear only
for their exact effective permissions; FastAPI still enforces every operation.

Business-master update, activation, deactivation, and delete requests preserve the
record's expected `version`. A stale 409 remains visible and offers a current-data
refresh instead of overwriting. Location parents use an accessible active-location
lookup showing code and name while storing the UUID internally.

Module-capability navigation and guards are intentionally absent until Sprint 16D.

## Commands

- `npm run dev`
- `npm run build`
- `npm run lint`
- `npm test`
