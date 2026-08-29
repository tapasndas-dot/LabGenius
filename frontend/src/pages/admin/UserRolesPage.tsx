import { useEffect, useState, type FormEvent } from 'react'
import { rolesApi, type Role } from '../../api/roles'
import { usersApi, type User } from '../../api/users'
import { ACCESS_SCOPES, userRolesApi, type AccessScope, type UserRole } from '../../api/userRoles'
import { useAuth } from '../../auth/AuthContext'
import { AdminHeader, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

export function UserRolesPage() {
  const { user: currentUser, refreshUser } = useAuth(); const [users, setUsers] = useState<User[]>([]); const [roles, setRoles] = useState<Role[]>([])
  const [userId, setUserId] = useState(''); const [rows, setRows] = useState<UserRole[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null)
  useEffect(() => { Promise.all([usersApi.list(), rolesApi.list()]).then(([u, r]) => { setUsers(u); setRoles(r); if (u[0]) setUserId(u[0].id) }).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false)) }, [])
  useEffect(() => { if (userId) userRolesApi.list(userId).then(setRows).catch((e) => setError(errorMessage(e))) }, [userId])
  async function mutate(operation: () => Promise<unknown>) { setError(null); try { await operation(); setRows(await userRolesApi.list(userId)); if (userId === currentUser?.id) await refreshUser() } catch (e) { setError(errorMessage(e)) } }
  async function assign(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); await mutate(() => userRolesApi.assign(userId, String(data.get('role_id')), String(data.get('access_scope')) as AccessScope)) }
  return <section className="admin-page"><AdminHeader title="User roles" description="Assignments carry a permission-specific backend-enforced access scope." />
    {error && <ErrorState message={error} />}{loading ? <LoadingState /> : <>
      <label className="standalone-field">User<select value={userId} onChange={(e) => setUserId(e.target.value)}>{users.map((u) => <option key={u.id} value={u.id}>{u.display_name} ({u.username})</option>)}</select></label>
      <form className="inline-form" onSubmit={assign}><label>Role<select name="role_id" required>{roles.filter((r) => r.is_active).map((r) => <option key={r.id} value={r.id}>{r.role_code}</option>)}</select></label>
        <label>Access scope<select name="access_scope" required>{ACCESS_SCOPES.map((scope) => <option key={scope}>{scope}</option>)}</select></label><button>Assign</button></form>
      {rows.length === 0 ? <EmptyState>No role assignments for this user.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Role</th><th>Scope</th><th>Action</th></tr></thead><tbody>
        {rows.map((row) => <tr key={row.id}><td>{roles.find((r) => r.id === row.role_id)?.role_code ?? row.role_id}</td><td>{row.access_scope}</td>
          <td><button type="button" className="small-button danger" onClick={() => void mutate(() => userRolesApi.remove(userId, row.role_id))}>Remove</button></td></tr>)}
      </tbody></table></div>}
    </>}</section>
}
