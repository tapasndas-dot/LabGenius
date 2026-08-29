import { Navigate } from 'react-router-dom'
import { ADMINISTRATION_PERMISSIONS } from '../auth/permissions'
import { useAuthorization } from '../auth/useAuthorization'

export function AdministrationPage() {
  const { hasAnyPermission } = useAuthorization()
  if (!hasAnyPermission(ADMINISTRATION_PERMISSIONS)) return <Navigate to="/not-authorized" replace />
  return <section className="content-card"><p className="eyebrow">Foundation</p>
    <h1>Administration</h1><p>Administration screens will be introduced in Task 15C.</p></section>
}
