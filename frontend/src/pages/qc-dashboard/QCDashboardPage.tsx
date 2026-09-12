import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { organizationLookupsApi, type BusinessUnitLookup, type DepartmentLookup, type DivisionLookup } from '../../api/organizationLookups'
import {
  qcDashboardApi,
  type QCDashboardSummary,
  type QCRecentActivityRow,
  type QCReviewQueueRow,
  type QCWorkQueueFilters,
  type QCWorkQueueRow,
} from '../../api/qcDashboard'
import { SAMPLE_STATUSES, samplesApi, type SampleTestAssignee } from '../../api/samples'
import { useAuthorization } from '../../auth/useAuthorization'
import { AdminHeader, EmptyState, ErrorState, LoadingState, errorMessage } from '../../components/admin/AdminPrimitives'

const TEST_STATUSES = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'RESULT_ENTERED', 'REVIEWED', 'FINALIZED', 'CANCELLED']
const KPI_FIELDS: Array<{ key: keyof QCDashboardSummary; label: string; help: string }> = [
  { key: 'active_samples', label: 'Active Samples', help: 'Visible Samples currently in operation' },
  { key: 'pending_tests', label: 'Pending Tests', help: 'Tests waiting to be assigned' },
  { key: 'assigned_or_in_progress_tests', label: 'Assigned / In Progress', help: 'Assigned tests and active testing work' },
  { key: 'awaiting_review', label: 'Awaiting Review', help: 'Entered Results available for review' },
  { key: 'awaiting_finalization', label: 'Awaiting Finalization', help: 'Reviewed Results available to finalize' },
  { key: 'finalized_tests', label: 'Finalized Tests', help: 'Visible tests in their final state' },
]

type SectionState<T> = { data: T; loading: boolean; error: string | null }
const emptyState = <T,>(data: T): SectionState<T> => ({ data, loading: true, error: null })
const readable = (value: string) => value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase())
const dateTime = (value: string | null) => value ? new Date(value).toLocaleString() : '—'
const dueDate = (value: string | null) => value ? new Date(value).toLocaleDateString() : '—'
const reference = (value: { code: string; name: string }) => `${value.code} — ${value.name}`
const method = (value: QCWorkQueueRow['method_version']) => value ? `${value.code} — ${value.name} — Version ${value.version_number}` : '—'
const status = (value: string) => <span className={`dashboard-badge ${value.toLowerCase()}`}>{readable(value)}</span>

function DashboardSection({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <section className="dashboard-section"><header><h2>{title}</h2><p>{description}</p></header>{children}</section>
}

export function QCDashboardPage() {
  const { hasPermission, hasAnyPermission } = useAuthorization()
  const showWorkflow = hasAnyPermission(['sample_test_result.review', 'sample_test_result.finalize'])
  const [summary, setSummary] = useState<SectionState<QCDashboardSummary | null>>(emptyState(null))
  const [work, setWork] = useState<SectionState<QCWorkQueueRow[]>>(emptyState([]))
  const [review, setReview] = useState<SectionState<QCReviewQueueRow[]>>(emptyState([]))
  const [activity, setActivity] = useState<SectionState<QCRecentActivityRow[]>>(emptyState([]))
  const [filters, setFilters] = useState<QCWorkQueueFilters>({})
  const [appliedFilters, setAppliedFilters] = useState<QCWorkQueueFilters>({})
  const [activityLimit, setActivityLimit] = useState(20)
  const [businessUnits, setBusinessUnits] = useState<BusinessUnitLookup[]>([])
  const [divisions, setDivisions] = useState<DivisionLookup[]>([])
  const [departments, setDepartments] = useState<DepartmentLookup[]>([])
  const [assignees, setAssignees] = useState<SampleTestAssignee[]>([])

  const loadSummary = useCallback(async () => {
    setSummary(current => ({ ...current, loading: true, error: null }))
    try { setSummary({ data: await qcDashboardApi.summary(), loading: false, error: null }) }
    catch (cause) { setSummary({ data: null, loading: false, error: errorMessage(cause) }) }
  }, [])
  const loadWork = useCallback(async () => {
    setWork(current => ({ ...current, loading: true, error: null }))
    try { setWork({ data: await qcDashboardApi.workQueue(appliedFilters), loading: false, error: null }) }
    catch (cause) { setWork({ data: [], loading: false, error: errorMessage(cause) }) }
  }, [appliedFilters])
  const loadReview = useCallback(async () => {
    if (!showWorkflow) return
    setReview(current => ({ ...current, loading: true, error: null }))
    try { setReview({ data: await qcDashboardApi.reviewQueue(), loading: false, error: null }) }
    catch (cause) { setReview({ data: [], loading: false, error: errorMessage(cause) }) }
  }, [showWorkflow])
  const loadActivity = useCallback(async () => {
    setActivity(current => ({ ...current, loading: true, error: null }))
    try { setActivity({ data: await qcDashboardApi.recentActivity(activityLimit), loading: false, error: null }) }
    catch (cause) { setActivity({ data: [], loading: false, error: errorMessage(cause) }) }
  }, [activityLimit])

  useEffect(() => { queueMicrotask(() => void loadSummary()) }, [loadSummary])
  useEffect(() => { queueMicrotask(() => void loadWork()) }, [loadWork])
  useEffect(() => { queueMicrotask(() => void loadReview()) }, [loadReview])
  useEffect(() => { queueMicrotask(() => void loadActivity()) }, [loadActivity])
  useEffect(() => {
    queueMicrotask(() => {
      void samplesApi.assignmentUsers().then(setAssignees).catch(() => setAssignees([]))
      if (hasPermission('business_unit.view')) void organizationLookupsApi.businessUnits().then(setBusinessUnits).catch(() => setBusinessUnits([]))
      if (hasPermission('division.view')) void organizationLookupsApi.divisions().then(setDivisions).catch(() => setDivisions([]))
      if (hasPermission('department.view')) void organizationLookupsApi.departments().then(setDepartments).catch(() => setDepartments([]))
    })
  }, [hasPermission])

  const setFilter = (key: keyof QCWorkQueueFilters, value: string) => setFilters(current => ({ ...current, [key]: value || undefined }))
  const applyFilters = () => setAppliedFilters({
    ...filters,
    due_from: filters.due_from ? `${filters.due_from}T00:00:00Z` : undefined,
    due_to: filters.due_to ? `${filters.due_to}T23:59:59.999Z` : undefined,
  })
  const clearFilters = () => { setFilters({}); setAppliedFilters({}) }

  return <section className="admin-page qc-dashboard-page">
    <AdminHeader title="QC Operational Dashboard" description="Current authorized Samples, testing work, Result review, and workflow activity." />

    <DashboardSection title="Operational Summary" description="Current operational counts within your authorized scope.">
      {summary.error ? <ErrorState message={summary.error} /> : summary.loading ? <LoadingState /> : summary.data && <div className="dashboard-kpis">{KPI_FIELDS.map(item => <article className="dashboard-kpi" key={item.key}><strong>{summary.data?.[item.key]}</strong><h3>{item.label}</h3><p>{item.help}</p></article>)}</div>}
    </DashboardSection>

    <DashboardSection title="Work Queue" description="Authorized QC tests and current assignments.">
      <div className="inline-form dashboard-filters">
        {hasPermission('business_unit.view') && <label>Business Unit<select aria-label="Business Unit filter" value={filters.business_unit_id ?? ''} onChange={event => setFilter('business_unit_id', event.target.value)}><option value="">All</option>{businessUnits.map(item => <option key={item.id} value={item.id}>{item.business_unit_code} — {item.business_unit_name}</option>)}</select></label>}
        {hasPermission('division.view') && <label>Division<select aria-label="Division filter" value={filters.division_id ?? ''} onChange={event => setFilter('division_id', event.target.value)}><option value="">All</option>{divisions.map(item => <option key={item.id} value={item.id}>{item.division_code} — {item.division_name}</option>)}</select></label>}
        {hasPermission('department.view') && <label>Department<select aria-label="Department filter" value={filters.department_id ?? ''} onChange={event => setFilter('department_id', event.target.value)}><option value="">All</option>{departments.map(item => <option key={item.id} value={item.id}>{item.department_code} — {item.department_name}</option>)}</select></label>}
        <label>Sample Status<select aria-label="Sample Status filter" value={filters.sample_status ?? ''} onChange={event => setFilter('sample_status', event.target.value)}><option value="">All</option>{SAMPLE_STATUSES.map(item => <option key={item} value={item}>{readable(item)}</option>)}</select></label>
        <label>Test Status<select aria-label="Sample Test Status filter" value={filters.sample_test_status ?? ''} onChange={event => setFilter('sample_test_status', event.target.value)}><option value="">All</option>{TEST_STATUSES.map(item => <option key={item} value={item}>{readable(item)}</option>)}</select></label>
        <label>Assigned User<select aria-label="Assigned User filter" value={filters.assigned_user_id ?? ''} onChange={event => setFilter('assigned_user_id', event.target.value)}><option value="">All</option>{assignees.map(item => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>
        <label>Due From<input aria-label="Due From" type="date" value={filters.due_from ?? ''} onChange={event => setFilter('due_from', event.target.value)} /></label>
        <label>Due To<input aria-label="Due To" type="date" value={filters.due_to ?? ''} onChange={event => setFilter('due_to', event.target.value)} /></label>
        <button type="button" onClick={applyFilters}>Apply Filters</button><button type="button" className="small-button secondary" onClick={clearFilters}>Clear Filters</button>
      </div>
      {work.error ? <ErrorState message={work.error} /> : work.loading ? <LoadingState /> : work.data.length === 0 ? <EmptyState>No authorized work items found.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Sample</th><th>Material</th><th>Test</th><th>Method</th><th>Sample Status</th><th>Test Status</th><th>Priority</th><th>Due</th><th>Assigned To</th><th>Result Status</th></tr></thead><tbody>{work.data.map(row => <tr key={row.sample_test_id}><td>{row.sample_number}</td><td>{reference(row.material)}</td><td>{reference(row.test)}</td><td>{method(row.method_version)}</td><td>{status(row.sample_status)}</td><td>{status(row.sample_test_status)}</td><td>{status(row.priority)}</td><td>{dueDate(row.due_at)}</td><td>{row.active_assignment?.assigned_user_display_name ?? 'Unassigned'}</td><td>{row.result ? status(row.result.status) : '—'}</td></tr>)}</tbody></table></div>}
    </DashboardSection>

    {showWorkflow && <DashboardSection title="Review & Finalization Queue" description="Result workflow stages returned for your exact permissions.">
      {review.error ? <ErrorState message={review.error} /> : review.loading ? <LoadingState /> : review.data.length === 0 ? <EmptyState>No Results are awaiting your workflow action.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Stage</th><th>Sample</th><th>Test</th><th>Assigned To</th><th>Entered By</th><th>Entered At</th><th>Reviewed By</th><th>Reviewed At</th><th>Due</th><th>Priority</th><th>Result Status</th></tr></thead><tbody>{review.data.map(row => <tr key={`${row.queue_stage}-${row.result_id}`}><td>{status(row.queue_stage)}</td><td>{row.sample_number}</td><td>{reference(row.test)}</td><td>{row.assigned_user_display_name ?? 'Unassigned'}</td><td>{row.entered_by_display_name ?? '—'}</td><td>{dateTime(row.entered_at)}</td><td>{row.reviewed_by_display_name ?? '—'}</td><td>{dateTime(row.reviewed_at)}</td><td>{dueDate(row.due_at)}</td><td>{status(row.priority)}</td><td>{status(row.result_status)}</td></tr>)}</tbody></table></div>}
    </DashboardSection>}

    <DashboardSection title="Recent Activity" description="Newest Result workflow activity within your authorized scope.">
      <label className="standalone-field">Activity limit<select aria-label="Activity limit" value={activityLimit} onChange={event => setActivityLimit(Number(event.target.value))}><option value={20}>20</option><option value={50}>50</option><option value={100}>100</option></select></label>
      {activity.error ? <ErrorState message={activity.error} /> : activity.loading ? <LoadingState /> : activity.data.length === 0 ? <EmptyState>No recent Result workflow activity.</EmptyState> : <div className="table-wrap"><table><thead><tr><th>Activity</th><th>Occurred</th><th>Sample</th><th>Test</th><th>Actor</th></tr></thead><tbody>{activity.data.map(row => <tr key={`${row.activity_type}-${row.result_id}-${row.occurred_at}`}><td>{status(row.activity_type)}</td><td>{dateTime(row.occurred_at)}</td><td>{row.sample_number}</td><td>{reference(row.test)}</td><td>{row.actor_display_name ?? '—'}</td></tr>)}</tbody></table></div>}
    </DashboardSection>
  </section>
}
