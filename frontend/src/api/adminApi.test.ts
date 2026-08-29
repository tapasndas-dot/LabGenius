import { beforeEach, describe, expect, it, vi } from 'vitest'
import { auditApi } from './audit'
import { rolesApi } from './roles'
import { usersApi } from './users'
import { userRolesApi } from './userRoles'
import { ApiError } from './client'
import { errorMessage } from '../components/admin/AdminPrimitives'

function response(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
beforeEach(() => {
  Object.defineProperty(globalThis, 'window', { value: { localStorage: { getItem: () => 'token', setItem: vi.fn(), removeItem: vi.fn() } }, configurable: true })
  vi.restoreAllMocks()
})

describe('administration API contracts', () => {
  it('keeps conflict and authorization failures visibly failed', () => {
    expect(errorMessage(new ApiError('Cannot remove final ADMIN.', 409))).toBe('Cannot remove final ADMIN.')
    expect(errorMessage(new ApiError('Forbidden', 403))).toContain('not authorized')
  })
  it('uses scoped users list and actual create/update contracts', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => response([]))
    await usersApi.list()
    await usersApi.create({ organization_id: 'o', business_unit_id: 'b', division_id: 'v', department_id: 'd', designation_id: 'g', employee_code: 'E1', first_name: 'A', last_name: 'B', display_name: 'A B', email: 'a@b.test', username: 'ab', password: 'Secret!12345', timezone: 'UTC', language: 'en' })
    await usersApi.update('u1', { display_name: 'Updated' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/users/')
    expect(JSON.parse(fetchMock.mock.calls[1][1]?.body as string).organization_id).toBe('o')
    expect(JSON.parse(fetchMock.mock.calls[2][1]?.body as string)).toEqual({ display_name: 'Updated' })
  })

  it('uses dedicated security and delete endpoints', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => response({}))
    await usersApi.deactivate('u1'); await usersApi.activate('u1'); await usersApi.unlock('u1'); await usersApi.remove('u1')
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual(['/api/users/u1/deactivate', '/api/users/u1/activate', '/api/users/u1/unlock', '/api/users/u1'])
  })

  it('uses role CRUD/status and role-permission assignment contracts', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => response({}))
    await rolesApi.create({ role_code: 'QC', role_name: 'QC', description: null })
    await rolesApi.update('r1', { role_name: 'Quality', description: null })
    await rolesApi.setStatus('r1', false)
    await rolesApi.assignPermission('r1', 'p1'); await rolesApi.removePermission('r1', 'p1')
    expect(fetchMock.mock.calls[2][0]).toBe('/api/roles/r1/status')
    expect(JSON.parse(fetchMock.mock.calls[3][1]?.body as string)).toEqual({ permission_id: 'p1' })
    expect(fetchMock.mock.calls[4][1]?.method).toBe('DELETE')
  })

  it('includes access_scope and removes the selected user-role assignment', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => response({}))
    await userRolesApi.assign('u1', 'r1', 'DEPARTMENT'); await userRolesApi.remove('u1', 'r1')
    expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({ role_id: 'r1', access_scope: 'DEPARTMENT' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/users/u1/roles/r1')
  })

  it('builds bounded audit pagination and filters and supports detail', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => response([]))
    await auditApi.list({ entity_type: 'User', action: 'UPDATE', limit: 25, offset: 25 }); await auditApi.get('e1')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/audit/events?entity_type=User&action=UPDATE&limit=25&offset=25')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/audit/events/e1')
  })
})
