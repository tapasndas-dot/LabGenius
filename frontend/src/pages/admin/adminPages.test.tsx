// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../App'
import { AuthProvider } from '../../auth/AuthContext'
import { tokenStorage } from '../../auth/tokenStorage'

function response(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function me(permissions: string[]) { return { id: 'me', username: 'admin', email: 'a@test', display_name: 'Admin', force_password_change: false, permissions } }
function renderPath(path: string) { return render(<AuthProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></AuthProvider>) }
beforeEach(() => { localStorage.clear(); tokenStorage.set('token'); vi.restoreAllMocks() })
afterEach(cleanup)

it('renders scoped user API results and scoped empty state', async () => {
  const hierarchy={organizations:[],business_units:[],divisions:[],departments:[],designations:[]}
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async input=>String(input).endsWith('/auth/me')?response(me(['user.view'])):String(input).includes('/hierarchy-lookups/')?response(hierarchy):response([{ id: 'u1', organization_id: 'o', business_unit_id: 'b', division_id: 'v', department_id: 'd', designation_id: 'g', employee_code: 'E1', first_name: 'A', last_name: 'B', display_name: 'Scoped User', email: 'u@test', mobile: null, username: 'user', account_status: 'ACTIVE', timezone: 'UTC', language: 'en', failed_login_attempts: 0, last_login: null, created_at: '', updated_at: '' }]))
  const first = renderPath('/app/administration/users')
  expect(await screen.findByText('Scoped User')).toBeTruthy(); first.unmount()
  fetchMock.mockReset().mockImplementation(async input=>String(input).endsWith('/auth/me')?response(me(['user.view'])):String(input).includes('/hierarchy-lookups/')?response(hierarchy):response([]))
  renderPath('/app/administration/users')
  expect(await screen.findByText('No users are available in your assigned scope.')).toBeTruthy()
})

it('blocks direct administration sections without the required permission', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(me(['role.view'])))
  renderPath('/app/administration/users')
  expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeTruthy()
})

it('renders audit events and safe structured detail controls', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(response(me(['audit.view'])))
    .mockResolvedValueOnce(response([{ id: 'e1', occurred_at: '2026-01-01T00:00:00Z', actor_user_id: null, action: 'UPDATE', entity_type: 'User', entity_id: 'u1', organization_id: 'o', request_id: null, source_ip: null, changes: { name: { before: 'A', after: 'B' } }, reason: null, source: 'HTTP' }]))
  renderPath('/app/administration/audit')
  expect(await screen.findByText('UPDATE')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'View' })).toBeTruthy()
})
