import { apiRequest } from './client'

export type User = {
  id: string; organization_id: string; business_unit_id: string; division_id: string;
  department_id: string; designation_id: string; employee_code: string; first_name: string;
  last_name: string; display_name: string; email: string; mobile: string | null; username: string;
  account_status: string; timezone: string; language: string; failed_login_attempts: number;
  last_login: string | null; created_at: string; updated_at: string
}
export type UserCreate = Omit<User, 'id' | 'account_status' | 'failed_login_attempts' | 'last_login' | 'created_at' | 'updated_at' | 'mobile'> & { password: string; mobile?: string | null }
export type UserUpdate = Partial<Pick<User, 'first_name' | 'last_name' | 'display_name' | 'email' | 'mobile' | 'department_id' | 'designation_id' | 'timezone' | 'language'>>
export type UserHierarchyLookups = {
  organizations: Array<{id:string;organization_code:string;organization_name:string}>
  business_units: Array<{id:string;organization_id:string;business_unit_code:string;business_unit_name:string}>
  divisions: Array<{id:string;business_unit_id:string;division_code:string;division_name:string}>
  departments: Array<{id:string;division_id:string;department_code:string;department_name:string}>
  designations: Array<{id:string;department_id:string;designation_code:string;designation_name:string}>
}
export type UserHierarchyOperation = 'view'|'create'|'update'
export type UserUpdateInput = UserUpdate & Partial<Pick<User,'organization_id'|'business_unit_id'|'division_id'>>

export const usersApi = {
  list: () => apiRequest<User[]>('/users/'),
  get: (id: string) => apiRequest<User>(`/users/${id}`),
  create: (data: UserCreate) => apiRequest<User>('/users/', { method: 'POST', body: data }),
  update: (id: string, data: UserUpdateInput) => apiRequest<User>(`/users/${id}`, { method: 'PUT', body: data }),
  hierarchyLookups: (operation:UserHierarchyOperation) => apiRequest<UserHierarchyLookups>(`/users/hierarchy-lookups/${operation}`),
  remove: (id: string) => apiRequest<{ message: string }>(`/users/${id}`, { method: 'DELETE' }),
  activate: (id: string) => apiRequest(`/users/${id}/activate`, { method: 'PUT' }),
  deactivate: (id: string) => apiRequest(`/users/${id}/deactivate`, { method: 'PUT' }),
  unlock: (id: string) => apiRequest(`/users/${id}/unlock`, { method: 'PUT' }),
  resetPassword: (id: string, password: string) => apiRequest(`/users/${id}/reset-password`, {
    method: 'POST', body: { new_password: password, confirm_new_password: password },
  }),
}
