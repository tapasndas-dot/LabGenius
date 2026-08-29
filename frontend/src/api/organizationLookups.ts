import { apiRequest } from './client'

export type BusinessUnitLookup = { id: string; business_unit_code: string; business_unit_name: string; is_active: boolean }
export type DivisionLookup = { id: string; business_unit_id: string; division_code: string; division_name: string; is_active: boolean }
export type DepartmentLookup = { id: string; division_id: string; department_code: string; department_name: string; is_active: boolean }

export const organizationLookupsApi = {
  businessUnits: () => apiRequest<BusinessUnitLookup[]>('/business-units/'),
  divisions: () => apiRequest<DivisionLookup[]>('/divisions/'),
  departments: () => apiRequest<DepartmentLookup[]>('/departments/'),
}
