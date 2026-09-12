import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError } from '../../api/client'
import { instrumentsApi, type Instrument } from '../../api/instruments'
import {
  samplesApi,
  type MethodParameterContext,
  type ParameterResult,
  type ResultTypedValueInput,
  type Sample,
  type SampleTest,
  type SampleTestResult,
} from '../../api/samples'
import { useAuthorization } from '../../auth/useAuthorization'
import { errorMessage } from '../../components/admin/AdminPrimitives'

type Props = {
  sample: Sample
  sampleTest: SampleTest
}

function currentValue(record: ParameterResult | undefined, parameter: MethodParameterContext) {
  if (!record) return ''
  switch (parameter.value_type) {
    case 'TEXT': return record.text_value ?? ''
    case 'NUMBER': return record.numeric_value ?? ''
    case 'INTEGER': return record.integer_value ?? ''
    case 'BOOLEAN': return record.boolean_value === null ? '' : String(record.boolean_value)
    case 'DATE': return record.date_value ?? ''
    case 'DATETIME': return record.datetime_value ? record.datetime_value.slice(0, 16) : ''
  }
}

function typedValue(parameter: MethodParameterContext, raw: string): ResultTypedValueInput {
  switch (parameter.value_type) {
    case 'TEXT':
      return { value_type: 'TEXT', text_value: raw }
    case 'NUMBER':
      return { value_type: 'NUMBER', numeric_value: raw }
    case 'INTEGER':
      return { value_type: 'INTEGER', integer_value: Number.parseInt(raw, 10) }
    case 'BOOLEAN':
      return { value_type: 'BOOLEAN', boolean_value: raw === 'true' }
    case 'DATE':
      return { value_type: 'DATE', date_value: raw }
    case 'DATETIME':
      return { value_type: 'DATETIME', datetime_value: new Date(raw).toISOString() }
  }
}

function localDateTimeValue(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function isoDateTimeValue(value: string) {
  return value ? new Date(value).toISOString() : null
}

function dateTime(value: string) {
  return new Date(value).toLocaleString()
}

function ParameterInput({
  parameter,
  value,
  disabled,
  onChange,
}: {
  parameter: MethodParameterContext
  value: string | number
  disabled: boolean
  onChange: (value: string) => void
}) {
  const common = {
    'aria-label': parameter.name,
    disabled,
  }

  if (parameter.value_type === 'BOOLEAN') {
    return (
      <select {...common} value={String(value)} onChange={event => onChange(event.target.value)}>
        <option value="">Select</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    )
  }

  if (parameter.value_type === 'DATE') {
    return <input {...common} type="date" value={String(value)} onChange={event => onChange(event.target.value)} />
  }

  if (parameter.value_type === 'DATETIME') {
    return <input {...common} type="datetime-local" value={String(value)} onChange={event => onChange(event.target.value)} />
  }

  if (parameter.value_type === 'NUMBER') {
    return <input {...common} type="number" step="any" value={String(value)} onChange={event => onChange(event.target.value)} />
  }

  if (parameter.value_type === 'INTEGER') {
    return <input {...common} type="number" step="1" value={String(value)} onChange={event => onChange(event.target.value)} />
  }

  return <input {...common} value={String(value)} onChange={event => onChange(event.target.value)} />
}

export function SampleTestResultPanel({ sample, sampleTest }: Props) {
  const { hasPermission } = useAuthorization()
  const [result, setResult] = useState<SampleTestResult | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [notes, setNotes] = useState('')
  const [startedAt, setStartedAt] = useState('')
  const [completedAt, setCompletedAt] = useState('')
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [instrumentId, setInstrumentId] = useState('')
  const [instrumentNotes, setInstrumentNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conflict, setConflict] = useState(false)

  const canView = hasPermission('sample_test_result.view')
  const canCreate = hasPermission('sample_test_result.create')
  const canUpdate = hasPermission('sample_test_result.update')
  const canSubmit = hasPermission('sample_test_result.submit')
  const canReview = hasPermission('sample_test_result.review')
  const canFinalize = hasPermission('sample_test_result.finalize')
  const canBrowseInstruments = hasPermission('instrument.view')

  const draft = result?.status === 'DRAFT'
  const editable = Boolean(result && draft && canUpdate)

  const entered = useMemo(
    () => new Map(result?.parameters.map(item => [item.method_parameter_id, item]) ?? []),
    [result],
  )

  const applyResult = useCallback((next: SampleTestResult | null) => {
    setResult(next)
    setNotes(next?.notes ?? '')
    setStartedAt(localDateTimeValue(next?.started_at ?? null))
    setCompletedAt(localDateTimeValue(next?.completed_at ?? null))
    if (!next) {
      setValues({})
      return
    }

    const nextValues: Record<string, string> = {}
    for (const parameter of next.method_parameters) {
      nextValues[parameter.id] = String(currentValue(
        next.parameters.find(item => item.method_parameter_id === parameter.id),
        parameter,
      ))
    }
    setValues(nextValues)
  }, [])

  const refresh = useCallback(async () => {
    if (!canView) {
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const rows = await samplesApi.results(sample.id, sampleTest.id)
      applyResult(rows[0] ?? null)
      setError(null)
      setConflict(false)
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setLoading(false)
    }
  }, [applyResult, canView, sample.id, sampleTest.id])

  useEffect(() => {
    queueMicrotask(() => void refresh())
  }, [refresh])

  useEffect(() => {
    if (!canBrowseInstruments) return
    queueMicrotask(() => {
      void instrumentsApi.list({ limit: 500, is_active: true })
        .then(setInstruments)
        .catch(() => setInstruments([]))
    })
  }, [canBrowseInstruments])

  const fail = (cause: unknown) => {
    const stale = cause instanceof ApiError && cause.status === 409
    setConflict(stale)
    setError(stale
      ? 'Result data has changed. Refresh the current Result and try again.'
      : errorMessage(cause))
  }

  const run = async (operation: () => Promise<SampleTestResult>) => {
    setSaving(true)
    try {
      applyResult(await operation())
      setError(null)
      setConflict(false)
    } catch (cause) {
      fail(cause)
    } finally {
      setSaving(false)
    }
  }

  const runWorkflow = async (operation: () => Promise<SampleTestResult>) => {
    setSaving(true)
    try {
      applyResult(await operation())
      setError(null)
      setConflict(false)
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409 && result) {
        try {
          applyResult(await samplesApi.result(sample.id, sampleTest.id, result.id))
          setConflict(true)
          setError('Result data changed and was refreshed. Review the current Result and try again.')
        } catch (refreshCause) {
          fail(refreshCause)
        }
      } else {
        fail(cause)
      }
    } finally {
      setSaving(false)
    }
  }

  const create = async () => {
    await run(() => samplesApi.createResult(sample.id, sampleTest.id))
  }

  const saveHeader = async () => {
  if (!result) return

  if (startedAt && completedAt && new Date(completedAt) < new Date(startedAt)) {
    setError('Completed At cannot be earlier than Started At.')
    return
  }

  await run(() => samplesApi.updateResult(
    sample.id,
    sampleTest.id,
    result.id,
    result.version,
    {
      notes: notes || null,
      started_at: isoDateTimeValue(startedAt),
      completed_at: isoDateTimeValue(completedAt),
    },
  ))
}

  const saveParameter = async (parameter: MethodParameterContext) => {
    if (!result) return

    const raw = values[parameter.id] ?? ''
    const existing = entered.get(parameter.id)

    if (!raw) {
        if (parameter.is_required) {
            setError(`${parameter.name} requires a value.`)
            return
        }

  if (existing) {
    await run(() => samplesApi.removeResultParameter(
      sample.id,
      sampleTest.id,
      result.id,
      existing.id,
      existing.version,
    ))
  }

  return
    }

    const payload = typedValue(parameter, raw)

    if (existing) {
      await run(() => samplesApi.updateResultParameter(
        sample.id,
        sampleTest.id,
        result.id,
        existing.id,
        { ...payload, version: existing.version },
      ))
    } else {
      await run(() => samplesApi.addResultParameter(
        sample.id,
        sampleTest.id,
        result.id,
        { method_parameter_id: parameter.id, ...payload },
      ))
    }
  }

  const removeParameter = async (parameter: MethodParameterContext) => {
    if (!result) return
    const existing = entered.get(parameter.id)
    if (!existing) return

    await run(() => samplesApi.removeResultParameter(
      sample.id,
      sampleTest.id,
      result.id,
      existing.id,
      existing.version,
    ))
  }

  const addInstrument = async () => {
    if (!result || !instrumentId) return

    await run(() => samplesApi.addResultInstrument(
      sample.id,
      sampleTest.id,
      result.id,
      instrumentId,
      instrumentNotes || null,
    ))

    setInstrumentId('')
    setInstrumentNotes('')
  }

  const removeInstrument = async (usageId: string, version: number) => {
    if (!result) return

    await run(() => samplesApi.removeResultInstrument(
      sample.id,
      sampleTest.id,
      result.id,
      usageId,
      version,
    ))
  }

  const submit = async () => {
    if (!result) return
    if (!window.confirm('Submit this Result? After submission, ordinary Result entry becomes read-only.')) return

    await run(() => samplesApi.submitResult(
      sample.id,
      sampleTest.id,
      result.id,
      result.version,
    ))
  }

  const review = async () => {
    if (!result) return
    await runWorkflow(() => samplesApi.reviewResult(
      sample.id, sampleTest.id, result.id, result.version,
    ))
  }

  const finalize = async () => {
    if (!result) return
    await runWorkflow(() => samplesApi.finalizeResult(
      sample.id, sampleTest.id, result.id, result.version,
    ))
  }

  if (!canView) return null
  if (loading) return <div className="form-help">Loading Result…</div>

  return (
    <div className="assignment-panel">
      <div><strong>Result:</strong> {result ? `Revision ${result.sequence_number} — ${result.status}` : 'Not started'}</div>

      {error && <div className="form-error" role="alert">{error}</div>}
      {conflict && (
        <button className="small-button secondary" onClick={() => void refresh()}>
          Refresh current Result
        </button>
      )}

      {!result && canCreate && (
        <button className="small-button" disabled={saving} onClick={() => void create()}>
          {saving ? 'Creating…' : 'Start Result Entry'}
        </button>
      )}

      {!result && !canCreate && <span className="form-help">No Result has been created.</span>}

      {result && (
        <details>
          <summary>Result Entry</summary>

          <dl className="record-meta">
            <div><dt>Status</dt><dd>{result.status}</dd></div>
            <div><dt>Test</dt><dd>{result.test.code} — {result.test.name}</dd></div>
            <div><dt>Method</dt><dd>{result.method_version.code} — Version {result.method_version.version_number}</dd></div>
          </dl>
          {(result.entered_at || result.reviewed_at || result.finalized_at) && (
            <section aria-label="Result workflow" className="record-meta">
              {result.entered_at && (
                <div><strong>Entered</strong> by {result.entered_by?.display_name ?? 'Unknown'} at {dateTime(result.entered_at)}</div>
              )}
              {result.reviewed_at && (
                <div><strong>Reviewed</strong> by {result.reviewed_by?.display_name ?? 'Unknown'} at {dateTime(result.reviewed_at)}</div>
              )}
              {result.finalized_at && (
                <div><strong>Finalized</strong> by {result.finalized_by?.display_name ?? 'Unknown'} at {dateTime(result.finalized_at)}</div>
              )}
            </section>
          )}
            <div className="inline-form">
                <label>
                    Started At
                    <input
                    aria-label="Result Started At"
                    type="datetime-local"
                    value={startedAt}
                    disabled={!editable}
                    onChange={event => setStartedAt(event.target.value)}
                    />
                </label>

                <label>
                    Completed At
                    <input
                    aria-label="Result Completed At"
                    type="datetime-local"
                    value={completedAt}
                    min={startedAt || undefined}
                    disabled={!editable}
                    onChange={event => setCompletedAt(event.target.value)}
                    />
                </label>
                </div>
          <label className="full-width">
            Result Notes
            <textarea
              aria-label="Result Notes"
              value={notes}
              disabled={!editable}
              onChange={event => setNotes(event.target.value)}
            />
          </label>

          {editable && (
            <button className="small-button secondary" disabled={saving} onClick={() => void saveHeader()}>
              Save Result Details
            </button>
          )}

          <h4>Method Parameters</h4>

          {result.method_parameters.length === 0 ? (
            <p className="form-help">This Method Version has no parameters.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Sequence</th>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Unit</th>
                    <th>Required</th>
                    <th>Value</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {[...result.method_parameters]
                    .sort((a, b) => (a.sequence_number ?? 0) - (b.sequence_number ?? 0))
                    .map(parameter => {
                      const existing = entered.get(parameter.id)
                      return (
                        <tr key={parameter.id}>
                          <td>{parameter.sequence_number ?? '—'}</td>
                          <td>{parameter.code} — {parameter.name}</td>
                          <td>{parameter.value_type}</td>
                          <td>{parameter.unit ?? '—'}</td>
                          <td>{parameter.is_required ? 'Yes' : 'No'}</td>
                          <td>
                            <ParameterInput
                              parameter={parameter}
                              value={values[parameter.id] ?? ''}
                              disabled={!editable}
                              onChange={value => setValues(current => ({ ...current, [parameter.id]: value }))}
                            />
                          </td>
                          <td className="table-actions">
                            {editable && (
                              <>
                                <button
                                  className="small-button secondary"
                                  disabled={saving}
                                  onClick={() => void saveParameter(parameter)}
                                >
                                  {existing ? 'Update Value' : 'Save Value'}
                                </button>

                                {existing && (
                                  <button
                                    className="small-button secondary"
                                    disabled={saving}
                                    onClick={() => void removeParameter(parameter)}
                                  >
                                    Remove Value
                                  </button>
                                )}
                              </>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                </tbody>
              </table>
            </div>
          )}

          <h4>Instruments Used</h4>

          {result.instrument_usages.length === 0 ? (
            <p className="form-help">No instrument linked.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Instrument</th><th>Model</th><th>Serial</th><th>Notes</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {result.instrument_usages.map(usage => (
                    <tr key={usage.id}>
                      <td>{usage.instrument.code} — {usage.instrument.name}</td>
                      <td>{usage.instrument.model_number ?? '—'}</td>
                      <td>{usage.instrument.serial_number ?? '—'}</td>
                      <td>{usage.usage_notes ?? '—'}</td>
                      <td>
                        {editable && (
                          <button
                            className="small-button secondary"
                            disabled={saving}
                            onClick={() => void removeInstrument(usage.id, usage.version)}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {editable && canBrowseInstruments && (
            <div className="inline-form">
              <label>
                Instrument
                <select
                  aria-label="Result Instrument"
                  value={instrumentId}
                  onChange={event => setInstrumentId(event.target.value)}
                >
                  <option value="">Select instrument</option>
                  {instruments.map(instrument => (
                    <option key={instrument.id} value={instrument.id}>
                      {instrument.instrument_code} — {instrument.instrument_name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Usage Notes
                <input
                  aria-label="Instrument Usage Notes"
                  value={instrumentNotes}
                  onChange={event => setInstrumentNotes(event.target.value)}
                />
              </label>

              <button disabled={saving || !instrumentId} onClick={() => void addInstrument()}>
                Add Instrument
              </button>
            </div>
          )}

          {editable && !canBrowseInstruments && (
            <p className="form-help">
              Instrument selection is unavailable with your current permissions. Result entry may continue without an instrument.
            </p>
          )}

          {draft && canSubmit && (
            <div className="form-actions">
              <button disabled={saving} onClick={() => void submit()}>
                Submit Result
              </button>
            </div>
          )}

          {result.status === 'ENTERED' && canReview && (
            <div className="form-actions">
              <button disabled={saving} onClick={() => void review()}>
                {saving ? 'Reviewing…' : 'Review Result'}
              </button>
            </div>
          )}

          {result.status === 'REVIEWED' && canFinalize && (
            <div className="form-actions">
              <button disabled={saving} onClick={() => void finalize()}>
                {saving ? 'Finalizing…' : 'Finalize Result'}
              </button>
            </div>
          )}

          {result.status !== 'DRAFT' && (
            <p className="form-help">
              This Result has been submitted and is read-only for ordinary Result entry.
            </p>
          )}
        </details>
      )}
    </div>
  )
}
