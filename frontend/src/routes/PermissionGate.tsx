import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthorization } from '../auth/useAuthorization'

export function PermissionGate({ anyOf, allOf, children }: { anyOf?: readonly string[]; allOf?: readonly string[]; children: ReactNode }) {
  const { hasAnyPermission, hasPermission } = useAuthorization()
  const allowed = (anyOf ? hasAnyPermission(anyOf) : true) && (allOf ? allOf.every(hasPermission) : true)
  return allowed ? children : <Navigate to="/not-authorized" replace />
}
