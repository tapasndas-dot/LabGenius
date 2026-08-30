// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../App'
import { AuthProvider } from '../../auth/AuthContext'
import { tokenStorage } from '../../auth/tokenStorage'

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function user(permissions: string[]) { return { id: 'me', username: 'user', email: 'u@test', display_name: 'User', force_password_change: false, permissions } }
const base = { id: '11111111-1111-1111-1111-111111111111', organization_id: 'o', code: 'LAB-1', name: 'Main Laboratory', description: 'Primary lab', is_active: true, version: 4, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
function renderPath(path: string) { return render(<AuthProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></AuthProvider>) }
beforeEach(() => { localStorage.clear(); tokenStorage.set('token'); vi.restoreAllMocks() })
afterEach(cleanup)

it('shows only permitted Masters navigation and guards direct routes', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(user(['location.view'])))
  const first = renderPath('/app')
  expect(await screen.findByRole('link', { name: 'Masters' })).toBeTruthy(); first.unmount()
  fetchMock.mockResolvedValue(json(user(['location.view'])))
  renderPath('/app/masters/materials')
  expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeTruthy()
})

it('renders records and sends server-side search and status filters', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(json(user(['manufacturer.view'])))
    .mockResolvedValue(json([{ ...base, website: 'https://example.test' }]))
  renderPath('/app/masters/manufacturers')
  expect(await screen.findByText('Main Laboratory')).toBeTruthy()
  fireEvent.change(screen.getByLabelText('Search masters'), { target: { value: 'main' } })
  fireEvent.change(screen.getByLabelText('Status filter'), { target: { value: 'inactive' } })
  await waitFor(() => expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain('search=main'))
  expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain('is_active=false')
})

it('uses human-readable location lookup and never asks for a parent UUID', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(json(user(['location.view', 'location.create'])))
    .mockResolvedValueOnce(json([{ ...base, parent_location_id: null, location_type: 'LABORATORY' }]))
    .mockResolvedValueOnce(json([{ ...base, parent_location_id: null, location_type: 'LABORATORY' }]))
  renderPath('/app/masters/locations')
  fireEvent.click(await screen.findByRole('button', { name: 'Create location' }))
  expect(await screen.findByRole('option', { name: 'LAB-1 — Main Laboratory' })).toBeTruthy()
  expect(screen.getByLabelText('Parent location')).toBeTruthy()
  expect(screen.queryByLabelText('Parent location UUID')).toBeNull()
})

it('sends expected version, preserves stale conflict, and offers refresh', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(json(user(['manufacturer.view', 'manufacturer.update'])))
    .mockResolvedValueOnce(json([{ ...base, website: null }]))
    .mockResolvedValueOnce(json({ detail: 'Record has been modified by another user. Refresh and try again.' }, 409))
    .mockResolvedValueOnce(json([{ ...base, version: 5, website: null }]))
  renderPath('/app/masters/manufacturers')
  fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Changed' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect((await screen.findByRole('alert')).textContent).toContain('Refresh and try again')
  const request = fetchMock.mock.calls[2][1]
  expect(JSON.parse(request?.body as string).version).toBe(4)
  fireEvent.click(screen.getByRole('button', { name: 'Refresh current data' }))
  expect(await screen.findByText('5')).toBeTruthy()
})

it('supports material types and permission-aware destructive actions', async () => {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(json(user(['material.view', 'material.create'])))
    .mockResolvedValueOnce(json([{ ...base, material_type: 'RAW_MATERIAL', default_unit_of_measure: 'kg' }]))
  renderPath('/app/masters/materials')
  expect(await screen.findByText('RAW MATERIAL')).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Create material' }))
  expect(screen.getByRole('option', { name: 'Finished Product' })).toBeTruthy()
})

it('submits canonical Material type values while displaying readable create labels', async () => {
  const requests: Array<Record<string, unknown>> = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(['material.view', 'material.create']))
    if (init?.method === 'POST') { requests.push(JSON.parse(init.body as string)); return json({ ...base, ...requests.at(-1), default_unit_of_measure: null }) }
    return json([])
  })
  renderPath('/app/masters/materials')
  fireEvent.click(await screen.findByRole('button', { name: 'Create material' }))
  const type = screen.getByLabelText('Material type')
  fireEvent.change(type, { target: { value: 'REFERENCE_STANDARD' } })
  expect(screen.getByRole('option', { name: 'Reference Standard' })).toBeTruthy()
  fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'RS-1' } })
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Reference' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(requests).toHaveLength(1))
  expect(requests[0].material_type).toBe('REFERENCE_STANDARD')
  fireEvent.click(await screen.findByRole('button', { name: 'Create material' }))
  fireEvent.change(screen.getByLabelText('Material type'), { target: { value: 'BULK_PRODUCT' } })
  fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'BP-1' } })
  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Bulk' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(requests).toHaveLength(2))
  expect(requests[1].material_type).toBe('BULK_PRODUCT')
})

it('renders and preserves a canonical Material type during edit', async () => {
  let update: Record<string, unknown> | undefined
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(['material.view', 'material.update']))
    if (init?.method === 'PUT') { update = JSON.parse(init.body as string); return json({ ...base, material_type: 'REFERENCE_STANDARD', default_unit_of_measure: null, version: 5 }) }
    return json([{ ...base, material_type: 'REFERENCE_STANDARD', default_unit_of_measure: null }])
  })
  renderPath('/app/masters/materials')
  fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
  const type = screen.getByLabelText('Material type') as HTMLSelectElement
  expect(type.value).toBe('REFERENCE_STANDARD')
  expect(screen.getByRole('option', { name: 'Reference Standard', selected: true })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(update).toBeTruthy())
  expect(update?.material_type).toBe('REFERENCE_STANDARD')
})

it('confirms status/delete mutations and sends their expected versions', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
  const fetchMock = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(json(user(['manufacturer.view', 'manufacturer.update', 'manufacturer.delete'])))
    .mockResolvedValueOnce(json([{ ...base, website: null }]))
    .mockResolvedValueOnce(json({ ...base, is_active: false, version: 5, website: null }))
    .mockResolvedValueOnce(json([{ ...base, is_active: false, version: 5, website: null }]))
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValueOnce(json([]))
  renderPath('/app/masters/manufacturers')
  fireEvent.click(await screen.findByRole('button', { name: 'Deactivate' }))
  await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(4))
  expect(JSON.parse(fetchMock.mock.calls[2][1]?.body as string)).toEqual({ version: 4 })
  fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
  await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(6))
  expect(JSON.parse(fetchMock.mock.calls[4][1]?.body as string)).toEqual({ version: 5 })
  expect(confirm).toHaveBeenCalledTimes(2)
})
