// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { SampleTestAssignmentPanel } from './SampleTestAssignmentPanel'
import type { Sample, SampleTest, SampleTestAssignment, SampleTestAssignmentMutation } from '../../api/samples'

const dates = { created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', version: 1 }
const sample = { ...dates, id:'sample-1', organization_id:'org', business_unit_id:null, division_id:null, department_id:null, sample_number:'S-1', external_reference:null, material_id:'m', specification_version_id:'sv', sample_description:null, quantity:null, quantity_unit:null, received_at:null, sampled_at:null, due_at:null, status:'REGISTERED', priority:'NORMAL', notes:null } as Sample
const pending = { ...dates, id:'test-1', sample_id:'sample-1', specification_test_id:'st', test_id:'t', method_version_id:null, sequence_number:1, status:'PENDING', is_required:true, display_name:'Assay' } as SampleTest
const users = [
  { id:'user-a', display_name:'User A', account_status:'ACTIVE' },
  { id:'user-b', display_name:'User B', account_status:'ACTIVE' },
  { id:'user-old', display_name:'Former User', account_status:'INACTIVE' },
]
const assignment = (id:string, user:string, version:number, active=true):SampleTestAssignment => ({ ...dates, id, sample_test_id:'test-1', assigned_user_id:user, assigned_by_user_id:'me', assigned_at:'2026-01-01T00:00:00Z', unassigned_at:active?null:'2026-01-02T00:00:00Z', unassigned_by_user_id:active?null:'me', is_active:active, notes:null, version })
const json = (body:unknown, status=200) => new Response(JSON.stringify(body), { status, headers:{'Content-Type':'application/json'} })

function Harness({ initialTest=pending, canAssign=true, initialSample=sample, onRefresh=vi.fn() }:{ initialTest?:SampleTest; canAssign?:boolean; initialSample?:Sample; onRefresh?:()=>SampleTest|void }) {
  const [test, setTest] = useState(initialTest)
  const reconcile = async (result?:SampleTestAssignmentMutation) => { if (result) setTest(result.sample_test); else { const refreshed=onRefresh();if(refreshed)setTest(refreshed) } }
  return <SampleTestAssignmentPanel sample={initialSample} sampleTest={test} users={users} canAssign={canAssign} onReconciled={reconcile}/>
}

beforeEach(() => vi.restoreAllMocks())
afterEach(cleanup)

it('lets sample.view inspect human-readable immutable assignment history without mutation controls', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => String(input).endsWith('/assignment-history')
    ? json([assignment('old','user-old',2,false), assignment('active','user-a',3)])
    : json(assignment('active','user-a',3)))
  render(<Harness initialTest={{...pending,status:'ASSIGNED'}} canAssign={false}/>)
  expect((await screen.findAllByText(/User A/)).length).toBeGreaterThan(0)
  fireEvent.click(screen.getByText('Assignment History'))
  expect(await screen.findByText('Former User')).toBeTruthy()
  expect(screen.getByText('Active')).toBeTruthy()
  expect(screen.getByText('Inactive')).toBeTruthy()
  expect(screen.queryByRole('button',{name:'Assign'})).toBeNull()
  expect(screen.queryByRole('button',{name:'Reassign'})).toBeNull()
  expect(screen.queryByRole('button',{name:'Unassign'})).toBeNull()
  expect(screen.queryByRole('button',{name:/Edit|Delete/})).toBeNull()
})

it('assigns then immediately reassigns with authoritative SampleTest and Assignment versions', async () => {
  let current:SampleTestAssignment|null = null
  let history:SampleTestAssignment[] = []
  const calls:Array<Record<string,unknown>> = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url=String(input)
    if (url.endsWith('/assignment-history')) return json(history)
    if (url.endsWith('/assignment')) return current ? json(current) : json({detail:'not found'},404)
    const body=JSON.parse(String(init?.body));calls.push(body)
    if (url.endsWith('/assign')) { current=assignment('a1','user-a',1);history=[current];return json({sample_test:{...pending,status:'ASSIGNED',version:2},assignment:current}) }
    current=assignment('a2','user-b',1);history=[current,assignment('a1','user-a',2,false)];return json({sample_test:{...pending,status:'ASSIGNED',version:3},assignment:current})
  })
  render(<Harness/>)
  expect(await screen.findByText(/Unassigned/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button',{name:'Assign'}))
  expect(screen.queryByRole('option',{name:'Former User'})).toBeNull()
  fireEvent.change(screen.getByLabelText('Assignee'),{target:{value:'user-a'}})
  fireEvent.click(screen.getByRole('button',{name:'Assign'}))
  expect((await screen.findAllByText(/User A/)).length).toBeGreaterThan(0)
  fireEvent.click(screen.getByRole('button',{name:'Reassign'}))
  fireEvent.change(screen.getByLabelText('Assignee'),{target:{value:'user-b'}})
  fireEvent.click(screen.getByRole('button',{name:'Reassign'}))
  expect((await screen.findAllByText(/User B/)).length).toBeGreaterThan(0)
  expect(calls[0]).toMatchObject({assigned_user_id:'user-a',expected_sample_test_version:1})
  expect(calls[1]).toMatchObject({assigned_user_id:'user-b',expected_sample_test_version:2,expected_assignment_version:1})
  fireEvent.click(screen.getByText('Assignment History'))
  expect(await screen.findByText('User A')).toBeTruthy()
})

it('confirms unassign and retains history while applying authoritative PENDING state', async () => {
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(true)
  let current:SampleTestAssignment|null=assignment('a1','user-a',4)
  let history:SampleTestAssignment[]=[current]
  let sent:Record<string,unknown>|undefined
  vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{const url=String(input);if(url.endsWith('/assignment-history'))return json(history);if(url.endsWith('/assignment'))return current?json(current):json({detail:'not found'},404);sent=JSON.parse(String(init?.body));history=[assignment('a1','user-a',5,false)];current=null;return json({sample_test:{...pending,status:'PENDING',version:8},assignment:null})})
  render(<Harness initialTest={{...pending,status:'ASSIGNED',version:7}}/>)
  fireEvent.click(await screen.findByRole('button',{name:'Unassign'}))
  await screen.findByText(/Unassigned/)
  expect(confirm).toHaveBeenCalled()
  expect(sent).toEqual({expected_sample_test_version:7,expected_assignment_version:4})
  expect(screen.getByRole('button',{name:'Assign'})).toBeTruthy()
  fireEvent.click(screen.getByText('Assignment History'))
  expect(await screen.findByText('Inactive')).toBeTruthy()
})

it('shows readable 409 recovery, refreshes explicitly, and suppresses controls for finalized Samples', async () => {
  const refreshed=vi.fn(()=>({...pending,version:5}))
  let attempts=0
  const bodies:Record<string,unknown>[]=[]
  vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{const url=String(input);if(url.endsWith('/assignment-history'))return json([]);if(url.endsWith('/assignment'))return json({detail:'not found'},404);if(init?.method==='POST'){attempts++;bodies.push(JSON.parse(String(init.body)));if(attempts===1)return json({detail:'conflict'},409);return json({sample_test:{...pending,status:'ASSIGNED',version:6},assignment:assignment('fresh','user-a',1)})}return json([])})
  const {rerender}=render(<Harness onRefresh={refreshed}/>)
  fireEvent.click(await screen.findByRole('button',{name:'Assign'}));fireEvent.change(screen.getByLabelText('Assignee'),{target:{value:'user-a'}});fireEvent.click(screen.getByRole('button',{name:'Assign'}))
  expect((await screen.findByRole('alert')).textContent).toContain('Assignment has changed')
  fireEvent.click(screen.getByRole('button',{name:'Refresh current Sample data'}))
  await waitFor(()=>expect(refreshed).toHaveBeenCalled())
  expect(attempts).toBe(1)
  fireEvent.click(screen.getByRole('button',{name:'Assign'}))
  await waitFor(()=>expect(attempts).toBe(2))
  expect(bodies[1].expected_sample_test_version).toBe(5)
  expect(screen.queryByRole('alert')).toBeNull()
  rerender(<Harness initialSample={{...sample,status:'FINALIZED'}}/>)
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Assign'})).toBeNull())
})
