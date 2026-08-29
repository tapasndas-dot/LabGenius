import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiError } from '../../api/client'
import { instrumentTypesApi, LOCATION_TYPES, locationsApi, manufacturersApi, MATERIAL_TYPES, materialsApi, type MasterInput, type MasterRecord } from '../../api/masters'
import { useAuthorization } from '../../auth/useAuthorization'
import { AdminHeader, ConfirmButton, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'
import { LocationLookup } from '../../components/masters/LookupSelect'

type Kind = 'location' | 'manufacturer' | 'instrument_type' | 'material'
const configs = {
  location: { title: 'Locations', singular: 'location', api: locationsApi, view: 'location.view', create: 'location.create', update: 'location.update', delete: 'location.delete' },
  manufacturer: { title: 'Manufacturers', singular: 'manufacturer', api: manufacturersApi, view: 'manufacturer.view', create: 'manufacturer.create', update: 'manufacturer.update', delete: 'manufacturer.delete' },
  instrument_type: { title: 'Instrument types', singular: 'instrument type', api: instrumentTypesApi, view: 'instrument_type.view', create: 'instrument_type.create', update: 'instrument_type.update', delete: 'instrument_type.delete' },
  material: { title: 'Materials', singular: 'material', api: materialsApi, view: 'material.view', create: 'material.create', update: 'material.update', delete: 'material.delete' },
} as const
type AnyApi = typeof locationsApi

function initial(record?: MasterRecord): Record<string, string> {
  const item = record as MasterRecord & Record<string, unknown> | undefined
  return { code: item?.code ?? '', name: item?.name ?? '', description: item?.description ?? '',
    parent_location_id: String(item?.parent_location_id ?? ''), location_type: String(item?.location_type ?? 'SITE'),
    website: String(item?.website ?? ''), material_type: String(item?.material_type ?? 'RAW_MATERIAL'),
    default_unit_of_measure: String(item?.default_unit_of_measure ?? '') }
}

function entityPayload(kind: Kind, values: Record<string, string>): MasterInput {
  const common: MasterInput = { code: values.code, name: values.name, description: values.description || null }
  if (kind === 'location') return { ...common, parent_location_id: values.parent_location_id || null, location_type: values.location_type }
  if (kind === 'manufacturer') return { ...common, website: values.website || null }
  if (kind === 'material') return { ...common, material_type: values.material_type, default_unit_of_measure: values.default_unit_of_measure || null }
  return common
}

function rowDetails(kind: Kind, item: MasterRecord & Record<string, unknown>, records: MasterRecord[]) {
  if (kind === 'location') {
    const parent = records.find((record) => record.id === item.parent_location_id)
    return `${String(item.location_type).replaceAll('_', ' ')}${item.parent_location_id ? ` · Parent: ${parent ? `${parent.code} — ${parent.name}` : 'assigned location'}` : ' · Root'}`
  }
  return String(item.material_type ?? item.website ?? item.default_unit_of_measure ?? '—').replaceAll('_', ' ')
}

function ExtraFields({ kind, values, set, editingId }: { kind: Kind; values: Record<string, string>; set: (key: string, value: string) => void; editingId?: string }) {
  if (kind === 'location') return <><label>Location type<select value={values.location_type} onChange={(e) => set('location_type', e.target.value)}>{LOCATION_TYPES.map((type) => <option key={type}>{type}</option>)}</select></label><LocationLookup value={values.parent_location_id} onChange={(value) => set('parent_location_id', value)} excludeId={editingId} /></>
  if (kind === 'manufacturer') return <label>Website<input type="url" value={values.website} onChange={(e) => set('website', e.target.value)} /></label>
  if (kind === 'material') return <><label>Material type<select value={values.material_type} onChange={(e) => set('material_type', e.target.value)}>{MATERIAL_TYPES.map((type) => <option key={type}>{type.replaceAll('_', ' ')}</option>)}</select></label><label>Default unit of measure<input value={values.default_unit_of_measure} onChange={(e) => set('default_unit_of_measure', e.target.value)} /></label></>
  return null
}

function MasterForm({ kind, record, onSave, onCancel }: { kind: Kind; record?: MasterRecord; onSave: (data: MasterInput) => Promise<void>; onCancel: () => void }) {
  const [values, setValues] = useState(() => initial(record)); const [saving, setSaving] = useState(false)
  const set = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value }))
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await onSave(entityPayload(kind, values)) } finally { setSaving(false) } }
  return <form className="admin-form form-grid" onSubmit={submit}><h2>{record ? `Edit ${record.code}` : `Create ${configs[kind].singular}`}</h2>
    <label>Code<input value={values.code} onChange={(e) => set('code', e.target.value)} required /></label>
    <label>Name<input value={values.name} onChange={(e) => set('name', e.target.value)} required /></label>
    <ExtraFields kind={kind} values={values} set={set} editingId={record?.id} />
    <label className="full-width">Description<textarea value={values.description} onChange={(e) => set('description', e.target.value)} /></label>
    <div className="form-actions full-width"><button disabled={saving}>{saving ? 'Saving…' : 'Save'}</button><button type="button" className="text-button" onClick={onCancel}>Cancel</button></div>
  </form>
}

export function MasterPage({ kind }: { kind: Kind }) {
  const config = configs[kind]; const api = config.api as AnyApi; const { hasPermission } = useAuthorization()
  const [records, setRecords] = useState<MasterRecord[]>([]); const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null); const [conflict, setConflict] = useState(false); const [success, setSuccess] = useState<string | null>(null)
  const [search, setSearch] = useState(''); const [active, setActive] = useState('all'); const [offset, setOffset] = useState(0)
  const [creating, setCreating] = useState(false); const [editing, setEditing] = useState<MasterRecord | null>(null); const [detail, setDetail] = useState<MasterRecord | null>(null)
  const limit = 20
  const params = useMemo(() => ({ limit, offset, search: search || undefined, is_active: active === 'all' ? undefined : active === 'active' }), [offset, search, active])
  const load = useCallback(async () => { setLoading(true); setError(null); setConflict(false); try { setRecords(await api.list(params)) } catch (cause) { setError(errorMessage(cause)) } finally { setLoading(false) } }, [api, params])
  useEffect(() => { queueMicrotask(() => void load()) }, [load])
  async function mutate(operation: () => Promise<unknown>, message: string) { setError(null); setConflict(false); setSuccess(null); try { await operation(); setSuccess(message); setCreating(false); setEditing(null); setDetail(null); await load() } catch (cause) { setConflict(cause instanceof ApiError && cause.status === 409); setError(errorMessage(cause)) } }
  return <section className="admin-page"><AdminHeader title={config.title} description={`Manage organization ${config.singular} reference records.`} actions={hasPermission(config.create) && <button className="small-button" type="button" onClick={() => setCreating(true)}>Create {config.singular}</button>} />
    {error && <><ErrorState message={error} />{conflict && <button className="small-button secondary refresh-button" type="button" onClick={() => void load()}>Refresh current data</button>}</>}
    {success && <p className="form-success" role="status">{success}</p>}
    {creating && <MasterForm kind={kind} onCancel={() => setCreating(false)} onSave={(data) => mutate(() => api.create(data), `${config.singular} created.`)} />}
    {editing && <MasterForm kind={kind} record={editing} onCancel={() => setEditing(null)} onSave={(data) => mutate(() => api.update(editing.id, editing.version, data), `${config.singular} updated.`)} />}
    <div className="inline-form"><label>Search<input aria-label="Search masters" value={search} onChange={(e) => { setOffset(0); setSearch(e.target.value) }} placeholder="Code or name" /></label><label>Status<select aria-label="Status filter" value={active} onChange={(e) => { setOffset(0); setActive(e.target.value) }}><option value="all">All</option><option value="active">Active</option><option value="inactive">Inactive</option></select></label></div>
    {loading ? <LoadingState /> : records.length === 0 ? <EmptyState>No {config.title.toLowerCase()} found.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>Type / details</th><th>Status</th><th>Version</th><th>Actions</th></tr></thead><tbody>{records.map((record) => { const item = record as MasterRecord & Record<string, unknown>; return <tr key={record.id}><td>{record.code}</td><td><strong>{record.name}</strong><small>{record.description}</small></td><td>{rowDetails(kind, item, records)}</td><td><span className={`status-pill ${record.is_active ? 'active' : 'inactive'}`}>{record.is_active ? 'Active' : 'Inactive'}</span></td><td>{record.version}</td><td className="table-actions"><button className="small-button secondary" type="button" onClick={() => setDetail(record)}>View</button>{hasPermission(config.update) && <><button className="small-button secondary" type="button" onClick={() => setEditing(record)}>Edit</button><ConfirmButton className="small-button secondary" prompt={`${record.is_active ? 'Deactivate' : 'Activate'} ${record.name}?`} onConfirm={() => void mutate(() => api.setActive(record.id, record.version, !record.is_active), `${config.singular} status updated.`)}>{record.is_active ? 'Deactivate' : 'Activate'}</ConfirmButton></>}{hasPermission(config.delete) && <ConfirmButton prompt={`Permanently delete ${record.name}? This cannot be undone.`} onConfirm={() => void mutate(() => api.remove(record.id, record.version), `${config.singular} deleted.`)}>Delete</ConfirmButton>}</td></tr> })}</tbody></table></div>}
    <div className="pagination"><button className="small-button secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button><span>Records {offset + 1}–{offset + records.length}</span><button className="small-button secondary" disabled={records.length < limit} onClick={() => setOffset(offset + limit)}>Next</button></div>
    {detail && <section className="admin-form master-detail"><h2>{detail.code} — {detail.name}</h2><dl className="record-meta">{Object.entries(detail).filter(([key]) => !['organization_id'].includes(key)).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value === null ? '—' : String(value)}</dd></div>)}</dl><button type="button" className="text-button" onClick={() => setDetail(null)}>Close</button></section>}
  </section>
}
