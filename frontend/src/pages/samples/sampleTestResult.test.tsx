// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AuthProvider } from '../../auth/AuthContext'
import { tokenStorage } from '../../auth/tokenStorage'
import { SampleTestResultPanel } from './SampleTestResultPanel'
import type {
  MethodParameterContext,
  Sample,
  SampleTest,
  SampleTestResult,
} from '../../api/samples'

const dates = {
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  version: 1,
}

const sample = {
  ...dates,
  id: 'sample-1',
  organization_id: 'org',
  business_unit_id: null,
  division_id: null,
  department_id: null,
  sample_number: 'S-001',
  external_reference: null,
  material_id: 'material-1',
  specification_version_id: 'spec-version-1',
  sample_description: null,
  quantity: null,
  quantity_unit: null,
  received_at: null,
  sampled_at: null,
  due_at: null,
  status: 'REGISTERED',
  priority: 'NORMAL',
  notes: null,
} as Sample

const sampleTest = {
  ...dates,
  id: 'sample-test-1',
  sample_id: 'sample-1',
  specification_test_id: 'spec-test-1',
  test_id: 'test-1',
  method_version_id: 'method-version-1',
  sequence_number: 1,
  status: 'ASSIGNED',
  is_required: true,
  display_name: 'Assay',
  test: { id: 'test-1', code: 'ASSAY', name: 'Assay' },
  method_version: {
    id: 'method-version-1',
    code: 'HPLC',
    name: 'HPLC Method',
    version_number: 1,
    status: 'APPROVED',
  },
  current_assignee: { id: 'analyst-1', display_name: 'Analyst One' },
} as SampleTest

const parameters: MethodParameterContext[] = [
  { id:'p-text', code:'OBS', name:'Observation', value_type:'TEXT', unit:null, is_required:true, sequence_number:1 },
  { id:'p-number', code:'ASSAY', name:'Assay Result', value_type:'NUMBER', unit:'%', is_required:true, sequence_number:2 },
  { id:'p-integer', code:'COUNT', name:'Count', value_type:'INTEGER', unit:null, is_required:false, sequence_number:3 },
  { id:'p-boolean', code:'PASS', name:'Appearance Acceptable', value_type:'BOOLEAN', unit:null, is_required:true, sequence_number:4 },
  { id:'p-date', code:'TESTDATE', name:'Test Date', value_type:'DATE', unit:null, is_required:true, sequence_number:5 },
  { id:'p-datetime', code:'TIME', name:'Reading Time', value_type:'DATETIME', unit:null, is_required:true, sequence_number:6 },
]

function result(overrides: Partial<SampleTestResult> = {}): SampleTestResult {
  return {
    ...dates,
    id: 'result-1',
    sample_test_id: sampleTest.id,
    sequence_number: 1,
    status: 'DRAFT',
    started_at: null,
    completed_at: null,
    entered_at: null,
    entered_by: null,
    reviewed_at: null,
    reviewed_by: null,
    finalized_at: null,
    finalized_by: null,
    notes: null,
    sample: { id: sample.id, code: sample.sample_number, name: sample.sample_number },
    sample_test: { id: sampleTest.id, code: 'ASSAY', name: 'Assay' },
    test: { id: 'test-1', code: 'ASSAY', name: 'Assay' },
    method_version: {
      id: 'method-version-1',
      method_id: 'method-1',
      code: 'HPLC',
      name: 'HPLC Method',
      version_number: 1,
    },
    method_parameters: parameters,
    parameters: [],
    instrument_usages: [],
    ...overrides,
  }
}

const user = (permissions: string[]) => ({
  id: 'me',
  username: 'analyst',
  email: 'analyst@test',
  display_name: 'Analyst',
  force_password_change: false,
  permissions,
})

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

function renderPanel() {
  return render(
    <AuthProvider>
      <SampleTestResultPanel sample={sample} sampleTest={sampleTest} />
    </AuthProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  tokenStorage.set('token')
  vi.restoreAllMocks()
})

afterEach(cleanup)

it('creates a draft and exposes all six frozen Method Parameter value types', async () => {
  let current: SampleTestResult | null = null

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith('/auth/me')) {
      return json(user([
        'sample_test_result.view',
        'sample_test_result.create',
        'sample_test_result.update',
        'sample_test_result.submit',
      ]))
    }

    if (url.endsWith('/results') && init?.method === 'POST') {
      current = result()
      return json(current, 201)
    }

    if (url.endsWith('/results')) return json(current ? [current] : [])

    return json([])
  })

  renderPanel()

  expect(await screen.findByText('Not started')).toBeTruthy()

  fireEvent.click(screen.getByRole('button', { name: 'Start Result Entry' }))

  expect(await screen.findByText(/Revision 1/)).toBeTruthy()

  fireEvent.click(screen.getByText('Result Entry'))

  expect(screen.getByLabelText('Observation')).toBeTruthy()
  expect(screen.getByLabelText('Assay Result')).toBeTruthy()
  expect(screen.getByLabelText('Count')).toBeTruthy()
  expect(screen.getByLabelText('Appearance Acceptable')).toBeTruthy()
  expect(screen.getByLabelText('Test Date')).toBeTruthy()
  expect(screen.getByLabelText('Reading Time')).toBeTruthy()

  expect((screen.getByLabelText('Assay Result') as HTMLInputElement).type).toBe('number')
  expect((screen.getByLabelText('Count') as HTMLInputElement).step).toBe('1')
  expect((screen.getByLabelText('Test Date') as HTMLInputElement).type).toBe('date')
  expect((screen.getByLabelText('Reading Time') as HTMLInputElement).type).toBe('datetime-local')
})

it('creates and updates typed values using authoritative returned versions', async () => {
  let current = result()
  const bodies: Record<string, unknown>[] = []

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith('/auth/me')) {
      return json(user([
        'sample_test_result.view',
        'sample_test_result.update',
      ]))
    }

    if (url.endsWith('/results')) return json([current])

    if (url.endsWith('/parameters') && init?.method === 'POST') {
      const body = JSON.parse(String(init.body))
      bodies.push(body)

      current = result({
        version: 2,
        parameters: [{
          ...dates,
          id: 'value-1',
          method_parameter_id: 'p-number',
          parameter: parameters[1],
          value_type: 'NUMBER',
          text_value: null,
          numeric_value: body.numeric_value,
          integer_value: null,
          boolean_value: null,
          date_value: null,
          datetime_value: null,
          version: 3,
        }],
      })

      return json(current, 201)
    }

    if (url.endsWith('/parameters/value-1') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      bodies.push(body)

      current = result({
        version: 3,
        parameters: [{
          ...dates,
          id: 'value-1',
          method_parameter_id: 'p-number',
          parameter: parameters[1],
          value_type: 'NUMBER',
          text_value: null,
          numeric_value: body.numeric_value,
          integer_value: null,
          boolean_value: null,
          date_value: null,
          datetime_value: null,
          version: 4,
        }],
      })

      return json(current)
    }

    return json([])
  })

  renderPanel()

  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))

  fireEvent.change(screen.getByLabelText('Assay Result'), {
    target: { value: '98.7' },
  })

  fireEvent.click(
  screen.getByLabelText('Assay Result')
    .closest('tr')!
    .querySelector('button')!,
    )

  await waitFor(() =>
    expect(bodies[0]).toMatchObject({
      method_parameter_id: 'p-number',
      value_type: 'NUMBER',
      numeric_value: '98.7',
    }),
  )

  fireEvent.change(screen.getByLabelText('Assay Result'), {
    target: { value: '99.2' },
  })

  fireEvent.click(
  screen.getByLabelText('Assay Result')
    .closest('tr')!
    .querySelector('button')!,
    )

  await waitFor(() =>
    expect(bodies[1]).toMatchObject({
      version: 3,
      value_type: 'NUMBER',
      numeric_value: '99.2',
    }),
  )
})

it('saves controlled execution timestamps and clears an optional existing value by deletion', async () => {
  let current = result({
    version: 5,
    started_at: '2026-08-01T04:30:00Z',
    completed_at: '2026-08-01T05:30:00Z',
    parameters: [{
      ...dates,
      id: 'integer-value',
      method_parameter_id: 'p-integer',
      parameter: parameters[2],
      value_type: 'INTEGER',
      text_value: null,
      numeric_value: null,
      integer_value: 7,
      boolean_value: null,
      date_value: null,
      datetime_value: null,
      version: 4,
    }],
  })

  const calls: Array<{ url: string; body: Record<string, unknown> }> = []

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith('/auth/me')) {
      return json(user([
        'sample_test_result.view',
        'sample_test_result.update',
      ]))
    }

    if (url.endsWith('/results')) return json([current])

    if (url.endsWith('/results/result-1') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      calls.push({ url, body })
      current = result({ ...current, ...body, version: 6 })
      return json(current)
    }

    if (url.endsWith('/parameters/integer-value') && init?.method === 'DELETE') {
      const body = JSON.parse(String(init.body))
      calls.push({ url, body })
      current = result({ ...current, version: 7, parameters: [] })
      return json(current)
    }

    return json([])
  })

  renderPanel()

  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))

  fireEvent.change(screen.getByLabelText('Result Started At'), {
    target: { value: '2026-08-02T10:00' },
  })

  fireEvent.change(screen.getByLabelText('Result Completed At'), {
    target: { value: '2026-08-02T11:00' },
  })

  fireEvent.change(screen.getByLabelText('Result Notes'), {
    target: { value: 'Execution complete' },
  })

  fireEvent.click(screen.getByRole('button', { name: 'Save Result Details' }))

  await waitFor(() => expect(calls.length).toBeGreaterThanOrEqual(1))

  expect(calls[0].body.version).toBe(5)
  expect(calls[0].body.notes).toBe('Execution complete')
  expect(String(calls[0].body.started_at)).toContain('2026-08-02')
  expect(String(calls[0].body.completed_at)).toContain('2026-08-02')

  fireEvent.change(screen.getByLabelText('Count'), {
    target: { value: '' },
  })

  fireEvent.click(
  screen.getByLabelText('Count')
    .closest('tr')!
    .querySelector('button')!,
    )

  await waitFor(() =>
    expect(calls.some(call =>
      call.url.endsWith('/parameters/integer-value') &&
      call.body.version === 4,
    )).toBe(true),
  )
})

it('links and removes an Instrument using the contextual Result response', async () => {
  let current = result()
  const calls: string[] = []

  const instrument = {
    ...dates,
    id: 'instrument-1',
    organization_id: 'org',
    business_unit_id: null,
    division_id: null,
    department_id: null,
    instrument_type_id: 'type-1',
    manufacturer_id: null,
    location_id: null,
    responsible_user_id: null,
    instrument_code: 'HPLC-01',
    instrument_name: 'Main HPLC',
    model_number: '1260',
    serial_number: 'SN-001',
    description: null,
    status: 'AVAILABLE',
    criticality: 'HIGH',
    calibration_required: true,
    maintenance_required: true,
    qualification_required: true,
    is_active: true,
  }

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith('/auth/me')) {
      return json(user([
        'sample_test_result.view',
        'sample_test_result.update',
        'instrument.view',
      ]))
    }

    if (url.startsWith('/api/instruments')) return json([instrument])

    if (url.endsWith('/results')) return json([current])

    if (url.endsWith('/instruments') && init?.method === 'POST') {
      calls.push(String(init.body))

      current = result({
        version: 2,
        instrument_usages: [{
          ...dates,
          id: 'usage-1',
          instrument_id: 'instrument-1',
          instrument: {
            id: 'instrument-1',
            code: 'HPLC-01',
            name: 'Main HPLC',
            model_number: '1260',
            serial_number: 'SN-001',
          },
          usage_notes: 'Primary chromatograph',
          version: 3,
        }],
      })

      return json(current, 201)
    }

    if (url.endsWith('/instruments/usage-1') && init?.method === 'DELETE') {
      calls.push(String(init.body))
      current = result({ version: 3, instrument_usages: [] })
      return json(current)
    }

    return json([])
  })

  renderPanel()

  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))

  fireEvent.change(screen.getByLabelText('Instrument Usage Notes'), {
    target: { value: 'Primary chromatograph' },
  })

  fireEvent.change(screen.getByLabelText('Result Instrument'), {
    target: { value: 'instrument-1' },
  })

  expect(await screen.findByRole('cell', { name: /HPLC-01/ })).toBeTruthy()
  expect(calls[0]).toContain('"instrument_id":"instrument-1"')
  expect(screen.queryByRole('button', { name: /Add|Link|Save instrument/i })).toBeNull()

  fireEvent.change(screen.getByLabelText('Result Notes'), {
    target: { value: 'Continued work' },
  })
  expect(screen.getByRole('cell', { name: /HPLC-01/ })).toBeTruthy()

  fireEvent.click(screen.getByRole('button', { name: 'Remove' }))

  await waitFor(() =>
    expect(calls.some(body => body.includes('"version":3'))).toBe(true),
  )
})

it('retains an immediately linked instrument through submission', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  const lookup = {
    ...dates, id: 'instrument-1', instrument_code: 'HPLC-01', instrument_name: 'Main HPLC',
    organization_id: 'org', business_unit_id: null, division_id: null, department_id: null,
    instrument_type_id: 'type-1', manufacturer_id: null, location_id: null,
    responsible_user_id: null, model_number: '1260', serial_number: 'SN-001',
    description: null, status: 'AVAILABLE', criticality: 'HIGH', calibration_required: true,
    maintenance_required: true, qualification_required: true, is_active: true,
  }
  const usage = {
    ...dates, id: 'usage-1', instrument_id: 'instrument-1', version: 1, usage_notes: null,
    instrument: { id: 'instrument-1', code: 'HPLC-01', name: 'Main HPLC', model_number: '1260', serial_number: 'SN-001' },
  }
  let current = result({ version: 4 })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user([
      'sample_test_result.view', 'sample_test_result.update',
      'sample_test_result.submit', 'instrument.view',
    ]))
    if (url.startsWith('/api/instruments')) return json([lookup])
    if (url.endsWith('/results')) return json([current])
    if (url.endsWith('/instruments') && init?.method === 'POST') {
      current = result({ version: 5, instrument_usages: [usage] })
      return json(current, 201)
    }
    if (url.endsWith('/submit') && init?.method === 'POST') {
      current = result({ version: 6, status: 'ENTERED', instrument_usages: [usage] })
      return json(current)
    }
    return json([])
  })

  renderPanel()
  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))
  fireEvent.change(screen.getByLabelText('Result Instrument'), { target: { value: 'instrument-1' } })
  expect(await screen.findByRole('cell', { name: /HPLC-01/ })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Submit Result' }))

  expect(await screen.findByText('Revision 1 — ENTERED')).toBeTruthy()
  expect(screen.getByRole('cell', { name: /HPLC-01/ })).toBeTruthy()
  expect((screen.getByLabelText('Result Notes') as HTMLTextAreaElement).disabled).toBe(true)
})

it('clears a failed transient selection without falsely rendering a link', async () => {
  const lookup = { id: 'instrument-1', instrument_code: 'HPLC-01', instrument_name: 'Main HPLC' }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user([
      'sample_test_result.view', 'sample_test_result.update', 'instrument.view',
    ]))
    if (url.startsWith('/api/instruments')) return json([lookup])
    if (url.endsWith('/results')) return json([result()])
    if (url.endsWith('/instruments') && init?.method === 'POST') {
      return json({ detail: 'Instrument link failed' }, 400)
    }
    return json([])
  })

  renderPanel()
  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))
  fireEvent.change(screen.getByLabelText('Result Instrument'), { target: { value: 'instrument-1' } })

  expect((await screen.findByRole('alert')).textContent).toContain('Instrument link failed')
  expect((screen.getByLabelText('Result Instrument') as HTMLSelectElement).value).toBe('')
  expect(screen.queryByRole('cell', { name: /HPLC-01/ })).toBeNull()
  expect(screen.getByText('No instrument linked.')).toBeTruthy()
})

it('prevents duplicate and concurrent instrument link requests', async () => {
  const lookup = { id: 'instrument-1', instrument_code: 'HPLC-01', instrument_name: 'Main HPLC' }
  let resolveLink!: (response: Response) => void
  const pendingLink = new Promise<Response>(resolve => { resolveLink = resolve })
  let linkCalls = 0
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user([
      'sample_test_result.view', 'sample_test_result.update', 'instrument.view',
    ]))
    if (url.startsWith('/api/instruments')) return json([lookup])
    if (url.endsWith('/results')) return json([result()])
    if (url.endsWith('/instruments') && init?.method === 'POST') {
      linkCalls++
      return pendingLink
    }
    return json([])
  })

  renderPanel()
  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))
  const select = screen.getByLabelText('Result Instrument')
  fireEvent.change(select, { target: { value: 'instrument-1' } })
  fireEvent.change(select, { target: { value: 'instrument-1' } })
  expect(linkCalls).toBe(1)

  resolveLink(json(result({ instrument_usages: [{
    ...dates, id: 'usage-1', instrument_id: 'instrument-1', version: 1, usage_notes: null,
    instrument: { id: 'instrument-1', code: 'HPLC-01', name: 'Main HPLC', model_number: null, serial_number: null },
  }] }), 201))
  expect(await screen.findByRole('cell', { name: /HPLC-01/ })).toBeTruthy()
  expect(screen.queryByRole('option', { name: /HPLC-01/ })).toBeNull()
})

it('submits with the current Result version and becomes read-only from authoritative ENTERED response', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
  let current = result({ version: 8 })
  let submitBody: Record<string, unknown> | null = null

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith('/auth/me')) {
      return json(user([
        'sample_test_result.view',
        'sample_test_result.update',
        'sample_test_result.submit',
      ]))
    }

    if (url.endsWith('/results')) return json([current])

    if (url.endsWith('/submit') && init?.method === 'POST') {
      submitBody = JSON.parse(String(init.body))

      current = result({
        version: 9,
        status: 'ENTERED',
        entered_at: '2026-08-03T10:00:00Z',
        entered_by: { id:'me', display_name:'Analyst' },
      })

      return json(current)
    }

    return json([])
  })

  renderPanel()

  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))

  fireEvent.click(screen.getByRole('button', { name: 'Submit Result' }))

  await waitFor(() => expect(submitBody).toEqual({ version: 8 }))
  expect(confirm).toHaveBeenCalled()

  expect(await screen.findByText('Revision 1 — ENTERED')).toBeTruthy()
  expect(screen.getByText(/submitted and is read-only/i)).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Submit Result' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Save Result Details' })).toBeNull()
})

it('shows explicit 409 recovery without inventing a new version client-side', async () => {
  let listCalls = 0

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith('/auth/me')) {
      return json(user([
        'sample_test_result.view',
        'sample_test_result.update',
      ]))
    }

    if (url.endsWith('/results')) {
      listCalls++
      return json([result({ version: listCalls === 1 ? 4 : 5 })])
    }

    if (url.endsWith('/results/result-1') && init?.method === 'PUT') {
      return json({ detail: 'conflict' }, 409)
    }

    return json([])
  })

  renderPanel()

  await screen.findByText(/Revision 1/)
  fireEvent.click(screen.getByText('Result Entry'))

  fireEvent.change(screen.getByLabelText('Result Notes'), {
    target: { value: 'Concurrent edit' },
  })

  fireEvent.click(screen.getByRole('button', { name: 'Save Result Details' }))

  expect((await screen.findByRole('alert')).textContent).toContain('Result data has changed')

  fireEvent.click(screen.getByRole('button', { name: 'Refresh current Result' }))

  await waitFor(() => expect(listCalls).toBe(2))
  expect(screen.queryByRole('alert')).toBeNull()
})

it.each([
  {
    name: 'DRAFT',
    current: result(),
    permissions: ['sample_test_result.view', 'sample_test_result.update', 'sample_test_result.submit'],
    action: 'Submit Result',
  },
  {
    name: 'ENTERED',
    current: result({
      status: 'ENTERED', entered_at: '2026-09-10T08:00:00Z',
      entered_by: { id: 'analyst-1', display_name: 'Analyst One' },
    }),
    permissions: ['sample_test_result.view', 'sample_test_result.update', 'sample_test_result.review'],
    action: 'Review Result',
  },
  {
    name: 'REVIEWED',
    current: result({
      status: 'REVIEWED', entered_at: '2026-09-10T08:00:00Z',
      entered_by: { id: 'analyst-1', display_name: 'Analyst One' },
      reviewed_at: '2026-09-10T09:00:00Z',
      reviewed_by: { id: 'reviewer-1', display_name: 'Reviewer One' },
    }),
    permissions: ['sample_test_result.view', 'sample_test_result.update', 'sample_test_result.finalize'],
    action: 'Finalize Result',
  },
])('$name exposes only its permitted workflow action and enforces content immutability', async ({ current, permissions, action }) => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(permissions))
    if (url.endsWith('/results')) return json([current])
    return json([])
  })

  renderPanel()
  await screen.findByText(`Revision 1 — ${current.status}`)
  fireEvent.click(screen.getByText('Result Entry'))

  expect(screen.getByRole('button', { name: action })).toBeTruthy()
  expect(screen.queryAllByRole('button', { name: /^(Submit|Review|Finalize) Result$/ })).toHaveLength(1)
  expect((screen.getByLabelText('Result Notes') as HTMLTextAreaElement).disabled).toBe(current.status !== 'DRAFT')
  expect(screen.queryByRole('button', { name: 'Save Result Details' }) !== null).toBe(current.status === 'DRAFT')
})

it('does not infer finalize permission and FINALIZED shows all metadata without actions', async () => {
  const finalized = result({
    status: 'FINALIZED',
    entered_at: '2026-09-10T08:00:00Z', entered_by: { id: 'a', display_name: 'Analyst One' },
    reviewed_at: '2026-09-10T09:00:00Z', reviewed_by: { id: 'r', display_name: 'Reviewer One' },
    finalized_at: '2026-09-10T10:00:00Z', finalized_by: { id: 'f', display_name: 'Finalizer One' },
  })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(['sample_test_result.view', 'sample_test_result.review']))
    if (url.endsWith('/results')) return json([finalized])
    return json([])
  })

  renderPanel()
  await screen.findByText('Revision 1 — FINALIZED')
  fireEvent.click(screen.getByText('Result Entry'))

  const workflow = screen.getByRole('region', { name: 'Result workflow' })
  expect(workflow.textContent).toContain('Entered by Analyst One')
  expect(workflow.textContent).toContain('Reviewed by Reviewer One')
  expect(workflow.textContent).toContain('Finalized by Finalizer One')
  expect(screen.queryByRole('button', { name: /^(Submit|Review|Finalize) Result$/ })).toBeNull()
  expect((screen.getByLabelText('Result Notes') as HTMLTextAreaElement).disabled).toBe(true)
})

it.each([
  { action: 'Review Result', path: '/review', permission: 'sample_test_result.review', from: 'ENTERED', to: 'REVIEWED' },
  { action: 'Finalize Result', path: '/finalize', permission: 'sample_test_result.finalize', from: 'REVIEWED', to: 'FINALIZED' },
])('successful $action sends the current version and applies the authoritative response', async ({ action, path, permission, from, to }) => {
  let current = result({ version: 12, status: from })
  let body: unknown
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(['sample_test_result.view', permission]))
    if (url.endsWith('/results')) return json([current])
    if (url.endsWith(path) && init?.method === 'POST') {
      body = JSON.parse(String(init.body))
      current = result({ version: 13, status: to })
      return json(current)
    }
    return json([])
  })

  renderPanel()
  await screen.findByText(`Revision 1 — ${from}`)
  fireEvent.click(screen.getByText('Result Entry'))
  fireEvent.click(screen.getByRole('button', { name: action }))

  await waitFor(() => expect(body).toEqual({ version: 12 }))
  expect(await screen.findByText(`Revision 1 — ${to}`)).toBeTruthy()
})

it.each([
  { action: 'Review Result', path: '/review', permission: 'sample_test_result.review', from: 'ENTERED' },
  { action: 'Finalize Result', path: '/finalize', permission: 'sample_test_result.finalize', from: 'REVIEWED' },
])('$action 409 reloads the authoritative Result and reports that it was refreshed', async ({ action, path, permission, from }) => {
  const initial = result({ version: 20, status: from })
  const refreshed = result({ version: 21, status: from })
  let detailCalls = 0
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/auth/me')) return json(user(['sample_test_result.view', permission]))
    if (url.endsWith('/results')) return json([initial])
    if (url.endsWith(path) && init?.method === 'POST') return json({ detail: 'conflict' }, 409)
    if (url.endsWith('/results/result-1') && (!init?.method || init.method === 'GET')) {
      detailCalls++
      return json(refreshed)
    }
    return json([])
  })

  renderPanel()
  await screen.findByText(`Revision 1 — ${from}`)
  fireEvent.click(screen.getByText('Result Entry'))
  fireEvent.click(screen.getByRole('button', { name: action }))

  expect((await screen.findByRole('alert')).textContent).toContain('changed and was refreshed')
  expect(detailCalls).toBe(1)
})
