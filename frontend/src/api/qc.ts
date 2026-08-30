import { apiRequest } from './client'

export const VERSION_STATUSES = ['DRAFT', 'APPROVED', 'RETIRED', 'SUPERSEDED'] as const
export const PARAMETER_TYPES = ['TEXT', 'NUMBER', 'INTEGER', 'BOOLEAN', 'DATE', 'DATETIME'] as const
export const CRITERIA = ['BETWEEN', 'MINIMUM', 'MAXIMUM', 'EQUAL', 'TEXT_MATCH', 'BOOLEAN', 'INFORMATIONAL'] as const
export type VersionStatus = typeof VERSION_STATUSES[number]
export type ParameterType = typeof PARAMETER_TYPES[number]
export type Criterion = typeof CRITERIA[number]
type Dates = { created_at: string; updated_at: string; version: number }
export type Test = Dates & { id: string; organization_id: string; test_code: string; test_name: string; description: string | null; test_category: string | null; default_unit: string | null; is_active: boolean }
export type Method = Dates & { id: string; organization_id: string; method_code: string; method_name: string; description: string | null; is_active: boolean }
export type MethodVersion = Dates & { id: string; method_id: string; version_number: number; version_label: string | null; status: VersionStatus; effective_from: string | null; effective_to: string | null; source_reference: string | null; description: string | null }
export type MethodParameter = Dates & { id: string; method_version_id: string; parameter_code: string; parameter_name: string; value_type: ParameterType; unit: string | null; default_value: string | null; sequence_number: number | null; is_required: boolean; description: string | null }
export type Specification = Dates & { id: string; organization_id: string; material_id: string; specification_code: string; specification_name: string; description: string | null; is_active: boolean }
export type SpecificationVersion = Dates & { id: string; specification_id: string; version_number: number; version_label: string | null; status: VersionStatus; effective_from: string | null; effective_to: string | null; description: string | null }
export type SpecificationTest = Dates & { id: string; specification_version_id: string; test_id: string; method_version_id: string | null; sequence_number: number; is_required: boolean; display_name: string | null; instructions: string | null }
export type SpecificationLimit = Dates & { id: string; specification_test_id: string; parameter_name: string | null; criterion_type: string; lower_limit: string | null; upper_limit: string | null; target_value: string | null; text_value: string | null; boolean_value: boolean | null; unit: string | null; sequence_number: number | null; description: string | null }
export type Input = Record<string, string | number | boolean | null>

function query(params: Record<string, unknown> = {}) { const q = new URLSearchParams(); Object.entries(params).forEach(([k,v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) }); return q.size ? `?${q}` : '' }
function headerApi<T>(path: string) { return {
  list: (params: Record<string, unknown> = {}) => apiRequest<T[]>(`${path}${query(params)}`),
  create: (data: Input) => apiRequest<T>(path, { method: 'POST', body: data }),
  update: (id: string, version: number, data: Input) => apiRequest<T>(`${path}/${id}`, { method: 'PUT', body: { ...data, version } }),
  setActive: (id: string, version: number, active: boolean) => apiRequest<T>(`${path}/${id}/${active ? 'activate' : 'deactivate'}`, { method: 'POST', body: { version } }),
  remove: (id: string, version: number) => apiRequest<void>(`${path}/${id}`, { method: 'DELETE', body: { version } }),
} }
export const testsApi = headerApi<Test>('/tests')
export const methodsApi = headerApi<Method>('/methods')
export const specificationsApi = headerApi<Specification>('/specifications')

export const methodTreeApi = {
  versions: (methodId: string) => apiRequest<MethodVersion[]>(`/methods/${methodId}/versions`),
  createVersion: (methodId: string, data: Input) => apiRequest<MethodVersion>(`/methods/${methodId}/versions`, { method: 'POST', body: data }),
  updateVersion: (methodId: string, id: string, version: number, data: Input) => apiRequest<MethodVersion>(`/methods/${methodId}/versions/${id}`, { method: 'PUT', body: { ...data, version } }),
  lifecycle: (methodId: string, item: MethodVersion, action: 'approve'|'retire'|'supersede') => apiRequest<MethodVersion>(`/methods/${methodId}/versions/${item.id}/${action}`, { method: 'POST', body: { version: item.version } }),
  parameters: (methodId: string, versionId: string) => apiRequest<MethodParameter[]>(`/methods/${methodId}/versions/${versionId}/parameters`),
  createParameter: (methodId: string, versionId: string, data: Input) => apiRequest<MethodParameter>(`/methods/${methodId}/versions/${versionId}/parameters`, { method: 'POST', body: data }),
  updateParameter: (methodId: string, versionId: string, id: string, version: number, data: Input) => apiRequest<MethodParameter>(`/methods/${methodId}/versions/${versionId}/parameters/${id}`, { method: 'PUT', body: { ...data, version } }),
  removeParameter: (methodId: string, versionId: string, id: string, version: number) => apiRequest<void>(`/methods/${methodId}/versions/${versionId}/parameters/${id}`, { method: 'DELETE', body: { version } }),
}
export const specificationTreeApi = {
  versions: (specId: string) => apiRequest<SpecificationVersion[]>(`/specifications/${specId}/versions`),
  createVersion: (specId: string, data: Input) => apiRequest<SpecificationVersion>(`/specifications/${specId}/versions`, { method: 'POST', body: data }),
  updateVersion: (specId: string, id: string, version: number, data: Input) => apiRequest<SpecificationVersion>(`/specifications/${specId}/versions/${id}`, { method: 'PUT', body: { ...data, version } }),
  lifecycle: (specId: string, item: SpecificationVersion, action: 'approve'|'retire'|'supersede') => apiRequest<SpecificationVersion>(`/specifications/${specId}/versions/${item.id}/${action}`, { method: 'POST', body: { version: item.version } }),
  tests: (specId: string, versionId: string) => apiRequest<SpecificationTest[]>(`/specifications/${specId}/versions/${versionId}/tests`),
  createTest: (specId: string, versionId: string, data: Input) => apiRequest<SpecificationTest>(`/specifications/${specId}/versions/${versionId}/tests`, { method: 'POST', body: data }),
  updateTest: (specId: string, versionId: string, id: string, version: number, data: Input) => apiRequest<SpecificationTest>(`/specifications/${specId}/versions/${versionId}/tests/${id}`, { method: 'PUT', body: { ...data, version } }),
  removeTest: (specId: string, versionId: string, id: string, version: number) => apiRequest<void>(`/specifications/${specId}/versions/${versionId}/tests/${id}`, { method: 'DELETE', body: { version } }),
  limits: (specId: string, versionId: string, testId: string) => apiRequest<SpecificationLimit[]>(`/specifications/${specId}/versions/${versionId}/tests/${testId}/limits`),
  createLimit: (specId: string, versionId: string, testId: string, data: Input) => apiRequest<SpecificationLimit>(`/specifications/${specId}/versions/${versionId}/tests/${testId}/limits`, { method: 'POST', body: data }),
  updateLimit: (specId: string, versionId: string, testId: string, id: string, version: number, data: Input) => apiRequest<SpecificationLimit>(`/specifications/${specId}/versions/${versionId}/tests/${testId}/limits/${id}`, { method: 'PUT', body: { ...data, version } }),
  removeLimit: (specId: string, versionId: string, testId: string, id: string, version: number) => apiRequest<void>(`/specifications/${specId}/versions/${versionId}/tests/${testId}/limits/${id}`, { method: 'DELETE', body: { version } }),
}
