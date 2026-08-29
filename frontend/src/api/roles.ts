import { apiRequest } from './client'

export type Role = { id: string; role_code: string; role_name: string; description: string | null; is_active: boolean; version: number }
export type Permission = { id: string; permission_code: string; permission_name: string; description: string | null; is_active: boolean; version: number }
export type RolePermission = { id: string; role_id: string; permission_id: string; is_active: boolean; version: number }

export const rolesApi = {
  list: () => apiRequest<Role[]>('/roles/'),
  create: (data: Pick<Role, 'role_code' | 'role_name' | 'description'>) => apiRequest<Role>('/roles/', { method: 'POST', body: data }),
  update: (id: string, data: Pick<Role, 'role_name' | 'description'>) => apiRequest<Role>(`/roles/${id}`, { method: 'PUT', body: data }),
  setStatus: (id: string, is_active: boolean) => apiRequest<Role>(`/roles/${id}/status`, { method: 'PUT', body: { is_active } }),
  permissions: () => apiRequest<Permission[]>('/permissions/'),
  assignments: (roleId: string) => apiRequest<RolePermission[]>(`/roles/${roleId}/permissions`),
  assignPermission: (roleId: string, permissionId: string) => apiRequest<RolePermission>(`/roles/${roleId}/permissions`, { method: 'POST', body: { permission_id: permissionId } }),
  removePermission: (roleId: string, permissionId: string) => apiRequest(`/roles/${roleId}/permissions/${permissionId}`, { method: 'DELETE' }),
}
