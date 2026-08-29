import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { changePassword } from '../auth/authApi'

function safePasswordError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === null) return error.message
    if (error.status === 401) return 'Your session is no longer valid. Please sign in again.'
    if (error.status === 403) return 'Password change is not available for this session.'
    if (error.status === 400 || error.status === 422) return error.message
  }
  return 'Password change failed. Please try again.'
}

export function ChangePasswordPage() {
  const { user, refreshUser, logout } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function clearPasswords() {
    setCurrentPassword('')
    setNewPassword('')
    setConfirmation('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    if (newPassword !== confirmation) {
      setError('New password and confirmation do not match.')
      setNewPassword('')
      setConfirmation('')
      return
    }

    setError(null)
    setIsSubmitting(true)
    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmation,
      })
      clearPasswords()
      const refreshedUser = await refreshUser()
      if (refreshedUser.force_password_change) {
        setError('Password changed, but the required-change state could not be confirmed.')
        return
      }
      navigate('/app', { replace: true })
    } catch (passwordError) {
      clearPasswords()
      setError(safePasswordError(passwordError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return <main className="password-page"><section className="password-card" aria-labelledby="password-heading">
    <header><p className="eyebrow">Account security</p><h1 id="password-heading">Change your password</h1>
      <p>{user?.force_password_change
        ? 'You must change your password before entering LabGenius.'
        : 'Choose a new password for your LabGenius account.'}</p></header>
    <p className="policy-note">Use at least 12 characters with uppercase, lowercase, a number, and a special character. The server validates the configured policy.</p>
    <form className="login-form" onSubmit={handleSubmit}>
      <label htmlFor="current-password">Current password</label>
      <input id="current-password" type="password" autoComplete="current-password" required
        value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
      <label htmlFor="new-password">New password</label>
      <input id="new-password" type="password" autoComplete="new-password" required minLength={12}
        value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
      <label htmlFor="confirm-password">Confirm new password</label>
      <input id="confirm-password" type="password" autoComplete="new-password" required minLength={12}
        value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="submit" disabled={isSubmitting || !currentPassword || !newPassword || !confirmation}>
        {isSubmitting ? 'Changing password…' : 'Change password'}
      </button>
      {!user?.force_password_change && <button type="button" className="text-button" onClick={() => navigate('/app')}>Cancel</button>}
      <button type="button" className="text-button" onClick={logout}>Sign out</button>
    </form>
  </section></main>
}
