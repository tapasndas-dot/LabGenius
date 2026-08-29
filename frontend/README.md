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

`/auth/me` does not currently return `force_password_change`. The frontend user
type accepts it when available; Task 15B must add forced-password-change routing
after the backend contract exposes the flag.

## Commands

- `npm run dev`
- `npm run build`
- `npm run lint`
- `npm test`
