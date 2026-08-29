import { useEffect, useState, type FormEvent } from 'react'
import { rolesApi, type Role } from '../../api/roles'
import { useAuth } from '../../auth/AuthContext'
import { useAuthorization } from '../../auth/useAuthorization'
import { AdminHeader, ConfirmButton, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

export function RolesPage() {
  const { refreshUser } = useAuth(); const { hasPermission } = useAuthorization()
  const [roles, setRoles] = useState<Role[]>([]); const [editing, setEditing] = useState<Role | null>(null)
  const [creating, setCreating] = useState(false); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null)
  async function load() { setLoading(true); try { setRoles(await rolesApi.list()) } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) } }
  useEffect(() => { queueMicrotask(() => void load()) }, [])
  async function mutate(operation: () => Promise<unknown>, refreshAuth = false) {
    setError(null); try { await operation(); await load(); if (refreshAuth) await refreshUser() } catch (e) { setError(errorMessage(e)) }
  }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget)
    await mutate(() => rolesApi.create({ role_code: String(data.get('role_code')), role_name: String(data.get('role_name')), description: String(data.get('description')) || null }))
    setCreating(false)
  }
  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!editing) return; const data = new FormData(event.currentTarget)
    await mutate(() => rolesApi.update(editing.id, { role_name: String(data.get('role_name')), description: String(data.get('description')) || null }), true); setEditing(null)
  }
  return <section className="admin-page"><AdminHeader title="Roles" description="Manage the global role catalog and role status."
    actions={hasPermission('role.create') && <button className="small-button" type="button" onClick={() => setCreating(!creating)}>Create role</button>} />
    {error && <ErrorState message={error} />}
    {creating && <form className="admin-form form-grid" onSubmit={create}><h2>Create role</h2>
      <label>Role code<input name="role_code" required /></label><label>Role name<input name="role_name" required /></label>
      <label className="full-width">Description<textarea name="description" /></label><div className="form-actions full-width"><button>Create</button></div></form>}
    {loading ? <LoadingState /> : roles.length === 0 ? <EmptyState>No roles found.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>Status</th><th>Version</th><th>Actions</th></tr></thead><tbody>
      {roles.map((role) => <tr key={role.id}><td>{role.role_code}</td><td><strong>{role.role_name}</strong><small>{role.description}</small></td>
        <td>{role.is_active ? 'Active' : 'Inactive'}</td><td>{role.version}</td><td className="table-actions">
          {hasPermission('role.update') && <><button type="button" className="small-button secondary" onClick={() => setEditing(role)}>Edit</button>
          <ConfirmButton className="small-button secondary" prompt={`${role.is_active ? 'Deactivate' : 'Activate'} ${role.role_name}?`}
            onConfirm={() => void mutate(() => rolesApi.setStatus(role.id, !role.is_active), true)}>{role.is_active ? 'Deactivate' : 'Activate'}</ConfirmButton></>}
        </td></tr>)}
    </tbody></table></div>}
    {editing && <form className="admin-form" onSubmit={update}><h2>Edit {editing.role_code}</h2>
      <label>Role name<input name="role_name" defaultValue={editing.role_name} required /></label>
      <label>Description<textarea name="description" defaultValue={editing.description ?? ''} /></label>
      <div className="form-actions"><button>Save</button><button type="button" className="text-button" onClick={() => setEditing(null)}>Cancel</button></div></form>}
  </section>
}
