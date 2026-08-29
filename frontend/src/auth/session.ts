import { authenticate, getCurrentUser } from './authApi'
import { ApiError } from '../api/client'
import { tokenStorage } from './tokenStorage'
import type { CurrentUser } from './types'

export async function loginSession(username: string, password: string): Promise<CurrentUser> {
  const token = await authenticate(username, password)
  tokenStorage.set(token.access_token)
  try {
    return await getCurrentUser()
  } catch (error) {
    tokenStorage.clear()
    throw error
  }
}

export async function restoreSession(): Promise<CurrentUser | null> {
  if (!tokenStorage.get()) return null
  try {
    return await getCurrentUser()
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      tokenStorage.clear()
    }
    return null
  }
}

export function logoutSession(): void {
  tokenStorage.clear()
}
