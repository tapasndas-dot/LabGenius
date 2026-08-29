import { useAuth } from './auth/AuthContext'
import { LoginPage } from './pages/LoginPage'
import './App.css'

function App() {
  const { user, isAuthenticated, isInitializing, logout } = useAuth()

  if (isInitializing) return <main className="app-loading" aria-label="Loading application"><span /></main>
  if (!isAuthenticated || !user) return <LoginPage />

  return <main className="session-page">
    <section className="session-card">
      <p className="eyebrow">Authenticated</p>
      <h1>Hello, {user.display_name}</h1>
      <p>Your LabGenius session is ready. Application routing follows in Task 15B.</p>
      {user.force_password_change && <p className="form-error">A password change is required.</p>}
      <button type="button" className="secondary-button" onClick={logout}>Sign out</button>
    </section>
  </main>
}

export default App
