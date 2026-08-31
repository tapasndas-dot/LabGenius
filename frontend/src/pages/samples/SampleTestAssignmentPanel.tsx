import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiError } from '../../api/client'
import {
  samplesApi,
  type Sample,
  type SampleTest,
  type SampleTestAssignee,
  type SampleTestAssignment,
  type SampleTestAssignmentMutation,
} from '../../api/samples'
import { errorMessage } from '../../components/admin/AdminPrimitives'

type Props = {
  sample: Sample
  sampleTest: SampleTest
  users: SampleTestAssignee[]
  canAssign: boolean
  onReconciled: (result?: SampleTestAssignmentMutation) => Promise<void>
}

const dateTime = (value: string | null) => value ? new Date(value).toLocaleString() : '—'
const safeError = (cause: unknown) => cause instanceof ApiError && cause.status === 404 ? 'Sample Test not found.' : errorMessage(cause)

export function SampleTestAssignmentPanel({ sample, sampleTest, users, canAssign, onReconciled }: Props) {
  const [assignment, setAssignment] = useState<SampleTestAssignment | null>(null)
  const [history, setHistory] = useState<SampleTestAssignment[]>([])
  const [mode, setMode] = useState<'assign' | 'reassign' | null>(null)
  const [userId, setUserId] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [conflict, setConflict] = useState(false)
  const [saving, setSaving] = useState(false)
  const names = useMemo(() => new Map(users.map(user => [user.id, user.display_name])), [users])
  const activeUsers = users.filter(user => user.account_status === 'ACTIVE')
  const mutable = canAssign && !['CANCELLED', 'FINALIZED'].includes(sample.status)

  const refresh = useCallback(async () => {
    const [current, records] = await Promise.all([
      samplesApi.assignment(sample.id, sampleTest.id).catch(error => {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }),
      samplesApi.assignmentHistory(sample.id, sampleTest.id),
    ])
    setAssignment(current)
    setHistory(records)
    setError(null)
    setConflict(false)
  }, [sample.id, sampleTest.id])

  useEffect(() => { queueMicrotask(() => void refresh().catch(cause => setError(safeError(cause)))) }, [refresh])

  const finish = async (result: SampleTestAssignmentMutation) => {
    setAssignment(result.assignment)
    await onReconciled(result)
    setHistory(await samplesApi.assignmentHistory(sample.id, sampleTest.id))
    setMode(null)
    setUserId('')
    setNotes('')
    setError(null)
    setConflict(false)
  }

  const fail = (cause: unknown) => {
    const stale = cause instanceof ApiError && cause.status === 409
    setConflict(stale)
    setError(stale ? 'Assignment has changed. Refresh current Sample data and try again.' : safeError(cause))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!userId) return
    setSaving(true)
    try {
      const common = { assigned_user_id: userId, expected_sample_test_version: sampleTest.version, notes: notes || null }
      const result = mode === 'reassign' && assignment
        ? await samplesApi.reassign(sample.id, sampleTest.id, { ...common, expected_assignment_version: assignment.version })
        : await samplesApi.assign(sample.id, sampleTest.id, common)
      await finish(result)
    } catch (cause) { fail(cause) } finally { setSaving(false) }
  }

  const unassign = async () => {
    if (!assignment || !window.confirm(`Unassign ${names.get(assignment.assigned_user_id) ?? 'the current assignee'}?`)) return
    setSaving(true)
    try {
      await finish(await samplesApi.unassign(sample.id, sampleTest.id, {
        expected_sample_test_version: sampleTest.version,
        expected_assignment_version: assignment.version,
      }))
    } catch (cause) { fail(cause) } finally { setSaving(false) }
  }

  const refreshAll = async () => {
    try { await onReconciled(); await refresh() } catch (cause) { setError(safeError(cause)) }
  }

  return <div className="assignment-panel">
    <div><strong>Assigned To:</strong> {assignment ? (names.get(assignment.assigned_user_id) ?? 'User details unavailable') : 'Unassigned'}</div>
    {error && <div role="alert">{error}</div>}
    {conflict && <button className="small-button secondary" onClick={() => void refreshAll()}>Refresh current Sample data</button>}
    {mutable && !mode && !assignment && sampleTest.status === 'PENDING' && <button className="small-button" onClick={() => setMode('assign')}>Assign</button>}
    {mutable && !mode && assignment && sampleTest.status === 'ASSIGNED' && <span className="table-actions">
      <button className="small-button secondary" onClick={() => setMode('reassign')}>Reassign</button>
      <button className="small-button secondary" disabled={saving} onClick={() => void unassign()}>Unassign</button>
    </span>}
    {mode && mutable && <form className="inline-form" onSubmit={submit}>
      {mode === 'reassign' && assignment && <span>Current assignee: {names.get(assignment.assigned_user_id) ?? 'User details unavailable'}</span>}
      <label>Assignee<select aria-label="Assignee" value={userId} onChange={event => setUserId(event.target.value)} required>
        <option value="">Select active user</option>
        {activeUsers.map(user => <option key={user.id} value={user.id}>{user.display_name}</option>)}
      </select></label>
      <label>Assignment Notes<textarea aria-label="Assignment Notes" value={notes} onChange={event => setNotes(event.target.value)} /></label>
      <button disabled={saving || !userId}>{saving ? 'Saving…' : mode === 'assign' ? 'Assign' : 'Reassign'}</button>
      <button type="button" className="text-button" onClick={() => setMode(null)}>Cancel</button>
    </form>}
    <details>
      <summary>Assignment History</summary>
      {history.length === 0 ? <p>No assignment history.</p> : <div className="table-wrap"><table>
        <thead><tr><th>Assignee</th><th>Assigned</th><th>Unassigned</th><th>State</th><th>Notes</th></tr></thead>
        <tbody>{history.map(record => <tr key={record.id}>
          <td>{names.get(record.assigned_user_id) ?? 'User details unavailable'}</td>
          <td>{dateTime(record.assigned_at)}</td><td>{dateTime(record.unassigned_at)}</td>
          <td>{record.is_active ? 'Active' : 'Inactive'}</td><td>{record.notes ?? '—'}</td>
        </tr>)}</tbody>
      </table></div>}
    </details>
  </div>
}
