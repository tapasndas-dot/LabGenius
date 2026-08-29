import { apiRequest } from './client'

export const INSTRUMENT_STATUSES = ['AVAILABLE', 'IN_USE', 'UNDER_CALIBRATION', 'UNDER_MAINTENANCE', 'OUT_OF_SERVICE', 'QUALIFICATION_PENDING', 'RETIRED'] as const
export const INSTRUMENT_CRITICALITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const
export type InstrumentStatus = typeof INSTRUMENT_STATUSES[number]
export type InstrumentCriticality = typeof INSTRUMENT_CRITICALITIES[number]

export type Instrument = {
  id: string; organization_id: string; business_unit_id: string | null;
  division_id: string | null; department_id: string | null; instrument_type_id: string;
  manufacturer_id: string | null; location_id: string | null; responsible_user_id: string | null;
  instrument_code: string; instrument_name: string; model_number: string | null;
  serial_number: string | null; description: string | null; status: InstrumentStatus;
  criticality: InstrumentCriticality | null; calibration_required: boolean;
  maintenance_required: boolean; qualification_required: boolean; is_active: boolean;
  version: number; created_at: string; updated_at: string
}
export type InstrumentInput = Omit<Instrument, 'id' | 'organization_id' | 'is_active' | 'version' | 'created_at' | 'updated_at'>
export type InstrumentListParams = Partial<{
  limit: number; offset: number; search: string; is_active: boolean; status: string;
  instrument_type_id: string; manufacturer_id: string; location_id: string
}>

function query(params: InstrumentListParams) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') search.set(key, String(value)) })
  return search.toString() ? `?${search}` : ''
}

export const instrumentsApi = {
  list: (params: InstrumentListParams = {}) => apiRequest<Instrument[]>(`/instruments${query(params)}`),
  get: (id: string) => apiRequest<Instrument>(`/instruments/${id}`),
  create: (data: InstrumentInput) => apiRequest<Instrument>('/instruments', { method: 'POST', body: data }),
  update: (id: string, version: number, data: Partial<InstrumentInput>) => apiRequest<Instrument>(`/instruments/${id}`, { method: 'PUT', body: { ...data, version } }),
  setActive: (id: string, version: number, active: boolean) => apiRequest<Instrument>(`/instruments/${id}/${active ? 'activate' : 'deactivate'}`, { method: 'PUT', body: { version } }),
  remove: (id: string, version: number) => apiRequest<void>(`/instruments/${id}`, { method: 'DELETE', body: { version } }),
}
