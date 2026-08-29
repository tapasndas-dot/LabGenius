import { apiRequest } from '../api/client'
import type { AuthToken, CurrentUser } from './types'

export function authenticate(username: string, password: string): Promise<AuthToken> {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)

  return apiRequest<AuthToken>('/auth/login', {
    method: 'POST',
    authenticated: false,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  })
}

export function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/auth/me')
}
