import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ADMINISTRATION_PERMISSIONS, LABORATORY_MASTER_VIEW_PERMISSIONS, MASTER_VIEW_PERMISSIONS } from '../auth/permissions'
import { useAuthorization } from '../auth/useAuthorization'
import { useCapabilities } from '../auth/CapabilityContext'

export function ApplicationShell() {
  const { user, logout } = useAuth()
  const { hasAnyPermission } = useAuthorization()
  const { canUse } = useCapabilities()
  return <div className="app-shell">
    <header className="app-header">
      <NavLink to="/app" className="product-link" aria-label="LabGenius home">
        <span className="brand-mark" aria-hidden="true">LG</span>
        <span><strong>LabGenius</strong><small>Laboratory workspace</small></span>
      </NavLink>
      <div className="user-menu">
        <span><strong>{user?.display_name}</strong><small>{user?.email}</small></span>
        <button type="button" className="text-button" onClick={logout}>Sign out</button>
      </div>
    </header>
    <div className="app-body">
      <aside className="app-sidebar"><nav aria-label="Primary navigation">
        <NavLink to="/app" end>Home</NavLink>
        {hasAnyPermission(MASTER_VIEW_PERMISSIONS) && <NavLink to="/app/masters">Masters</NavLink>}
        {hasAnyPermission(LABORATORY_MASTER_VIEW_PERMISSIONS) && <NavLink to="/app/laboratory-masters">Laboratory Masters</NavLink>}
        {canUse('INSTRUMENTS', 'instrument.view') && <NavLink to="/app/instruments">Instruments</NavLink>}
        {hasAnyPermission(ADMINISTRATION_PERMISSIONS) && <NavLink to="/app/administration">Administration</NavLink>}
      </nav></aside>
      <main className="app-content"><Outlet /></main>
    </div>
  </div>
}
