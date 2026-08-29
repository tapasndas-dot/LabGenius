import { NavLink, Navigate, Outlet } from 'react-router-dom'
import { ADMINISTRATION_PERMISSIONS } from '../auth/permissions'
import { useAuthorization } from '../auth/useAuthorization'

const sections = [
  { to: 'users', label: 'Users', permissions: ['user.view'] },
  { to: 'roles', label: 'Roles', permissions: ['role.view'] },
  { to: 'role-permissions', label: 'Role permissions', permissions: ['role.view', 'permission.view'], requireAll: true },
  { to: 'user-roles', label: 'User roles', permissions: ['user.view', 'role.view'], requireAll: true },
  { to: 'audit', label: 'Audit', permissions: ['audit.view'] },
] as const

export function AdministrationPage() {
  const { hasAnyPermission } = useAuthorization()
  if (!hasAnyPermission(ADMINISTRATION_PERMISSIONS)) return <Navigate to="/not-authorized" replace />
  return <div className="admin-area"><nav className="admin-tabs" aria-label="Administration sections">
    {sections.filter((section) => 'requireAll' in section ? section.permissions.every((code) => hasAnyPermission([code])) : hasAnyPermission(section.permissions)).map((section) => <NavLink key={section.to} to={section.to}>{section.label}</NavLink>)}
  </nav><Outlet /></div>
}

export function AdministrationIndex() {
  const { hasAnyPermission } = useAuthorization()
  const first = sections.find((section) => 'requireAll' in section ? section.permissions.every((code) => hasAnyPermission([code])) : hasAnyPermission(section.permissions))
  return first ? <Navigate to={first.to} replace /> : <Navigate to="/not-authorized" replace />
}
