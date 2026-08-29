import { useCallback, useMemo } from 'react'
import { useAuth } from './AuthContext'

export function hasPermission(permissionCodes: readonly string[], code: string): boolean {
  return permissionCodes.includes(code)
}

export function useAuthorization() {
  const { user } = useAuth()
  const permissions = useMemo(() => user?.permissions ?? [], [user?.permissions])
  const can = useCallback((code: string) => hasPermission(permissions, code), [permissions])
  const canAny = useCallback(
    (codes: readonly string[]) => codes.some((code) => hasPermission(permissions, code)),
    [permissions],
  )
  return { permissions, hasPermission: can, hasAnyPermission: canAny }
}
