# Render Deployment Foundation

**Milestone:** D1.1

**Baseline:** v0.28.0

**Environment classification:** Demonstration

## Architecture

The initial hosted topology is:

`Render Static Site -> Render Web Service -> separate demo PostgreSQL/Supabase database`

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
- `SUPABASE_URL` and `SUPABASE_KEY` for the isolated demo project.
- `DATABASE_URL` for the isolated demo PostgreSQL database.
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

Never point a prospective-customer demo at the development database. Create a separate
PostgreSQL/Supabase project, credentials, and data lifecycle for the demo environment.

After setting the demo `DATABASE_URL`, run migrations as a controlled deployment step
from the `backend` directory/context:

```text
alembic upgrade head
```

Confirm the command targets the demo database before running it. D1.1 adds no migration.
Do not add `alembic upgrade head` to the Web Service start command.

## Deployment order

1. Provision the isolated demo PostgreSQL/Supabase database.
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
- The database contains only isolated demo data and no development credentials.
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

Do not hard-code demo credentials or add demo users to deployment configuration.
`DEMO_VIEWER` and seeded demo data are deferred to D1.2. Before treating any environment
as production, maintain at least two active ADMIN accounts or establish and test an
explicit administrative recovery mechanism.
