import { apiRequest } from './client'
export type ModuleDefinition = { id: string; code: string; name: string; description: string | null; capability_class: string; is_core: boolean; is_active: boolean; version: number; created_at: string; updated_at: string }
export type ModuleState = { module: ModuleDefinition; is_enabled: boolean; version: number; dependencies: string[] }
export const modulesApi = {
  enabled: () => apiRequest<string[]>('/modules/enabled'),
  states: () => apiRequest<ModuleState[]>('/modules/organization'),
  enable: (code: string, version: number) => apiRequest<ModuleState>(`/modules/${code}/enable`, { method: 'PUT', body: { version } }),
  disable: (code: string, version: number) => apiRequest<ModuleState>(`/modules/${code}/disable`, { method: 'PUT', body: { version } }),
}
