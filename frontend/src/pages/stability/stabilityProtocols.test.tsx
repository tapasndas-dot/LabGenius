// @vitest-environment jsdom
import { afterEach,beforeEach,expect,it,vi } from 'vitest'
import { cleanup,fireEvent,render,screen,waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../App'
import { AuthProvider } from '../../auth/AuthContext'
import { CapabilityProvider } from '../../auth/CapabilityContext'
import { tokenStorage } from '../../auth/tokenStorage'

const meta={created_at:'2026-01-01T00:00:00Z',updated_at:'2026-01-01T00:00:00Z',version:3}
const protocol={...meta,id:'p1',organization_id:'o1',protocol_code:'STAB',protocol_name:'Stability',description:null,is_active:true}
const draft={...meta,id:'v1',stability_protocol_id:'p1',version_number:1,version_label:'Draft',status:'DRAFT',effective_from:null,effective_to:null,description:null}
const approved={...draft,id:'v2',version_number:2,version_label:'Approved',status:'APPROVED'}
const condition={...meta,id:'c1',stability_protocol_version_id:'v1',sequence_number:1,condition_code:'LONG',condition_name:'Long term',temperature_value:'25',temperature_unit:'C',temperature_tolerance:'2',humidity_value:'60',humidity_unit:'RH',humidity_tolerance:'5',description:null}
const timepoint={...meta,id:'t1',stability_protocol_condition_id:'c1',sequence_number:1,label:'Initial',interval_value:null,interval_unit:null,is_initial:true,specification_version_id:'sv1',description:null}
const material={...meta,id:'m1',organization_id:'o1',code:'MAT',name:'Material',description:null,is_active:true,material_type:'OTHER',default_unit_of_measure:null}
const spec={...meta,id:'s1',organization_id:'o1',material_id:'m1',specification_code:'REL',specification_name:'Release',description:null,is_active:true}
const specVersion={...meta,id:'sv1',specification_id:'s1',version_number:1,version_label:null,status:'APPROVED',effective_from:null,effective_to:null,description:null}
const user=(permissions:string[])=>({id:'me',username:'u',email:'u@test',display_name:'User',force_password_change:false,permissions})
const json=(x:unknown,status=200)=>new Response(JSON.stringify(x),{status,headers:{'Content-Type':'application/json'}})
function mock(permissions:string[],enabled=true){return vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{const u=String(input);if(u.endsWith('/auth/me'))return json(user(permissions));if(u.endsWith('/modules/enabled'))return json(enabled?['STABILITY']:[]);if(u.includes('/materials'))return json([material]);if(u==='/api/specifications'||u.startsWith('/api/specifications?'))return json([spec]);if(u.includes('/specifications/s1/versions'))return json([specVersion]);if(u.includes('/conditions/c1/timepoints'))return json([timepoint]);if(u.includes('/versions/v1/conditions'))return json([condition]);if(u.includes('/versions'))return json([draft,approved]);if(u.endsWith('/stability-protocols/p1'))return json(protocol);if(u==='/api/stability-protocols')return json([protocol]);if(init?.method)return json(protocol);return json([])})}
const mount=(path:string)=>render(<AuthProvider><CapabilityProvider><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></CapabilityProvider></AuthProvider>)
beforeEach(()=>{localStorage.clear();tokenStorage.set('token');vi.restoreAllMocks()});afterEach(cleanup)

it('gates Stability Protocol navigation and direct access by capability and permission',async()=>{mock(['stability_protocol.view']);const first=mount('/app');expect(await screen.findByRole('link',{name:'Stability Protocols'})).toBeTruthy();first.unmount();mock(['stability_protocol.view'],false);mount('/app/stability/protocols');expect(await screen.findByRole('heading',{name:'Not authorized'})).toBeTruthy();cleanup();mock(['user.view']);mount('/app/stability/protocols');expect(await screen.findByRole('heading',{name:'Not authorized'})).toBeTruthy()})

it('renders nested structure, approved exact Specification lookup, and keeps view-only users read-only',async()=>{mock(['stability_protocol.view','specification.view','material.view']);mount('/app/stability/protocols');expect(await screen.findByText('STAB')).toBeTruthy();fireEvent.click(screen.getByRole('button',{name:'Versions'}));expect(await screen.findByText('Draft')).toBeTruthy();fireEvent.click(screen.getAllByRole('button',{name:'Structure'})[0]);expect(await screen.findByText(/LONG.*Long term/)).toBeTruthy();fireEvent.click(screen.getByRole('button',{name:'Timepoints'}));expect(await screen.findByText('MAT — Release — Version 1 — APPROVED')).toBeTruthy();expect(screen.queryByRole('button',{name:/Create|Add|Edit|Delete|Approve/})).toBeNull()})

it('uses current server versions for lifecycle and initial Timepoint mutations',async()=>{const fetchMock=mock(['stability_protocol.view','stability_protocol.create','stability_protocol.update','specification.view','material.view']);vi.spyOn(window,'confirm').mockReturnValue(true);mount('/app/stability/protocols');fireEvent.click(await screen.findByRole('button',{name:'Versions'}));fireEvent.click(await screen.findByRole('button',{name:'Approve'}));await waitFor(()=>expect(fetchMock.mock.calls.some(([u])=>String(u).endsWith('/versions/v1/approve'))).toBe(true));const call=fetchMock.mock.calls.find(([u])=>String(u).endsWith('/versions/v1/approve'));expect(JSON.parse(String(call?.[1]?.body))).toEqual({version:3});fireEvent.click((await screen.findAllByRole('button',{name:'Structure'}))[0]);fireEvent.click(await screen.findByRole('button',{name:'Timepoints'}));fireEvent.click(await screen.findByRole('button',{name:'Add Timepoint'}));fireEvent.click(screen.getByLabelText('Initial'));expect((screen.getByLabelText('Interval value') as HTMLInputElement).disabled).toBe(true);expect((screen.getByRole('option',{name:'MAT — Release — Version 1 — APPROVED'}) as HTMLOptionElement).value).toBe('sv1')})
