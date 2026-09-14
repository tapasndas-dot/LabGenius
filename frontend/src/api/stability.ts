import { apiRequest } from './client'

export type ProtocolVersionStatus = 'DRAFT' | 'APPROVED' | 'RETIRED' | 'SUPERSEDED'
export type StudyStatus = 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED'
export type PullStatus = 'SCHEDULED' | 'PULLED' | 'SAMPLE_CREATED' | 'CANCELLED'
export type IntervalUnit = 'DAY' | 'WEEK' | 'MONTH' | 'YEAR'
type RecordMeta = { id: string; version: number; created_at: string; updated_at: string }

export type StabilityProtocol = RecordMeta & { organization_id: string; protocol_code: string; protocol_name: string; description: string | null; is_active: boolean }
export type StabilityProtocolVersion = RecordMeta & { stability_protocol_id: string; version_number: number; version_label: string | null; status: ProtocolVersionStatus; effective_from: string | null; effective_to: string | null; description: string | null }
export type StabilityProtocolCondition = RecordMeta & { stability_protocol_version_id: string; sequence_number: number; condition_code: string; condition_name: string; temperature_value: string | null; temperature_unit: string | null; temperature_tolerance: string | null; humidity_value: string | null; humidity_unit: string | null; humidity_tolerance: string | null; description: string | null }
export type StabilityProtocolTimepoint = RecordMeta & { stability_protocol_condition_id: string; sequence_number: number; label: string; interval_value: number | null; interval_unit: IntervalUnit | null; is_initial: boolean; specification_version_id: string; description: string | null }
export type StabilityStudy = RecordMeta & { organization_id: string; business_unit_id: string | null; division_id: string | null; department_id: string | null; study_number: string; study_name: string; material_id: string; stability_protocol_version_id: string; start_date: string | null; status: StudyStatus; batch_number: string | null; lot_number: string | null; notes: string | null }
export type StabilityStudyCondition = RecordMeta & { stability_study_id: string; stability_protocol_condition_id: string; instrument_id: string; assigned_at: string | null; ended_at: string | null; notes: string | null }
export type StabilityPull = RecordMeta & {
  stability_study_id: string
  stability_study_condition_id: string
  stability_protocol_timepoint_id: string
  specification_version_id: string
  scheduled_date: string
  status: PullStatus
  qc_sample_id: string | null
  pulled_at: string | null
  notes: string | null
  protocol_condition: { id: string; code: string; name: string } | null
  timepoint: { id: string; label: string; sequence_number: number; is_initial: boolean } | null
  assigned_instrument: { id: string; code: string; name: string; status: string } | null
  qc_sample: { id: string; sample_number: string; status: string } | null
}
export type StabilityPullFilters = { status?: PullStatus; study_condition_id?: string; scheduled_from?: string; scheduled_to?: string; limit?: number; offset?: number }

export type ProtocolInput = { protocol_code: string; protocol_name: string; description?: string | null }
export type ProtocolVersionInput = { version_number: number; version_label?: string | null; effective_from?: string | null; effective_to?: string | null; description?: string | null }
export type ConditionInput = { sequence_number: number; condition_code: string; condition_name: string; temperature_value?: number | null; temperature_unit?: string | null; temperature_tolerance?: number | null; humidity_value?: number | null; humidity_unit?: string | null; humidity_tolerance?: number | null; description?: string | null }
export type TimepointInput = { sequence_number: number; label: string; interval_value?: number | null; interval_unit?: IntervalUnit | null; is_initial: boolean; specification_version_id: string; description?: string | null }
export type StudyInput = { business_unit_id?: string | null; division_id?: string | null; department_id?: string | null; study_number: string; study_name: string; material_id: string; stability_protocol_version_id: string; start_date?: string | null; batch_number?: string | null; lot_number?: string | null; notes?: string | null }
export type StudyConditionInput = { stability_protocol_condition_id: string; instrument_id: string; assigned_at?: string | null; ended_at?: string | null; notes?: string | null }

const body = (version: number) => ({ version })
const timestamp = (value: string | null | undefined) => value ? new Date(value).toISOString() : value
export const stabilityProtocolsApi = {
  list: () => apiRequest<StabilityProtocol[]>('/stability-protocols'),
  get: (id: string) => apiRequest<StabilityProtocol>(`/stability-protocols/${id}`),
  create: (data: ProtocolInput) => apiRequest<StabilityProtocol>('/stability-protocols', { method: 'POST', body: data }),
  update: (id: string, version: number, data: Partial<ProtocolInput>) => apiRequest<StabilityProtocol>(`/stability-protocols/${id}`, { method: 'PUT', body: { ...data, version } }),
  setActive: (item: StabilityProtocol, active: boolean) => apiRequest<StabilityProtocol>(`/stability-protocols/${item.id}/${active ? 'activate' : 'deactivate'}`, { method: 'POST', body: body(item.version) }),
  remove: (item: StabilityProtocol) => apiRequest<void>(`/stability-protocols/${item.id}`, { method: 'DELETE', body: body(item.version) }),
}
export const stabilityProtocolTreeApi = {
  versions: (p: string) => apiRequest<StabilityProtocolVersion[]>(`/stability-protocols/${p}/versions`),
  createVersion: (p: string, data: ProtocolVersionInput) => apiRequest<StabilityProtocolVersion>(`/stability-protocols/${p}/versions`, { method: 'POST', body: data }),
  updateVersion: (p: string, item: StabilityProtocolVersion, data: Partial<ProtocolVersionInput>) => { const { version_number: _ignored, ...changes } = data; void _ignored; return apiRequest<StabilityProtocolVersion>(`/stability-protocols/${p}/versions/${item.id}`, { method: 'PUT', body: { ...changes, effective_from: timestamp(changes.effective_from), effective_to: timestamp(changes.effective_to), version: item.version } }) },
  lifecycle: (p: string, item: StabilityProtocolVersion, action: 'approve'|'retire'|'supersede') => apiRequest<StabilityProtocolVersion>(`/stability-protocols/${p}/versions/${item.id}/${action}`, { method: 'POST', body: body(item.version) }),
  conditions: (p: string, v: string) => apiRequest<StabilityProtocolCondition[]>(`/stability-protocols/${p}/versions/${v}/conditions`),
  createCondition: (p: string, v: string, data: ConditionInput) => apiRequest<StabilityProtocolCondition>(`/stability-protocols/${p}/versions/${v}/conditions`, { method: 'POST', body: data }),
  updateCondition: (p: string, v: string, item: StabilityProtocolCondition, data: Partial<ConditionInput>) => apiRequest<StabilityProtocolCondition>(`/stability-protocols/${p}/versions/${v}/conditions/${item.id}`, { method: 'PUT', body: { ...data, version: item.version } }),
  removeCondition: (p: string, v: string, item: StabilityProtocolCondition) => apiRequest<void>(`/stability-protocols/${p}/versions/${v}/conditions/${item.id}`, { method: 'DELETE', body: body(item.version) }),
  timepoints: (p: string, v: string, c: string) => apiRequest<StabilityProtocolTimepoint[]>(`/stability-protocols/${p}/versions/${v}/conditions/${c}/timepoints`),
  createTimepoint: (p: string, v: string, c: string, data: TimepointInput) => apiRequest<StabilityProtocolTimepoint>(`/stability-protocols/${p}/versions/${v}/conditions/${c}/timepoints`, { method: 'POST', body: data }),
  updateTimepoint: (p: string, v: string, c: string, item: StabilityProtocolTimepoint, data: Partial<TimepointInput>) => apiRequest<StabilityProtocolTimepoint>(`/stability-protocols/${p}/versions/${v}/conditions/${c}/timepoints/${item.id}`, { method: 'PUT', body: { ...data, version: item.version } }),
  removeTimepoint: (p: string, v: string, c: string, item: StabilityProtocolTimepoint) => apiRequest<void>(`/stability-protocols/${p}/versions/${v}/conditions/${c}/timepoints/${item.id}`, { method: 'DELETE', body: body(item.version) }),
}
export const stabilityStudiesApi = {
  list: () => apiRequest<StabilityStudy[]>('/stability-studies'),
  get: (id: string) => apiRequest<StabilityStudy>(`/stability-studies/${id}`),
  create: (data: StudyInput) => apiRequest<StabilityStudy>('/stability-studies', { method: 'POST', body: data }),
  update: (item: StabilityStudy, data: Partial<StudyInput>) => { const { study_number: _number, material_id: _material, stability_protocol_version_id: _protocol, ...changes } = data; void [_number, _material, _protocol]; return apiRequest<StabilityStudy>(`/stability-studies/${item.id}`, { method: 'PUT', body: { ...changes, version: item.version } }) },
  lifecycle: (item: StabilityStudy, action: 'activate'|'complete'|'cancel') => apiRequest<StabilityStudy>(`/stability-studies/${item.id}/${action}`, { method: 'POST', body: body(item.version) }),
  conditions: (id: string) => apiRequest<StabilityStudyCondition[]>(`/stability-studies/${id}/conditions`),
  createCondition: (id: string, data: StudyConditionInput) => apiRequest<StabilityStudyCondition>(`/stability-studies/${id}/conditions`, { method: 'POST', body: { ...data, assigned_at: timestamp(data.assigned_at), ended_at: timestamp(data.ended_at) } }),
  updateCondition: (study: string, item: StabilityStudyCondition, data: Partial<StudyConditionInput>) => apiRequest<StabilityStudyCondition>(`/stability-studies/${study}/conditions/${item.id}`, { method: 'PUT', body: { ...data, assigned_at: timestamp(data.assigned_at), ended_at: timestamp(data.ended_at), version: item.version } }),
  removeCondition: (study: string, item: StabilityStudyCondition) => apiRequest<void>(`/stability-studies/${study}/conditions/${item.id}`, { method: 'DELETE', body: body(item.version) }),
}

const pullQuery = (filters: StabilityPullFilters = {}) => {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, item]) => {
    if (item !== undefined && item !== '') query.set(key, String(item))
  })
  const value = query.toString()
  return value ? `?${value}` : ''
}

export const stabilityPullsApi = {
  pulls: (studyId: string, filters: StabilityPullFilters = {}) => apiRequest<StabilityPull[]>(`/stability-studies/${studyId}/pulls${pullQuery(filters)}`),
  pull: (studyId: string, pullId: string) => apiRequest<StabilityPull>(`/stability-studies/${studyId}/pulls/${pullId}`),
  markPulled: (studyId: string, pullId: string, version: number, pulledAt: string, notes: string | null) => apiRequest<StabilityPull>(`/stability-studies/${studyId}/pulls/${pullId}/mark-pulled`, { method: 'POST', body: { version, pulled_at: pulledAt, notes } }),
  createPullSample: (studyId: string, pullId: string, version: number, sampleNumber: string) => apiRequest<StabilityPull>(`/stability-studies/${studyId}/pulls/${pullId}/create-sample`, { method: 'POST', body: { version, sample_number: sampleNumber } }),
  cancelPull: (studyId: string, pullId: string, version: number) => apiRequest<StabilityPull>(`/stability-studies/${studyId}/pulls/${pullId}/cancel`, { method: 'POST', body: { version } }),
}
