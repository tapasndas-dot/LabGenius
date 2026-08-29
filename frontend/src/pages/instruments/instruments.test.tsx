// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../App'
import { AuthProvider } from '../../auth/AuthContext'
import { CapabilityProvider } from '../../auth/CapabilityContext'
import { tokenStorage } from '../../auth/tokenStorage'

const instrument = {
  id: 'instrument-1', organization_id: 'org-1', business_unit_id: 'bu-1', division_id: 'div-1', department_id: 'dep-1',
  instrument_type_id: 'type-1', manufacturer_id: 'maker-1', location_id: 'location-1', responsible_user_id: 'user-1',
  instrument_code: 'CH-001', instrument_name: 'Main chamber', model_number: 'M-1', serial_number: 'SN-1', description: null,
  status: 'AVAILABLE', criticality: 'HIGH', calibration_required: true, maintenance_required: false,
  qualification_required: true, is_active: true, version: 4, created_at: '', updated_at: '',
}
const type = { id: 'type-1', organization_id: 'org-1', code: 'CHAMBER', name: 'Stability Chamber', description: null, is_active: true, version: 1, created_at: '', updated_at: '' }
const maker = { ...type, id: 'maker-1', code: 'ACME', name: 'Acme Instruments' }
const location = { ...type, id: 'location-1', code: 'LAB-1', name: 'Main Laboratory', parent_location_id: null, location_type: 'LABORATORY' }
const currentUser = (permissions: string[]) => ({ id: 'user-1', username: 'owner', email: 'owner@example.test', display_name: 'Asset Owner', force_password_change: false, permissions })
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function apiMock(permissions: string[], capabilities = ['INSTRUMENTS']) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(currentUser(permissions))
    if (url.endsWith('/modules/enabled')) return json(capabilities)
    if (url.includes('/instruments')) return json([instrument])
    if (url.includes('/instrument-types')) return json([type])
    if (url.includes('/manufacturers')) return json([maker])
    if (url.includes('/locations')) return json([location])
    if (url.includes('/business-units')) return json([{ id: 'bu-1', business_unit_code: 'BU-1', business_unit_name: 'Laboratory', is_active: true }, { id: 'bu-2', business_unit_code: 'BU-2', business_unit_name: 'Other', is_active: true }])
    if (url.includes('/divisions')) return json([{ id: 'div-1', business_unit_id: 'bu-1', division_code: 'DIV-1', division_name: 'Quality', is_active: true }, { id: 'div-2', business_unit_id: 'bu-2', division_code: 'DIV-2', division_name: 'Other', is_active: true }])
    if (url.includes('/departments')) return json([{ id: 'dep-1', division_id: 'div-1', department_code: 'DEP-1', department_name: 'QC', is_active: true }])
    if (url.endsWith('/users/')) return json([{ id: 'user-1', display_name: 'Asset Owner', username: 'owner', email: 'owner@example.test' }])
    return json([])
  })
}

function renderPath(path = '/app/instruments') {
  return render(<AuthProvider><CapabilityProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></CapabilityProvider></AuthProvider>)
}

beforeEach(() => { localStorage.clear(); tokenStorage.set('token'); vi.restoreAllMocks() })
afterEach(cleanup)

it('requires capability and view permission for navigation and direct route access', async () => {
  const firstFetch = apiMock(['instrument.view'], [])
  const first = renderPath('/app')
  await screen.findByRole('heading', { name: 'Home' })
  await waitFor(() => expect(firstFetch).toHaveBeenCalledWith('/api/modules/enabled', expect.anything()))
  expect(screen.queryByRole('link', { name: 'Instruments' })).toBeNull(); first.unmount()

  apiMock(['user.view'], ['INSTRUMENTS'])
  renderPath()
  expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeTruthy()
})

it('renders human-readable list values and permission-aware actions', async () => {
  apiMock(['instrument.view', 'instrument.create', 'instrument.update', 'instrument_type.view', 'manufacturer.view', 'location.view', 'user.view'])
  renderPath()
  expect(await screen.findByText('CH-001')).toBeTruthy()
  expect(await screen.findByText('Stability Chamber')).toBeTruthy()
  expect(screen.getByText('Acme Instruments')).toBeTruthy()
  expect(screen.getByText('Main Laboratory')).toBeTruthy()
  expect(screen.getAllByText('Asset Owner').length).toBeGreaterThan(1)
  expect(screen.getByRole('button', { name: 'Create instrument' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Edit' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
})

it('uses dependent hierarchy selectors and human-readable lookup options', async () => {
  apiMock(['instrument.view', 'instrument.create', 'instrument_type.view', 'manufacturer.view', 'location.view', 'user.view', 'business_unit.view', 'division.view', 'department.view'])
  renderPath()
  fireEvent.click(await screen.findByRole('button', { name: 'Create instrument' }))
  expect((await screen.findAllByRole('option', { name: 'CHAMBER — Stability Chamber' })).length).toBeGreaterThan(1)
  fireEvent.change(screen.getByLabelText('Business Unit'), { target: { value: 'bu-1' } })
  expect(screen.getByRole('option', { name: 'DIV-1 — Quality' })).toBeTruthy()
  expect(screen.queryByRole('option', { name: 'DIV-2 — Other' })).toBeNull()
  fireEvent.change(screen.getByLabelText('Division'), { target: { value: 'div-1' } })
  expect(screen.getByRole('option', { name: 'DEP-1 — QC' })).toBeTruthy()
  fireEvent.change(screen.getByLabelText('Business Unit'), { target: { value: 'bu-2' } })
  expect((screen.getByLabelText('Division') as HTMLSelectElement).value).toBe('')
  expect((screen.getByLabelText('Department') as HTMLSelectElement).value).toBe('')
})

it('shows stale conflict and offers a current-data refresh', async () => {
  const fetchMock = apiMock(['instrument.view', 'instrument.update', 'instrument_type.view'])
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(currentUser(['instrument.view', 'instrument.update', 'instrument_type.view']))
    if (url.endsWith('/modules/enabled')) return json(['INSTRUMENTS'])
    if (url.includes('/instrument-types')) return json([type])
    if (url.includes('/instruments/instrument-1') && init?.method === 'PUT') return json({ detail: 'Record has been modified by another user. Refresh and try again.' }, 409)
    if (url.includes('/instruments')) return json([instrument])
    return json([], 403)
  })
  renderPath()
  fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
  fireEvent.change(screen.getByLabelText('Instrument name'), { target: { value: 'Changed' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect((await screen.findByRole('alert')).textContent).toContain('Refresh and try again')
  expect(screen.getByRole('button', { name: 'Refresh current instrument data' })).toBeTruthy()
  const update = fetchMock.mock.calls.find(([url, init]) => String(url).includes('/instruments/instrument-1') && init?.method === 'PUT')
  expect(JSON.parse(update?.[1]?.body as string).version).toBe(4)
})

it('confirms activate/deactivate and delete with expected versions', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
  const fetchMock = apiMock(['instrument.view', 'instrument.update', 'instrument.delete'])
  renderPath()
  fireEvent.click(await screen.findByRole('button', { name: 'Deactivate' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/instruments/instrument-1/deactivate'))).toBe(true))
  const deactivate = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/instruments/instrument-1/deactivate'))
  expect(JSON.parse(deactivate?.[1]?.body as string)).toEqual({ version: 4 })
  fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/instruments/instrument-1') && init?.method === 'DELETE')).toBe(true))
  const remove = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/instruments/instrument-1') && init?.method === 'DELETE')
  expect(JSON.parse(remove?.[1]?.body as string)).toEqual({ version: 4 })
  expect(confirm).toHaveBeenCalledTimes(2)
})
