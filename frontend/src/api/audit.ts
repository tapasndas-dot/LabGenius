import { apiRequest } from './client'

export type AuditEvent = {
  id: string; occurred_at: string; actor_user_id: string | null; action: string;
  entity_type: string; entity_id: string | null; organization_id: string | null;
  request_id: string | null; source_ip: string | null; changes: Record<string, unknown> | null;
  reason: string | null; source: string
}
export type AuditFilters = { entity_type?: string; action?: string; actor_user_id?: string; entity_id?: string; limit?: number; offset?: number }

export const auditApi = {
  list: (filters: AuditFilters = {}) => {
    const query = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== '') query.set(key, String(value)) })
    return apiRequest<AuditEvent[]>(`/audit/events?${query}`)
  },
  get: (id: string) => apiRequest<AuditEvent>(`/audit/events/${id}`),
}
