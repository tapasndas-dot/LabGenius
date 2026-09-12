import { apiRequest } from './client'

export type DashboardReference = { id: string; code: string; name: string }
export type DashboardMethodVersion = DashboardReference & { version_number: number }
export type DashboardAssignment = {
  assignment_id: string
  assigned_user_id: string
  assigned_user_display_name: string
  assigned_at: string
}
export type DashboardResult = {
  result_id: string
  status: string
  sequence_number: number
  entered_at: string | null
  reviewed_at: string | null
  finalized_at: string | null
}
export type QCDashboardSummary = {
  active_samples: number
  pending_tests: number
  assigned_or_in_progress_tests: number
  awaiting_review: number
  awaiting_finalization: number
  finalized_tests: number
}
export type QCWorkQueueRow = {
  sample_id: string
  sample_number: string
  sample_status: string
  sample_test_id: string
  sample_test_status: string
  priority: string
  due_at: string | null
  material: DashboardReference
  test: DashboardReference
  method_version: DashboardMethodVersion | null
  active_assignment: DashboardAssignment | null
  result: DashboardResult | null
}
export type QCReviewQueueRow = {
  queue_stage: 'REVIEW' | 'FINALIZE'
  sample_id: string
  sample_number: string
  sample_test_id: string
  sample_test_status: string
  result_id: string
  result_status: string
  result_version: number
  test: DashboardReference
  method_version: DashboardMethodVersion | null
  assigned_user_display_name: string | null
  entered_at: string | null
  entered_by_display_name: string | null
  reviewed_at: string | null
  reviewed_by_display_name: string | null
  due_at: string | null
  priority: string
}
export type QCRecentActivityRow = {
  activity_type: 'SUBMITTED' | 'REVIEWED' | 'FINALIZED'
  occurred_at: string
  sample_id: string
  sample_number: string
  sample_test_id: string
  result_id: string
  test: DashboardReference
  actor_display_name: string | null
}
export type QCWorkQueueFilters = Partial<{
  business_unit_id: string
  division_id: string
  department_id: string
  sample_status: string
  sample_test_status: string
  assigned_user_id: string
  due_from: string
  due_to: string
}>

function query(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  return params.size ? `?${params}` : ''
}

export const qcDashboardApi = {
  summary: () => apiRequest<QCDashboardSummary>('/qc-dashboard/summary'),
  workQueue: (filters: QCWorkQueueFilters = {}) =>
    apiRequest<QCWorkQueueRow[]>(`/qc-dashboard/work-queue${query(filters)}`),
  reviewQueue: () => apiRequest<QCReviewQueueRow[]>('/qc-dashboard/review-queue'),
  recentActivity: (limit = 20) =>
    apiRequest<QCRecentActivityRow[]>(`/qc-dashboard/recent-activity${query({ limit })}`),
}
