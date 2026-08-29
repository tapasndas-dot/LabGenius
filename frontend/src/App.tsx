import { Navigate, Route, Routes } from 'react-router-dom'
import { ApplicationShell } from './layouts/ApplicationShell'
import { AdministrationPage } from './pages/AdministrationPage'
import { ChangePasswordPage } from './pages/ChangePasswordPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { NotAuthorizedPage } from './pages/NotAuthorizedPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PublicOnlyRoute, RequireAuthenticated, RequireNormalSession } from './routes/RouteGuards'
import { useAuth } from './auth/AuthContext'
import './App.css'

function UnknownRoute() {
  const { user, isInitializing } = useAuth()
  if (isInitializing) return <main className="app-loading" aria-label="Loading application"><span /></main>
  if (user?.force_password_change) return <Navigate to="/change-password" replace />
  return <NotFoundPage />
}

function App() {
  return <Routes>
    <Route element={<PublicOnlyRoute />}><Route path="/login" element={<LoginPage />} /></Route>
    <Route element={<RequireAuthenticated />}>
      <Route path="/change-password" element={<ChangePasswordPage />} />
    </Route>
    <Route element={<RequireNormalSession />}>
      <Route path="/not-authorized" element={<NotAuthorizedPage />} />
      <Route path="/app" element={<ApplicationShell />}>
        <Route index element={<HomePage />} />
        <Route path="administration" element={<AdministrationPage />} />
      </Route>
    </Route>
    <Route path="/" element={<Navigate to="/app" replace />} />
    <Route path="*" element={<UnknownRoute />} />
  </Routes>
}

export default App
