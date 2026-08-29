import { Navigate, NavLink, Outlet } from 'react-router-dom'
import { useAuthorization } from '../../auth/useAuthorization'

const sections = [
  { to: 'locations', label: 'Locations', permission: 'location.view' },
  { to: 'manufacturers', label: 'Manufacturers', permission: 'manufacturer.view' },
  { to: 'instrument-types', label: 'Instrument types', permission: 'instrument_type.view' },
  { to: 'materials', label: 'Materials', permission: 'material.view' },
] as const
export function MastersLayout() {
  const { hasPermission } = useAuthorization()
  if (!sections.some((section) => hasPermission(section.permission))) return <Navigate to="/not-authorized" replace />
  return <div className="admin-area"><nav className="admin-tabs" aria-label="Masters sections">
    {sections.filter((section) => hasPermission(section.permission)).map((section) => <NavLink key={section.to} to={section.to}>{section.label}</NavLink>)}
  </nav><Outlet /></div>
}

export function MastersIndex() {
  const { hasPermission } = useAuthorization()
  const first = sections.find((section) => hasPermission(section.permission))
  return first ? <Navigate to={first.to} replace /> : <Navigate to="/not-authorized" replace />
}
