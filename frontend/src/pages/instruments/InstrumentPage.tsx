import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiError } from '../../api/client'
import { INSTRUMENT_CRITICALITIES, INSTRUMENT_STATUSES, instrumentsApi, type Instrument, type InstrumentInput } from '../../api/instruments'
import { instrumentTypesApi, locationsApi, manufacturersApi, type MasterRecord } from '../../api/masters'
import { organizationLookupsApi, type BusinessUnitLookup, type DepartmentLookup, type DivisionLookup } from '../../api/organizationLookups'
import { usersApi, type User } from '../../api/users'
import { useAuthorization } from '../../auth/useAuthorization'
import { AdminHeader, ConfirmButton, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

type Lookups = {
  businessUnits: BusinessUnitLookup[]; divisions: DivisionLookup[]; departments: DepartmentLookup[];
  instrumentTypes: MasterRecord[]; manufacturers: MasterRecord[]; locations: MasterRecord[]; users: User[]
}
const emptyLookups: Lookups = { businessUnits: [], divisions: [], departments: [], instrumentTypes: [], manufacturers: [], locations: [], users: [] }
const label = (value: string) => value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())
const masterLabel = (item: MasterRecord) => `${item.code} — ${item.name}`

function initial(record?: Instrument): InstrumentInput {
  return {
    business_unit_id: record?.business_unit_id ?? null, division_id: record?.division_id ?? null,
    department_id: record?.department_id ?? null, instrument_type_id: record?.instrument_type_id ?? '',
    manufacturer_id: record?.manufacturer_id ?? null, location_id: record?.location_id ?? null,
    responsible_user_id: record?.responsible_user_id ?? null, instrument_code: record?.instrument_code ?? '',
    instrument_name: record?.instrument_name ?? '', model_number: record?.model_number ?? null,
    serial_number: record?.serial_number ?? null, description: record?.description ?? null,
    status: record?.status ?? 'AVAILABLE', criticality: record?.criticality ?? null,
    calibration_required: record?.calibration_required ?? false,
    maintenance_required: record?.maintenance_required ?? false,
    qualification_required: record?.qualification_required ?? false,
  }
}

function SelectField({ labelText, value, options, optional = true, unavailable, onChange }: {
  labelText: string; value: string | null; options: Array<{ id: string; text: string }>;
  optional?: boolean; unavailable?: boolean; onChange: (value: string | null) => void
}) {
  const hasCurrent = Boolean(value && !options.some((option) => option.id === value))
  return <label>{labelText}<select aria-label={labelText} value={value ?? ''} required={!optional} disabled={Boolean(unavailable && options.length === 0)} onChange={(event) => onChange(event.target.value || null)}>
    <option value="">{optional ? `No ${labelText.toLowerCase()}` : `Select ${labelText.toLowerCase()}`}</option>
    {hasCurrent && <option value={value ?? ''}>Current assignment (lookup unavailable)</option>}
    {options.map((option) => <option key={option.id} value={option.id}>{option.text}</option>)}
  </select>{unavailable && options.length === 0 && <span className="form-help">Lookup unavailable with your current permissions.</span>}</label>
}

function InstrumentForm({ record, lookups, unavailable, onSave, onCancel }: {
  record?: Instrument; lookups: Lookups; unavailable: Set<string>;
  onSave: (values: InstrumentInput) => Promise<void>; onCancel: () => void
}) {
  const [values, setValues] = useState(() => initial(record)); const [saving, setSaving] = useState(false)
  const set = <K extends keyof InstrumentInput>(key: K, value: InstrumentInput[K]) => setValues((current) => ({ ...current, [key]: value }))
  const divisions = lookups.divisions.filter((item) => !values.business_unit_id || item.business_unit_id === values.business_unit_id)
  const departments = lookups.departments.filter((item) => !values.division_id || item.division_id === values.division_id)
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await onSave(values) } finally { setSaving(false) } }
  return <form className="admin-form form-grid instrument-form" onSubmit={submit}>
    <h2>{record ? `Edit ${record.instrument_code}` : 'Create instrument'}</h2>
    <label>Instrument code<input value={values.instrument_code} required onChange={(e) => set('instrument_code', e.target.value)} /></label>
    <label>Instrument name<input value={values.instrument_name} required onChange={(e) => set('instrument_name', e.target.value)} /></label>
    <SelectField labelText="Business Unit" value={values.business_unit_id} unavailable={unavailable.has('businessUnits')} options={lookups.businessUnits.filter((item) => item.is_active || item.id === values.business_unit_id).map((item) => ({ id: item.id, text: `${item.business_unit_code} — ${item.business_unit_name}` }))} onChange={(value) => setValues((current) => ({ ...current, business_unit_id: value, division_id: null, department_id: null }))} />
    <SelectField labelText="Division" value={values.division_id} unavailable={unavailable.has('divisions')} options={divisions.filter((item) => item.is_active || item.id === values.division_id).map((item) => ({ id: item.id, text: `${item.division_code} — ${item.division_name}` }))} onChange={(value) => setValues((current) => ({ ...current, division_id: value, department_id: null }))} />
    <SelectField labelText="Department" value={values.department_id} unavailable={unavailable.has('departments')} options={departments.filter((item) => item.is_active || item.id === values.department_id).map((item) => ({ id: item.id, text: `${item.department_code} — ${item.department_name}` }))} onChange={(value) => set('department_id', value)} />
    <SelectField labelText="Instrument Type" value={values.instrument_type_id} optional={false} unavailable={unavailable.has('instrumentTypes')} options={lookups.instrumentTypes.filter((item) => item.is_active || item.id === values.instrument_type_id).map((item) => ({ id: item.id, text: masterLabel(item) }))} onChange={(value) => set('instrument_type_id', value ?? '')} />
    <SelectField labelText="Manufacturer" value={values.manufacturer_id} unavailable={unavailable.has('manufacturers')} options={lookups.manufacturers.filter((item) => item.is_active || item.id === values.manufacturer_id).map((item) => ({ id: item.id, text: masterLabel(item) }))} onChange={(value) => set('manufacturer_id', value)} />
    <SelectField labelText="Location" value={values.location_id} unavailable={unavailable.has('locations')} options={lookups.locations.filter((item) => item.is_active || item.id === values.location_id).map((item) => ({ id: item.id, text: masterLabel(item) }))} onChange={(value) => set('location_id', value)} />
    <SelectField labelText="Responsible User" value={values.responsible_user_id} unavailable={unavailable.has('users')} options={lookups.users.map((item) => ({ id: item.id, text: item.display_name || item.username || item.email }))} onChange={(value) => set('responsible_user_id', value)} />
    <label>Model number<input value={values.model_number ?? ''} onChange={(e) => set('model_number', e.target.value || null)} /></label>
    <label>Serial number<input value={values.serial_number ?? ''} onChange={(e) => set('serial_number', e.target.value || null)} /></label>
    <label>Operational status<select value={values.status} onChange={(e) => set('status', e.target.value as InstrumentInput['status'])}>{INSTRUMENT_STATUSES.map((item) => <option key={item} value={item}>{label(item)}</option>)}</select></label>
    <label>Criticality<select value={values.criticality ?? ''} onChange={(e) => set('criticality', (e.target.value || null) as InstrumentInput['criticality'])}><option value="">Not assigned</option>{INSTRUMENT_CRITICALITIES.map((item) => <option key={item} value={item}>{label(item)}</option>)}</select></label>
    <fieldset className="instrument-flags full-width"><legend>Governance requirements</legend>{(['calibration_required', 'maintenance_required', 'qualification_required'] as const).map((key) => <label key={key}><input type="checkbox" checked={values[key]} onChange={(e) => set(key, e.target.checked)} />{label(key)}</label>)}</fieldset>
    <label className="full-width">Description<textarea value={values.description ?? ''} onChange={(e) => set('description', e.target.value || null)} /></label>
    {record && <p className="form-help full-width">Editing version {record.version}. A newer server version will require refresh before saving.</p>}
    <div className="form-actions full-width"><button disabled={saving || !values.instrument_type_id}>{saving ? 'Saving…' : 'Save'}</button><button type="button" className="text-button" onClick={onCancel}>Cancel</button></div>
  </form>
}

export function InstrumentPage() {
  const { hasPermission } = useAuthorization(); const [records, setRecords] = useState<Instrument[]>([])
  const [lookups, setLookups] = useState<Lookups>(emptyLookups); const [unavailable, setUnavailable] = useState(new Set<string>())
  const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null); const [conflict, setConflict] = useState(false)
  const [success, setSuccess] = useState<string | null>(null); const [creating, setCreating] = useState(false); const [editing, setEditing] = useState<Instrument | null>(null)
  const [search, setSearch] = useState(''); const [active, setActive] = useState('all'); const [statusFilter, setStatusFilter] = useState(''); const [typeFilter, setTypeFilter] = useState(''); const [manufacturerFilter, setManufacturerFilter] = useState(''); const [locationFilter, setLocationFilter] = useState(''); const [offset, setOffset] = useState(0); const limit = 20
  const params = useMemo(() => ({ limit, offset, search: search || undefined, is_active: active === 'all' ? undefined : active === 'active', status: statusFilter || undefined, instrument_type_id: typeFilter || undefined, manufacturer_id: manufacturerFilter || undefined, location_id: locationFilter || undefined }), [offset, search, active, statusFilter, typeFilter, manufacturerFilter, locationFilter])
  const load = useCallback(async () => { setLoading(true); setError(null); setConflict(false); try { setRecords(await instrumentsApi.list(params)) } catch (cause) { setError(errorMessage(cause)) } finally { setLoading(false) } }, [params])
  const loadLookups = useCallback(async () => {
    const requests: Array<[keyof Lookups, boolean, () => Promise<unknown[]>]> = [
      ['businessUnits', hasPermission('business_unit.view'), organizationLookupsApi.businessUnits], ['divisions', hasPermission('division.view'), organizationLookupsApi.divisions], ['departments', hasPermission('department.view'), organizationLookupsApi.departments],
      ['instrumentTypes', hasPermission('instrument_type.view'), () => instrumentTypesApi.list({ limit: 500, offset: 0 })], ['manufacturers', hasPermission('manufacturer.view'), () => manufacturersApi.list({ limit: 500, offset: 0 })], ['locations', hasPermission('location.view'), () => locationsApi.list({ limit: 500, offset: 0 })], ['users', hasPermission('user.view'), usersApi.list],
    ]
    const next = { ...emptyLookups }; const missing = new Set<string>()
    await Promise.all(requests.map(async ([key, allowed, request]) => { if (!allowed) { missing.add(key); return } try { (next[key] as unknown[]) = await request() } catch { missing.add(key) } }))
    setLookups(next); setUnavailable(missing)
  }, [hasPermission])
  useEffect(() => { queueMicrotask(() => { void load(); void loadLookups() }) }, [load, loadLookups])
  const lookupName = (kind: keyof Pick<Lookups, 'instrumentTypes' | 'manufacturers' | 'locations'>, id: string | null) => id ? (lookups[kind] as MasterRecord[]).find((item) => item.id === id)?.name ?? 'Assigned (lookup unavailable)' : '—'
  const userName = (id: string | null) => id ? lookups.users.find((item) => item.id === id)?.display_name ?? 'Assigned (lookup unavailable)' : '—'
  async function mutate(operation: () => Promise<unknown>, message: string) { setError(null); setConflict(false); setSuccess(null); try { await operation(); setCreating(false); setEditing(null); setSuccess(message); await load() } catch (cause) { setConflict(cause instanceof ApiError && cause.status === 409); setError(errorMessage(cause)) } }
  return <section className="admin-page"><AdminHeader title="Instrument Registry" description="Manage scoped laboratory instruments and assets. Operational status remains separate from active state." actions={hasPermission('instrument.create') && <button className="small-button" type="button" onClick={() => setCreating(true)}>Create instrument</button>} />
    {error && <><ErrorState message={error} />{conflict && <button className="small-button secondary refresh-button" type="button" onClick={() => void load()}>Refresh current instrument data</button>}</>}{success && <p className="form-success" role="status">{success}</p>}
    {creating && <InstrumentForm lookups={lookups} unavailable={unavailable} onCancel={() => setCreating(false)} onSave={(values) => mutate(() => instrumentsApi.create(values), 'Instrument created.')} />}
    {editing && <InstrumentForm record={editing} lookups={lookups} unavailable={unavailable} onCancel={() => setEditing(null)} onSave={(values) => mutate(() => instrumentsApi.update(editing.id, editing.version, values), 'Instrument updated.')} />}
    <div className="inline-form instrument-filters"><label>Search<input aria-label="Search instruments" value={search} placeholder="Code or name" onChange={(e) => { setOffset(0); setSearch(e.target.value) }} /></label><label>Active state<select aria-label="Active filter" value={active} onChange={(e) => { setOffset(0); setActive(e.target.value) }}><option value="all">All</option><option value="active">Active</option><option value="inactive">Inactive</option></select></label><label>Operational status<select aria-label="Operational status filter" value={statusFilter} onChange={(e) => { setOffset(0); setStatusFilter(e.target.value) }}><option value="">All statuses</option>{INSTRUMENT_STATUSES.map((item) => <option key={item} value={item}>{label(item)}</option>)}</select></label><SelectField labelText="Instrument Type filter" value={typeFilter} options={lookups.instrumentTypes.map((item) => ({ id: item.id, text: masterLabel(item) }))} onChange={(value) => { setOffset(0); setTypeFilter(value ?? '') }} /><SelectField labelText="Manufacturer filter" value={manufacturerFilter} options={lookups.manufacturers.map((item) => ({ id: item.id, text: masterLabel(item) }))} onChange={(value) => { setOffset(0); setManufacturerFilter(value ?? '') }} /><SelectField labelText="Location filter" value={locationFilter} options={lookups.locations.map((item) => ({ id: item.id, text: masterLabel(item) }))} onChange={(value) => { setOffset(0); setLocationFilter(value ?? '') }} /></div>
    {loading ? <LoadingState /> : records.length === 0 ? <EmptyState>No instruments found.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Instrument</th><th>Type</th><th>Manufacturer</th><th>Location</th><th>Status</th><th>Criticality</th><th>Responsible user</th><th>Active</th><th>Version</th><th>Actions</th></tr></thead><tbody>{records.map((record) => <tr key={record.id}><td><strong>{record.instrument_code}</strong><small>{record.instrument_name}</small></td><td>{lookupName('instrumentTypes', record.instrument_type_id)}</td><td>{lookupName('manufacturers', record.manufacturer_id)}</td><td>{lookupName('locations', record.location_id)}</td><td>{label(record.status)}</td><td>{record.criticality ? label(record.criticality) : '—'}</td><td>{userName(record.responsible_user_id)}</td><td><span className={`status-pill ${record.is_active ? 'active' : 'inactive'}`}>{record.is_active ? 'Active' : 'Inactive'}</span></td><td>{record.version}</td><td className="table-actions">{hasPermission('instrument.update') && <><button className="small-button secondary" type="button" onClick={() => setEditing(record)}>Edit</button><ConfirmButton className="small-button secondary" prompt={`${record.is_active ? 'Deactivate' : 'Activate'} ${record.instrument_name}? Operational status will not change.`} onConfirm={() => void mutate(() => instrumentsApi.setActive(record.id, record.version, !record.is_active), `Instrument ${record.is_active ? 'deactivated' : 'activated'}.`)}>{record.is_active ? 'Deactivate' : 'Activate'}</ConfirmButton></>}{hasPermission('instrument.delete') && <ConfirmButton prompt={`Permanently delete ${record.instrument_name}? This cannot be undone.`} onConfirm={() => void mutate(() => instrumentsApi.remove(record.id, record.version), 'Instrument deleted.')}>Delete</ConfirmButton>}</td></tr>)}</tbody></table></div>}
    <div className="pagination"><button className="small-button secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button><span>Records {records.length ? offset + 1 : 0}–{offset + records.length}</span><button className="small-button secondary" disabled={records.length < limit} onClick={() => setOffset(offset + limit)}>Next</button></div>
  </section>
}
