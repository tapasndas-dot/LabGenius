import { apiRequest } from './client'

export const LOCATION_TYPES = ['SITE', 'BUILDING', 'AREA', 'LABORATORY', 'ROOM', 'STORAGE', 'OTHER'] as const
export const MATERIAL_TYPES = ['RAW_MATERIAL', 'PACKAGING_MATERIAL', 'INTERMEDIATE', 'BULK_PRODUCT', 'FINISHED_PRODUCT', 'REFERENCE_STANDARD', 'REAGENT', 'OTHER'] as const

export type MasterRecord = {
  id: string; organization_id: string; code: string; name: string; description: string | null;
  is_active: boolean; version: number; created_at: string; updated_at: string
}
export type Location = MasterRecord & { parent_location_id: string | null; location_type: typeof LOCATION_TYPES[number] }
export type Manufacturer = MasterRecord & { website: string | null }
export type InstrumentType = MasterRecord
export type Material = MasterRecord & { material_type: typeof MATERIAL_TYPES[number]; default_unit_of_measure: string | null }
export type ListParams = { limit?: number; offset?: number; search?: string; is_active?: boolean; parent_location_id?: string; location_type?: string; material_type?: string }
export type MasterInput = Record<string, string | null>

function query(params: ListParams = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') search.set(key, String(value)) })
  return search.size ? `?${search}` : ''
}

function masterApi<T extends MasterRecord>(path: string) {
  return {
    list: (params?: ListParams) => apiRequest<T[]>(`${path}${query(params)}`),
    get: (id: string) => apiRequest<T>(`${path}/${id}`),
    create: (data: MasterInput) => apiRequest<T>(path, { method: 'POST', body: data }),
    update: (id: string, version: number, data: MasterInput) => apiRequest<T>(`${path}/${id}`, { method: 'PUT', body: { ...data, version } }),
    setActive: (id: string, version: number, active: boolean) => apiRequest<T>(`${path}/${id}/${active ? 'activate' : 'deactivate'}`, { method: 'PUT', body: { version } }),
    remove: (id: string, version: number) => apiRequest<void>(`${path}/${id}`, { method: 'DELETE', body: { version } }),
  }
}

export const locationsApi = masterApi<Location>('/locations')
export const manufacturersApi = masterApi<Manufacturer>('/manufacturers')
export const instrumentTypesApi = masterApi<InstrumentType>('/instrument-types')
export const materialsApi = masterApi<Material>('/materials')
