import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setError(null)
    setIsSubmitting(true)
    try {
      await login(username.trim(), password)
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Sign in failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-heading">
        <header className="login-header">
          <div className="brand-mark" aria-hidden="true">LG</div>
          <div>
            <p className="eyebrow">LabGenius</p>
            <h1 id="login-heading">Welcome back</h1>
            <p className="subtitle">Sign in to continue to your laboratory workspace.</p>
          </div>
        </header>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="username">Username</label>
          <input id="username" name="username" autoComplete="username" required
            value={username} onChange={(event) => setUsername(event.target.value)} />

          <label htmlFor="password">Password</label>
          <input id="password" name="password" type="password" autoComplete="current-password"
            required value={password} onChange={(event) => setPassword(event.target.value)} />

          {error && <p className="form-error" role="alert">{error}</p>}

          <button type="submit" disabled={isSubmitting || !username.trim() || !password}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}
