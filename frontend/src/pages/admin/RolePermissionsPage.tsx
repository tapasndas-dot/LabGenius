import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { rolesApi, type Permission, type Role, type RolePermission } from '../../api/roles'
import { useAuth } from '../../auth/AuthContext'
import { AdminHeader, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

export function RolePermissionsPage() {
  const { refreshUser } = useAuth(); const [roles, setRoles] = useState<Role[]>([]); const [permissions, setPermissions] = useState<Permission[]>([])
  const [roleId, setRoleId] = useState(''); const [rows, setRows] = useState<RolePermission[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null)
  const assigned = useMemo(() => new Set(rows.map((row) => row.permission_id)), [rows])
  async function initialize() { setLoading(true); try { const [r, p] = await Promise.all([rolesApi.list(), rolesApi.permissions()]); setRoles(r); setPermissions(p); if (r[0]) setRoleId(r[0].id) } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) } }
  useEffect(() => { queueMicrotask(() => void initialize()) }, [])
  useEffect(() => { if (roleId) rolesApi.assignments(roleId).then(setRows).catch((e) => setError(errorMessage(e))) }, [roleId])
  async function mutate(operation: () => Promise<unknown>) { setError(null); try { await operation(); setRows(await rolesApi.assignments(roleId)); await refreshUser() } catch (e) { setError(errorMessage(e)) } }
  async function assign(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const permissionId = String(new FormData(event.currentTarget).get('permission_id')); if (permissionId) await mutate(() => rolesApi.assignPermission(roleId, permissionId)); event.currentTarget.reset() }
  return <section className="admin-page"><AdminHeader title="Role permissions" description="Assign active catalog permissions to a selected role." />
    {error && <ErrorState message={error} />}{loading ? <LoadingState /> : <>
      <label className="standalone-field">Role<select value={roleId} onChange={(e) => setRoleId(e.target.value)}>{roles.map((role) => <option key={role.id} value={role.id}>{role.role_code} — {role.role_name}</option>)}</select></label>
      <form className="inline-form" onSubmit={assign}><label>Available permission<select name="permission_id" required defaultValue=""><option value="" disabled>Select permission</option>
        {permissions.filter((p) => p.is_active && !assigned.has(p.id)).map((p) => <option key={p.id} value={p.id}>{p.permission_code}</option>)}</select></label><button>Assign</button></form>
      {rows.length === 0 ? <EmptyState>No permissions assigned to this role.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Permission</th><th>Name</th><th>Action</th></tr></thead><tbody>
        {rows.map((row) => { const permission = permissions.find((p) => p.id === row.permission_id); return <tr key={row.id}><td>{permission?.permission_code ?? row.permission_id}</td><td>{permission?.permission_name ?? 'Unknown'}</td>
          <td><button type="button" className="small-button danger" onClick={() => void mutate(() => rolesApi.removePermission(roleId, row.permission_id))}>Remove</button></td></tr> })}
      </tbody></table></div>}
    </>}</section>
}
