import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useCapabilities } from '../auth/CapabilityContext'
import { useAuthorization } from '../auth/useAuthorization'

export function CapabilityGate({ capability, permission, children }: { capability: string; permission: string; children: ReactNode }) {
  const { hasCapability, isLoading } = useCapabilities()
  const { hasPermission } = useAuthorization()
  if (isLoading) return <main className="app-loading" aria-label="Loading capabilities"><span /></main>
  return hasCapability(capability) && hasPermission(permission)
    ? children
    : <Navigate to="/not-authorized" replace />
}
