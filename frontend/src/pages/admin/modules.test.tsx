// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../App'
import { AuthProvider } from '../../auth/AuthContext'
import { CapabilityProvider } from '../../auth/CapabilityContext'
import { tokenStorage } from '../../auth/tokenStorage'
import { canUseCapability } from '../../auth/capabilities'

const core = { id: 'c', code: 'CORE_LAB', name: 'Core Lab', description: 'Core', capability_class: 'CORE_LAB', is_core: true, is_active: true, version: 1, created_at: '', updated_at: '' }
const instruments = { id: 'i', code: 'INSTRUMENTS', name: 'Instrument / Asset Registry', description: 'Assets', capability_class: 'OPTIONAL_SHARED', is_core: false, is_active: true, version: 1, created_at: '', updated_at: '' }
function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function renderPath(path: string) { return render(<AuthProvider><CapabilityProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></CapabilityProvider></AuthProvider>) }
beforeEach(() => { localStorage.clear(); tokenStorage.set('token'); vi.restoreAllMocks() }); afterEach(cleanup)

function mockApi(permissions: string[], conflict = false) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json({ id: 'u', username: 'u', email: 'u@test', display_name: 'User', force_password_change: false, permissions })
    if (url.endsWith('/modules/enabled')) return json(['PLATFORM', 'CORE_LAB'])
    if (url.endsWith('/modules/organization')) return json([{ module: core, is_enabled: true, version: 0, dependencies: [] }, { module: instruments, is_enabled: false, version: 0, dependencies: [] }])
    if (url.endsWith('/modules/INSTRUMENTS/enable') && init?.method === 'PUT') return conflict ? json({ detail: 'Enable required capabilities first.' }, 409) : json({ module: instruments, is_enabled: true, version: 1, dependencies: [] })
    return json([])
  })
}

it('shows capability administration only with module.view', async () => {
  const fetchMock = mockApi([]); const first = renderPath('/app')
  await screen.findByRole('heading', { name: 'Home' }); expect(screen.queryByRole('link', { name: 'Capabilities' })).toBeNull(); first.unmount()
  fetchMock.mockRestore(); mockApi(['module.view']); renderPath('/app/administration')
  expect(await screen.findByRole('link', { name: 'Capabilities' })).toBeTruthy()
})

it('enables an optional capability with expected version when manage is granted', async () => {
  const fetchMock = mockApi(['module.view', 'module.manage']); vi.spyOn(window, 'confirm').mockReturnValue(true)
  renderPath('/app/administration/modules')
  fireEvent.click(await screen.findByRole('button', { name: 'Enable' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/modules/INSTRUMENTS/enable'))).toBe(true))
  const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/modules/INSTRUMENTS/enable'))
  expect(JSON.parse(call?.[1]?.body as string)).toEqual({ version: 0 })
})

it('keeps capability and permission independent and displays dependency conflicts', async () => {
  expect(canUseCapability(['INSTRUMENTS'], ['instrument.view'], 'INSTRUMENTS', 'instrument.view')).toBe(true)
  expect(canUseCapability([], ['instrument.view'], 'INSTRUMENTS', 'instrument.view')).toBe(false)
  expect(canUseCapability(['INSTRUMENTS'], [], 'INSTRUMENTS', 'instrument.view')).toBe(false)
  mockApi(['module.view', 'module.manage'], true); vi.spyOn(window, 'confirm').mockReturnValue(true)
  renderPath('/app/administration/modules')
  fireEvent.click(await screen.findByRole('button', { name: 'Enable' }))
  expect((await screen.findByRole('alert')).textContent).toContain('Enable required capabilities first')
})
