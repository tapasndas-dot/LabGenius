import { useEffect, useState, type FormEvent } from 'react'
import { usersApi, type User, type UserCreate } from '../../api/users'
import { useAuthorization } from '../../auth/useAuthorization'
import { AdminHeader, ConfirmButton, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

const emptyCreate: UserCreate = {
  organization_id: '', business_unit_id: '', division_id: '', department_id: '', designation_id: '',
  employee_code: '', first_name: '', last_name: '', display_name: '', email: '', username: '',
  password: '', timezone: 'Asia/Kolkata', language: 'en', mobile: null,
}

export function UsersPage() {
  const { hasPermission } = useAuthorization()
  const [users, setUsers] = useState<User[]>([])
  const [selected, setSelected] = useState<User | null>(null)
  const [createData, setCreateData] = useState<UserCreate>(emptyCreate)
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true); setError(null)
    try { setUsers(await usersApi.list()) } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) }
  }
  useEffect(() => { queueMicrotask(() => void load()) }, [])

  async function action(operation: () => Promise<unknown>, success?: () => void) {
    setError(null)
    try { await operation(); success?.(); await load() } catch (e) { setError(errorMessage(e)) }
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    await action(() => usersApi.create(createData), () => { setCreateData(emptyCreate); setShowCreate(false) })
  }

  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return
    const form = new FormData(event.currentTarget)
    await action(() => usersApi.update(selected.id, {
      first_name: String(form.get('first_name')), last_name: String(form.get('last_name')),
      display_name: String(form.get('display_name')), email: String(form.get('email')),
      mobile: String(form.get('mobile')) || null, timezone: String(form.get('timezone')),
      language: String(form.get('language')),
    }), () => setSelected(null))
  }

  function createField(field: keyof UserCreate, label: string, type = 'text') {
    return <label>{label}<input type={type} required value={String(createData[field] ?? '')}
      onChange={(e) => setCreateData({ ...createData, [field]: e.target.value })} /></label>
  }

  return <section className="admin-page">
    <AdminHeader title="Users" description="Users returned here are already filtered by backend organization scope."
      actions={hasPermission('user.create') && <button type="button" className="small-button" onClick={() => setShowCreate(!showCreate)}>Create user</button>} />
    {error && <ErrorState message={error} />}
    {showCreate && <form className="admin-form form-grid" onSubmit={create}>
      <h2>Create user</h2>
      {createField('organization_id', 'Organization ID')}{createField('business_unit_id', 'Business unit ID')}
      {createField('division_id', 'Division ID')}{createField('department_id', 'Department ID')}
      {createField('designation_id', 'Designation ID')}{createField('employee_code', 'Employee code')}
      {createField('first_name', 'First name')}{createField('last_name', 'Last name')}
      {createField('display_name', 'Display name')}{createField('email', 'Email', 'email')}
      {createField('username', 'Username')}{createField('password', 'Temporary password', 'password')}
      <p className="form-help full-width">Hierarchy identifiers must come from authorized organization lookup data. The backend validates their relationship.</p>
      <div className="form-actions full-width"><button type="submit">Create</button><button type="button" className="text-button" onClick={() => setShowCreate(false)}>Cancel</button></div>
    </form>}
    {loading ? <LoadingState /> : users.length === 0 ? <EmptyState>No users are available in your assigned scope.</EmptyState> :
      <div className="table-wrap"><table><thead><tr><th>User</th><th>Status</th><th>Employee</th><th>Actions</th></tr></thead><tbody>
        {users.map((item) => <tr key={item.id}><td><strong>{item.display_name}</strong><small>{item.username} · {item.email}</small></td>
          <td>{item.account_status}</td><td>{item.employee_code}</td><td className="table-actions">
            <button type="button" className="small-button secondary" onClick={() => setSelected(item)}>View/Edit</button>
            {hasPermission('user.update') && <>
              <ConfirmButton prompt={`${item.account_status === 'INACTIVE' ? 'Activate' : 'Deactivate'} ${item.display_name}?`}
                className="small-button secondary" onConfirm={() => void action(() => item.account_status === 'INACTIVE' ? usersApi.activate(item.id) : usersApi.deactivate(item.id))}>
                {item.account_status === 'INACTIVE' ? 'Activate' : 'Deactivate'}
              </ConfirmButton>
              {item.failed_login_attempts > 0 && <button className="small-button secondary" type="button" onClick={() => void action(() => usersApi.unlock(item.id))}>Unlock</button>}
              <button className="small-button secondary" type="button" onClick={() => {
                const password = window.prompt(`Enter a temporary password for ${item.display_name}.`)
                if (password) void action(() => usersApi.resetPassword(item.id, password))
              }}>Reset password</button>
            </>}
            {hasPermission('user.delete') && <ConfirmButton prompt={`Permanently delete ${item.display_name}? This cannot be undone.`}
              onConfirm={() => void action(() => usersApi.remove(item.id))}>Delete</ConfirmButton>}
          </td></tr>)}
      </tbody></table></div>}
    {selected && <form className="admin-form" onSubmit={update}><h2>User details</h2>
      <div className="form-grid"><label>First name<input name="first_name" defaultValue={selected.first_name} required /></label>
      <label>Last name<input name="last_name" defaultValue={selected.last_name} required /></label>
      <label>Display name<input name="display_name" defaultValue={selected.display_name} required /></label>
      <label>Email<input name="email" type="email" defaultValue={selected.email} required /></label>
      <label>Mobile<input name="mobile" defaultValue={selected.mobile ?? ''} /></label>
      <label>Timezone<input name="timezone" defaultValue={selected.timezone} required /></label>
      <label>Language<input name="language" defaultValue={selected.language} required /></label></div>
      <dl className="record-meta"><dt>ID</dt><dd>{selected.id}</dd><dt>Department</dt><dd>{selected.department_id}</dd></dl>
      <div className="form-actions">{hasPermission('user.update') && <button type="submit">Save changes</button>}<button type="button" className="text-button" onClick={() => setSelected(null)}>Close</button></div>
    </form>}
  </section>
}
