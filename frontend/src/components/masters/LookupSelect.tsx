import { useEffect, useState } from 'react'
import { locationsApi, type Location } from '../../api/masters'
import { errorMessage } from '../admin/AdminPrimitives'

export function LocationLookup({ value, onChange, excludeId }: { value: string; onChange: (value: string) => void; excludeId?: string }) {
  const [options, setOptions] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { queueMicrotask(async () => {
    try { setOptions(await locationsApi.list({ limit: 500, offset: 0, is_active: true })) }
    catch (cause) { setError(errorMessage(cause)) }
    finally { setLoading(false) }
  }) }, [])
  return <label>Parent location
    <select aria-label="Parent location" value={value} onChange={(event) => onChange(event.target.value)} disabled={loading}>
      <option value="">{loading ? 'Loading locations…' : 'No parent (root location)'}</option>
      {options.filter((item) => item.id !== excludeId).map((item) => <option key={item.id} value={item.id}>{item.code} — {item.name}</option>)}
    </select>
    {!loading && options.length === 0 && !error && <span className="form-help">No accessible active locations found.</span>}
    {error && <span className="form-error" role="alert">{error}</span>}
  </label>
}
