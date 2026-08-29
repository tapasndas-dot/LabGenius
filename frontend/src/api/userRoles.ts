import { apiRequest } from './client'

export const ACCESS_SCOPES = ['ORGANIZATION', 'BUSINESS_UNIT', 'DIVISION', 'DEPARTMENT', 'SELF'] as const
export type AccessScope = typeof ACCESS_SCOPES[number]
export type UserRole = { id: string; user_id: string; role_id: string; access_scope: AccessScope; is_active: boolean; version: number }

export const userRolesApi = {
  list: (userId: string) => apiRequest<UserRole[]>(`/users/${userId}/roles`),
  assign: (userId: string, roleId: string, accessScope: AccessScope) => apiRequest<UserRole>(`/users/${userId}/roles`, { method: 'POST', body: { role_id: roleId, access_scope: accessScope } }),
  remove: (userId: string, roleId: string) => apiRequest(`/users/${userId}/roles/${roleId}`, { method: 'DELETE' }),
}
