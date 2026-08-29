import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { modulesApi } from '../api/modules'
import { useAuth } from './AuthContext'
import { useAuthorization } from './useAuthorization'
import { canUseCapability } from './capabilities'

type CapabilityContextValue = { capabilities: string[]; isLoading: boolean; refreshCapabilities: () => Promise<void>; hasCapability: (code: string) => boolean; canUse: (capability: string, permission: string) => boolean }
const CapabilityContext = createContext<CapabilityContextValue | null>(null)

export function CapabilityProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth(); const { permissions } = useAuthorization()
  const [capabilities, setCapabilities] = useState<string[]>([]); const [isLoading, setLoading] = useState(false)
  const refreshCapabilities = useCallback(async () => {
    if (!user) { setCapabilities([]); return }
    setLoading(true); try { setCapabilities(await modulesApi.enabled()) } catch { setCapabilities([]) } finally { setLoading(false) }
  }, [user])
  useEffect(() => { queueMicrotask(() => void refreshCapabilities()) }, [refreshCapabilities])
  const value = useMemo(() => ({ capabilities, isLoading, refreshCapabilities,
    hasCapability: (code: string) => capabilities.includes(code),
    canUse: (capability: string, permission: string) => canUseCapability(capabilities, permissions, capability, permission),
  }), [capabilities, isLoading, permissions, refreshCapabilities])
  return <CapabilityContext.Provider value={value}>{children}</CapabilityContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCapabilities() { const value = useContext(CapabilityContext); if (!value) throw new Error('useCapabilities must be used within CapabilityProvider.'); return value }
