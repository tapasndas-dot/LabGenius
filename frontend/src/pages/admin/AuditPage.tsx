import { useEffect, useState, type FormEvent } from 'react'
import { auditApi, type AuditEvent } from '../../api/audit'
import { AdminHeader, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

const PAGE_SIZE = 25
export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]); const [detail, setDetail] = useState<AuditEvent | null>(null)
  const [offset, setOffset] = useState(0); const [filters, setFilters] = useState({ entity_type: '', action: '' })
  const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null)
  async function load(nextOffset = offset, nextFilters = filters) { setLoading(true); setError(null); try { setEvents(await auditApi.list({ ...nextFilters, limit: PAGE_SIZE, offset: nextOffset })) } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) } }
  // Initial request intentionally uses the initial filter/page snapshot.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { queueMicrotask(() => void load(0, { entity_type: '', action: '' })) }, [])
  function apply(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); const next = { entity_type: String(data.get('entity_type')), action: String(data.get('action')) }; setFilters(next); setOffset(0); void load(0, next) }
  async function show(id: string) { try { setDetail(await auditApi.get(id)) } catch (e) { setError(errorMessage(e)) } }
  function page(next: number) { setOffset(next); void load(next) }
  return <section className="admin-page"><AdminHeader title="Audit" description="Read-only application audit events visible within your backend scope." />
    <form className="inline-form" onSubmit={apply}><label>Entity type<input name="entity_type" placeholder="User" /></label><label>Action<input name="action" placeholder="UPDATE" /></label><button>Apply filters</button></form>
    {error && <ErrorState message={error} />}{loading ? <LoadingState /> : events.length === 0 ? <EmptyState>No audit events match this page and filter.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Occurred</th><th>Action</th><th>Entity</th><th>Actor</th><th>Detail</th></tr></thead><tbody>
      {events.map((item) => <tr key={item.id}><td>{new Date(item.occurred_at).toLocaleString()}</td><td>{item.action}</td><td>{item.entity_type}<small>{item.entity_id ?? 'System/global'}</small></td><td>{item.actor_user_id ?? 'System'}</td><td><button type="button" className="small-button secondary" onClick={() => void show(item.id)}>View</button></td></tr>)}
    </tbody></table></div>}
    <div className="pagination"><button type="button" className="small-button secondary" disabled={offset === 0} onClick={() => page(Math.max(0, offset - PAGE_SIZE))}>Previous</button><span>Page {Math.floor(offset / PAGE_SIZE) + 1}</span><button type="button" className="small-button secondary" disabled={events.length < PAGE_SIZE} onClick={() => page(offset + PAGE_SIZE)}>Next</button></div>
    {detail && <section className="admin-form"><h2>Audit event detail</h2><dl className="record-meta"><dt>ID</dt><dd>{detail.id}</dd><dt>Request</dt><dd>{detail.request_id ?? '—'}</dd><dt>Source</dt><dd>{detail.source}</dd><dt>Reason</dt><dd>{detail.reason ?? '—'}</dd></dl>
      <h3>Changes</h3><pre className="json-view">{JSON.stringify(detail.changes, null, 2)}</pre><button type="button" className="text-button" onClick={() => setDetail(null)}>Close</button></section>}
  </section>
}
