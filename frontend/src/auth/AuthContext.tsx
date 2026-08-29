import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ApiError, setUnauthorizedHandler } from '../api/client'
import { getCurrentUser } from './authApi'
import { loginSession, logoutSession, restoreSession } from './session'
import { tokenStorage } from './tokenStorage'
import type { CurrentUser } from './types'

type AuthContextValue = {
  user: CurrentUser | null
  isAuthenticated: boolean
  isInitializing: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<CurrentUser>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function safeLoginMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'Sign in failed. Please try again.'
  }
  if (error.status === null) {
    return error.message
  }
  if (error.status === 401) {
    return 'Invalid username or password.'
  }
  if (error.status === 403) {
    return 'This account is not allowed to sign in here.'
  }
  return 'Sign in failed. Please try again.'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)

  const logout = useCallback(() => {
    logoutSession()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)
      return currentUser
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        logout()
      }
      throw error
    }
  }, [logout])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(undefined)
  }, [logout])

  useEffect(() => {
    let active = true

    async function initializeSession() {
      try {
        const currentUser = await restoreSession()
        if (active) setUser(currentUser)
      } finally {
        if (active) setIsInitializing(false)
      }
    }

    void initializeSession()
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    try {
      setUser(await loginSession(username, password))
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        tokenStorage.clear()
      }
      setUser(null)
      throw new Error(safeLoginMessage(error), { cause: error })
    }
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isAuthenticated: user !== null,
    isInitializing,
    login,
    logout,
    refreshUser,
  }), [isInitializing, login, logout, refreshUser, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Kept beside the provider until Task 15B introduces the broader routing module.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider.')
  return context
}
