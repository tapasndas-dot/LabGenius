// @vitest-environment jsdom
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, configure, fireEvent, getConfig, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { AuthProvider } from '../auth/AuthContext'
import { CapabilityProvider } from '../auth/CapabilityContext'
import { tokenStorage } from '../auth/tokenStorage'

// Test fixture, not a role-name authorization path. Kept aligned with the operator
// specification by the first test; the UI receives normal effective permissions.
const permissions = [
  'organization.view', 'business_unit.view', 'division.view', 'department.view',
  'designation.view', 'location.view', 'manufacturer.view', 'instrument_type.view',
  'material.view', 'instrument.view', 'test.view', 'method.view', 'specification.view',
  'sample.view', 'sample_test_result.view', 'stability_protocol.view',
  'stability_study.view', 'stability_pull.view',
]
const meta = { created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', version: 1 }
const master = { ...meta, id: 'maker1', organization_id: 'org1', code: 'MAKER', name: 'Preview Manufacturer', description: null, is_active: true, website: null }
const material = { ...master, id: 'material1', code: 'MAT', name: 'Preview Material', material_type: 'FINISHED_PRODUCT', default_unit_of_measure: 'kg' }
const instrument = { ...meta, id: 'instrument1', organization_id: 'org1', business_unit_id: null, division_id: null, department_id: null, instrument_code: 'CH-001', instrument_name: 'Preview Chamber', instrument_type_id: null, manufacturer_id: 'maker1', location_id: null, responsible_user_id: null, model_number: null, serial_number: null, description: null, status: 'AVAILABLE', criticality: null, calibration_required: false, maintenance_required: false, qualification_required: false, is_active: true }
const labTest = { ...meta, id: 'test1', organization_id: 'org1', test_code: 'ASSAY', test_name: 'Preview Assay', test_category: 'Chemical', default_unit: '%', description: null, is_active: true }
const method = { ...meta, id: 'method1', organization_id: 'org1', method_code: 'HPLC', method_name: 'Preview Method', description: null, is_active: true }
const methodVersion = { ...meta, id: 'mv1', method_id: 'method1', version_number: 1, version_label: 'Draft method', status: 'DRAFT', effective_from: null, effective_to: null, source_reference: null, description: null }
const specification = { ...meta, id: 'spec1', organization_id: 'org1', material_id: 'material1', specification_code: 'REL', specification_name: 'Preview Specification', description: null, is_active: true }
const specVersion = { ...meta, id: 'sv1', specification_id: 'spec1', version_number: 1, version_label: null, status: 'APPROVED', effective_from: null, effective_to: null, description: null }
const sample = { ...meta, id: 'sample1', organization_id: 'org1', business_unit_id: null, division_id: null, department_id: null, sample_number: 'QC-001', external_reference: null, material_id: 'material1', specification_version_id: 'sv1', sample_description: null, quantity: null, quantity_unit: null, received_at: null, sampled_at: null, due_at: null, status: 'REGISTERED', priority: 'NORMAL', notes: null }
const sampleTest = { ...meta, id: 'sampleTest1', sample_id: 'sample1', specification_test_id: 'specTest1', test_id: 'test1', method_version_id: 'mv1', sequence_number: 1, status: 'ASSIGNED', is_required: true, display_name: 'Preview Assay', test: { id: 'test1', code: 'ASSAY', name: 'Preview Assay' }, method_version: { id: 'mv1', code: 'HPLC', name: 'Preview Method', version_number: 1, status: 'APPROVED' }, current_assignee: { id: 'analyst1', display_name: 'Preview Analyst' } }
const protocol = { ...meta, id: 'protocol1', organization_id: 'org1', protocol_code: 'STAB', protocol_name: 'Preview Protocol', description: null, is_active: true }
const protocolVersion = { ...meta, id: 'pv1', stability_protocol_id: 'protocol1', version_number: 1, version_label: 'Draft protocol', status: 'DRAFT', effective_from: null, effective_to: null, description: null }
const study = { ...meta, id: 'study1', organization_id: 'org1', business_unit_id: null, division_id: null, department_id: null, study_number: 'ST-001', study_name: 'Preview Study', material_id: 'material1', stability_protocol_version_id: 'pv1', start_date: '2026-01-01', status: 'ACTIVE', batch_number: null, lot_number: null, notes: null }
const pulls = ['SCHEDULED', 'PULLED'].map((status, index) => ({ ...meta, id: `pull${index}`, stability_study_id: 'study1', stability_study_condition_id: 'condition1', stability_protocol_timepoint_id: 'timepoint1', specification_version_id: 'sv1', scheduled_date: '2026-02-01', status, qc_sample_id: null, pulled_at: null, notes: null, qc_sample: null, protocol_condition: { id: 'condition1', code: 'LONG', name: 'Long term' }, timepoint: { id: 'timepoint1', label: 'Month 1', sequence_number: 1, is_initial: false }, assigned_instrument: { id: 'instrument1', code: 'CH-001', name: 'Preview Chamber', status: 'AVAILABLE' } }))
type ResultStatus = 'DRAFT' | 'ENTERED' | 'REVIEWED' | null

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi(resultStatus: ResultStatus = 'DRAFT', assigned = true) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const path = String(input).split('?')[0].replace(/^\/api/, '').replace(/\/$/, '')
    if (init?.method && init.method !== 'GET') throw new Error('Unexpected demo mutation request')
    if (path === '/auth/me') return json({ id: 'viewer1', username: 'preview-fixture', email: 'preview@example.test', display_name: 'Preview Fixture', force_password_change: false, permissions })
    if (path === '/modules/enabled') return json(['INSTRUMENTS', 'STABILITY'])
    if (path === '/manufacturers') return json([master])
    if (path === '/materials') return json([material])
    if (path === '/instruments') return json([instrument])
    if (path === '/instruments/instrument1/chamber-profile') return json({ detail: 'Profile not found' }, 404)
    if (path === '/tests') return json([labTest])
    if (path === '/methods') return json([method])
    if (path === '/methods/method1/versions') return json([methodVersion])
    if (path === '/specifications') return json([specification])
    if (path === '/specifications/spec1/versions') return json([specVersion])
    if (path === '/samples') return json([sample])
    if (path === '/samples/sample1') return json(sample)
    if (path === '/samples/sample1/tests') return json([{ ...sampleTest, status: assigned ? 'ASSIGNED' : 'PENDING', current_assignee: assigned ? sampleTest.current_assignee : null }])
    if (path.endsWith('/assignment')) return assigned ? json({ ...meta, id: 'assignment1', sample_test_id: 'sampleTest1', assigned_user_id: 'analyst1', assigned_by_user_id: null, assigned_at: '2026-01-01T00:00:00Z', unassigned_at: null, is_active: true, notes: null }) : json({ detail: 'No assignment' }, 404)
    if (path.endsWith('/results')) return json(resultStatus ? [{ ...meta, id: 'result1', sample_test_id: 'sampleTest1', sequence_number: 1, status: resultStatus, started_at: null, completed_at: null, entered_at: null, entered_by: null, reviewed_at: null, reviewed_by: null, finalized_at: null, finalized_by: null, notes: 'Read-only observation', sample: { id: 'sample1', code: 'QC-001', name: 'QC-001' }, sample_test: { id: 'sampleTest1', code: 'ASSAY', name: 'Assay' }, test: sampleTest.test, method_version: { ...sampleTest.method_version, method_id: 'method1' }, method_parameters: [], parameters: [], instrument_usages: [] }] : [])
    if (path === '/stability-protocols') return json([protocol])
    if (path === '/stability-protocols/protocol1/versions') return json([protocolVersion])
    if (path === '/stability-studies') return json([study])
    if (path === '/stability-studies/study1') return json(study)
    if (path === '/stability-studies/study1/pulls') return json(pulls)
    if (path === '/qc-dashboard/summary') return json({ active_samples: 1, pending_tests: 1, assigned_or_in_progress_tests: 1, awaiting_review: 1, awaiting_finalization: 1, finalized_tests: 1 })
    return json([])
  })
}

function mount(path: string) {
  return render(<AuthProvider><CapabilityProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></CapabilityProvider></AuthProvider>)
}

function expectNoMutations() {
  expect(screen.queryAllByRole('button', { name: /^(Create\b|Register Sample|Edit\b|Delete\b|Activate\b|Deactivate\b|Assign\b|Reassign\b|Unassign\b|Generate Tests|Refresh Generated Tests|Start Result Entry|Save Result|Submit Result|Review Result|Finalize Result|Mark Pulled|Cancel Pull|Cancel Sample|Add\b|Approve\b|Complete\b)/, hidden: true })).toHaveLength(0)
}

const originalAsyncTimeout = getConfig().asyncUtilTimeout
// These routed acceptance tests initialize auth, capabilities, and page lookups.
// Allow slow CI/Windows scheduling without changing the authorization assertions.
beforeAll(() => {
  configure({ asyncUtilTimeout: 5000 })
  vi.setConfig({ testTimeout: 15000 })
})
afterAll(() => {
  configure({ asyncUtilTimeout: originalAsyncTimeout })
  vi.resetConfig()
})
beforeEach(() => { localStorage.clear(); tokenStorage.set('synthetic-test-session'); vi.restoreAllMocks() })
afterEach(cleanup)

it('uses exactly the backend canonical permission specification', () => {
  const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../../backend/app/seeds/demo_viewer.py'), 'utf8')
  const tuple = source.match(/DEMO_VIEWER_PERMISSION_CODES = \(([\s\S]*?)\n\)/)?.[1] ?? ''
  const backendCodes = [...tuple.matchAll(/"([a-z_]+\.view)"/g)].map(match => match[1])
  expect(permissions).toHaveLength(18)
  expect(permissions).toEqual(backendCodes)
})

it('shows product navigation but no Administration navigation', async () => {
  mockApi(); mount('/app')
  const navigation = within(await screen.findByRole('navigation', { name: 'Primary navigation' }))
  await navigation.findByRole('link', { name: 'Instruments' })
  for (const name of ['Masters', 'Laboratory Masters', 'Samples', 'QC Dashboard', 'Instruments', 'Stability Protocols', 'Stability Studies']) {
    expect(navigation.getByRole('link', { name })).toBeTruthy()
  }
  expect(navigation.queryByRole('link', { name: 'Administration' })).toBeNull()
})

it.each(['', '/users', '/roles', '/role-permissions', '/user-roles', '/audit', '/modules'])('denies direct Administration access: %s', async suffix => {
  const fetchMock = mockApi(); mount(`/app/administration${suffix}`)
  expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeTruthy()
  expect(fetchMock.mock.calls.some(([url]) => /\/api\/(users|roles|permissions|audit)/.test(String(url)))).toBe(false)
})

it.each([
  ['/app/masters/manufacturers', 'Preview Manufacturer'],
  ['/app/instruments', 'CH-001'],
  ['/app/laboratory-masters/tests', 'ASSAY'],
  ['/app/laboratory-masters/methods', 'HPLC'],
  ['/app/laboratory-masters/specifications', 'REL'],
  ['/app/samples', 'QC-001'],
  ['/app/stability/protocols', 'STAB'],
  ['/app/stability/studies', 'ST-001'],
])('can browse %s without mutation controls', async (path, label) => {
  mockApi(); mount(path)
  expect(await screen.findByText(label)).toBeTruthy()
  expectNoMutations()
})

it('keeps chamber-profile and draft laboratory/protocol structures read-only', async () => {
  mockApi()
  let page = mount('/app/instruments')
  fireEvent.click(await screen.findByRole('button', { name: 'Chamber Profile' }))
  await screen.findByText('No Stability Chamber Profile configured.')
  expectNoMutations(); page.unmount()
  page = mount('/app/laboratory-masters/methods')
  fireEvent.click(await screen.findByRole('button', { name: 'Versions' }))
  await screen.findByText('Draft method')
  fireEvent.click(screen.getByRole('button', { name: 'Parameters' }))
  await screen.findByText('No parameters configured.')
  expectNoMutations(); page.unmount()
  mount('/app/stability/protocols')
  fireEvent.click(await screen.findByRole('button', { name: 'Versions' }))
  await screen.findByText('Draft protocol')
  fireEvent.click(screen.getByRole('button', { name: 'Structure' }))
  await screen.findByText('No Conditions.')
  expectNoMutations()
})

it.each<ResultStatus>([null, 'DRAFT', 'ENTERED', 'REVIEWED'])('keeps sample assignments and result stage %s read-only', async status => {
  const fetchMock = mockApi(status); mount('/app/samples')
  fireEvent.click(await screen.findByRole('button', { name: 'View' }))
  await screen.findByRole('heading', { name: 'Sample Tests' })
  if (status) {
    const summary = await screen.findByText('Result Entry', { selector: 'summary' })
    fireEvent.click(summary)
    await waitFor(() => expect((screen.getByLabelText('Result Notes') as HTMLTextAreaElement).disabled).toBe(true))
  } else {
    await screen.findByText('No Result has been created.')
  }
  await waitFor(() => expect(screen.getByText('Preview Analyst')).toBeTruthy())
  expectNoMutations()
  expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true)
})

it('cannot assign an unassigned pending test or generate tests', async () => {
  mockApi(null, false); mount('/app/samples')
  fireEvent.click(await screen.findByRole('button', { name: 'View' }))
  await screen.findByRole('heading', { name: 'Sample Tests' })
  await screen.findByText('No Result has been created.')
  expectNoMutations()
})

it('can inspect scheduled and pulled stability operations without executing them', async () => {
  const fetchMock = mockApi(); mount('/app/stability/studies')
  fireEvent.click(await screen.findByRole('button', { name: 'View' }))
  await screen.findByRole('heading', { name: 'Pull Schedule' })
  await screen.findByText('Scheduled', { selector: 'span' })
  await screen.findByText('Pulled', { selector: 'span' })
  expectNoMutations()
  expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true)
})

it('shows operational QC information and omits Review/Finalize workflow sections', async () => {
  const fetchMock = mockApi(); mount('/app/qc-dashboard')
  await screen.findByText('Active Samples')
  expect(screen.getByRole('heading', { name: 'Work Queue' })).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Recent Activity' })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: 'Review & Finalization Queue' })).toBeNull()
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/review-queue'))).toBe(false)
  expectNoMutations()
})
