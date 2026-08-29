import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

function LoadingScreen() {
  return <main className="app-loading" aria-label="Loading application"><span /></main>
}

export function RequireAuthenticated() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()
  if (isInitializing) return <LoadingScreen />
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function RequireNormalSession() {
  const { user, isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()
  if (isInitializing) return <LoadingScreen />
  if (!isAuthenticated || !user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (user.force_password_change) return <Navigate to="/change-password" replace />
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { user, isAuthenticated, isInitializing } = useAuth()
  if (isInitializing) return <LoadingScreen />
  if (isAuthenticated && user) {
    return <Navigate to={user.force_password_change ? '/change-password' : '/app'} replace />
  }
  return <Outlet />
}
