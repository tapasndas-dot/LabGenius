import { useCallback, useEffect, useState } from 'react'
import { modulesApi, type ModuleState } from '../../api/modules'
import { useAuthorization } from '../../auth/useAuthorization'
import { useCapabilities } from '../../auth/CapabilityContext'
import { AdminHeader, ConfirmButton, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

export function ModulesPage() {
  const { hasPermission } = useAuthorization(); const { refreshCapabilities } = useCapabilities()
  const [states, setStates] = useState<ModuleState[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null)
  const load = useCallback(async () => { setLoading(true); try { setStates(await modulesApi.states()); setError(null) } catch (cause) { setError(errorMessage(cause)) } finally { setLoading(false) } }, [])
  useEffect(() => { queueMicrotask(() => void load()) }, [load])
  async function mutate(item: ModuleState) { setError(null); try { if (item.is_enabled) await modulesApi.disable(item.module.code, item.version); else await modulesApi.enable(item.module.code, item.version); await load(); await refreshCapabilities() } catch (cause) { setError(errorMessage(cause)) } }
  return <section className="admin-page"><AdminHeader title="Organization capabilities" description="Enable optional laboratory capabilities independently from user permissions." />
    {error && <ErrorState message={error} />}
    {loading ? <LoadingState /> : states.length === 0 ? <EmptyState>No capabilities are registered.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Capability</th><th>Class</th><th>Dependencies</th><th>Status</th><th>Version</th><th>Actions</th></tr></thead><tbody>{states.map((item) => <tr key={item.module.code}><td><strong>{item.module.name}</strong><small>{item.module.code} · {item.module.description}</small></td><td>{item.module.capability_class.replaceAll('_', ' ')}</td><td>{item.dependencies.join(', ') || 'None'}</td><td>{item.is_enabled ? 'Enabled' : 'Disabled'}{item.module.is_core && <small>Mandatory</small>}</td><td>{item.version || '—'}</td><td className="table-actions">{hasPermission('module.manage') && !item.module.is_core && <ConfirmButton className="small-button secondary" prompt={`${item.is_enabled ? 'Disable' : 'Enable'} ${item.module.name}?`} onConfirm={() => void mutate(item)}>{item.is_enabled ? 'Disable' : 'Enable'}</ConfirmButton>}</td></tr>)}</tbody></table></div>}
  </section>
}
