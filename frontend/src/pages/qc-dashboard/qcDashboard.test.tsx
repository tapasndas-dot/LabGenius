// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../App'
import { AuthProvider } from '../../auth/AuthContext'
import { CapabilityProvider } from '../../auth/CapabilityContext'
import { tokenStorage } from '../../auth/tokenStorage'

const summary = {
  active_samples: 6,
  pending_tests: 5,
  assigned_or_in_progress_tests: 4,
  awaiting_review: 3,
  awaiting_finalization: 2,
  finalized_tests: 1,
}
const workRows = [{
  sample_id: 'sample-1', sample_number: 'S-001', sample_status: 'IN_TESTING',
  sample_test_id: 'sample-test-1', sample_test_status: 'IN_PROGRESS', priority: 'HIGH',
  due_at: '2026-09-15T00:00:00Z', material: { id: 'material-1', code: 'MAT-1', name: 'Material One' },
  test: { id: 'test-1', code: 'ASSAY', name: 'Assay' },
  method_version: { id: 'method-version-1', code: 'HPLC', name: 'HPLC Method', version_number: 2 },
  active_assignment: { assignment_id: 'assignment-1', assigned_user_id: 'analyst-1', assigned_user_display_name: 'Analyst One', assigned_at: '2026-09-12T00:00:00Z' },
  result: { result_id: 'result-1', status: 'DRAFT', sequence_number: 1, entered_at: null, reviewed_at: null, finalized_at: null },
}, {
  sample_id: 'sample-2', sample_number: 'S-002', sample_status: 'REGISTERED',
  sample_test_id: 'sample-test-2', sample_test_status: 'PENDING', priority: 'NORMAL', due_at: null,
  material: { id: 'material-2', code: 'MAT-2', name: 'Material Two' },
  test: { id: 'test-2', code: 'IDENT', name: 'Identification' }, method_version: null,
  active_assignment: null, result: null,
}]
const reviewRows = [
  { queue_stage: 'REVIEW', sample_id: 'sample-1', sample_number: 'S-001', sample_test_id: 'sample-test-1', sample_test_status: 'RESULT_ENTERED', result_id: 'result-1', result_status: 'ENTERED', result_version: 3, test: { id: 'test-1', code: 'ASSAY', name: 'Assay' }, method_version: null, assigned_user_display_name: 'Analyst One', entered_at: '2026-09-12T10:00:00Z', entered_by_display_name: 'Analyst One', reviewed_at: null, reviewed_by_display_name: null, due_at: null, priority: 'HIGH' },
  { queue_stage: 'FINALIZE', sample_id: 'sample-2', sample_number: 'S-002', sample_test_id: 'sample-test-2', sample_test_status: 'REVIEWED', result_id: 'result-2', result_status: 'REVIEWED', result_version: 4, test: { id: 'test-2', code: 'IDENT', name: 'Identification' }, method_version: null, assigned_user_display_name: null, entered_at: '2026-09-11T10:00:00Z', entered_by_display_name: 'Analyst Two', reviewed_at: '2026-09-12T12:00:00Z', reviewed_by_display_name: 'Reviewer One', due_at: null, priority: 'NORMAL' },
]
const activityRows = ['SUBMITTED', 'REVIEWED', 'FINALIZED'].map((activity_type, index) => ({ activity_type, occurred_at: `2026-09-1${3-index}T10:00:00Z`, sample_id: `sample-${index}`, sample_number: `S-00${index}`, sample_test_id: `sample-test-${index}`, result_id: `result-${index}`, test: { id: `test-${index}`, code: 'ASSAY', name: 'Assay' }, actor_display_name: index === 2 ? null : `Actor ${index}` }))

const user = (permissions: string[]) => ({ id: 'me', username: 'u', email: 'u@test', display_name: 'User', force_password_change: false, permissions })
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
type MockOptions = { work?: unknown[]; review?: unknown[]; activity?: unknown[]; fail?: string }
function mockApi(permissions: string[], options: MockOptions = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(permissions))
    if (url.endsWith('/modules/enabled')) return json([])
    if (url.includes(options.fail ?? '__never__')) return json({ detail: 'Dashboard unavailable' }, 500)
    if (url.endsWith('/qc-dashboard/summary')) return json(summary)
    if (url.includes('/qc-dashboard/work-queue')) return json(options.work ?? workRows)
    if (url.endsWith('/qc-dashboard/review-queue')) return json(options.review ?? reviewRows)
    if (url.includes('/qc-dashboard/recent-activity')) return json(options.activity ?? activityRows)
    if (url.endsWith('/samples/assignment-users')) return json([{ id: 'analyst-1', display_name: 'Analyst One' }])
    if (url.includes('/business-units')) return json([{ id: 'bu-1', business_unit_code: 'BU-1', business_unit_name: 'Lab', is_active: true }])
    if (url.includes('/divisions')) return json([{ id: 'division-1', business_unit_id: 'bu-1', division_code: 'DIV-1', division_name: 'Quality', is_active: true }])
    if (url.includes('/departments')) return json([{ id: 'department-1', division_id: 'division-1', department_code: 'DEP-1', department_name: 'QC', is_active: true }])
    return json([])
  })
}
const renderPath = (permissions: string[], options?: MockOptions, path = '/app/qc-dashboard') => {
  const fetchMock = mockApi(permissions, options)
  render(<AuthProvider><CapabilityProvider><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></CapabilityProvider></AuthProvider>)
  return fetchMock
}

beforeEach(() => { localStorage.clear(); tokenStorage.set('token'); vi.restoreAllMocks() })
afterEach(cleanup)

it('renders all six authoritative summary KPIs and contextual work values', async () => {
  renderPath(['sample.view'])
  expect(await screen.findByText('Active Samples')).toBeTruthy()
  Object.values(summary).forEach(count => expect(screen.getByText(String(count))).toBeTruthy())
  expect(await screen.findByText('MAT-1 — Material One')).toBeTruthy()
  expect(screen.getByText('HPLC — HPLC Method — Version 2')).toBeTruthy()
  expect(screen.getAllByText('Analyst One').length).toBeGreaterThanOrEqual(1)
  expect(screen.getByText('Draft')).toBeTruthy()
})

it('renders null work fields safely and introduces no dashboard mutation actions', async () => {
  renderPath(['sample.view'])
  expect((await screen.findAllByText('S-002')).length).toBeGreaterThanOrEqual(1)
  expect(screen.getByText('Unassigned')).toBeTruthy()
  expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2)
  expect(screen.queryByRole('button', { name: /assign|review|finalize|edit|delete/i })).toBeNull()
})

it('renders independent work and activity empty states', async () => {
  renderPath(['sample.view'], { work: [], activity: [] })
  expect(await screen.findByText('No authorized work items found.')).toBeTruthy()
  expect(screen.getByText('No recent Result workflow activity.')).toBeTruthy()
})

it('keeps successful sections usable when one dashboard endpoint fails', async () => {
  renderPath(['sample.view'], { fail: '/work-queue' })
  expect((await screen.findByRole('alert')).textContent).toContain('Dashboard unavailable')
  expect(screen.getByText('Active Samples')).toBeTruthy()
  expect(screen.getByText('Submitted')).toBeTruthy()
})

it('passes selected hierarchy, status, assignee, and ISO date filters to the backend', async () => {
  const fetchMock = renderPath(['sample.view', 'business_unit.view', 'division.view', 'department.view'])
  await screen.findAllByText('S-001')
  await screen.findByRole('option', { name: 'Analyst One' })
  fireEvent.change(screen.getByLabelText('Business Unit filter'), { target: { value: 'bu-1' } })
  fireEvent.change(screen.getByLabelText('Division filter'), { target: { value: 'division-1' } })
  fireEvent.change(screen.getByLabelText('Department filter'), { target: { value: 'department-1' } })
  fireEvent.change(screen.getByLabelText('Sample Status filter'), { target: { value: 'REGISTERED' } })
  fireEvent.change(screen.getByLabelText('Sample Test Status filter'), { target: { value: 'ASSIGNED' } })
  fireEvent.change(screen.getByLabelText('Assigned User filter'), { target: { value: 'analyst-1' } })
  fireEvent.change(screen.getByLabelText('Due From'), { target: { value: '2026-09-01' } })
  fireEvent.change(screen.getByLabelText('Due To'), { target: { value: '2026-09-30' } })
  fireEvent.click(screen.getByRole('button', { name: 'Apply Filters' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
    const url = String(input)
    return url.includes('/qc-dashboard/work-queue?') && url.includes('business_unit_id=bu-1') && url.includes('division_id=division-1') && url.includes('department_id=department-1') && url.includes('sample_status=REGISTERED') && url.includes('sample_test_status=ASSIGNED') && url.includes('assigned_user_id=analyst-1') && url.includes('due_from=2026-09-01T00%3A00%3A00Z') && url.includes('due_to=2026-09-30T23%3A59%3A59.999Z')
  })).toBe(true))
  fireEvent.click(screen.getByRole('button', { name: 'Clear Filters' }))
  expect((screen.getByLabelText('Sample Status filter') as HTMLSelectElement).value).toBe('')
})

it.each([['sample_test_result.review'], ['sample_test_result.finalize']])('shows authoritative review and finalize stages with workflow permission %s', async workflowPermission => {
  renderPath(['sample.view', workflowPermission])
  expect(await screen.findByText('Review & Finalization Queue')).toBeTruthy()
  expect(await screen.findByText('Reviewer One')).toBeTruthy()
  expect(screen.getAllByText('Review').length).toBeGreaterThanOrEqual(1)
  expect(screen.getAllByText('Finalize').length).toBeGreaterThanOrEqual(1)
})

it('omits the workflow section and endpoint call without either workflow permission', async () => {
  const fetchMock = renderPath(['sample.view'])
  await screen.findByText('QC Operational Dashboard')
  await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/recent-activity'))).toBe(true))
  expect(screen.queryByText('Review & Finalization Queue')).toBeNull()
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/review-queue'))).toBe(false)
})

it('renders all activity types and requests a newly selected valid limit', async () => {
  const fetchMock = renderPath(['sample.view'])
  expect(await screen.findByText('Submitted')).toBeTruthy()
  expect(screen.getAllByText('Reviewed').length).toBeGreaterThanOrEqual(1)
  expect(screen.getAllByText('Finalized').length).toBeGreaterThanOrEqual(1)
  fireEvent.change(screen.getByLabelText('Activity limit'), { target: { value: '50' } })
  await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/qc-dashboard/recent-activity?limit=50'))).toBe(true))
})

it('gates both the route and navigation with sample.view', async () => {
  renderPath(['user.view'])
  expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeTruthy()
  expect(screen.queryByRole('link', { name: 'QC Dashboard' })).toBeNull()
  cleanup()
  renderPath(['sample.view'], undefined, '/app')
  expect(await screen.findByRole('link', { name: 'QC Dashboard' })).toBeTruthy()
})
